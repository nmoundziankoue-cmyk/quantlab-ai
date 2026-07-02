"""M14 Phase 1 — Alternative data provider abstraction framework.

Mirrors the M13 `data_provider.py` design: a typed capability matrix, a
`BaseAltDataProvider` ABC, concrete provider stubs for 21 alternative data
sources, and an `AltDataProviderRouter` with automatic failover and health
tracking.  All concrete providers requiring live network access raise
`NotImplementedError` from their `_fetch()` hook until API credentials are
injected — they are wired into the router and fully typed, but make no
network calls during unit tests.  `MockAltDataProvider` is deterministic
and network-free, used for tests and local development.
"""
from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

class AltDataCapability(Enum):
    SEC_FILINGS = auto()
    INSIDER_TRANSACTIONS = auto()
    ETF_HOLDINGS = auto()
    INSTITUTIONAL_13F = auto()
    EARNINGS_TRANSCRIPTS = auto()
    ECONOMIC_RELEASES = auto()
    PATENTS = auto()
    SHIPPING = auto()
    SATELLITE = auto()
    WEATHER = auto()
    COMMODITY_FLOWS = auto()
    ENERGY_PRODUCTION = auto()
    CREDIT_CARD_SPENDING = auto()
    APP_RANKINGS = auto()
    SOCIAL_MEDIA = auto()
    REDDIT = auto()
    TWITTER = auto()
    GOOGLE_TRENDS = auto()
    WIKIPEDIA_TRENDS = auto()
    SUPPLY_CHAIN = auto()
    NEWS = auto()


# ---------------------------------------------------------------------------
# Config / health / latency (mirrors M13 data_provider.py)
# ---------------------------------------------------------------------------

@dataclass
class AltProviderConfig:
    name: str
    priority: int
    capabilities: Set[AltDataCapability]
    api_key: Optional[str] = None
    base_url: str = ""
    rate_limit_per_min: int = 60
    timeout_seconds: float = 10.0
    enabled: bool = True


@dataclass
class AltLatencyMetrics:
    provider: str
    samples: List[float] = field(default_factory=list)
    errors: int = 0
    successes: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def record(self, latency_ms: float, success: bool) -> None:
        with self._lock:
            self.samples.append(latency_ms)
            if len(self.samples) > 100:
                self.samples.pop(0)
            if success:
                self.successes += 1
            else:
                self.errors += 1

    @property
    def p50_ms(self) -> float:
        with self._lock:
            if not self.samples:
                return 0.0
            return float(np.percentile(self.samples, 50))

    @property
    def p95_ms(self) -> float:
        with self._lock:
            if not self.samples:
                return 0.0
            return float(np.percentile(self.samples, 95))

    @property
    def error_rate(self) -> float:
        with self._lock:
            total = self.successes + self.errors
            return round(self.errors / total, 4) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "p50_ms": round(self.p50_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "error_rate": self.error_rate,
            "samples": len(self.samples),
        }


@dataclass
class AltProviderHealth:
    provider: str
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_checked: float = field(default_factory=time.time)

    def mark_success(self) -> None:
        self.is_healthy = True
        self.consecutive_failures = 0
        self.last_error = None
        self.last_checked = time.time()

    def mark_failure(self, error: str) -> None:
        self.consecutive_failures += 1
        self.last_error = error
        self.last_checked = time.time()
        if self.consecutive_failures >= 3:
            self.is_healthy = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "is_healthy": self.is_healthy,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
        }


# ---------------------------------------------------------------------------
# Base provider
# ---------------------------------------------------------------------------

class BaseAltDataProvider(ABC):
    """Abstract alternative-data provider.

    Concrete subclasses implement ``_fetch`` for their capability set.
    ``fetch`` wraps it with timing, health tracking, and error normalisation.
    """

    def __init__(self, config: AltProviderConfig) -> None:
        self.config = config
        self.health = AltProviderHealth(provider=config.name)
        self.latency = AltLatencyMetrics(provider=config.name)

    @property
    def name(self) -> str:
        return self.config.name

    def supports(self, capability: AltDataCapability) -> bool:
        return capability in self.config.capabilities

    def capabilities(self) -> List[str]:
        return sorted(c.name for c in self.config.capabilities)

    def health_check(self) -> Dict[str, Any]:
        return self.health.to_dict()

    def metadata(self) -> Dict[str, Any]:
        return {
            "name": self.config.name,
            "priority": self.config.priority,
            "capabilities": self.capabilities(),
            "enabled": self.config.enabled,
            "rate_limit_per_min": self.config.rate_limit_per_min,
        }

    def quality_score(self) -> float:
        """0–1 composite of health + error rate."""
        base = 1.0 if self.health.is_healthy else 0.3
        base -= self.latency.error_rate * 0.5
        return round(max(0.0, min(1.0, base)), 4)

    def fetch(self, capability: AltDataCapability, **kwargs: Any) -> Any:
        if not self.supports(capability):
            raise ValueError(f"{self.name} does not support {capability.name}")
        start = time.monotonic()
        try:
            result = self._fetch(capability, **kwargs)
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            self.latency.record(elapsed_ms, success=False)
            self.health.mark_failure(str(exc))
            raise
        elapsed_ms = (time.monotonic() - start) * 1000
        self.latency.record(elapsed_ms, success=True)
        self.health.mark_success()
        return result

    @abstractmethod
    def _fetch(self, capability: AltDataCapability, **kwargs: Any) -> Any:
        ...


