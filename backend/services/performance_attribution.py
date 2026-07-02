"""M17 — Performance Attribution Engine (pure Python, in-memory).

Institutional performance attribution: Brinson-Hood-Beebower (BHB) model
decomposing excess return into allocation, selection, and interaction effects.
Also provides sector, country, currency, and factor attribution.

No SQLAlchemy, no external libraries — stdlib + math only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AttributionModel(str, Enum):
    BRINSON = "BRINSON"
    BRINSON_FACHLER = "BRINSON_FACHLER"


class AttributionDimension(str, Enum):
    SECTOR = "SECTOR"
    COUNTRY = "COUNTRY"
    CURRENCY = "CURRENCY"
    FACTOR = "FACTOR"


# ---------------------------------------------------------------------------
# Input structures
# ---------------------------------------------------------------------------

@dataclass
class Holding:
    """A portfolio or benchmark holding.

    Args:
        category: Sector, country, currency, or factor label.
        portfolio_weight: Weight in the portfolio (0–1).
        benchmark_weight: Weight in the benchmark (0–1).
        portfolio_return: Period return of this category in the portfolio.
        benchmark_return: Period return of this category in the benchmark.
    """

    category: str
    portfolio_weight: float
    benchmark_weight: float
    portfolio_return: float
    benchmark_return: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "category": self.category,
            "portfolio_weight": round(self.portfolio_weight, 6),
            "benchmark_weight": round(self.benchmark_weight, 6),
            "portfolio_return": round(self.portfolio_return, 6),
            "benchmark_return": round(self.benchmark_return, 6),
        }


@dataclass
class FactorExposure:
    """Portfolio and benchmark factor exposures for factor attribution.

    Args:
        factor_name: Factor name (e.g. "VALUE", "MOMENTUM").
        portfolio_exposure: Portfolio beta to this factor.
        benchmark_exposure: Benchmark beta to this factor.
        factor_return: Return of the factor over the period.
    """

    factor_name: str
    portfolio_exposure: float
    benchmark_exposure: float
    factor_return: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "factor_name": self.factor_name,
            "portfolio_exposure": round(self.portfolio_exposure, 6),
            "benchmark_exposure": round(self.benchmark_exposure, 6),
            "factor_return": round(self.factor_return, 6),
        }


# ---------------------------------------------------------------------------
# Result structures
# ---------------------------------------------------------------------------

@dataclass
class BrinsonEffect:
    """Brinson attribution effects for a single category.

    Brinson-Hood-Beebower formula:
        Allocation  = (wp - wb) * (Rb - R_bench)
        Selection   = wb * (Rp - Rb)
        Interaction = (wp - wb) * (Rp - Rb)

    Args:
        category: Sector/country/currency label.
        portfolio_weight: Portfolio weight.
        benchmark_weight: Benchmark weight.
        portfolio_return: Portfolio category return.
        benchmark_return: Benchmark category return.
        benchmark_total_return: Total benchmark return (used in B-F variant).
        allocation_effect: Contribution from overweighting/underweighting.
        selection_effect: Contribution from security selection.
        interaction_effect: Cross-term (weight × selection).
        total_effect: Allocation + Selection + Interaction.
    """

    category: str
    portfolio_weight: float
    benchmark_weight: float
    portfolio_return: float
    benchmark_return: float
    benchmark_total_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    total_effect: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "category": self.category,
            "portfolio_weight": round(self.portfolio_weight, 6),
            "benchmark_weight": round(self.benchmark_weight, 6),
            "portfolio_return": round(self.portfolio_return, 6),
            "benchmark_return": round(self.benchmark_return, 6),
            "allocation_effect": round(self.allocation_effect, 6),
            "selection_effect": round(self.selection_effect, 6),
            "interaction_effect": round(self.interaction_effect, 6),
            "total_effect": round(self.total_effect, 6),
        }


@dataclass
class BrinsonResult:
    """Complete Brinson attribution report.

    Args:
        model: Attribution model used.
        portfolio_return: Total portfolio return.
        benchmark_return: Total benchmark return.
        active_return: portfolio_return - benchmark_return.
        total_allocation: Sum of allocation effects across all categories.
        total_selection: Sum of selection effects.
        total_interaction: Sum of interaction effects.
        total_explained: total_allocation + total_selection + total_interaction.
        unexplained: active_return - total_explained.
        category_effects: Per-category Brinson effects.
    """

    model: AttributionModel
    portfolio_return: float
    benchmark_return: float
    active_return: float
    total_allocation: float
    total_selection: float
    total_interaction: float
    total_explained: float
    unexplained: float
    category_effects: List[BrinsonEffect]

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "model": self.model.value,
            "portfolio_return": round(self.portfolio_return, 6),
            "benchmark_return": round(self.benchmark_return, 6),
            "active_return": round(self.active_return, 6),
            "total_allocation": round(self.total_allocation, 6),
            "total_selection": round(self.total_selection, 6),
            "total_interaction": round(self.total_interaction, 6),
            "total_explained": round(self.total_explained, 6),
            "unexplained": round(self.unexplained, 6),
            "category_effects": [e.to_dict() for e in self.category_effects],
        }


@dataclass
class FactorAttributionResult:
    """Factor-based return attribution.

    Args:
        factor_name: Factor identifier.
        active_exposure: portfolio_exposure - benchmark_exposure.
        factor_return: Factor return for the period.
        attribution: active_exposure * factor_return.
    """

    factor_name: str
    portfolio_exposure: float
    benchmark_exposure: float
    active_exposure: float
    factor_return: float
    attribution: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "factor_name": self.factor_name,
            "portfolio_exposure": round(self.portfolio_exposure, 6),
            "benchmark_exposure": round(self.benchmark_exposure, 6),
            "active_exposure": round(self.active_exposure, 6),
            "factor_return": round(self.factor_return, 6),
            "attribution": round(self.attribution, 6),
        }


@dataclass
class FullAttributionReport:
    """Combined attribution report across all dimensions.

    Args:
        brinson: Sector-level Brinson attribution.
        country_brinson: Country-level Brinson attribution (if provided).
        currency_attribution: Currency effect estimates.
        factor_attribution: Factor-level attribution results.
        portfolio_return: Total portfolio return.
        benchmark_return: Total benchmark return.
        active_return: Active (excess) return.
        information_ratio: Active return / tracking error.
        tracking_error: Annualised std dev of active returns.
    """

    brinson: Optional[BrinsonResult]
    country_brinson: Optional[BrinsonResult]
    currency_attribution: List[FactorAttributionResult]
    factor_attribution: List[FactorAttributionResult]
    portfolio_return: float
    benchmark_return: float
    active_return: float
    information_ratio: float
    tracking_error: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "portfolio_return": round(self.portfolio_return, 6),
            "benchmark_return": round(self.benchmark_return, 6),
            "active_return": round(self.active_return, 6),
            "information_ratio": round(self.information_ratio, 6),
            "tracking_error": round(self.tracking_error, 6),
            "brinson_sector": self.brinson.to_dict() if self.brinson else None,
            "brinson_country": self.country_brinson.to_dict() if self.country_brinson else None,
            "currency_attribution": [c.to_dict() for c in self.currency_attribution],
            "factor_attribution": [f.to_dict() for f in self.factor_attribution],
        }


# ---------------------------------------------------------------------------
# Performance Attribution Engine
# ---------------------------------------------------------------------------

class PerformanceAttributionEngine:
    """Institutional performance attribution engine (pure Python).

    Implements Brinson-Hood-Beebower (BHB) and Brinson-Fachler (BF)
    models for sector, country, and currency attribution, plus a
    linear factor attribution model.
    """

    # ------------------------------------------------------------------
    # Brinson attribution
    # ------------------------------------------------------------------

    def brinson_attribution(
        self,
        holdings: List[Holding],
        benchmark_total_return: float,
        model: AttributionModel = AttributionModel.BRINSON,
    ) -> BrinsonResult:
        """Compute Brinson attribution over a list of category holdings.

        Brinson-Hood-Beebower:
            Allocation  = (wp - wb) * (Rb - R_bench)
            Selection   = wb * (Rp - Rb)
            Interaction = (wp - wb) * (Rp - Rb)

        Brinson-Fachler (removes interaction term from allocation):
            Allocation  = (wp - wb) * (Rb - R_bench)
            Selection   = wp * (Rp - Rb)
            Interaction = 0

        Args:
            holdings: Per-category portfolio and benchmark data.
            benchmark_total_return: Total benchmark return for the period.
            model: BHB or Brinson-Fachler.

        Returns:
            BrinsonResult with full decomposition.

        Raises:
            ValueError: If holdings list is empty.
        """
        if not holdings:
            raise ValueError("holdings list cannot be empty")

        portfolio_return = sum(
            h.portfolio_weight * h.portfolio_return for h in holdings
        )

        effects: List[BrinsonEffect] = []
        for h in holdings:
            wp = h.portfolio_weight
            wb = h.benchmark_weight
            rp = h.portfolio_return
            rb = h.benchmark_return
            rb_bench = benchmark_total_return

            if model == AttributionModel.BRINSON:
                alloc = (wp - wb) * (rb - rb_bench)
                sel = wb * (rp - rb)
                inter = (wp - wb) * (rp - rb)
            else:  # BRINSON_FACHLER
                alloc = (wp - wb) * (rb - rb_bench)
                sel = wp * (rp - rb)
                inter = 0.0

            total = alloc + sel + inter
            effects.append(BrinsonEffect(
                category=h.category,
                portfolio_weight=wp,
                benchmark_weight=wb,
                portfolio_return=rp,
                benchmark_return=rb,
                benchmark_total_return=rb_bench,
                allocation_effect=alloc,
                selection_effect=sel,
                interaction_effect=inter,
                total_effect=total,
            ))

        total_alloc = sum(e.allocation_effect for e in effects)
        total_sel = sum(e.selection_effect for e in effects)
        total_inter = sum(e.interaction_effect for e in effects)
        total_explained = total_alloc + total_sel + total_inter
        active = portfolio_return - benchmark_total_return
        unexplained = active - total_explained

        return BrinsonResult(
            model=model,
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_total_return,
            active_return=active,
            total_allocation=total_alloc,
            total_selection=total_sel,
            total_interaction=total_inter,
            total_explained=total_explained,
            unexplained=unexplained,
            category_effects=effects,
        )

    # ------------------------------------------------------------------
    # Factor attribution
    # ------------------------------------------------------------------

    def factor_attribution(
        self,
        factors: List[FactorExposure],
    ) -> List[FactorAttributionResult]:
        """Compute factor-based return attribution.

        For each factor:
            attribution = (portfolio_exposure - benchmark_exposure) * factor_return

        Args:
            factors: List of factor exposures with portfolio/benchmark betas
                     and the factor return for the period.

        Returns:
            List of FactorAttributionResult sorted by |attribution| descending.

        Raises:
            ValueError: If factors list is empty.
        """
        if not factors:
            raise ValueError("factors list cannot be empty")

        results = []
        for f in factors:
            active_exp = f.portfolio_exposure - f.benchmark_exposure
            attr = active_exp * f.factor_return
            results.append(FactorAttributionResult(
                factor_name=f.factor_name,
                portfolio_exposure=f.portfolio_exposure,
                benchmark_exposure=f.benchmark_exposure,
                active_exposure=active_exp,
                factor_return=f.factor_return,
                attribution=attr,
            ))

        return sorted(results, key=lambda r: abs(r.attribution), reverse=True)

    # ------------------------------------------------------------------
    # Currency attribution
    # ------------------------------------------------------------------

    def currency_attribution(
        self,
        currency_holdings: List[Tuple[str, float, float, float]],
    ) -> List[FactorAttributionResult]:
        """Estimate currency contribution to active return.

        For each currency:
            attribution ≈ (portfolio_weight - benchmark_weight) * currency_return

        Args:
            currency_holdings: List of (currency, portfolio_weight, benchmark_weight,
                                        currency_return) tuples.

        Returns:
            List of FactorAttributionResult sorted by |attribution| descending.
        """
        results = []
        for currency, pw, bw, cret in currency_holdings:
            active = pw - bw
            attr = active * cret
            results.append(FactorAttributionResult(
                factor_name=currency,
                portfolio_exposure=pw,
                benchmark_exposure=bw,
                active_exposure=active,
                factor_return=cret,
                attribution=attr,
            ))
        return sorted(results, key=lambda r: abs(r.attribution), reverse=True)

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def full_report(
        self,
        sector_holdings: List[Holding],
        benchmark_total_return: float,
        country_holdings: Optional[List[Holding]] = None,
        currency_holdings: Optional[List[Tuple[str, float, float, float]]] = None,
        factor_exposures: Optional[List[FactorExposure]] = None,
        active_return_series: Optional[List[float]] = None,
        periods_per_year: int = 252,
        model: AttributionModel = AttributionModel.BRINSON,
    ) -> FullAttributionReport:
        """Generate a full attribution report across all dimensions.

        Args:
            sector_holdings: Sector-level Brinson input.
            benchmark_total_return: Total benchmark return.
            country_holdings: Optional country-level Brinson input.
            currency_holdings: Optional list of (ccy, pw, bw, ret) tuples.
            factor_exposures: Optional factor betas and returns.
            active_return_series: Optional series for IR / TE computation.
            periods_per_year: Annualisation factor (252 for daily).
            model: Brinson model variant.

        Returns:
            FullAttributionReport.
        """
        sector_brinson = self.brinson_attribution(
            sector_holdings, benchmark_total_return, model
        )
        portfolio_return = sector_brinson.portfolio_return
        active_return = sector_brinson.active_return

        country_brinson = None
        if country_holdings:
            country_brinson = self.brinson_attribution(
                country_holdings, benchmark_total_return, model
            )

        ccy_attr: List[FactorAttributionResult] = []
        if currency_holdings:
            ccy_attr = self.currency_attribution(currency_holdings)

        factor_attr: List[FactorAttributionResult] = []
        if factor_exposures:
            factor_attr = self.factor_attribution(factor_exposures)

        ir = 0.0
        te = 0.0
        if active_return_series and len(active_return_series) > 1:
            n = len(active_return_series)
            mean_ar = sum(active_return_series) / n
            variance = sum((r - mean_ar) ** 2 for r in active_return_series) / (n - 1)
            te_period = math.sqrt(variance)
            te = te_period * math.sqrt(periods_per_year)
            ir = (mean_ar * periods_per_year) / te if te > 0 else 0.0

        return FullAttributionReport(
            brinson=sector_brinson,
            country_brinson=country_brinson,
            currency_attribution=ccy_attr,
            factor_attribution=factor_attr,
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_total_return,
            active_return=active_return,
            information_ratio=ir,
            tracking_error=te,
        )

    # ------------------------------------------------------------------
    # Decompose active return
    # ------------------------------------------------------------------

    def decompose_active_return(
        self,
        holdings: List[Holding],
        benchmark_total_return: float,
    ) -> Dict:
        """Summarise active return decomposition into BHB components.

        Args:
            holdings: Per-category holding data.
            benchmark_total_return: Total benchmark return.

        Returns:
            Dict with allocation, selection, interaction, and active return.
        """
        result = self.brinson_attribution(holdings, benchmark_total_return)
        return {
            "active_return": round(result.active_return, 6),
            "allocation_effect": round(result.total_allocation, 6),
            "selection_effect": round(result.total_selection, 6),
            "interaction_effect": round(result.total_interaction, 6),
            "total_explained": round(result.total_explained, 6),
            "unexplained": round(result.unexplained, 6),
        }

    # ------------------------------------------------------------------
    # Information ratio
    # ------------------------------------------------------------------

    def information_ratio(
        self,
        active_returns: List[float],
        periods_per_year: int = 252,
    ) -> float:
        """Compute annualised Information Ratio from active return series.

        IR = mean(active_returns) / std(active_returns) * sqrt(periods_per_year)

        Args:
            active_returns: Period active returns (portfolio - benchmark).
            periods_per_year: Annualisation factor.

        Returns:
            Annualised Information Ratio.

        Raises:
            ValueError: If active_returns has fewer than 2 observations.
        """
        if len(active_returns) < 2:
            raise ValueError("Need at least 2 active return observations")
        n = len(active_returns)
        mean_ar = sum(active_returns) / n
        variance = sum((r - mean_ar) ** 2 for r in active_returns) / (n - 1)
        te = math.sqrt(variance) * math.sqrt(periods_per_year)
        if te == 0:
            return 0.0
        return (mean_ar * periods_per_year) / te

    # ------------------------------------------------------------------
    # Tracking error
    # ------------------------------------------------------------------

    def tracking_error(
        self,
        active_returns: List[float],
        periods_per_year: int = 252,
    ) -> float:
        """Compute annualised Tracking Error from active return series.

        Args:
            active_returns: Period active returns.
            periods_per_year: Annualisation factor.

        Returns:
            Annualised Tracking Error.

        Raises:
            ValueError: If active_returns has fewer than 2 observations.
        """
        if len(active_returns) < 2:
            raise ValueError("Need at least 2 active return observations")
        n = len(active_returns)
        mean_ar = sum(active_returns) / n
        variance = sum((r - mean_ar) ** 2 for r in active_returns) / (n - 1)
        return math.sqrt(variance) * math.sqrt(periods_per_year)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_performance_attribution: Optional[PerformanceAttributionEngine] = None


def get_performance_attribution_engine() -> PerformanceAttributionEngine:
    """Return the singleton PerformanceAttributionEngine instance.

    Returns:
        Shared PerformanceAttributionEngine instance.
    """
    global _default_performance_attribution
    if _default_performance_attribution is None:
        _default_performance_attribution = PerformanceAttributionEngine()
    return _default_performance_attribution
