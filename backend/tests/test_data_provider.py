"""M13 — Tests for services/data_provider.py.

All tests are deterministic.  No network calls — MockDataProvider is used.
"""
from __future__ import annotations

import time
import threading

import numpy as np
import pandas as pd
import pytest

from services.data_provider import (
    ALL_PROVIDER_CLASSES,
    DataCapability,
    DataProviderRouter,
    FREDProvider,
    LatencyMetrics,
    MockDataProvider,
    OHLCVBar,
    PolygonProvider,
    ProviderConfig,
    ProviderHealth,
    Quote,
    SECEdgarProvider,
    YahooFinanceProvider,
    build_router_from_env,
    get_default_router,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _router(n: int = 1, fail_after: int = 0) -> DataProviderRouter:
    providers = [MockDataProvider(name=f"mock_{i}", priority=i, fail_after=fail_after) for i in range(n)]
    return DataProviderRouter(providers)


def _date_range() -> tuple:
    start = pd.Timestamp("2023-01-01", tz="UTC")
    end = pd.Timestamp("2023-03-31", tz="UTC")
    return start, end


# ===========================================================================
# DataCapability enum
# ===========================================================================

def test_all_capabilities_present():
    caps = list(DataCapability)
    assert len(caps) >= 16
    assert DataCapability.HISTORICAL_OHLCV in caps
    assert DataCapability.TICK_DATA in caps
    assert DataCapability.OPTIONS_CHAIN in caps
    assert DataCapability.ECONOMIC_RELEASES in caps


# ===========================================================================
# ProviderConfig
# ===========================================================================

def test_provider_config_defaults():
    cfg = ProviderConfig(
        name="test",
        priority=1,
        capabilities={DataCapability.HISTORICAL_OHLCV},
    )
    assert cfg.enabled is True
    assert cfg.rate_limit_per_min == 60
    assert cfg.timeout_seconds == 10.0
    assert cfg.api_key is None


# ===========================================================================
# LatencyMetrics
# ===========================================================================

def test_latency_record_single():
    lm = LatencyMetrics(provider="test")
    lm.record(50.0)
    assert lm.successes == 1
    assert lm.p50_ms == 50.0


def test_latency_p95_gt_p50():
    lm = LatencyMetrics(provider="test")
    for ms in [10, 15, 12, 8, 200]:
        lm.record(float(ms))
    assert lm.p95_ms >= lm.p50_ms


def test_latency_error_rate():
    lm = LatencyMetrics(provider="test")
    lm.record(10.0)
    lm.record(20.0)
    lm.record_error()
    assert abs(lm.error_rate - 1 / 3) < 0.01


def test_latency_no_samples_returns_zero():
    lm = LatencyMetrics(provider="empty")
    assert lm.p50_ms == 0.0
    assert lm.p95_ms == 0.0
    assert lm.error_rate == 0.0


def test_latency_to_dict_keys():
    lm = LatencyMetrics(provider="x")
    d = lm.to_dict()
    for key in ("provider", "p50_ms", "p95_ms", "error_rate", "total_successes", "total_errors"):
        assert key in d


def test_latency_capped_at_100_samples():
    lm = LatencyMetrics(provider="cap")
    for i in range(150):
        lm.record(float(i))
    assert len(lm.samples) == 100


# ===========================================================================
# ProviderHealth
# ===========================================================================

def test_health_default_healthy():
    ph = ProviderHealth(provider="p", is_healthy=True)
    assert ph.is_healthy
    assert ph.consecutive_failures == 0


def test_health_to_dict():
    ph = ProviderHealth(provider="p", is_healthy=False, last_error="timeout")
    d = ph.to_dict()
    assert d["is_healthy"] is False
    assert d["last_error"] == "timeout"
    assert "last_check_ago_s" in d


# ===========================================================================
# MockDataProvider
# ===========================================================================

def test_mock_provider_ohlcv_returns_df():
    mock = MockDataProvider()
    start, end = _date_range()
    df = mock.get_historical_ohlcv("AAPL", start, end)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "close" in df.columns


def test_mock_provider_ohlcv_positive_prices():
    mock = MockDataProvider()
    start, end = _date_range()
    df = mock.get_historical_ohlcv("AAPL", start, end)
    assert (df["close"] > 0).all()
    assert (df["volume"] > 0).all()


def test_mock_provider_deterministic():
    mock1 = MockDataProvider()
    mock2 = MockDataProvider()
    start, end = _date_range()
    df1 = mock1.get_historical_ohlcv("AAPL", start, end)
    df2 = mock2.get_historical_ohlcv("AAPL", start, end)
    pd.testing.assert_frame_equal(df1, df2)


def test_mock_provider_different_symbols_differ():
    mock = MockDataProvider()
    start, end = _date_range()
    df_aapl = mock.get_historical_ohlcv("AAPL", start, end)
    df_msft = mock.get_historical_ohlcv("MSFT", start, end)
    assert not df_aapl["close"].equals(df_msft["close"])


def test_mock_provider_quote():
    mock = MockDataProvider()
    quote = mock.get_quote("AAPL")
    assert isinstance(quote, Quote)
    assert quote.bid < quote.ask
    assert quote.symbol == "AAPL"


def test_mock_provider_dividends():
    mock = MockDataProvider()
    divs = mock.get_dividends("AAPL")
    assert isinstance(divs, pd.DataFrame)
    assert "dividend" in divs.columns
    assert len(divs) > 0


def test_mock_provider_splits():
    mock = MockDataProvider()
    splits = mock.get_splits("AAPL")
    assert isinstance(splits, pd.DataFrame)
    assert "ratio" in splits.columns


def test_mock_provider_fundamentals():
    mock = MockDataProvider()
    info = mock.get_fundamentals("AAPL")
    assert isinstance(info, dict)
    assert "pe_ratio" in info


def test_mock_provider_news():
    mock = MockDataProvider()
    news = mock.get_news("AAPL", limit=3)
    assert isinstance(news, list)
    assert len(news) == 3


def test_mock_provider_company_profile():
    mock = MockDataProvider()
    profile = mock.get_company_profile("AAPL")
    assert "symbol" in profile
    assert profile["symbol"] == "AAPL"


def test_mock_provider_supports_all_capabilities():
    mock = MockDataProvider()
    for cap in DataCapability:
        assert mock.supports(cap)


def test_mock_provider_latency_recorded_after_call():
    mock = MockDataProvider()
    start, end = _date_range()
    mock.get_historical_ohlcv("AAPL", start, end)
    assert mock.latency.successes == 1


def test_mock_provider_fails_after_n():
    mock = MockDataProvider(fail_after=2)
    start, end = _date_range()
    mock.get_historical_ohlcv("AAPL", start, end)
    mock.get_historical_ohlcv("AAPL", start, end)
    with pytest.raises(RuntimeError):
        mock.get_historical_ohlcv("AAPL", start, end)


# ===========================================================================
# DataProviderRouter — basic
# ===========================================================================

def test_router_single_provider():
    router = _router(1)
    start, end = _date_range()
    df = router.get_historical_ohlcv("AAPL", start, end)
    assert not df.empty


def test_router_returns_dataframe():
    router = _router()
    start, end = _date_range()
    result = router.get_historical_ohlcv("AAPL", start, end)
    assert isinstance(result, pd.DataFrame)


def test_router_health_summary():
    router = _router(2)
    health = router.health_summary()
    assert len(health) == 2
    assert all("provider" in h for h in health)


def test_router_latency_summary():
    router = _router(2)
    start, end = _date_range()
    router.get_historical_ohlcv("AAPL", start, end)
    lat = router.latency_summary()
    assert len(lat) == 2


def test_router_capabilities_matrix():
    router = _router(2)
    caps = router.capabilities_matrix()
    assert len(caps) == 2
    for name, cap_list in caps.items():
        assert isinstance(cap_list, list)


def test_router_providers_for_filters_by_capability():
    mock = MockDataProvider()
    fred = FREDProvider()
    router = DataProviderRouter([mock, fred])
    providers = router.providers_for(DataCapability.TICK_DATA)
    names = [p.name for p in providers]
    assert "mock" in names
    assert "fred" not in names


def test_router_quote():
    router = _router()
    quote = router.get_quote("AAPL")
    assert isinstance(quote, Quote)


# ===========================================================================
# DataProviderRouter — failover
# ===========================================================================

def test_failover_to_second_provider():
    failing = MockDataProvider(name="primary", priority=0, fail_after=0)
    working = MockDataProvider(name="backup", priority=1)
    # Mark the failing provider as already unhealthy so router skips it
    failing.health.is_healthy = False
    router = DataProviderRouter([failing, working])
    start, end = _date_range()
    df = router.get_historical_ohlcv("AAPL", start, end)
    assert not df.empty


def test_all_providers_fail_raises():
    # FRED and SEC Edgar do not support HISTORICAL_OHLCV — router must raise
    from services.data_provider import FREDProvider, SECEdgarProvider
    router = DataProviderRouter([FREDProvider(), SECEdgarProvider()])
    with pytest.raises(RuntimeError):
        router.get_historical_ohlcv("AAPL", *_date_range())


def test_router_register_adds_provider():
    router = _router(1)
    new_mock = MockDataProvider(name="new_mock", priority=99)
    router.register(new_mock)
    caps = router.capabilities_matrix()
    assert "new_mock" in caps


# ===========================================================================
# Concrete provider stubs
# ===========================================================================

def test_yahoo_finance_provider_config():
    p = YahooFinanceProvider()
    assert p.name == "yahoo_finance"
    assert p.priority == 1
    assert DataCapability.HISTORICAL_OHLCV in p.config.capabilities


def test_polygon_provider_config():
    p = PolygonProvider(api_key="test_key")
    assert p.name == "polygon"
    assert DataCapability.TICK_DATA in p.config.capabilities


def test_fred_provider_config():
    p = FREDProvider(api_key="key")
    assert DataCapability.ECONOMIC_RELEASES in p.config.capabilities
    assert DataCapability.HISTORICAL_OHLCV not in p.config.capabilities


def test_sec_edgar_config():
    p = SECEdgarProvider()
    assert DataCapability.FUNDAMENTALS in p.config.capabilities
    assert DataCapability.TICK_DATA not in p.config.capabilities


def test_all_provider_classes_registry():
    assert len(ALL_PROVIDER_CLASSES) == 11
    assert "yahoo_finance" in ALL_PROVIDER_CLASSES
    assert "sec_edgar" in ALL_PROVIDER_CLASSES


def test_build_router_from_env_returns_router():
    router = build_router_from_env()
    assert isinstance(router, DataProviderRouter)
    assert len(router.capabilities_matrix()) >= 1


def test_get_default_router_singleton():
    r1 = get_default_router()
    r2 = get_default_router()
    assert r1 is r2


# ===========================================================================
# Thread safety
# ===========================================================================

def test_router_thread_safe_concurrent_calls():
    router = _router(2)
    start, end = _date_range()
    results = []
    errors = []

    def call():
        try:
            df = router.get_historical_ohlcv("AAPL", start, end)
            results.append(len(df))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=call) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert all(r > 0 for r in results)
