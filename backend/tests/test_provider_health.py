"""Tests for M9 Phase 1 — provider health, latency, quota, retry."""
import math
import threading
import time
import pytest
from unittest.mock import MagicMock, patch

from services.provider_health import (
    LatencyTracker, QuotaConfig, QuotaTracker, HealthScore,
    InstrumentedProvider, ProviderHealthRouter, get_health_router,
    retry_with_backoff,
)
from services.market_data_provider import (
    ProviderError, ProviderUnavailable, YahooProvider, Quote,
)


# ---------------------------------------------------------------------------
# LatencyTracker
# ---------------------------------------------------------------------------

class TestLatencyTracker:
    def test_empty(self):
        t = LatencyTracker()
        assert t.avg_latency_ms == 0.0
        assert t.p95_latency_ms == 0.0
        assert t.success_rate == 1.0
        assert t.call_count == 0

    def test_single_record(self):
        t = LatencyTracker()
        t.record(50.0, True)
        assert t.avg_latency_ms == 50.0
        assert t.success_rate == 1.0
        assert t.call_count == 1

    def test_failure_reduces_success_rate(self):
        t = LatencyTracker()
        t.record(20.0, True)
        t.record(30.0, False)
        assert t.success_rate == 0.5

    def test_p95_single(self):
        t = LatencyTracker()
        for v in [10, 20, 30, 40, 100]:
            t.record(v, True)
        assert t.p95_latency_ms >= 40

    def test_rolling_window(self):
        t = LatencyTracker(window=3)
        for v in [100, 200, 300, 400]:
            t.record(v, True)
        assert t.call_count == 3
        assert t.avg_latency_ms == pytest.approx(300.0)

    def test_stats_dict(self):
        t = LatencyTracker()
        t.record(80.0, True)
        s = t.stats()
        assert "avg_latency_ms" in s
        assert "success_rate" in s
        assert "call_count" in s

    def test_thread_safety(self):
        t = LatencyTracker()
        def worker():
            for _ in range(50):
                t.record(10.0, True)
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert t.call_count == 100  # maxlen capped at 100 default


# ---------------------------------------------------------------------------
# QuotaTracker
# ---------------------------------------------------------------------------

class TestQuotaTracker:
    def test_allows_within_limit(self):
        q = QuotaTracker(QuotaConfig(calls_per_minute=10, calls_per_day=100))
        for _ in range(10):
            assert q.check_and_consume()

    def test_blocks_above_minute_limit(self):
        q = QuotaTracker(QuotaConfig(calls_per_minute=2, calls_per_day=100))
        assert q.check_and_consume()
        assert q.check_and_consume()
        assert not q.check_and_consume()

    def test_blocks_above_day_limit(self):
        q = QuotaTracker(QuotaConfig(calls_per_minute=1000, calls_per_day=2))
        assert q.check_and_consume()
        assert q.check_and_consume()
        assert not q.check_and_consume()

    def test_stats(self):
        q = QuotaTracker()
        q.check_and_consume()
        s = q.stats()
        assert s["minute_calls"] == 1
        assert s["day_calls"] == 1
        assert "minute_remaining" in s


# ---------------------------------------------------------------------------
# HealthScore
# ---------------------------------------------------------------------------

class TestHealthScore:
    def test_initial_score_is_one(self):
        h = HealthScore()
        assert h.value == pytest.approx(1.0, abs=0.01)

    def test_failure_reduces_score(self):
        h = HealthScore()
        for _ in range(20):
            h.update(False, 500.0)
        assert h.value < 0.5

    def test_success_maintains_score(self):
        h = HealthScore()
        for _ in range(10):
            h.update(True, 50.0)
        assert h.value > 0.8

    def test_high_latency_penalizes(self):
        h1 = HealthScore()
        h2 = HealthScore()
        h1.update(True, 10.0)
        h2.update(True, 2000.0)
        assert h1.value > h2.value

    def test_float_cast(self):
        h = HealthScore()
        assert isinstance(float(h), float)


# ---------------------------------------------------------------------------
# InstrumentedProvider
# ---------------------------------------------------------------------------

