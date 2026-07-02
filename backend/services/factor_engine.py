"""M16 Phase 3 — Multi-Factor Analytics Engine.

Deterministic factor analytics: 10 classic factors, exposure computation,
factor returns, attribution, and factor clustering using pure Python.
No scipy, numpy, or external libraries.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Pure-Python statistical primitives
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    """Arithmetic mean."""
    return sum(values) / len(values) if values else 0.0


def _variance(values: List[float], ddof: int = 1) -> float:
    """Sample or population variance."""
    n = len(values)
    if n <= ddof:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (n - ddof)


def _std(values: List[float], ddof: int = 1) -> float:
    """Standard deviation."""
    return math.sqrt(_variance(values, ddof))


def _zscore(values: List[float]) -> List[float]:
    """Z-score normalise a list in-place (returns new list)."""
    m = _mean(values)
    s = _std(values)
    if s == 0.0:
        return [0.0] * len(values)
    return [(v - m) / s for v in values]


def _covariance(x: List[float], y: List[float]) -> float:
    """Sample covariance."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    mx, my = _mean(x[:n]), _mean(y[:n])
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)


def _ols(y: List[float], x: List[float]) -> Tuple[float, float]:
    """OLS regression — returns (alpha, beta)."""
    n = min(len(y), len(x))
    if n < 2:
        return 0.0, 0.0
    vx = _variance(x[:n])
    if vx == 0.0:
        return _mean(y[:n]), 0.0
    b = _covariance(y[:n], x[:n]) / vx
    a = _mean(y[:n]) - b * _mean(x[:n])
    return a, b


# ---------------------------------------------------------------------------
# Factor identifiers
# ---------------------------------------------------------------------------

class FactorType(str, Enum):
    MARKET = "market"
    SIZE = "size"
    VALUE = "value"
    MOMENTUM = "momentum"
    QUALITY = "quality"
    LOW_VOLATILITY = "low_volatility"
    GROWTH = "growth"
    PROFITABILITY = "profitability"
    INVESTMENT = "investment"
    DIVIDEND_YIELD = "dividend_yield"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FactorExposure:
    """Factor exposures (loadings) for a single asset.

    Attributes:
        ticker: Asset ticker.
        exposures: Dict mapping FactorType -> z-score exposure.
        dominant_factor: Factor with largest absolute exposure.
    """
    ticker: str
    exposures: Dict[FactorType, float]
    dominant_factor: FactorType

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "exposures": {k.value: round(v, 6) for k, v in self.exposures.items()},
            "dominant_factor": self.dominant_factor.value,
        }


@dataclass
class FactorReturn:
    """Period return attributed to a single factor.

    Attributes:
        factor: Factor type.
        period_return: Return for the period.
        cumulative_return: Cumulative return over all periods.
        volatility: Annualised return volatility.
        sharpe: Sharpe ratio (annualised, risk-free = 0).
        hit_rate: Fraction of periods with positive return.
    """
    factor: FactorType
    period_return: float
    cumulative_return: float
    volatility: float
    sharpe: float
    hit_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "factor": self.factor.value,
            "period_return": round(self.period_return, 6),
            "cumulative_return": round(self.cumulative_return, 6),
            "volatility": round(self.volatility, 6),
            "sharpe": round(self.sharpe, 6),
            "hit_rate": round(self.hit_rate, 6),
        }


@dataclass
class FactorAttribution:
    """Return attribution for a portfolio across factors.

    Attributes:
        ticker: Asset ticker.
        total_return: Total return of the asset.
        factor_contributions: Dict mapping factor -> attributed return.
        idiosyncratic_return: Unexplained residual.
        r_squared: Model R² of factor explanation.
    """
    ticker: str
    total_return: float
    factor_contributions: Dict[FactorType, float]
    idiosyncratic_return: float
    r_squared: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "total_return": round(self.total_return, 6),
            "factor_contributions": {k.value: round(v, 6) for k, v in self.factor_contributions.items()},
            "idiosyncratic_return": round(self.idiosyncratic_return, 6),
            "r_squared": round(self.r_squared, 6),
        }


