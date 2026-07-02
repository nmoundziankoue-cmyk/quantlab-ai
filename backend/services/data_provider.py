"""M13 — Institutional data provider abstraction.

Defines a capability-aware provider registry with automatic failover,
provider ranking, health monitoring, and latency metrics.

All network I/O is isolated to concrete provider ``_fetch_*`` methods,
keeping the router layer and all tests fully deterministic.
"""
from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Capability registry
# ---------------------------------------------------------------------------

class DataCapability(Enum):
    HISTORICAL_OHLCV = auto()
    INTRADAY_OHLCV = auto()
    TICK_DATA = auto()
    QUOTES = auto()
    TRADES = auto()
    DIVIDENDS = auto()
    SPLITS = auto()
    EARNINGS = auto()
    ECONOMIC_RELEASES = auto()
    FUNDAMENTALS = auto()
    OPTIONS_CHAIN = auto()
    NEWS = auto()
    COMPANY_PROFILE = auto()
    INSIDER_TRANSACTIONS = auto()
    ANALYST_ESTIMATES = auto()
    ETF_HOLDINGS = auto()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class OHLCVBar:
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: Optional[float] = None
    vwap: Optional[float] = None


@dataclass
class Quote:
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: pd.Timestamp
    exchange: str = ""


@dataclass
class ProviderConfig:
    name: str
    priority: int                        # lower = higher priority
    capabilities: Set[DataCapability]
    api_key: Optional[str] = None
    base_url: str = ""
    rate_limit_per_min: int = 60
    timeout_seconds: float = 10.0
    enabled: bool = True


@dataclass
class LatencyMetrics:
    provider: str
    samples: List[float] = field(default_factory=list)
    errors: int = 0
    successes: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def record(self, latency_ms: float) -> None:
        with self._lock:
            self.samples.append(latency_ms)
            if len(self.samples) > 100:
                self.samples = self.samples[-100:]
            self.successes += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors += 1

    @property
    def p50_ms(self) -> float:
        with self._lock:
            return float(np.percentile(self.samples, 50)) if self.samples else 0.0

    @property
    def p95_ms(self) -> float:
        with self._lock:
            return float(np.percentile(self.samples, 95)) if self.samples else 0.0

    @property
    def error_rate(self) -> float:
        with self._lock:
            total = self.errors + self.successes
            return self.errors / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "error_rate": round(self.error_rate, 4),
            "total_successes": self.successes,
            "total_errors": self.errors,
        }


@dataclass
class ProviderHealth:
    provider: str
    is_healthy: bool
    last_check: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "is_healthy": self.is_healthy,
            "last_check_ago_s": round(time.time() - self.last_check, 1),
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
        }


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------