class TestInstrumentedProvider:
    def _make_provider(self, fail=False):
        mock = MagicMock()
        mock.name = "test_prov"
        mock.priority = 1
        if fail:
            mock.get_quote.side_effect = ProviderError("boom")
        else:
            mock.get_quote.return_value = Quote(ticker="AAPL", price=150.0, change=1.0, change_pct=0.7,
                                                 volume=1000, provider="test")
        mock.get_bars.return_value = []
        return InstrumentedProvider(mock)

    def test_successful_call_records_metrics(self):
        p = self._make_provider(fail=False)
        q = p.get_quote("AAPL")
        assert q.price == 150.0
        assert p._latency.call_count == 1
        assert p._total_calls == 1
        assert p._error_count == 0

    def test_failed_call_records_error(self):
        p = self._make_provider(fail=True)
        with pytest.raises(ProviderError):
            p.get_quote("AAPL")
        assert p._error_count > 0

    def test_quota_exhaustion_raises(self):
        mock = MagicMock()
        mock.name = "t"
        mock.priority = 1
        p = InstrumentedProvider(mock, quota=QuotaConfig(calls_per_minute=0, calls_per_day=0))
        with pytest.raises(ProviderError, match="quota"):
            p.get_quote("AAPL")

    def test_stats_structure(self):
        p = self._make_provider()
        p.get_quote("AAPL")
        s = p.stats()
        assert "health_score" in s
        assert "latency" in s
        assert "quota" in s
        assert "total_calls" in s

    def test_unavailable_not_retried(self):
        mock = MagicMock()
        mock.name = "t"
        mock.priority = 1
        mock.get_quote.side_effect = ProviderUnavailable("no key")
        p = InstrumentedProvider(mock, max_retries=2)
        with pytest.raises(ProviderUnavailable):
            p.get_quote("AAPL")
        assert mock.get_quote.call_count == 1  # no retries


# ---------------------------------------------------------------------------
# ProviderHealthRouter
# ---------------------------------------------------------------------------

class TestProviderHealthRouter:
    def _make_router(self, fail_all=False):
        mock = MagicMock()
        mock.name = "yahoo"
        mock.priority = 1
        if fail_all:
            mock.get_quote.side_effect = ProviderError("down")
        else:
            mock.get_quote.return_value = Quote(ticker="AAPL", price=180.0, change=0, change_pct=0,
                                                  volume=1000, provider="yahoo")
        mock.get_bars.return_value = [{"time": "2024-01-01", "close": 180.0}]
        return ProviderHealthRouter(providers=[mock])

    def test_get_quote_success(self):
        r = self._make_router()
        q = r.get_quote("AAPL")
        assert q.price == 180.0

    def test_caching(self):
        r = self._make_router()
        r.get_quote("AAPL")
        r.get_quote("AAPL")  # should hit cache
        # provider called only once
        r._providers[0].provider.get_quote.call_count == 1

    def test_all_fail_raises(self):
        r = self._make_router(fail_all=True)
        with pytest.raises(ProviderError):
            r.get_quote("AAPL")

    def test_get_all_stats(self):
        r = self._make_router()
        r.get_quote("AAPL")
        stats = r.get_all_stats()
        assert len(stats) == 1
        assert "health_score" in stats[0]

    def test_health_summary(self):
        r = self._make_router()
        summary = r.health_summary()
        assert "provider_count" in summary
        assert "healthy_count" in summary

    def test_invalidate_cache(self):
        r = self._make_router()
        r.get_quote("AAPL")
        assert "AAPL" in r._quote_cache
        r.invalidate_cache("AAPL")
        assert "AAPL" not in r._quote_cache

    def test_invalidate_all(self):
        r = self._make_router()
        r.get_quote("AAPL")
        r.invalidate_cache()
        assert len(r._quote_cache) == 0

    def test_provider_names(self):
        r = self._make_router()
        names = r.provider_names()
        assert "yahoo" in names

    def test_singleton(self):
        r1 = get_health_router()
        r2 = get_health_router()
        assert r1 is r2


# ---------------------------------------------------------------------------
# retry_with_backoff decorator
# ---------------------------------------------------------------------------

class TestRetryWithBackoff:
    def test_succeeds_on_first(self):
        calls = []
        @retry_with_backoff(max_attempts=3, base_delay_s=0)
        def fn():
            calls.append(1)
            return "ok"
        assert fn() == "ok"
        assert len(calls) == 1

    def test_retries_on_error(self):
        calls = []
        @retry_with_backoff(max_attempts=3, base_delay_s=0, jitter=False)
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ProviderError("fail")
            return "ok"
        assert fn() == "ok"
        assert len(calls) == 3

    def test_raises_after_max_attempts(self):
        @retry_with_backoff(max_attempts=2, base_delay_s=0, jitter=False)
        def fn():
            raise ProviderError("always fails")
        with pytest.raises(ProviderError):
            fn()

    def test_unavailable_not_retried(self):
        calls = []
        @retry_with_backoff(max_attempts=3, base_delay_s=0)
        def fn():
            calls.append(1)
            raise ProviderUnavailable("no key")
        with pytest.raises(ProviderUnavailable):
            fn()
        assert len(calls) == 1