@dataclass
class FactorCluster:
    """Cluster of correlated factors.

    Attributes:
        cluster_id: Numeric cluster index.
        factors: Member factor types.
        centroid_factor: Representative factor (closest to cluster mean).
    """
    cluster_id: int
    factors: List[FactorType]
    centroid_factor: FactorType

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "cluster_id": self.cluster_id,
            "factors": [f.value for f in self.factors],
            "centroid_factor": self.centroid_factor.value,
        }


# ---------------------------------------------------------------------------
# FactorEngine
# ---------------------------------------------------------------------------

class FactorEngine:
    """Multi-factor analytics engine.

    Computes factor exposures, factor returns, attribution, and clustering
    using pure Python arithmetic — no scipy or numpy.

    All methods are stateless; inputs are passed directly as arguments.
    """

    ALL_FACTORS: List[FactorType] = list(FactorType)

    # ------------------------------------------------------------------
    # Factor score computation from raw characteristics
    # ------------------------------------------------------------------

    def compute_market_exposure(self, asset_returns: List[float], market_returns: List[float]) -> float:
        """OLS beta of asset against market factor.

        Args:
            asset_returns: Asset return series.
            market_returns: Market return series.

        Returns:
            Market beta exposure.
        """
        _, b = _ols(asset_returns, market_returns)
        return round(b, 6)

    def compute_size_score(self, market_cap: float, universe_caps: List[float]) -> float:
        """Size factor exposure — z-score of log(market_cap).

        Smaller cap → higher (positive) size exposure in SMB convention.

        Args:
            market_cap: Market capitalisation in USD millions.
            universe_caps: All market caps in universe.

        Returns:
            Size z-score (negative = large cap).
        """
        if not universe_caps or market_cap <= 0:
            return 0.0
        log_caps = [math.log(max(1.0, c)) for c in universe_caps]
        log_me = math.log(max(1.0, market_cap))
        zs = _zscore(log_caps)
        idx = min(range(len(universe_caps)), key=lambda i: abs(universe_caps[i] - market_cap))
        return round(-zs[idx], 6)  # negate: small = positive exposure

    def compute_value_score(self, book_to_market: float, universe_btm: List[float]) -> float:
        """Value factor exposure — z-score of book-to-market ratio.

        Args:
            book_to_market: Asset's book-to-market ratio.
            universe_btm: All book-to-market ratios in universe.

        Returns:
            Value z-score.
        """
        if not universe_btm:
            return 0.0
        zs = _zscore(universe_btm)
        idx = min(range(len(universe_btm)), key=lambda i: abs(universe_btm[i] - book_to_market))
        return round(zs[idx], 6)

    def compute_momentum_score(self, returns: List[float], lookback: int = 12) -> float:
        """Momentum factor — sum of returns over lookback period (skip last month).

        Args:
            returns: Monthly return series (oldest first).
            lookback: Lookback in months.

        Returns:
            Momentum score (cumulative return over lookback, skipping last).
        """
        if len(returns) < 2:
            return 0.0
        window = returns[-(lookback + 1):-1]
        return round(sum(window), 6)

    def compute_quality_score(
        self,
        roe: float,
        debt_to_equity: float,
        earnings_stability: float,
    ) -> float:
        """Quality factor composite.

        Higher ROE, lower D/E, and more stable earnings → higher quality.

        Args:
            roe: Return on equity (0-1 scale).
            debt_to_equity: Debt-to-equity ratio.
            earnings_stability: Earnings stability score (0-1, higher = more stable).

        Returns:
            Quality composite z-score.
        """
        raw = roe - 0.5 * debt_to_equity + earnings_stability
        return round(raw, 6)

    def compute_low_vol_score(self, returns: List[float]) -> float:
        """Low-volatility factor — negative of realised volatility.

        Args:
            returns: Return series.

        Returns:
            Negative annualised volatility (higher = lower risk).
        """
        vol = _std(returns) * math.sqrt(252) if len(returns) > 1 else 0.0
        return round(-vol, 6)

    def compute_growth_score(
        self,
        revenue_growth: float,
        earnings_growth: float,
    ) -> float:
        """Growth factor composite.

        Args:
            revenue_growth: YoY revenue growth rate.
            earnings_growth: YoY earnings growth rate.

        Returns:
            Growth composite score.
        """
        return round(0.5 * revenue_growth + 0.5 * earnings_growth, 6)

    def compute_profitability_score(self, gross_profit_to_assets: float) -> float:
        """Profitability factor — Novy-Marx gross profit / total assets.

        Args:
            gross_profit_to_assets: Gross profit / total assets ratio.

        Returns:
            Profitability score.
        """
        return round(gross_profit_to_assets, 6)

    def compute_investment_score(self, asset_growth: float) -> float:
        """Investment (conservative-minus-aggressive) factor.

        Lower asset growth → higher conservative exposure.

        Args:
            asset_growth: YoY total asset growth rate.

        Returns:
            Investment score (negative of asset growth).
        """
        return round(-asset_growth, 6)

    def compute_dividend_yield_score(
        self,
        dividend_yield: float,
        universe_yields: List[float],
    ) -> float:
        """Dividend yield factor — z-score of yield in universe.

        Args:
            dividend_yield: Asset annual dividend yield (0-1).
            universe_yields: All yields in universe.

        Returns:
            Dividend yield z-score.
        """
        if not universe_yields:
            return 0.0
        zs = _zscore(universe_yields)
        idx = min(range(len(universe_yields)), key=lambda i: abs(universe_yields[i] - dividend_yield))
        return round(zs[idx], 6)

    # ------------------------------------------------------------------
    # Composite exposure object
    # ------------------------------------------------------------------

    def compute_exposures(
        self,
        ticker: str,
        factor_scores: Dict[FactorType, float],
    ) -> FactorExposure:
        """Wrap precomputed factor scores into a FactorExposure.

        Args:
            ticker: Asset ticker.
            factor_scores: Dict mapping FactorType -> score.

        Returns:
            FactorExposure with dominant factor identified.
        """
        if not factor_scores:
            dominant = FactorType.MARKET
        else:
            dominant = max(factor_scores, key=lambda f: abs(factor_scores[f]))
        return FactorExposure(ticker=ticker, exposures=factor_scores, dominant_factor=dominant)

    # ------------------------------------------------------------------
    # Factor returns
    # ------------------------------------------------------------------

    def compute_factor_returns(
        self,
        factor: FactorType,
        long_returns: List[float],
        short_returns: List[float],
    ) -> FactorReturn:
        """Compute factor return statistics from long-short portfolio.

        Args:
            factor: Factor type.
            long_returns: Returns of the long leg (high-exposure assets).
            short_returns: Returns of the short leg (low-exposure assets).

        Returns:
            FactorReturn with performance statistics.
        """
        n = min(len(long_returns), len(short_returns))
        factor_rets = [long_returns[i] - short_returns[i] for i in range(n)]
        if not factor_rets:
            return FactorReturn(
                factor=factor,
                period_return=0.0,
                cumulative_return=0.0,
                volatility=0.0,
                sharpe=0.0,
                hit_rate=0.0,
            )
        cum = sum(factor_rets)
        vol = _std(factor_rets) * math.sqrt(252) if len(factor_rets) > 1 else 0.0
        sharpe = (sum(factor_rets) / len(factor_rets) * 252) / vol if vol > 0 else 0.0
        hit_rate = sum(1 for r in factor_rets if r > 0) / len(factor_rets)
        return FactorReturn(
            factor=factor,
            period_return=round(factor_rets[-1], 6),
            cumulative_return=round(cum, 6),
            volatility=round(vol, 6),
            sharpe=round(sharpe, 6),
            hit_rate=round(hit_rate, 6),
        )

    # ------------------------------------------------------------------
    # Attribution
    # ------------------------------------------------------------------

    def attribute_returns(
        self,
        ticker: str,
        asset_returns: List[float],
        factor_returns_map: Dict[FactorType, List[float]],
        exposures: Dict[FactorType, float],
    ) -> FactorAttribution:
        """Decompose asset returns into factor contributions + idiosyncratic.

        Contribution of factor f = exposure[f] × mean(factor_returns[f]).

        Args:
            ticker: Asset ticker.
            asset_returns: Observed asset return series.
            factor_returns_map: Dict mapping factor -> return series.
            exposures: Dict mapping factor -> exposure score.

        Returns:
            FactorAttribution with per-factor contributions.
        """
        total_return = sum(asset_returns)
        contributions: Dict[FactorType, float] = {}
        explained = 0.0
        for factor, f_rets in factor_returns_map.items():
            exp = exposures.get(factor, 0.0)
            mean_fr = _mean(f_rets) if f_rets else 0.0
            contrib = exp * mean_fr * len(asset_returns)
            contributions[factor] = round(contrib, 6)
            explained += contrib
        idiosyncratic = total_return - explained

        # R² = explained variance / total variance
        var_total = _variance(asset_returns, ddof=0)
        if var_total > 0:
            residuals = [asset_returns[i] - (explained / len(asset_returns)) for i in range(len(asset_returns))]
            var_resid = _variance(residuals, ddof=0)
            r2 = max(0.0, min(1.0, 1.0 - var_resid / var_total))
        else:
            r2 = 1.0

        return FactorAttribution(
            ticker=ticker,
            total_return=round(total_return, 6),
            factor_contributions=contributions,
            idiosyncratic_return=round(idiosyncratic, 6),
            r_squared=round(r2, 6),
        )

    # ------------------------------------------------------------------
    # Factor correlation and clustering
    # ------------------------------------------------------------------

    def factor_correlation(
        self,
        factor_returns_map: Dict[FactorType, List[float]],
    ) -> Dict[str, Any]:
        """Compute pairwise correlation matrix of factor returns.

        Args:
            factor_returns_map: Dict mapping factor -> return series.

        Returns:
            Dict with factors list and correlation matrix.
        """
        factors = sorted(factor_returns_map.keys(), key=lambda f: f.value)
        n = len(factors)
        mat = [[0.0] * n for _ in range(n)]
        for i in range(n):
            mat[i][i] = 1.0
            for j in range(i + 1, n):
                ri = factor_returns_map[factors[i]]
                rj = factor_returns_map[factors[j]]
                length = min(len(ri), len(rj))
                if length < 2:
                    c = 0.0
                else:
                    mi, mj = _mean(ri[:length]), _mean(rj[:length])
                    si = _std(ri[:length])
                    sj = _std(rj[:length])
                    c = _covariance(ri[:length], rj[:length]) / (si * sj) if si > 0 and sj > 0 else 0.0
                c = round(max(-1.0, min(1.0, c)), 6)
                mat[i][j] = c
                mat[j][i] = c
        return {
            "factors": [f.value for f in factors],
            "matrix": mat,
        }

    def cluster_factors(
        self,
        factor_returns_map: Dict[FactorType, List[float]],
        n_clusters: int = 3,
    ) -> List[FactorCluster]:
        """Cluster factors by return correlation using greedy linkage.

        Uses agglomerative-style clustering: repeatedly merge the pair with
        highest average correlation until n_clusters remain.

        Args:
            factor_returns_map: Dict mapping factor -> return series.
            n_clusters: Number of clusters to produce.

        Returns:
            List of FactorCluster objects.
        """
        factors = sorted(factor_returns_map.keys(), key=lambda f: f.value)
        if len(factors) <= n_clusters:
            return [
                FactorCluster(cluster_id=i, factors=[f], centroid_factor=f)
                for i, f in enumerate(factors)
            ]

        # Build correlation matrix
        n = len(factors)
        corr: Dict[Tuple[int, int], float] = {}
        for i in range(n):
            for j in range(i + 1, n):
                ri = factor_returns_map[factors[i]]
                rj = factor_returns_map[factors[j]]
                length = min(len(ri), len(rj))
                if length < 2:
                    c = 0.0
                else:
                    si, sj = _std(ri[:length]), _std(rj[:length])
                    c = _covariance(ri[:length], rj[:length]) / (si * sj) if si > 0 and sj > 0 else 0.0
                corr[(i, j)] = round(c, 6)

        clusters: List[List[int]] = [[i] for i in range(n)]

        while len(clusters) > n_clusters:
            best_pair = (-1, -1)
            best_corr = -999.0
            for a in range(len(clusters)):
                for b in range(a + 1, len(clusters)):
                    total, count = 0.0, 0
                    for i in clusters[a]:
                        for j in clusters[b]:
                            key = (min(i, j), max(i, j))
                            total += corr.get(key, 0.0)
                            count += 1
                    avg = total / count if count else 0.0
                    if avg > best_corr:
                        best_corr = avg
                        best_pair = (a, b)
            a_idx, b_idx = best_pair
            clusters[a_idx] = clusters[a_idx] + clusters[b_idx]
            clusters.pop(b_idx)

        result: List[FactorCluster] = []
        for cluster_id, member_indices in enumerate(clusters):
            members = [factors[i] for i in member_indices]
            # Centroid = member with highest total absolute correlation to others in cluster
            if len(members) == 1:
                centroid = members[0]
            else:
                scores = []
                for idx, f in zip(member_indices, members):
                    total = 0.0
                    for other_idx in member_indices:
                        if other_idx != idx:
                            key = (min(idx, other_idx), max(idx, other_idx))
                            total += abs(corr.get(key, 0.0))
                    scores.append((f, total))
                centroid = max(scores, key=lambda x: x[1])[0]
            result.append(FactorCluster(cluster_id=cluster_id, factors=members, centroid_factor=centroid))
        return result

    # ------------------------------------------------------------------
    # Portfolio-level factor exposure
    # ------------------------------------------------------------------

    def portfolio_factor_exposure(
        self,
        holdings: Dict[str, float],
        asset_exposures: Dict[str, Dict[FactorType, float]],
    ) -> Dict[FactorType, float]:
        """Compute weighted average factor exposure for a portfolio.

        Args:
            holdings: Dict mapping ticker -> portfolio weight (sum to 1).
            asset_exposures: Dict mapping ticker -> factor exposures dict.

        Returns:
            Dict mapping FactorType -> weighted portfolio exposure.
        """
        port_exp: Dict[FactorType, float] = {f: 0.0 for f in FactorType}
        for ticker, weight in holdings.items():
            exps = asset_exposures.get(ticker, {})
            for factor, exp in exps.items():
                port_exp[factor] = port_exp.get(factor, 0.0) + weight * exp
        return {k: round(v, 6) for k, v in port_exp.items()}

    # ------------------------------------------------------------------
    # Factor statistics summary
    # ------------------------------------------------------------------

    def factor_statistics(
        self,
        factor_returns_map: Dict[FactorType, List[float]],
    ) -> Dict[str, Any]:
        """Compute descriptive statistics for each factor return series.

        Args:
            factor_returns_map: Dict mapping factor -> return series.

        Returns:
            Dict mapping factor name -> statistics dict.
        """
        stats: Dict[str, Any] = {}
        for factor, rets in factor_returns_map.items():
            if not rets:
                stats[factor.value] = {}
                continue
            vol = _std(rets) * math.sqrt(252) if len(rets) > 1 else 0.0
            mean_ann = _mean(rets) * 252
            sharpe = mean_ann / vol if vol > 0 else 0.0
            stats[factor.value] = {
                "mean_annual": round(mean_ann, 6),
                "volatility_annual": round(vol, 6),
                "sharpe": round(sharpe, 6),
                "skewness": round(self._skewness(rets), 6),
                "kurtosis": round(self._kurtosis(rets), 6),
                "min": round(min(rets), 6),
                "max": round(max(rets), 6),
                "n_periods": len(rets),
            }
        return stats

    def _skewness(self, values: List[float]) -> float:
        """Pearson skewness of a series."""
        n = len(values)
        if n < 3:
            return 0.0
        m = _mean(values)
        s = _std(values)
        if s == 0.0:
            return 0.0
        return sum(((v - m) / s) ** 3 for v in values) * n / ((n - 1) * (n - 2))

    def _kurtosis(self, values: List[float]) -> float:
        """Excess kurtosis (Fisher definition)."""
        n = len(values)
        if n < 4:
            return 0.0
        m = _mean(values)
        s = _std(values)
        if s == 0.0:
            return 0.0
        raw_kurt = sum(((v - m) / s) ** 4 for v in values) / n
        return raw_kurt - 3.0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_factor_engine: Optional[FactorEngine] = None


def get_factor_engine() -> FactorEngine:
    """Return the singleton FactorEngine instance.

    Returns:
        Shared FactorEngine instance.
    """
    global _default_factor_engine
    if _default_factor_engine is None:
        _default_factor_engine = FactorEngine()
    return _default_factor_engine