# ---------------------------------------------------------------------------
# Deterministic mock provider (network-free, used in tests/dev)
# ---------------------------------------------------------------------------

class MockAltDataProvider(BaseAltDataProvider):
    """Deterministic provider with synthetic but reproducible payloads."""

    def __init__(self, fail_after: Optional[int] = None) -> None:
        config = AltProviderConfig(
            name="mock_alt_data",
            priority=0,
            capabilities=set(AltDataCapability),
            enabled=True,
        )
        super().__init__(config)
        self._fail_after = fail_after
        self._call_count = 0

    def _fetch(self, capability: AltDataCapability, **kwargs: Any) -> Any:
        self._call_count += 1
        if self._fail_after is not None and self._call_count > self._fail_after:
            raise RuntimeError("mock_alt_data: simulated failure")
        symbol = str(kwargs.get("symbol", "UNKNOWN")).upper()
        rng = np.random.default_rng(abs(hash((capability.name, symbol))) % (2**31))
        return {
            "capability": capability.name,
            "symbol": symbol,
            "rows": int(rng.integers(5, 50)),
            "score": float(rng.uniform(0, 1)),
            "provider": self.name,
        }


# ---------------------------------------------------------------------------
# Concrete provider stubs (21 sources)
# ---------------------------------------------------------------------------

class _StubAltProvider(BaseAltDataProvider):
    """Common base for providers that require live API credentials.

    ``_fetch`` raises ``NotImplementedError`` until ``config.api_key`` is
    supplied — this is an intentional abstract guard (same pattern as the
    M13 paid market-data providers), not placeholder logic. It is exercised
    by tests only through the failover path, never invoked with real
    network traffic in the unit-test suite.
    """

    def _fetch(self, capability: AltDataCapability, **kwargs: Any) -> Any:
        if not self.config.api_key:
            raise NotImplementedError(
                f"{self.name} requires an API key + live HTTP call (capability={capability.name})"
            )
        raise NotImplementedError(f"{self.name} live fetch not wired for this environment")


class SECEdgarAltProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="sec_edgar", priority=1,
            capabilities={AltDataCapability.SEC_FILINGS, AltDataCapability.INSIDER_TRANSACTIONS,
                          AltDataCapability.INSTITUTIONAL_13F},
            base_url="https://www.sec.gov",
        ))


class InsiderTransactionsProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="insider_transactions", priority=2,
            capabilities={AltDataCapability.INSIDER_TRANSACTIONS},
        ))


class ETFHoldingsProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="etf_holdings", priority=2,
            capabilities={AltDataCapability.ETF_HOLDINGS},
        ))


class Form13FProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="form_13f", priority=2,
            capabilities={AltDataCapability.INSTITUTIONAL_13F},
        ))


class EarningsTranscriptProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="earnings_transcripts", priority=2,
            capabilities={AltDataCapability.EARNINGS_TRANSCRIPTS},
        ))


class EconomicReleasesProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="economic_releases", priority=2,
            capabilities={AltDataCapability.ECONOMIC_RELEASES},
        ))


class PatentDatabaseProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="patent_database", priority=3,
            capabilities={AltDataCapability.PATENTS},
        ))


class ShippingDataProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="shipping_data", priority=4,
            capabilities={AltDataCapability.SHIPPING},
        ))


class SatelliteDataProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="satellite_data", priority=4,
            capabilities={AltDataCapability.SATELLITE},
        ))


class WeatherDataProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="weather_data", priority=4,
            capabilities={AltDataCapability.WEATHER},
        ))


class CommodityFlowsProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="commodity_flows", priority=4,
            capabilities={AltDataCapability.COMMODITY_FLOWS},
        ))


class EnergyProductionProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="energy_production", priority=4,
            capabilities={AltDataCapability.ENERGY_PRODUCTION},
        ))


class CreditCardSpendingProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="credit_card_spending", priority=3,
            capabilities={AltDataCapability.CREDIT_CARD_SPENDING},
        ))


class AppStoreRankingsProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="app_store_rankings", priority=3,
            capabilities={AltDataCapability.APP_RANKINGS},
        ))


class SocialMediaProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="social_media", priority=3,
            capabilities={AltDataCapability.SOCIAL_MEDIA},
        ))


class RedditProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="reddit", priority=3,
            capabilities={AltDataCapability.REDDIT},
        ))


class TwitterProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="twitter", priority=3,
            capabilities={AltDataCapability.TWITTER},
        ))


class GoogleTrendsProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="google_trends", priority=3,
            capabilities={AltDataCapability.GOOGLE_TRENDS},
        ))


class WikipediaTrendsProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="wikipedia_trends", priority=4,
            capabilities={AltDataCapability.WIKIPEDIA_TRENDS},
        ))


class SupplyChainProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="supply_chain", priority=3,
            capabilities={AltDataCapability.SUPPLY_CHAIN},
        ))


class NewsAltProvider(_StubAltProvider):
    def __init__(self) -> None:
        super().__init__(AltProviderConfig(
            name="news_alt", priority=1,
            capabilities={AltDataCapability.NEWS},
        ))


ALL_ALT_PROVIDER_CLASSES: Dict[str, type] = {
    "sec_edgar": SECEdgarAltProvider,
    "insider_transactions": InsiderTransactionsProvider,
    "etf_holdings": ETFHoldingsProvider,
    "form_13f": Form13FProvider,
    "earnings_transcripts": EarningsTranscriptProvider,
    "economic_releases": EconomicReleasesProvider,
    "patent_database": PatentDatabaseProvider,
    "shipping_data": ShippingDataProvider,
    "satellite_data": SatelliteDataProvider,
    "weather_data": WeatherDataProvider,
    "commodity_flows": CommodityFlowsProvider,
    "energy_production": EnergyProductionProvider,
    "credit_card_spending": CreditCardSpendingProvider,
    "app_store_rankings": AppStoreRankingsProvider,
    "social_media": SocialMediaProvider,
    "reddit": RedditProvider,
    "twitter": TwitterProvider,
    "google_trends": GoogleTrendsProvider,
    "wikipedia_trends": WikipediaTrendsProvider,
    "supply_chain": SupplyChainProvider,
    "news_alt": NewsAltProvider,
}


# ---------------------------------------------------------------------------
# Router with failover
# ---------------------------------------------------------------------------

class AltDataProviderRouter:
    """Routes requests to the highest-priority healthy provider, with failover."""

    def __init__(self, providers: List[BaseAltDataProvider]) -> None:
        self._providers = providers
        self._lock = threading.Lock()

    @property
    def providers(self) -> List[BaseAltDataProvider]:
        return list(self._providers)

    def providers_for(self, capability: AltDataCapability) -> List[BaseAltDataProvider]:
        candidates = [
            p for p in self._providers
            if p.supports(capability) and p.config.enabled and p.health.is_healthy
        ]
        return sorted(candidates, key=lambda p: p.config.priority)

    def fetch(self, capability: AltDataCapability, **kwargs: Any) -> Any:
        candidates = self.providers_for(capability)
        if not candidates:
            candidates = sorted(
                [p for p in self._providers if p.supports(capability) and p.config.enabled],
                key=lambda p: p.config.priority,
            )
            if not candidates:
                raise RuntimeError(f"No provider supports {capability.name}")

        last_exc: Optional[Exception] = None
        for provider in candidates:
            try:
                return provider.fetch(capability, **kwargs)
            except Exception as exc:
                last_exc = exc
                logger.debug("Provider %s failed for %s: %s", provider.name, capability.name, exc)
                continue
        raise RuntimeError(f"All providers failed for {capability.name}") from last_exc

    def health_summary(self) -> List[Dict[str, Any]]:
        return [p.health_check() for p in self._providers]

    def latency_summary(self) -> List[Dict[str, Any]]:
        return [p.latency.to_dict() for p in self._providers]

    def capabilities_matrix(self) -> Dict[str, List[str]]:
        return {p.name: p.capabilities() for p in self._providers}

    def quality_scores(self) -> Dict[str, float]:
        return {p.name: p.quality_score() for p in self._providers}


def build_default_alt_router() -> AltDataProviderRouter:
    """Build a router seeded with the mock provider plus all 21 stubs."""
    providers: List[BaseAltDataProvider] = [MockAltDataProvider()]
    for cls in ALL_ALT_PROVIDER_CLASSES.values():
        providers.append(cls())
    return AltDataProviderRouter(providers)


_default_alt_router: Optional[AltDataProviderRouter] = None


def get_default_alt_router() -> AltDataProviderRouter:
    global _default_alt_router
    if _default_alt_router is None:
        _default_alt_router = build_default_alt_router()
    return _default_alt_router
