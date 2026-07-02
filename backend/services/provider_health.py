"""Production-grade market-data provider health, latency tracking, retry/backoff,
quota management, and provider ranking (M9 Phase 1).

Wraps the provider abstraction from services/market_data_provider.py without
modifying it.  Import ``ProviderHealthMonitor`` and use it as a drop-in
replacement for ``MarketDataRouter``.

Usage::

    from services.provider_health import get_health_router

    router = get_health_router()
    quote = router.get_quote("AAPL")
    stats = router.get_all_stats()
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple, TypeVar

from services.market_data_provider import (
    MarketDataProvider,
    MarketDataRouter,
    ProviderError,
    ProviderUnavailable,
    Quote,
    YahooProvider,
    PolygonProvider,
    AlpacaProvider,
    TwelveDataProvider,
    FinnhubProvider,
    AlphaVantageProvider,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Retry / exponential-backoff decorator
# ---------------------------------------------------------------------------

def retry_with_backoff(
    max_attempts: int = 3,
    base_delay_s: float = 0.5,
    max_delay_s: float = 8.0,
    jitter: bool = True,
    retriable_exceptions: Tuple = (ProviderError,),
):
    """Decorate a provider call with exponential-backoff retry.

    Raises the last exception when all attempts are exhausted.
    ``ProviderUnavailable`` is NOT retried — it means no key configured.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except ProviderUnavailable:
                    raise  # skip retries
                except retriable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        delay = min(base_delay_s * (2 ** attempt), max_delay_s)
                        if jitter:
                            import random
                            delay *= 0.5 + random.random() * 0.5
                        logger.debug(
                            "Retry %d/%d for %s after %.2fs: %s",
                            attempt + 1,
                            max_attempts,
                            func.__name__,
                            delay,
                            exc,
                        )
                        time.sleep(delay)
            raise last_exc
        return wrapper  # type: ignore[return-value]
    return decorator


# ---------------------------------------------------------------------------
# Latency tracker (rolling window)
# ---------------------------------------------------------------------------

class LatencyTracker:
    """Tracks call latency and success rate in a rolling window."""

    def __init__(self, window: int = 100) -> None:
        self._latencies: Deque[float] = deque(maxlen=window)
        self._successes: Deque[bool] = deque(maxlen=window)
        self._lock = threading.Lock()

    def record(self, latency_ms: float, success: bool) -> None:
        with self._lock:
            self._latencies.append(latency_ms)
            self._successes.append(success)

    @property
    def avg_latency_ms(self) -> float:
        with self._lock:
            return sum(self._latencies) / len(self._latencies) if self._latencies else 0.0

    @property
    def p95_latency_ms(self) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            sorted_lat = sorted(self._latencies)
            idx = max(0, int(len(sorted_lat) * 0.95) - 1)
            return sorted_lat[idx]

    @property
    def success_rate(self) -> float:
        with self._lock:
            if not self._successes:
                return 1.0
            return sum(self._successes) / len(self._successes)

    @property
    def call_count(self) -> int:
        with self._lock:
            return len(self._latencies)

    def stats(self) -> dict:
        return {
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "success_rate": round(self.success_rate, 4),
            "call_count": self.call_count,
        }


# ---------------------------------------------------------------------------
# Quota tracker
# ---------------------------------------------------------------------------

@dataclass
class QuotaConfig:
    calls_per_minute: int = 500
    calls_per_day: int = 5000


