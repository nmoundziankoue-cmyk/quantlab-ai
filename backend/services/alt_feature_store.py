"""M14 Phase 7 — Alternative feature store.

Computes reusable alternative-data-derived features from a per-symbol
`AltDataBundle` of documents, detected events, insider activity, patent
counts, concentration shares, and social/search signal series.  Mirrors the
M13 `FeatureStore` design (catalog + cache + compute) so it composes
naturally with the price-based feature store at the router/consumer level,
without modifying the stable M13 module.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from services.document_ai import sentiment_score, uncertainty_score
from services.event_detection import AltEvent, event_density


@dataclass
class AltFeatureDefinition:
    name: str
    category: str
    description: str


ALT_FEATURE_CATALOG: List[AltFeatureDefinition] = [
    AltFeatureDefinition("alt_sentiment", "sentiment", "Mean lexicon sentiment across documents + transcripts"),
    AltFeatureDefinition("alt_filing_frequency", "filings", "Filing frequency normalised to [0,1] (1 filing/day saturates)"),
    AltFeatureDefinition("alt_insider_buying_ratio", "insider", "Insider buys / (buys + sells); 0.5 = neutral/no data"),
    AltFeatureDefinition("alt_executive_turnover", "leadership", "Executive changes / total executives"),
    AltFeatureDefinition("alt_earnings_surprise_history", "earnings", "tanh-clipped mean of historical earnings surprises"),
    AltFeatureDefinition("alt_patent_growth", "innovation", "Period-over-period growth rate of patent counts"),
    AltFeatureDefinition("alt_supplier_concentration", "supply_chain", "HHI-style concentration of supplier revenue shares"),
    AltFeatureDefinition("alt_customer_concentration", "supply_chain", "HHI-style concentration of customer revenue shares"),
    AltFeatureDefinition("alt_esg_score", "esg", "ESG score (0.5 neutral placeholder when not supplied)"),
    AltFeatureDefinition("alt_news_intensity", "news", "Normalised news mention volume over the window"),
    AltFeatureDefinition("alt_social_momentum", "social", "Period-over-period growth rate of social mentions"),
    AltFeatureDefinition("alt_search_trend_score", "search", "Mean search-trend index, normalised to [0,1]"),
    AltFeatureDefinition("alt_transcript_positivity", "transcripts", "Mean sentiment across earnings-call transcripts"),
    AltFeatureDefinition("alt_transcript_uncertainty", "transcripts", "Mean lexicon-based uncertainty across transcripts"),
    AltFeatureDefinition("alt_event_density", "events", "Detected events per document, normalised to [0,1]"),
]

ALT_FEATURE_NAMES = [f.name for f in ALT_FEATURE_CATALOG]


@dataclass
class AltDataBundle:
    symbol: str
    documents: List[Dict[str, str]] = field(default_factory=list)
    events: List[AltEvent] = field(default_factory=list)
    insider_buys: int = 0
    insider_sells: int = 0
    executive_changes: int = 0
    total_executives: int = 1
    earnings_surprises: List[float] = field(default_factory=list)
    patent_counts_by_period: List[float] = field(default_factory=list)
    supplier_concentration_shares: List[float] = field(default_factory=list)
    customer_concentration_shares: List[float] = field(default_factory=list)
    news_mentions_by_period: List[float] = field(default_factory=list)
    social_mentions_by_period: List[float] = field(default_factory=list)
    search_trend_values: List[float] = field(default_factory=list)
    esg_score: Optional[float] = None
    transcript_texts: List[str] = field(default_factory=list)
    window_days: int = 30


def _growth_rate(values: List[float]) -> float:
    """(last - mean(prior)) / mean(prior), clipped to [-1, 1]. 0.0 if insufficient data."""
    if len(values) < 2:
        return 0.0
    prior = values[:-1]
    mean_prior = sum(prior) / len(prior)
    if abs(mean_prior) < 1e-9:
        return 0.0
    rate = (values[-1] - mean_prior) / abs(mean_prior)
    return round(max(-1.0, min(1.0, rate)), 4)


def _hhi(shares: List[float]) -> float:
    """Herfindahl-Hirschman-style concentration on shares (auto-normalised to sum to 1)."""
    if not shares:
        return 0.0
    total = sum(shares)
    if total <= 0:
        return 0.0
    normalized = [s / total for s in shares]
    return round(sum(s ** 2 for s in normalized), 4)


def _tanh_clip(x: float) -> float:
    return round(math.tanh(x), 4)


class AltFeatureStore:
    """Computes and caches the M14 alternative feature catalog per symbol."""

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def catalog(self) -> List[Dict[str, str]]:
        return [{"name": f.name, "category": f.category, "description": f.description} for f in ALT_FEATURE_CATALOG]

    def compute(self, bundle: AltDataBundle, use_cache: bool = True) -> Dict[str, float]:
        key = bundle.symbol.upper()
        if use_cache:
            with self._lock:
                cached = self._cache.get(key)
            if cached is not None:
                return cached

        texts = [d.get("text", "") for d in bundle.documents if d.get("text")]
        all_sentiment_texts = texts + bundle.transcript_texts
        sentiment = (
            round(sum(sentiment_score(t) for t in all_sentiment_texts) / len(all_sentiment_texts), 4)
            if all_sentiment_texts else 0.0
        )

        filing_frequency = round(min(1.0, len(bundle.documents) / max(bundle.window_days, 1)), 4)

        total_insider = bundle.insider_buys + bundle.insider_sells
        insider_buying_ratio = round(bundle.insider_buys / total_insider, 4) if total_insider > 0 else 0.5

        executive_turnover = round(
            min(1.0, bundle.executive_changes / max(bundle.total_executives, 1)), 4
        )

        earnings_surprise_history = (
            _tanh_clip(sum(bundle.earnings_surprises) / len(bundle.earnings_surprises))
            if bundle.earnings_surprises else 0.0
        )

        patent_growth = _growth_rate(bundle.patent_counts_by_period)
        supplier_concentration = _hhi(bundle.supplier_concentration_shares)
        customer_concentration = _hhi(bundle.customer_concentration_shares)
        esg = round(bundle.esg_score, 4) if bundle.esg_score is not None else 0.5

        news_intensity = round(
            min(1.0, sum(bundle.news_mentions_by_period) / max(bundle.window_days * 5, 1)), 4
        ) if bundle.news_mentions_by_period else 0.0

        social_momentum = _growth_rate(bundle.social_mentions_by_period)

        search_trend_score = (
            round(min(1.0, max(0.0, (sum(bundle.search_trend_values) / len(bundle.search_trend_values)) / 100.0)), 4)
            if bundle.search_trend_values else 0.0
        )

        transcript_positivity = (
            round(sum(sentiment_score(t) for t in bundle.transcript_texts) / len(bundle.transcript_texts), 4)
            if bundle.transcript_texts else 0.0
        )
        transcript_uncertainty = (
            round(sum(uncertainty_score(t) for t in bundle.transcript_texts) / len(bundle.transcript_texts), 4)
            if bundle.transcript_texts else 0.0
        )

        density = event_density(bundle.events, max(len(bundle.documents), 1))

        features = {
            "alt_sentiment": sentiment,
            "alt_filing_frequency": filing_frequency,
            "alt_insider_buying_ratio": insider_buying_ratio,
            "alt_executive_turnover": executive_turnover,
            "alt_earnings_surprise_history": earnings_surprise_history,
            "alt_patent_growth": patent_growth,
            "alt_supplier_concentration": supplier_concentration,
            "alt_customer_concentration": customer_concentration,
            "alt_esg_score": esg,
            "alt_news_intensity": news_intensity,
            "alt_social_momentum": social_momentum,
            "alt_search_trend_score": search_trend_score,
            "alt_transcript_positivity": transcript_positivity,
            "alt_transcript_uncertainty": transcript_uncertainty,
            "alt_event_density": density,
        }

        with self._lock:
            self._cache[key] = features
        return features

    def invalidate(self, symbol: str) -> None:
        with self._lock:
            self._cache.pop(symbol.upper(), None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


_default_alt_feature_store: Optional[AltFeatureStore] = None


def get_default_alt_feature_store() -> AltFeatureStore:
    global _default_alt_feature_store
    if _default_alt_feature_store is None:
        _default_alt_feature_store = AltFeatureStore()
    return _default_alt_feature_store
