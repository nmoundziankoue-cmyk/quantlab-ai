"""M16 Phase 9 — Portfolio Exposure Engine.

Multi-dimensional portfolio exposure analysis: sector, country, currency,
factor, asset class, market cap, credit, duration, and concentration metrics.
Pure Python, in-memory, no external dependencies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Holding:
    """A single portfolio holding.

    Attributes:
        ticker: Ticker symbol.
        weight: Portfolio weight as fraction (sum to 1).
        sector: GICS sector string.
        country: ISO-2 country code.
        currency: ISO-3 currency code.
        asset_class: 'equity', 'bond', 'crypto', 'commodity', 'cash', 'derivative'.
        market_cap_bucket: 'large', 'mid', 'small', 'micro'.
        credit_rating: Credit rating string (for bonds).
        duration: Modified duration (for bonds; 0 for equities).
        beta: Market beta.
        factor_exposures: Dict mapping factor name -> z-score exposure.
    """
    ticker: str
    weight: float
    sector: str = ""
    country: str = ""
    currency: str = "USD"
    asset_class: str = "equity"
    market_cap_bucket: str = "large"
    credit_rating: str = ""
    duration: float = 0.0
    beta: float = 1.0
    factor_exposures: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "weight": round(self.weight, 6),
            "sector": self.sector,
            "country": self.country,
            "currency": self.currency,
            "asset_class": self.asset_class,
            "market_cap_bucket": self.market_cap_bucket,
            "credit_rating": self.credit_rating,
            "duration": round(self.duration, 4),
            "beta": round(self.beta, 4),
            "factor_exposures": {k: round(v, 4) for k, v in self.factor_exposures.items()},
        }


@dataclass
class ExposureBreakdown:
    """Exposure breakdown along a single dimension.

    Attributes:
        dimension: Dimension name (e.g. 'sector', 'country').
        breakdown: Dict mapping category -> portfolio weight.
        top_category: Category with highest weight.
        top_weight: Weight of the dominant category.
        herfindahl_index: HHI of the weight distribution.
        n_categories: Number of distinct categories.
    """
    dimension: str
    breakdown: Dict[str, float]
    top_category: str
    top_weight: float
    herfindahl_index: float
    n_categories: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "dimension": self.dimension,
            "breakdown": {k: round(v, 6) for k, v in self.breakdown.items()},
            "top_category": self.top_category,
            "top_weight": round(self.top_weight, 6),
            "herfindahl_index": round(self.herfindahl_index, 6),
            "n_categories": self.n_categories,
        }


@dataclass
class FactorExposureReport:
    """Portfolio-level factor exposure summary.

    Attributes:
        factor_exposures: Dict mapping factor name -> weighted portfolio exposure.
        dominant_factor: Factor with largest absolute exposure.
        factor_risk_contribution: Dict mapping factor -> estimated risk contribution.
    """
    factor_exposures: Dict[str, float]
    dominant_factor: str
    factor_risk_contribution: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "factor_exposures": {k: round(v, 6) for k, v in self.factor_exposures.items()},
            "dominant_factor": self.dominant_factor,
            "factor_risk_contribution": {k: round(v, 6) for k, v in self.factor_risk_contribution.items()},
        }


@dataclass
class ConcentrationMetrics:
    """Portfolio concentration metrics.

    Attributes:
        hhi: Herfindahl-Hirschman Index of holdings weights.
        effective_n: Inverse HHI — effective number of holdings.
        top1_weight: Weight of single largest holding.
        top5_weight: Combined weight of top-5 holdings.
        top10_weight: Combined weight of top-10 holdings.
        gini_coefficient: Gini coefficient of weight distribution.
    """
    hhi: float
    effective_n: float
    top1_weight: float
    top5_weight: float
    top10_weight: float
    gini_coefficient: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "hhi": round(self.hhi, 6),
            "effective_n": round(self.effective_n, 2),
            "top1_weight": round(self.top1_weight, 6),
            "top5_weight": round(self.top5_weight, 6),
            "top10_weight": round(self.top10_weight, 6),
            "gini_coefficient": round(self.gini_coefficient, 6),
        }


@dataclass
class RiskExposure:
    """Portfolio-level risk metrics.

    Attributes:
        portfolio_beta: Weighted average beta vs market.
        portfolio_duration: Weighted average bond duration.
        equity_share: Fraction of portfolio in equities.
        bond_share: Fraction in bonds.
        cash_share: Fraction in cash.
        alternative_share: Fraction in alternatives.
        currency_risk_score: Fraction of non-USD exposure.
        emerging_market_share: Fraction in EM countries.
    """
    portfolio_beta: float
    portfolio_duration: float
    equity_share: float
    bond_share: float
    cash_share: float
    alternative_share: float
    currency_risk_score: float
    emerging_market_share: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "portfolio_beta": round(self.portfolio_beta, 4),
            "portfolio_duration": round(self.portfolio_duration, 4),
            "equity_share": round(self.equity_share, 6),
            "bond_share": round(self.bond_share, 6),
            "cash_share": round(self.cash_share, 6),
            "alternative_share": round(self.alternative_share, 6),
            "currency_risk_score": round(self.currency_risk_score, 6),
            "emerging_market_share": round(self.emerging_market_share, 6),
        }


# ---------------------------------------------------------------------------
# PortfolioExposureEngine
# ---------------------------------------------------------------------------

_EM_COUNTRIES = {
    "CN", "IN", "BR", "MX", "RU", "ZA", "KR", "TW", "ID", "TH",
    "MY", "PH", "AR", "CL", "CO", "EG", "PL", "HU", "CZ", "TR",
    "SA", "AE", "QA", "NG", "KE", "VN", "PK", "BD", "PE",
}


class PortfolioExposureEngine:
    """Multi-dimensional portfolio exposure analytics engine.

    Computes sector, country, currency, factor, asset-class, and
    concentration exposures from a list of Holding objects.
    """

    # ------------------------------------------------------------------
    # Generic dimension breakdown
    # ------------------------------------------------------------------

    def _breakdown(self, holdings: List[Holding], attr: str) -> ExposureBreakdown:
        """Aggregate portfolio weight by a string attribute.

        Args:
            holdings: List of Holding.
            attr: Attribute name on Holding.

        Returns:
            ExposureBreakdown for the dimension.
        """
        agg: Dict[str, float] = {}
        for h in holdings:
            cat = getattr(h, attr, "") or "unknown"
            agg[cat] = agg.get(cat, 0.0) + h.weight
        if not agg:
            return ExposureBreakdown(
                dimension=attr, breakdown={}, top_category="", top_weight=0.0,
                herfindahl_index=0.0, n_categories=0
            )
        top = max(agg, key=lambda c: agg[c])
        hhi = sum(v ** 2 for v in agg.values())
        return ExposureBreakdown(
            dimension=attr,
            breakdown={k: round(v, 6) for k, v in sorted(agg.items(), key=lambda x: -x[1])},
            top_category=top,
            top_weight=round(agg[top], 6),
            herfindahl_index=round(hhi, 6),
            n_categories=len(agg),
        )

    def sector_exposure(self, holdings: List[Holding]) -> ExposureBreakdown:
        """Portfolio exposure by GICS sector.

        Args:
            holdings: List of Holding.

        Returns:
            ExposureBreakdown along 'sector' dimension.
        """
        return self._breakdown(holdings, "sector")

    def country_exposure(self, holdings: List[Holding]) -> ExposureBreakdown:
        """Portfolio exposure by country.

        Args:
            holdings: List of Holding.

        Returns:
            ExposureBreakdown along 'country' dimension.
        """
        return self._breakdown(holdings, "country")

    def currency_exposure(self, holdings: List[Holding]) -> ExposureBreakdown:
        """Portfolio exposure by currency.

        Args:
            holdings: List of Holding.

        Returns:
            ExposureBreakdown along 'currency' dimension.
        """
        return self._breakdown(holdings, "currency")

    def asset_class_exposure(self, holdings: List[Holding]) -> ExposureBreakdown:
        """Portfolio exposure by asset class.

        Args:
            holdings: List of Holding.

        Returns:
            ExposureBreakdown along 'asset_class' dimension.
        """
        return self._breakdown(holdings, "asset_class")

    def market_cap_exposure(self, holdings: List[Holding]) -> ExposureBreakdown:
        """Portfolio exposure by market cap bucket.

        Args:
            holdings: List of Holding.

        Returns:
            ExposureBreakdown along 'market_cap_bucket' dimension.
        """
        return self._breakdown(holdings, "market_cap_bucket")

    # ------------------------------------------------------------------
    # Factor exposure
    # ------------------------------------------------------------------

    def factor_exposure(self, holdings: List[Holding]) -> FactorExposureReport:
        """Compute weighted factor exposures across holdings.

        Args:
            holdings: List of Holding with factor_exposures populated.

        Returns:
            FactorExposureReport.
        """
        agg: Dict[str, float] = {}
        for h in holdings:
            for factor, exp in h.factor_exposures.items():
                agg[factor] = agg.get(factor, 0.0) + h.weight * exp

        if not agg:
            return FactorExposureReport(
                factor_exposures={},
                dominant_factor="",
                factor_risk_contribution={},
            )

        dominant = max(agg, key=lambda f: abs(agg[f]))
        total_abs = sum(abs(v) for v in agg.values())
        risk_contrib = {
            f: round(abs(v) / total_abs, 6) if total_abs > 0 else 0.0
            for f, v in agg.items()
        }
        return FactorExposureReport(
            factor_exposures={k: round(v, 6) for k, v in agg.items()},
            dominant_factor=dominant,
            factor_risk_contribution=risk_contrib,
        )

    # ------------------------------------------------------------------
    # Concentration
    # ------------------------------------------------------------------

    def concentration_metrics(self, holdings: List[Holding]) -> ConcentrationMetrics:
        """Compute concentration metrics from holding weights.

        Args:
            holdings: List of Holding.

        Returns:
            ConcentrationMetrics.
        """
        weights = sorted([h.weight for h in holdings], reverse=True)
        if not weights:
            return ConcentrationMetrics(0, 0, 0, 0, 0, 0)

        hhi = sum(w ** 2 for w in weights)
        eff_n = 1.0 / hhi if hhi > 0 else 0.0
        top1 = weights[0] if weights else 0.0
        top5 = sum(weights[:5])
        top10 = sum(weights[:10])

        # Gini coefficient
        n = len(weights)
        sorted_w = sorted(weights)
        numer = sum((2 * i - n - 1) * sorted_w[i - 1] for i in range(1, n + 1))
        gini = numer / (n * sum(sorted_w)) if sum(sorted_w) > 0 else 0.0

        return ConcentrationMetrics(
            hhi=round(hhi, 6),
            effective_n=round(eff_n, 2),
            top1_weight=round(top1, 6),
            top5_weight=round(top5, 6),
            top10_weight=round(top10, 6),
            gini_coefficient=round(gini, 6),
        )

    # ------------------------------------------------------------------
    # Risk exposure
    # ------------------------------------------------------------------

    def risk_exposure(self, holdings: List[Holding]) -> RiskExposure:
        """Compute portfolio-level risk metrics.

        Args:
            holdings: List of Holding.

        Returns:
            RiskExposure.
        """
        port_beta = sum(h.weight * h.beta for h in holdings)
        port_dur = sum(h.weight * h.duration for h in holdings)
        equity_w = sum(h.weight for h in holdings if h.asset_class == "equity")
        bond_w = sum(h.weight for h in holdings if h.asset_class == "bond")
        cash_w = sum(h.weight for h in holdings if h.asset_class == "cash")
        alt_w = max(0.0, 1.0 - equity_w - bond_w - cash_w)
        non_usd = sum(h.weight for h in holdings if h.currency != "USD")
        em_w = sum(h.weight for h in holdings if h.country.upper() in _EM_COUNTRIES)

        return RiskExposure(
            portfolio_beta=round(port_beta, 4),
            portfolio_duration=round(port_dur, 4),
            equity_share=round(equity_w, 6),
            bond_share=round(bond_w, 6),
            cash_share=round(cash_w, 6),
            alternative_share=round(alt_w, 6),
            currency_risk_score=round(non_usd, 6),
            emerging_market_share=round(em_w, 6),
        )

    # ------------------------------------------------------------------
    # Drift analysis
    # ------------------------------------------------------------------

    def drift_from_target(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """Compute weight drift between current and target allocations.

        Args:
            current_weights: Dict ticker -> current weight.
            target_weights: Dict ticker -> target weight.

        Returns:
            Dict with per-ticker drift and total absolute drift.
        """
        all_tickers = set(current_weights) | set(target_weights)
        drifts: Dict[str, float] = {}
        for t in all_tickers:
            cur = current_weights.get(t, 0.0)
            tgt = target_weights.get(t, 0.0)
            drifts[t] = round(cur - tgt, 6)
        total_abs_drift = sum(abs(v) for v in drifts.values())
        return {
            "drifts": drifts,
            "total_absolute_drift": round(total_abs_drift, 6),
            "rebalance_needed": total_abs_drift > 0.05,
        }

    # ------------------------------------------------------------------
    # Full exposure report
    # ------------------------------------------------------------------

    def full_report(self, holdings: List[Holding]) -> Dict[str, Any]:
        """Produce a comprehensive exposure report across all dimensions.

        Args:
            holdings: List of Holding.

        Returns:
            Dict with all exposure breakdowns and risk metrics.
        """
        return {
            "sector": self.sector_exposure(holdings).to_dict(),
            "country": self.country_exposure(holdings).to_dict(),
            "currency": self.currency_exposure(holdings).to_dict(),
            "asset_class": self.asset_class_exposure(holdings).to_dict(),
            "market_cap": self.market_cap_exposure(holdings).to_dict(),
            "factor": self.factor_exposure(holdings).to_dict(),
            "concentration": self.concentration_metrics(holdings).to_dict(),
            "risk": self.risk_exposure(holdings).to_dict(),
            "n_holdings": len(holdings),
        }

    # ------------------------------------------------------------------
    # Active weight analysis (vs benchmark)
    # ------------------------------------------------------------------

    def active_weights(
        self,
        portfolio: List[Holding],
        benchmark: List[Holding],
    ) -> Dict[str, float]:
        """Compute active weights (portfolio - benchmark) for each ticker.

        Args:
            portfolio: Portfolio holdings.
            benchmark: Benchmark holdings.

        Returns:
            Dict mapping ticker -> active weight.
        """
        port_map = {h.ticker: h.weight for h in portfolio}
        bench_map = {h.ticker: h.weight for h in benchmark}
        all_tickers = set(port_map) | set(bench_map)
        return {
            t: round(port_map.get(t, 0.0) - bench_map.get(t, 0.0), 6)
            for t in sorted(all_tickers)
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_portfolio_exposure: Optional[PortfolioExposureEngine] = None


def get_portfolio_exposure_engine() -> PortfolioExposureEngine:
    """Return the singleton PortfolioExposureEngine instance.

    Returns:
        Shared PortfolioExposureEngine instance.
    """
    global _default_portfolio_exposure
    if _default_portfolio_exposure is None:
        _default_portfolio_exposure = PortfolioExposureEngine()
    return _default_portfolio_exposure