class QuotaTracker:
    """Per-provider API quota enforcement."""

    def __init__(self, config: Optional[QuotaConfig] = None) -> None:
        self._cfg = config or QuotaConfig()
        self._minute_calls: int = 0
        self._day_calls: int = 0
        self._minute_window_start: float = time.time()
        self._day_window_start: float = time.time()
        self._lock = threading.Lock()

    def check_and_consume(self) -> bool:
        """Return True if quota allows this call, consuming one unit."""
        with self._lock:
            now = time.time()
            if now - self._minute_window_start > 60:
                self._minute_calls = 0
                self._minute_window_start = now
            if now - self._day_window_start > 86400:
                self._day_calls = 0
                self._day_window_start = now

            if self._minute_calls >= self._cfg.calls_per_minute:
                return False
            if self._day_calls >= self._cfg.calls_per_day:
                return False

            self._minute_calls += 1
            self._day_calls += 1
            return True

    def stats(self) -> dict:
        with self._lock:
            return {
                "minute_calls": self._minute_calls,
                "day_calls": self._day_calls,
                "minute_limit": self._cfg.calls_per_minute,
                "day_limit": self._cfg.calls_per_day,
                "minute_remaining": max(0, self._cfg.calls_per_minute - self._minute_calls),
                "day_remaining": max(0, self._cfg.calls_per_day - self._day_calls),
            }


# ---------------------------------------------------------------------------
# Health score (EWMA of success rate + latency penalty)
# ---------------------------------------------------------------------------

class HealthScore:
    """Exponential weighted moving average health score in [0, 1].

    Score = ewma_success_rate * latency_weight
    latency_weight = exp(-latency_ms / TARGET_LATENCY_MS) scaled to [0.5, 1]
    """

    TARGET_LATENCY_MS = 200.0
    ALPHA = 0.1  # EWMA smoothing factor

    def __init__(self) -> None:
        self._score: float = 1.0
        self._lock = threading.Lock()

    def update(self, success: bool, latency_ms: float) -> None:
        penalty = max(0.5, math.exp(-latency_ms / self.TARGET_LATENCY_MS))
        raw = (1.0 if success else 0.0) * penalty
        with self._lock:
            self._score = self.ALPHA * raw + (1 - self.ALPHA) * self._score

    @property
    def value(self) -> float:
        with self._lock:
            return round(self._score, 4)

    def __float__(self) -> float:
        return self.value


# ---------------------------------------------------------------------------
# Instrumented provider wrapper
# ---------------------------------------------------------------------------

class InstrumentedProvider:
    """Wraps a MarketDataProvider with health monitoring."""

    def __init__(
        self,
        provider: MarketDataProvider,
        quota: Optional[QuotaConfig] = None,
        max_retries: int = 2,
    ) -> None:
        self.provider = provider
        self.name = provider.name
        self.priority = provider.priority
        self._latency = LatencyTracker()
        self._quota = QuotaTracker(quota)
        self._health = HealthScore()
        self._max_retries = max_retries
        self._error_count: int = 0
        self._total_calls: int = 0
        self._lock = threading.Lock()

    def get_quote(self, ticker: str) -> Quote:
        if not self._quota.check_and_consume():
            raise ProviderError(f"{self.name}: quota exhausted")
        return self._call(self.provider.get_quote, ticker)

    def get_bars(self, ticker: str, *, period: str = "1mo", interval: str = "1d") -> list:
        if not self._quota.check_and_consume():
            raise ProviderError(f"{self.name}: quota exhausted")
        return self._call(self.provider.get_bars, ticker, period=period, interval=interval)

    def _call(self, func: Callable, *args, **kwargs) -> Any:
        attempt = 0
        last_exc: Optional[Exception] = None
        base_delay = 0.3

        while attempt <= self._max_retries:
            t0 = time.monotonic()
            try:
                result = func(*args, **kwargs)
                latency_ms = (time.monotonic() - t0) * 1000
                self._record(True, latency_ms)
                return result
            except ProviderUnavailable:
                raise
            except Exception as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                self._record(False, latency_ms)
                last_exc = exc
                if attempt < self._max_retries:
                    delay = min(base_delay * (2 ** attempt), 4.0)
                    logger.debug("%s retry %d: %s (wait %.2fs)", self.name, attempt + 1, exc, delay)
                    time.sleep(delay)
                attempt += 1

        raise ProviderError(f"{self.name} failed after {attempt} attempts: {last_exc}") from last_exc

    def _record(self, success: bool, latency_ms: float) -> None:
        self._latency.record(latency_ms, success)
        self._health.update(success, latency_ms)
        with self._lock:
            self._total_calls += 1
            if not success:
                self._error_count += 1

    @property
    def health_score(self) -> float:
        return self._health.value

    def stats(self) -> dict:
        with self._lock:
            total = self._total_calls
            errors = self._error_count
        return {
            "name": self.name,
            "priority": self.priority,
            "health_score": self.health_score,
            "latency": self._latency.stats(),
            "quota": self._quota.stats(),
            "total_calls": total,
            "error_count": errors,
            "error_rate": round(errors / total, 4) if total else 0.0,
        }


