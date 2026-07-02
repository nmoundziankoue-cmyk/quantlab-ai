"""M16 Phase 4 — ETF Intelligence Engine.

Holdings analysis, sector/country exposure, fund overlap, tracking
difference, and flow estimation — pure Python, in-memory.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class FlowDirection(str, Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    NEUTRAL = "neutral"


class TrackingQuality(str, Enum):
    EXCELLENT = "excellent"   # TD < 0.10%
    GOOD = "good"             # 0.10% – 0.25%
    FAIR = "fair"             # 0.25% – 0.50%
    POOR = "poor"             # > 0.50%


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ETFHolding:
    """A single holding within an ETF.

    Attributes:
        ticker: Holding ticker symbol.
        name: Company name.
        weight: Portfolio weight as a fraction (0–1).
        sector: GICS sector.
        country: ISO-2 country code.
        market_cap_bucket: 'large', 'mid', 'small', or 'micro'.
        asset_type: 'equity', 'bond', 'derivative', etc.
    """
    ticker: str
    name: str
    weight: float
    sector: str
    country: str
    market_cap_bucket: str = "large"
    asset_type: str = "equity"

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "weight": round(self.weight, 6),
            "sector": self.sector,
            "country": self.country,
            "market_cap_bucket": self.market_cap_bucket,
            "asset_type": self.asset_type,
        }


@dataclass
class ETFProfile:
    """Metadata and holdings for a single ETF.

    Attributes:
        ticker: ETF ticker symbol.
        name: Full fund name.
        expense_ratio: Annual expense ratio (fraction, e.g. 0.0003 = 0.03%).
        aum_usd: Assets under management in USD millions.
        benchmark: Benchmark index tracked.
        holdings: List of ETFHolding.
        inception_date: YYYY-MM-DD string.
        issuer: Fund issuer name.
    """
    ticker: str
    name: str
    expense_ratio: float
    aum_usd: float
    benchmark: str
    holdings: List[ETFHolding] = field(default_factory=list)
    inception_date: str = ""
    issuer: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "expense_ratio": round(self.expense_ratio, 6),
            "aum_usd": round(self.aum_usd, 2),
            "benchmark": self.benchmark,
            "holdings": [h.to_dict() for h in self.holdings],
            "inception_date": self.inception_date,
            "issuer": self.issuer,
        }


@dataclass
class SectorExposure:
    """Sector breakdown for a fund.

    Attributes:
        etf_ticker: Parent ETF ticker.
        sectors: Dict mapping sector name -> weight.
        top_sector: Sector with largest weight.
        concentration_ratio: Weight of top-3 sectors combined.
    """
    etf_ticker: str
    sectors: Dict[str, float]
    top_sector: str
    concentration_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "etf_ticker": self.etf_ticker,
            "sectors": {k: round(v, 6) for k, v in self.sectors.items()},
            "top_sector": self.top_sector,
            "concentration_ratio": round(self.concentration_ratio, 6),
        }


@dataclass
class CountryExposure:
    """Geographic breakdown for a fund.

    Attributes:
        etf_ticker: Parent ETF ticker.
        countries: Dict mapping ISO-2 country code -> weight.
        top_country: Country with largest weight.
        domestic_weight: Weight in home country (largest single country).
    """
    etf_ticker: str
    countries: Dict[str, float]
    top_country: str
    domestic_weight: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "etf_ticker": self.etf_ticker,
            "countries": {k: round(v, 6) for k, v in self.countries.items()},
            "top_country": self.top_country,
            "domestic_weight": round(self.domestic_weight, 6),
        }


@dataclass
class ETFOverlap:
    """Portfolio overlap analysis between two ETFs.

    Attributes:
        etf_a: First ETF ticker.
        etf_b: Second ETF ticker.
        overlap_weight: Shared weight (sum of min weights for common holdings).
        common_tickers: List of tickers held by both funds.
        n_common: Number of common holdings.
        jaccard_similarity: |common| / |union| of tickers.
    """
    etf_a: str
    etf_b: str
    overlap_weight: float
    common_tickers: List[str]
    n_common: int
    jaccard_similarity: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "etf_a": self.etf_a,
            "etf_b": self.etf_b,
            "overlap_weight": round(self.overlap_weight, 6),
            "common_tickers": self.common_tickers,
            "n_common": self.n_common,
            "jaccard_similarity": round(self.jaccard_similarity, 6),
        }


@dataclass
class TrackingDifference:
    """Tracking difference between an ETF and its benchmark.

    Attributes:
        etf_ticker: ETF ticker.
        benchmark: Benchmark name.
        tracking_difference: ETF cumulative return − benchmark cumulative return.
        tracking_error: Annualised std of excess return.
        quality: TrackingQuality classification.
        expense_ratio: Fund annual expense ratio.
    """
    etf_ticker: str
    benchmark: str
    tracking_difference: float
    tracking_error: float
    quality: TrackingQuality
    expense_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "etf_ticker": self.etf_ticker,
            "benchmark": self.benchmark,
            "tracking_difference": round(self.tracking_difference, 6),
            "tracking_error": round(self.tracking_error, 6),
            "quality": self.quality.value,
            "expense_ratio": round(self.expense_ratio, 6),
        }


@dataclass
class FlowEstimate:
    """AUM-based flow estimate for an ETF period.

    Attributes:
        etf_ticker: ETF ticker.
        period_return: NAV return for the period.
        aum_start: AUM at period start (USD millions).
        aum_end: AUM at period end (USD millions).
        net_flow_usd: Estimated net flow in USD millions.
        direction: Inflow / outflow / neutral.
    """
    etf_ticker: str
    period_return: float
    aum_start: float
    aum_end: float
    net_flow_usd: float
    direction: FlowDirection

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "etf_ticker": self.etf_ticker,
            "period_return": round(self.period_return, 6),
            "aum_start": round(self.aum_start, 2),
            "aum_end": round(self.aum_end, 2),
            "net_flow_usd": round(self.net_flow_usd, 2),
            "direction": self.direction.value,
        }


# ---------------------------------------------------------------------------
# ETFEngine
# ---------------------------------------------------------------------------

class ETFEngine:
    """ETF Intelligence Engine.

    Provides holdings decomposition, exposure analysis, fund overlap,
    tracking difference, and flow estimation.  All methods are stateless;
    ETFProfile objects are passed directly as arguments.
    """

    # ------------------------------------------------------------------
    # Exposure analysis
    # ------------------------------------------------------------------

    def sector_exposure(self, etf: ETFProfile) -> SectorExposure:
        """Aggregate holdings weight by GICS sector.

        Args:
            etf: ETFProfile with populated holdings list.

        Returns:
            SectorExposure with per-sector weights.
        """
        sectors: Dict[str, float] = {}
        for h in etf.holdings:
            sectors[h.sector] = round(sectors.get(h.sector, 0.0) + h.weight, 8)
        if not sectors:
            return SectorExposure(
                etf_ticker=etf.ticker, sectors={}, top_sector="", concentration_ratio=0.0
            )
        top = max(sectors, key=lambda s: sectors[s])
        sorted_weights = sorted(sectors.values(), reverse=True)
        top3 = sum(sorted_weights[:3])
        return SectorExposure(
            etf_ticker=etf.ticker,
            sectors={k: round(v, 6) for k, v in sectors.items()},
            top_sector=top,
            concentration_ratio=round(top3, 6),
        )

    def country_exposure(self, etf: ETFProfile) -> CountryExposure:
        """Aggregate holdings weight by country.

        Args:
            etf: ETFProfile with populated holdings list.

        Returns:
            CountryExposure with per-country weights.
        """
        countries: Dict[str, float] = {}
        for h in etf.holdings:
            countries[h.country] = round(countries.get(h.country, 0.0) + h.weight, 8)
        if not countries:
            return CountryExposure(
                etf_ticker=etf.ticker, countries={}, top_country="", domestic_weight=0.0
            )
        top = max(countries, key=lambda c: countries[c])
        return CountryExposure(
            etf_ticker=etf.ticker,
            countries={k: round(v, 6) for k, v in countries.items()},
            top_country=top,
            domestic_weight=round(countries[top], 6),
        )

    def market_cap_exposure(self, etf: ETFProfile) -> Dict[str, float]:
        """Aggregate weight by market-cap bucket.

        Args:
            etf: ETFProfile with populated holdings.

        Returns:
            Dict mapping market_cap_bucket -> weight.
        """
        buckets: Dict[str, float] = {}
        for h in etf.holdings:
            buckets[h.market_cap_bucket] = round(buckets.get(h.market_cap_bucket, 0.0) + h.weight, 8)
        return {k: round(v, 6) for k, v in sorted(buckets.items())}

    # ------------------------------------------------------------------
    # Overlap analysis
    # ------------------------------------------------------------------

    def compute_overlap(self, etf_a: ETFProfile, etf_b: ETFProfile) -> ETFOverlap:
        """Compute portfolio overlap between two ETFs.

        Args:
            etf_a: First ETF.
            etf_b: Second ETF.

        Returns:
            ETFOverlap with shared weight and Jaccard similarity.
        """
        weights_a = {h.ticker: h.weight for h in etf_a.holdings}
        weights_b = {h.ticker: h.weight for h in etf_b.holdings}
        tickers_a = set(weights_a)
        tickers_b = set(weights_b)
        common = tickers_a & tickers_b
        union = tickers_a | tickers_b
        overlap_w = sum(min(weights_a[t], weights_b[t]) for t in common)
        jaccard = len(common) / len(union) if union else 0.0
        return ETFOverlap(
            etf_a=etf_a.ticker,
            etf_b=etf_b.ticker,
            overlap_weight=round(overlap_w, 6),
            common_tickers=sorted(common),
            n_common=len(common),
            jaccard_similarity=round(jaccard, 6),
        )

    def multi_fund_overlap(self, etfs: List[ETFProfile]) -> Dict[str, Any]:
        """Compute pairwise overlap matrix for a list of ETFs.

        Args:
            etfs: List of ETFProfile objects.

        Returns:
            Dict with tickers list and pairwise overlap matrix.
        """
        n = len(etfs)
        tickers = [e.ticker for e in etfs]
        mat = [[0.0] * n for _ in range(n)]
        for i in range(n):
            mat[i][i] = 1.0
            for j in range(i + 1, n):
                ov = self.compute_overlap(etfs[i], etfs[j])
                mat[i][j] = ov.overlap_weight
                mat[j][i] = ov.overlap_weight
        return {
            "tickers": tickers,
            "matrix": [[round(v, 6) for v in row] for row in mat],
        }

    # ------------------------------------------------------------------
    # Tracking difference
    # ------------------------------------------------------------------

    def tracking_difference(
        self,
        etf: ETFProfile,
        etf_returns: List[float],
        benchmark_returns: List[float],
    ) -> TrackingDifference:
        """Compute tracking difference and error vs benchmark.

        Args:
            etf: ETFProfile with expense_ratio and benchmark.
            etf_returns: ETF daily return series.
            benchmark_returns: Benchmark daily return series.

        Returns:
            TrackingDifference with quality classification.
        """
        n = min(len(etf_returns), len(benchmark_returns))
        if n == 0:
            return TrackingDifference(
                etf_ticker=etf.ticker,
                benchmark=etf.benchmark,
                tracking_difference=0.0,
                tracking_error=0.0,
                quality=TrackingQuality.EXCELLENT,
                expense_ratio=etf.expense_ratio,
            )
        excess = [etf_returns[i] - benchmark_returns[i] for i in range(n)]
        td = sum(excess)
        te_daily = (sum((e - sum(excess) / n) ** 2 for e in excess) / max(n - 1, 1)) ** 0.5
        te_ann = te_daily * math.sqrt(252)

        abs_td = abs(td)
        if abs_td < 0.001:
            quality = TrackingQuality.EXCELLENT
        elif abs_td < 0.0025:
            quality = TrackingQuality.GOOD
        elif abs_td < 0.005:
            quality = TrackingQuality.FAIR
        else:
            quality = TrackingQuality.POOR

        return TrackingDifference(
            etf_ticker=etf.ticker,
            benchmark=etf.benchmark,
            tracking_difference=round(td, 6),
            tracking_error=round(te_ann, 6),
            quality=quality,
            expense_ratio=etf.expense_ratio,
        )

    # ------------------------------------------------------------------
    # Flow estimation
    # ------------------------------------------------------------------

    def estimate_flows(
        self,
        etf: ETFProfile,
        aum_start: float,
        aum_end: float,
        period_return: float,
    ) -> FlowEstimate:
        """Estimate net flows from AUM change and NAV return.

        net_flow = AUM_end - AUM_start × (1 + period_return)

        Args:
            etf: ETFProfile.
            aum_start: AUM at period start (USD millions).
            aum_end: AUM at period end (USD millions).
            period_return: NAV return for the period.

        Returns:
            FlowEstimate with net flow and direction.
        """
        expected_aum = aum_start * (1 + period_return)
        net_flow = aum_end - expected_aum
        if net_flow > aum_start * 0.005:
            direction = FlowDirection.INFLOW
        elif net_flow < -aum_start * 0.005:
            direction = FlowDirection.OUTFLOW
        else:
            direction = FlowDirection.NEUTRAL
        return FlowEstimate(
            etf_ticker=etf.ticker,
            period_return=round(period_return, 6),
            aum_start=round(aum_start, 2),
            aum_end=round(aum_end, 2),
            net_flow_usd=round(net_flow, 2),
            direction=direction,
        )

    # ------------------------------------------------------------------
    # Concentration metrics
    # ------------------------------------------------------------------

    def herfindahl_index(self, etf: ETFProfile) -> float:
        """Herfindahl-Hirschman Index for portfolio concentration.

        Args:
            etf: ETFProfile with holdings.

        Returns:
            HHI in [0, 1] — higher means more concentrated.
        """
        return round(sum(h.weight ** 2 for h in etf.holdings), 6)

    def effective_number_of_holdings(self, etf: ETFProfile) -> float:
        """Effective N based on inverse HHI.

        Args:
            etf: ETFProfile with holdings.

        Returns:
            Effective number of holdings.
        """
        hhi = self.herfindahl_index(etf)
        return round(1.0 / hhi, 2) if hhi > 0 else 0.0

    def top_n_holdings(self, etf: ETFProfile, n: int = 10) -> List[ETFHolding]:
        """Return top-n holdings by weight.

        Args:
            etf: ETFProfile with holdings.
            n: Number of top holdings to return.

        Returns:
            Sorted list of top ETFHolding objects.
        """
        return sorted(etf.holdings, key=lambda h: h.weight, reverse=True)[:n]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def fund_summary(self, etf: ETFProfile) -> Dict[str, Any]:
        """Compute a comprehensive one-page fund summary.

        Args:
            etf: ETFProfile.

        Returns:
            Dict with key metrics and exposures.
        """
        sec_exp = self.sector_exposure(etf)
        cty_exp = self.country_exposure(etf)
        cap_exp = self.market_cap_exposure(etf)
        hhi = self.herfindahl_index(etf)
        eff_n = self.effective_number_of_holdings(etf)
        return {
            "ticker": etf.ticker,
            "name": etf.name,
            "aum_usd": etf.aum_usd,
            "expense_ratio": etf.expense_ratio,
            "benchmark": etf.benchmark,
            "n_holdings": len(etf.holdings),
            "hhi": hhi,
            "effective_n": eff_n,
            "top_sector": sec_exp.top_sector,
            "top_country": cty_exp.top_country,
            "sector_concentration": sec_exp.concentration_ratio,
            "market_cap_buckets": cap_exp,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_etf_engine: Optional[ETFEngine] = None


def get_etf_engine() -> ETFEngine:
    """Return the singleton ETFEngine instance.

    Returns:
        Shared ETFEngine instance.
    """
    global _default_etf_engine
    if _default_etf_engine is None:
        _default_etf_engine = ETFEngine()
    return _default_etf_engine
