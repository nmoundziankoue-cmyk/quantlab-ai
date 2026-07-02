"""Tests for services/market_data_provider.py (M8)."""
from __future__ import annotations

import pytest

from services.market_data_provider import (
    AlpacaProvider,
    AlphaVantageProvider,
    FinnhubProvider,
    MarketDataRouter,
    PolygonProvider,
    ProviderError,
    ProviderUnavailable,
    Quote,
    TwelveDataProvider,
    YahooProvider,
    get_router,
)


# ==========================================================================
# Quote dataclass
# ==========================================================================


class TestQuote:
    def test_quote_creation(self):
        q = Quote(ticker="AAPL", price=150.0)
        assert q.ticker == "AAPL"
        assert q.price == 150.0

    def test_quote_to_dict(self):
        q = Quote(ticker="MSFT", price=300.0, change=2.5, change_pct=0.84, volume=1000)
        d = q.to_dict()
        assert d["ticker"] == "MSFT"
        assert d["price"] == 300.0
        assert "change" in d
        assert "provider" in d
        assert "timestamp" in d

    def test_quote_default_provider(self):
        q = Quote(ticker="GOOG", price=100.0)
        assert q.provider == "unknown"

    def test_quote_with_provider(self):
        q = Quote(ticker="GOOG", price=100.0, provider="yahoo")
        assert q.provider == "yahoo"


# ==========================================================================
# Stub providers
# ==========================================================================


class TestStubProviders:
    """Stub providers raise ProviderUnavailable when no API key is configured."""

    def _test_stub(self, provider_cls):
        p = provider_cls()
        with pytest.raises(ProviderUnavailable):
            p.get_quote("AAPL")
        with pytest.raises(ProviderUnavailable):
            p.get_bars("AAPL")

    def test_polygon_stub(self):
        self._test_stub(PolygonProvider)

    def test_alpaca_stub(self):
        self._test_stub(AlpacaProvider)

    def test_twelvedata_stub(self):
        self._test_stub(TwelveDataProvider)

    def test_finnhub_stub(self):
        self._test_stub(FinnhubProvider)

    def test_alphavantage_stub(self):
        self._test_stub(AlphaVantageProvider)

    def test_stub_priorities_ordered(self):
        providers = [PolygonProvider(), AlpacaProvider(), TwelveDataProvider()]
        priorities = [p.priority for p in providers]
        assert priorities == sorted(priorities)


# ==========================================================================
# Yahoo provider (live — may require network)
# ==========================================================================


class TestYahooProvider:
    def test_provider_name(self):
        assert YahooProvider.name == "yahoo"

    def test_provider_priority_is_lowest(self):
        yahoo = YahooProvider()
        stubs = [PolygonProvider(), AlpacaProvider()]
        assert all(yahoo.priority <= s.priority for s in stubs)

    def test_get_quote_structure(self):
        yahoo = YahooProvider()
        try:
            q = yahoo.get_quote("AAPL")
            assert q.ticker == "AAPL"
            assert isinstance(q.price, float)
            assert q.price > 0
            assert q.provider == "yahoo"
        except ProviderError:
            pytest.skip("Yahoo Finance unavailable in test environment")

    def test_get_bars_structure(self):
        yahoo = YahooProvider()
        try:
            bars = yahoo.get_bars("AAPL", period="5d", interval="1d")
            assert isinstance(bars, list)
            if bars:
                assert "time" in bars[0]
                assert "open" in bars[0]
                assert "close" in bars[0]
        except ProviderError:
            pytest.skip("Yahoo Finance unavailable in test environment")


# ==========================================================================
# MarketDataRouter
# ==========================================================================


class TestMarketDataRouter:
    def test_router_has_providers(self):
        router = MarketDataRouter()
        assert len(router.provider_names()) > 0

    def test_yahoo_is_first_provider(self):
        router = MarketDataRouter()
        assert router.provider_names()[0] == "yahoo"

    def test_get_quote_live(self):
        router = MarketDataRouter()
        try:
            q = router.get_quote("AAPL")
            assert isinstance(q, Quote)
            assert q.price > 0
        except ProviderError:
            pytest.skip("No provider available in test environment")

    def test_get_quote_caches_result(self):
        router = MarketDataRouter(cache_ttl_s=60)
        try:
            q1 = router.get_quote("MSFT")
            q2 = router.get_quote("MSFT")
            assert q1.timestamp == q2.timestamp  # same cached object
        except ProviderError:
            pytest.skip("No provider available in test environment")

    def test_all_stubs_fail_raises_provider_error(self):
        # Clear any cached entry so we actually hit the (stub) providers
        from services.cache import cache
        cache.ns_delete("mdrouter:quote:AAPL")
        router = MarketDataRouter(providers=[PolygonProvider(), AlpacaProvider()])
        with pytest.raises(ProviderError):
            router.get_quote("AAPL")

    def test_health_returns_dict(self):
        router = MarketDataRouter(providers=[PolygonProvider()])
        health = router.health()
        assert isinstance(health, dict)
        assert "polygon" in health

    def test_custom_providers_respected(self):
        class MockProvider:
            name = "mock"
            priority = 0

            def get_quote(self, ticker):
                return Quote(ticker=ticker, price=42.0, provider="mock")

            def get_bars(self, ticker, **_):
                return []

            def health_check(self):
                return True

        router = MarketDataRouter(providers=[MockProvider()])
        q = router.get_quote("TEST")
        assert q.price == 42.0
        assert q.provider == "mock"

    def test_module_singleton(self):
        r = get_router()
        assert r is not None
        assert isinstance(r, MarketDataRouter)

    def test_singleton_is_cached(self):
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2
