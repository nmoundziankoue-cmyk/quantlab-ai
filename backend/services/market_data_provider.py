"""Market data provider abstraction with failover and circuit breaker (M8/M10).

Usage::

    from services.market_data_provider import get_router

    router = get_router()
    quote = router.get_quote("AAPL")
    bars = router.get_bars("AAPL", period="1mo")
    cb_states = router.circuit_breaker_states()
"""
from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class _CBState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker (closed → open → half_open → closed).

    CLOSED: normal operation.
    OPEN:   provider tripped; requests blocked for COOLDOWN_SECONDS.
    HALF_OPEN: cooldown elapsed; one probe request allowed.
    """

    FAILURE_THRESHOLD: int = 3
    COOLDOWN_SECONDS: float = 30.0

    def __init__(self) -> None:
        self._state = _CBState.CLOSED
        self._failures = 0
        self._opened_at: float = 0.0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            if self._state == _CBState.CLOSED:
                return True
            if self._state == _CBState.OPEN:
                if time.time() - self._opened_at >= self.COOLDOWN_SECONDS:
                    self._state = _CBState.HALF_OPEN
                    return True
                return False
            return True  # HALF_OPEN — allow one probe

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = _CBState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._state == _CBState.HALF_OPEN or self._failures >= self.FAILURE_THRESHOLD:
                self._state = _CBState.OPEN
                self._opened_at = time.time()

    def state_dict(self) -> dict:
        with self._lock:
            return {
                "state": self._state,
                "failures": self._failures,
                "opened_at": self._opened_at if self._state != _CBState.CLOSED else None,
            }


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProviderError(RuntimeError):
    """Generic provider error."""


class ProviderUnavailable(ProviderError):
    """Provider not configured / external service unreachable."""


class RateLimitError(ProviderError):
    """Provider rate limit hit."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class Quote:
    """Normalised real-time quote."""

    __slots__ = ("ticker", "price", "change", "change_pct", "volume", "timestamp", "provider")

    def __init__(
        self,
        ticker: str,
        price: float,
        change: float = 0.0,
        change_pct: float = 0.0,
        volume: int = 0,
        timestamp: Optional[float] = None,
        provider: str = "unknown",
    ) -> None:
        self.ticker = ticker
        self.price = price
        self.change = change
        self.change_pct = change_pct
        self.volume = volume
        self.timestamp = timestamp or time.time()
        self.provider = provider

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "change": self.change,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "timestamp": self.timestamp,
            "provider": self.provider,
        }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class MarketDataProvider(ABC):
    """Abstract market data provider interface."""

    name: str = "base"
    priority: int = 99  # Lower = higher priority

    @abstractmethod
    def get_quote(self, ticker: str) -> Quote:
        ...

    @abstractmethod
    def get_bars(self, ticker: str, *, period: str = "1mo", interval: str = "1d") -> List[Dict]:
        ...

    def health_check(self) -> bool:
        try:
            self.get_quote("AAPL")
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Yahoo Finance provider (real implementation via yfinance)
# ---------------------------------------------------------------------------


class YahooProvider(MarketDataProvider):
    name = "yahoo"
    priority = 1

    def get_quote(self, ticker: str) -> Quote:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.fast_info
            price = float(getattr(info, "last_price", 0) or 0)
            prev_close = float(getattr(info, "previous_close", price) or price)
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0.0
            volume = int(getattr(info, "three_month_average_volume", 0) or 0)
            return Quote(
                ticker=ticker.upper(),
                price=price,
                change=change,
                change_pct=change_pct,
                volume=volume,
                provider=self.name,
            )
        except Exception as exc:
            raise ProviderError(f"Yahoo quote failed for {ticker}: {exc}") from exc

    def get_bars(self, ticker: str, *, period: str = "1mo", interval: str = "1d") -> List[Dict]:
        try:
            import yfinance as yf
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
            if df.empty:
                return []
            bars = []
            for ts, row in df.iterrows():
                bars.append(
                    {
                        "time": int(ts.timestamp()),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row.get("Volume", 0)),
                    }
                )
            return bars
        except Exception as exc:
            raise ProviderError(f"Yahoo bars failed for {ticker}: {exc}") from exc


# ---------------------------------------------------------------------------
# Stub providers — raise ProviderUnavailable unless configured
# ---------------------------------------------------------------------------