# ---------------------------------------------------------------------------
# Production router with health-aware failover
# ---------------------------------------------------------------------------

class ProviderHealthRouter:
    """Production market-data router that orders providers by health score,
    measures latency, enforces quotas, and retries with exponential backoff.
    """

    def __init__(
        self,
        providers: Optional[List[MarketDataProvider]] = None,
        cache_ttl_s: int = 30,
        rerank_interval_s: float = 60.0,
    ) -> None:
        base = providers or self._default_providers()
        self._providers: List[InstrumentedProvider] = [
            InstrumentedProvider(p) for p in base
        ]
        self._cache_ttl = cache_ttl_s
        self._quote_cache: Dict[str, Tuple[Quote, float]] = {}
        self._rerank_interval = rerank_interval_s
        self._last_rerank: float = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API (same interface as MarketDataRouter)
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Quote:
        cached = self._quote_cache.get(ticker)
        if cached and time.time() - cached[1] < self._cache_ttl:
            return cached[0]

        last_exc: Optional[Exception] = None
        for p in self._ranked_providers():
            try:
                quote = p.get_quote(ticker)
                with self._lock:
                    self._quote_cache[ticker] = (quote, time.time())
                return quote
            except ProviderUnavailable:
                continue
            except Exception as exc:
                last_exc = exc
                logger.warning("%s failed get_quote(%s): %s", p.name, ticker, exc)
                continue

        raise ProviderError(f"All providers failed for {ticker}: {last_exc}")

    def get_bars(self, ticker: str, *, period: str = "1mo", interval: str = "1d") -> list:
        last_exc: Optional[Exception] = None
        for p in self._ranked_providers():
            try:
                return p.get_bars(ticker, period=period, interval=interval)
            except ProviderUnavailable:
                continue
            except Exception as exc:
                last_exc = exc
                continue
        raise ProviderError(f"All providers failed bars for {ticker}: {last_exc}")

    def get_all_stats(self) -> List[dict]:
        return [p.stats() for p in self._providers]

    def get_provider_stats(self, name: str) -> Optional[dict]:
        for p in self._providers:
            if p.name == name:
                return p.stats()
        return None

    def health_summary(self) -> dict:
        stats = self.get_all_stats()
        ranked = sorted(stats, key=lambda s: s["health_score"], reverse=True)
        return {
            "provider_count": len(self._providers),
            "healthy_count": sum(1 for s in stats if s["health_score"] > 0.8),
            "ranked": ranked,
        }

    def provider_names(self) -> List[str]:
        return [p.name for p in self._providers]

    def invalidate_cache(self, ticker: Optional[str] = None) -> None:
        with self._lock:
            if ticker:
                self._quote_cache.pop(ticker, None)
            else:
                self._quote_cache.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ranked_providers(self) -> List[InstrumentedProvider]:
        now = time.time()
        if now - self._last_rerank > self._rerank_interval:
            with self._lock:
                # Re-sort: primary = health_score desc, secondary = priority asc
                self._providers.sort(
                    key=lambda p: (-p.health_score, p.priority)
                )
                self._last_rerank = now
        return self._providers

    @staticmethod
    def _default_providers() -> List[MarketDataProvider]:
        return [
            YahooProvider(),
            PolygonProvider(),
            AlpacaProvider(),
            TwelveDataProvider(),
            FinnhubProvider(),
            AlphaVantageProvider(),
        ]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_health_router: Optional[ProviderHealthRouter] = None


def get_health_router() -> ProviderHealthRouter:
    global _health_router
    if _health_router is None:
        _health_router = ProviderHealthRouter()
    return _health_router