class BaseDataProvider(ABC):
    """Abstract base for all market data providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.latency = LatencyMetrics(provider=config.name)
        self.health = ProviderHealth(provider=config.name, is_healthy=True)
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def priority(self) -> int:
        return self.config.priority

    def supports(self, capability: DataCapability) -> bool:
        return capability in self.config.capabilities

    def _timed_call(self, fn, *args, **kwargs) -> Any:
        """Execute fn, recording latency and health."""
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.latency.record(elapsed_ms)
            with self._lock:
                self.health.is_healthy = True
                self.health.consecutive_failures = 0
            return result
        except Exception as exc:
            self.latency.record_error()
            with self._lock:
                self.health.consecutive_failures += 1
                self.health.is_healthy = self.health.consecutive_failures < 3
                self.health.last_error = str(exc)
                self.health.last_check = time.time()
            raise

    def get_historical_ohlcv(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        interval: str = "1d",
    ) -> pd.DataFrame:
        return self._timed_call(self._fetch_ohlcv, symbol, start, end, interval)

    def get_quote(self, symbol: str) -> Quote:
        return self._timed_call(self._fetch_quote, symbol)

    def get_dividends(self, symbol: str) -> pd.DataFrame:
        return self._timed_call(self._fetch_dividends, symbol)

    def get_splits(self, symbol: str) -> pd.DataFrame:
        return self._timed_call(self._fetch_splits, symbol)

    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        return self._timed_call(self._fetch_fundamentals, symbol)

    def get_news(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._timed_call(self._fetch_news, symbol, limit)

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        return self._timed_call(self._fetch_company_profile, symbol)

    # --- Abstract fetch methods (override in concrete providers) ---

    @abstractmethod
    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        ...

    def _fetch_quote(self, symbol: str) -> Quote:
        raise NotImplementedError(f"{self.name} does not support QUOTES")

    def _fetch_dividends(self, symbol: str) -> pd.DataFrame:
        raise NotImplementedError(f"{self.name} does not support DIVIDENDS")

    def _fetch_splits(self, symbol: str) -> pd.DataFrame:
        raise NotImplementedError(f"{self.name} does not support SPLITS")

    def _fetch_fundamentals(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.name} does not support FUNDAMENTALS")

    def _fetch_news(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError(f"{self.name} does not support NEWS")

    def _fetch_company_profile(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.name} does not support COMPANY_PROFILE")


# ---------------------------------------------------------------------------
# Concrete provider stubs — network I/O injected via _http (testable)
# ---------------------------------------------------------------------------

def _empty_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])


class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance via yfinance (no API key required)."""

    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.DIVIDENDS,
        DataCapability.SPLITS,
        DataCapability.FUNDAMENTALS,
        DataCapability.COMPANY_PROFILE,
        DataCapability.OPTIONS_CHAIN,
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        super().__init__(ProviderConfig(
            name="yahoo_finance",
            priority=1,
            capabilities=self.CAPABILITIES,
            rate_limit_per_min=2000,
        ))
        self._yf = None  # lazy import

    def _get_yf(self):
        if self._yf is None:
            import yfinance as yf  # noqa: PLC0415
            self._yf = yf
        return self._yf

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        yf = self._get_yf()
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start.date(), end=end.date(), interval=interval, auto_adjust=True)
        if df.empty:
            return _empty_ohlcv()
        df.index = pd.to_datetime(df.index, utc=True)
        df.columns = [c.lower() for c in df.columns]
        return df[["open", "high", "low", "close", "volume"]].copy()

    def _fetch_dividends(self, symbol: str) -> pd.DataFrame:
        yf = self._get_yf()
        return yf.Ticker(symbol).dividends.to_frame("dividend")

    def _fetch_splits(self, symbol: str) -> pd.DataFrame:
        yf = self._get_yf()
        return yf.Ticker(symbol).splits.to_frame("ratio")

    def _fetch_fundamentals(self, symbol: str) -> Dict[str, Any]:
        yf = self._get_yf()
        return yf.Ticker(symbol).info or {}

    def _fetch_company_profile(self, symbol: str) -> Dict[str, Any]:
        return self._fetch_fundamentals(symbol)


class AlphaVantageProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.FUNDAMENTALS,
        DataCapability.ECONOMIC_RELEASES,
        DataCapability.NEWS,
        DataCapability.ANALYST_ESTIMATES,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="alpha_vantage",
            priority=2,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://www.alphavantage.co/query",
            rate_limit_per_min=5,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("Alpha Vantage requires API key and live HTTP call")


class PolygonProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.TICK_DATA,
        DataCapability.QUOTES,
        DataCapability.TRADES,
        DataCapability.DIVIDENDS,
        DataCapability.SPLITS,
        DataCapability.NEWS,
        DataCapability.COMPANY_PROFILE,
        DataCapability.OPTIONS_CHAIN,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="polygon",
            priority=3,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://api.polygon.io",
            rate_limit_per_min=1000,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("Polygon requires API key and live HTTP call")


class DatabentoProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.TICK_DATA,
        DataCapability.QUOTES,
        DataCapability.TRADES,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="databento",
            priority=4,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://hist.databento.com",
            rate_limit_per_min=500,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("Databento requires API key and live HTTP call")


class AlpacaProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.TICK_DATA,
        DataCapability.QUOTES,
        DataCapability.TRADES,
        DataCapability.NEWS,
    }

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        super().__init__(ProviderConfig(
            name="alpaca",
            priority=5,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://data.alpaca.markets",
            rate_limit_per_min=200,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("Alpaca requires API key and live HTTP call")


class FinnhubProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.QUOTES,
        DataCapability.NEWS,
        DataCapability.FUNDAMENTALS,
        DataCapability.COMPANY_PROFILE,
        DataCapability.INSIDER_TRANSACTIONS,
        DataCapability.ANALYST_ESTIMATES,
        DataCapability.EARNINGS,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="finnhub",
            priority=6,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://finnhub.io/api/v1",
            rate_limit_per_min=60,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("Finnhub requires API key and live HTTP call")


class IEXCloudProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.QUOTES,
        DataCapability.FUNDAMENTALS,
        DataCapability.DIVIDENDS,
        DataCapability.SPLITS,
        DataCapability.NEWS,
        DataCapability.COMPANY_PROFILE,
        DataCapability.EARNINGS,
        DataCapability.ANALYST_ESTIMATES,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="iex_cloud",
            priority=7,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://cloud.iexapis.com/stable",
            rate_limit_per_min=100,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("IEX Cloud requires API key and live HTTP call")


class TwelveDataProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.QUOTES,
        DataCapability.FUNDAMENTALS,
        DataCapability.EARNINGS,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="twelve_data",
            priority=8,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://api.twelvedata.com",
            rate_limit_per_min=800,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("TwelveData requires API key and live HTTP call")


class TiingoProvider(BaseDataProvider):
    CAPABILITIES = {
        DataCapability.HISTORICAL_OHLCV,
        DataCapability.INTRADAY_OHLCV,
        DataCapability.FUNDAMENTALS,
        DataCapability.NEWS,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="tiingo",
            priority=9,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://api.tiingo.com",
            rate_limit_per_min=500,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("Tiingo requires API key and live HTTP call")


class FREDProvider(BaseDataProvider):
    """Federal Reserve Economic Data (FRED)."""

    CAPABILITIES = {
        DataCapability.ECONOMIC_RELEASES,
    }

    def __init__(self, api_key: str = "") -> None:
        super().__init__(ProviderConfig(
            name="fred",
            priority=10,
            capabilities=self.CAPABILITIES,
            api_key=api_key,
            base_url="https://api.stlouisfed.org/fred",
            rate_limit_per_min=120,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("FRED does not support OHLCV")


class SECEdgarProvider(BaseDataProvider):
    """SEC EDGAR filings and fundamentals."""

    CAPABILITIES = {
        DataCapability.FUNDAMENTALS,
        DataCapability.EARNINGS,
        DataCapability.INSIDER_TRANSACTIONS,
    }

    def __init__(self) -> None:
        super().__init__(ProviderConfig(
            name="sec_edgar",
            priority=11,
            capabilities=self.CAPABILITIES,
            base_url="https://data.sec.gov",
            rate_limit_per_min=10,
        ))

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        raise NotImplementedError("SEC EDGAR does not support OHLCV")


# ---------------------------------------------------------------------------
# Mock provider for testing (deterministic, no network)
# ---------------------------------------------------------------------------

class MockDataProvider(BaseDataProvider):
    """Deterministic provider for tests — no network calls."""

    CAPABILITIES = set(DataCapability)

    def __init__(
        self,
        name: str = "mock",
        priority: int = 0,
        fail_after: int = 0,
    ) -> None:
        super().__init__(ProviderConfig(
            name=name,
            priority=priority,
            capabilities=self.CAPABILITIES,
        ))
        self._fail_after = fail_after
        self._call_count = 0

    def _fetch_ohlcv(
        self, symbol: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        self._call_count += 1
        if self._fail_after and self._call_count > self._fail_after:
            raise RuntimeError(f"{self.name}: simulated failure on call {self._call_count}")
        dates = pd.date_range(start, end, freq="B", tz="UTC")
        rng = np.random.default_rng(hash(symbol) % 2**31)
        n = len(dates)
        close = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, n))
        df = pd.DataFrame({
            "open": close * (1 + rng.normal(0, 0.002, n)),
            "high": close * (1 + np.abs(rng.normal(0, 0.005, n))),
            "low": close * (1 - np.abs(rng.normal(0, 0.005, n))),
            "close": close,
            "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
        }, index=dates)
        return df

    def _fetch_quote(self, symbol: str) -> Quote:
        return Quote(
            symbol=symbol,
            bid=99.9,
            ask=100.1,
            bid_size=100.0,
            ask_size=100.0,
            timestamp=pd.Timestamp.now(tz="UTC"),
        )

    def _fetch_dividends(self, symbol: str) -> pd.DataFrame:
        dates = pd.to_datetime(["2023-03-10", "2023-06-10", "2023-09-10", "2023-12-10"])
        return pd.DataFrame({"dividend": [0.25, 0.25, 0.25, 0.25]}, index=dates)

    def _fetch_splits(self, symbol: str) -> pd.DataFrame:
        dates = pd.to_datetime(["2020-08-28"])
        return pd.DataFrame({"ratio": [4.0]}, index=dates)

    def _fetch_fundamentals(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol, "pe_ratio": 25.4, "market_cap": 2.8e12,
            "revenue": 394e9, "eps": 6.11, "debt_to_equity": 1.73,
        }

    def _fetch_news(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        return [{"headline": f"{symbol} News {i}", "source": "mock"} for i in range(min(limit, 5))]

    def _fetch_company_profile(self, symbol: str) -> Dict[str, Any]:
        return {"symbol": symbol, "name": f"{symbol} Corporation", "sector": "Technology"}


# ---------------------------------------------------------------------------
# Provider router with failover
# ---------------------------------------------------------------------------

class DataProviderRouter:
    """Routes data requests across providers with failover and latency ranking.

    Providers are tried in priority order.  If a provider raises, the router
    falls back to the next capable provider and records the failure.
    """

    def __init__(self, providers: Optional[List[BaseDataProvider]] = None) -> None:
        self._providers: List[BaseDataProvider] = sorted(
            providers or [YahooFinanceProvider()],
            key=lambda p: p.priority,
        )
        self._lock = threading.Lock()

    def register(self, provider: BaseDataProvider) -> None:
        with self._lock:
            self._providers.append(provider)
            self._providers.sort(key=lambda p: p.priority)

    def providers_for(self, capability: DataCapability) -> List[BaseDataProvider]:
        with self._lock:
            return [
                p for p in self._providers
                if p.supports(capability) and p.config.enabled and p.health.is_healthy
            ]

    def _call_with_failover(
        self,
        capability: DataCapability,
        method: str,
        *args,
        **kwargs,
    ) -> Any:
        candidates = self.providers_for(capability)
        if not candidates:
            candidates_disabled = [
                p for p in self._providers
                if p.supports(capability) and p.config.enabled
            ]
            if not candidates_disabled:
                raise RuntimeError(f"No provider supports {capability}")
            candidates = candidates_disabled

        last_exc: Optional[Exception] = None
        for provider in candidates:
            try:
                return getattr(provider, method)(*args, **kwargs)
            except Exception as exc:
                logger.warning("Provider %s failed for %s: %s", provider.name, method, exc)
                last_exc = exc
        raise RuntimeError(f"All providers failed for {capability}: {last_exc}") from last_exc

    def get_historical_ohlcv(
        self,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        interval: str = "1d",
    ) -> pd.DataFrame:
        return self._call_with_failover(
            DataCapability.HISTORICAL_OHLCV,
            "get_historical_ohlcv",
            symbol, start, end, interval,
        )

    def get_quote(self, symbol: str) -> Quote:
        return self._call_with_failover(DataCapability.QUOTES, "get_quote", symbol)

    def get_dividends(self, symbol: str) -> pd.DataFrame:
        return self._call_with_failover(DataCapability.DIVIDENDS, "get_dividends", symbol)

    def get_splits(self, symbol: str) -> pd.DataFrame:
        return self._call_with_failover(DataCapability.SPLITS, "get_splits", symbol)

    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        return self._call_with_failover(
            DataCapability.FUNDAMENTALS, "get_fundamentals", symbol
        )

    def get_news(self, symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        return self._call_with_failover(DataCapability.NEWS, "get_news", symbol, limit)

    def health_summary(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.health.to_dict() for p in self._providers]

    def latency_summary(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.latency.to_dict() for p in self._providers]

    def capabilities_matrix(self) -> Dict[str, List[str]]:
        with self._lock:
            return {
                p.name: [c.name for c in p.config.capabilities]
                for p in self._providers
            }


# ---------------------------------------------------------------------------
# Registry of all known provider classes
# ---------------------------------------------------------------------------

ALL_PROVIDER_CLASSES: Dict[str, type] = {
    "yahoo_finance": YahooFinanceProvider,
    "alpha_vantage": AlphaVantageProvider,
    "polygon": PolygonProvider,
    "databento": DatabentoProvider,
    "alpaca": AlpacaProvider,
    "finnhub": FinnhubProvider,
    "iex_cloud": IEXCloudProvider,
    "twelve_data": TwelveDataProvider,
    "tiingo": TiingoProvider,
    "fred": FREDProvider,
    "sec_edgar": SECEdgarProvider,
}


def build_router_from_env() -> DataProviderRouter:
    """Build a router from environment variables (API keys injected at startup)."""
    import os
    providers: List[BaseDataProvider] = [YahooFinanceProvider()]
    key_map = {
        "alpha_vantage": ("ALPHA_VANTAGE_KEY", AlphaVantageProvider),
        "polygon": ("POLYGON_KEY", PolygonProvider),
        "alpaca": ("ALPACA_KEY", AlpacaProvider),
        "finnhub": ("FINNHUB_KEY", FinnhubProvider),
        "tiingo": ("TIINGO_KEY", TiingoProvider),
        "twelve_data": ("TWELVE_DATA_KEY", TwelveDataProvider),
        "fred": ("FRED_KEY", FREDProvider),
    }
    for name, (env_var, cls) in key_map.items():
        key = os.environ.get(env_var, "")
        if key:
            providers.append(cls(api_key=key))  # type: ignore[call-arg]
    providers.append(SECEdgarProvider())
    return DataProviderRouter(providers)


# Singleton — replace with build_router_from_env() in production startup
_default_router: Optional[DataProviderRouter] = None


def get_default_router() -> DataProviderRouter:
    global _default_router
    if _default_router is None:
        _default_router = DataProviderRouter([YahooFinanceProvider()])
    return _default_router