class _StubProvider(MarketDataProvider):
    """Base for stub providers that require external API keys."""

    _required_env: str = ""

    def _check_configured(self) -> None:
        import os
        key = os.getenv(self._required_env, "")
        if not key:
            raise ProviderUnavailable(
                f"{self.name} provider not configured (missing env {self._required_env})"
            )

    def get_quote(self, ticker: str) -> Quote:
        self._check_configured()
        raise NotImplementedError(f"{self.name} get_quote not yet implemented")

    def get_bars(self, ticker: str, *, period: str = "1mo", interval: str = "1d") -> List[Dict]:
        self._check_configured()
        raise NotImplementedError(f"{self.name} get_bars not yet implemented")


class PolygonProvider(_StubProvider):
    name = "polygon"
    priority = 2
    _required_env = "POLYGON_API_KEY"


class AlpacaProvider(_StubProvider):
    name = "alpaca"
    priority = 3
    _required_env = "ALPACA_API_KEY"


class TwelveDataProvider(_StubProvider):
    name = "twelvedata"
    priority = 4
    _required_env = "TWELVEDATA_API_KEY"


class FinnhubProvider(_StubProvider):
    name = "finnhub"
    priority = 5
    _required_env = "FINNHUB_API_KEY"


class AlphaVantageProvider(_StubProvider):
    name = "alphavantage"
    priority = 6
    _required_env = "ALPHAVANTAGE_API_KEY"


# ---------------------------------------------------------------------------
# Router with failover
# ---------------------------------------------------------------------------


class MarketDataRouter:
    """Routes market data requests across providers with priority failover and circuit breakers.

    Providers are tried in ascending priority order. On error, the next
    provider is attempted. A per-provider circuit breaker trips after
    ``CircuitBreaker.FAILURE_THRESHOLD`` consecutive failures and reopens
    after ``CircuitBreaker.COOLDOWN_SECONDS``.

    Quote results are cached via ``CacheBackend`` (Redis → in-memory fallback).
    """

    def __init__(
        self,
        providers: Optional[List[MarketDataProvider]] = None,
        cache_ttl_s: int = 30,
    ) -> None:
        self._providers: List[MarketDataProvider] = sorted(
            providers or self._default_providers(), key=lambda p: p.priority
        )
        self._cache_ttl = cache_ttl_s
        self._breakers: Dict[str, CircuitBreaker] = {
            p.name: CircuitBreaker() for p in self._providers
        }

    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Quote:
        from services.cache import cache
        ns_key = f"mdrouter:quote:{ticker}"
        cached = cache.ns_get(ns_key)
        if cached:
            return Quote(**cached)

        last_error: Optional[Exception] = None
        for provider in self._providers:
            cb = self._breakers[provider.name]
            if not cb.allow_request():
                continue
            try:
                quote = provider.get_quote(ticker)
                cb.record_success()
                cache.ns_set(ns_key, quote.to_dict(), ttl=self._cache_ttl)
                return quote
            except (ProviderUnavailable, NotImplementedError):
                continue  # skip unconfigured providers silently
            except ProviderError as exc:
                cb.record_failure()
                last_error = exc
                logger.warning("Provider %s failed for %s: %s", provider.name, ticker, exc)
                continue
            except Exception as exc:
                cb.record_failure()
                last_error = exc
                logger.warning("Unexpected error from %s for %s: %s", provider.name, ticker, exc)
                continue

        raise ProviderError(
            f"All providers failed for {ticker}. Last error: {last_error}"
        )

    def get_bars(self, ticker: str, *, period: str = "1mo", interval: str = "1d") -> List[Dict]:
        last_error: Optional[Exception] = None
        for provider in self._providers:
            cb = self._breakers[provider.name]
            if not cb.allow_request():
                continue
            try:
                bars = provider.get_bars(ticker, period=period, interval=interval)
                cb.record_success()
                return bars
            except (ProviderUnavailable, NotImplementedError):
                continue
            except (ProviderError, Exception) as exc:
                cb.record_failure()
                last_error = exc
                logger.warning("Provider %s bars failed for %s: %s", provider.name, ticker, exc)
                continue
        raise ProviderError(f"All providers failed for {ticker} bars. Last error: {last_error}")

    def health(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for p in self._providers:
            try:
                results[p.name] = p.health_check()
            except Exception:
                results[p.name] = False
        return results

    def circuit_breaker_states(self) -> Dict[str, dict]:
        """Return circuit breaker state for every provider."""
        return {name: cb.state_dict() for name, cb in self._breakers.items()}

    def provider_names(self) -> List[str]:
        return [p.name for p in self._providers]

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

_router: Optional[MarketDataRouter] = None


def get_router() -> MarketDataRouter:
    global _router
    if _router is None:
        _router = MarketDataRouter()
    return _router
