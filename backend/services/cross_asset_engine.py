"""M16 Phase 2 — Cross-Asset Analytics Engine.

Deterministic cross-asset analytics: correlation matrices, rolling betas,
lead-lag analysis, spillover scores, and risk transmission matrices.
Pure Python, in-memory, no external dependencies.
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
    """Arithmetic mean of a numeric list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _variance(values: List[float], ddof: int = 1) -> float:
    """Sample variance (ddof=1) or population variance (ddof=0)."""
    n = len(values)
    if n <= ddof:
        return 0.0
    m = _mean(values)
    return sum((x - m) ** 2 for x in values) / (n - ddof)


def _std(values: List[float], ddof: int = 1) -> float:
    """Standard deviation."""
    return math.sqrt(_variance(values, ddof))


def _covariance(x: List[float], y: List[float]) -> float:
    """Sample covariance between two equal-length series."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    mx, my = _mean(x[:n]), _mean(y[:n])
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)


def _correlation(x: List[float], y: List[float]) -> float:
    """Pearson correlation coefficient clamped to [-1, 1]."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    sx, sy = _std(x[:n]), _std(y[:n])
    if sx == 0.0 or sy == 0.0:
        return 0.0
    return max(-1.0, min(1.0, _covariance(x[:n], y[:n]) / (sx * sy)))


def _ols_beta(y: List[float], x: List[float]) -> float:
    """OLS slope coefficient β in y = α + β·x."""
    n = min(len(y), len(x))
    if n < 2:
        return 0.0
    var_x = _variance(x[:n])
    if var_x == 0.0:
        return 0.0
    return _covariance(y[:n], x[:n]) / var_x


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CorrelationMethod(str, Enum):
    PEARSON = "pearson"
    ROLLING = "rolling"
    RANK = "rank"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CorrelationMatrix:
    """Full pairwise correlation matrix.

    Attributes:
        tickers: Ordered list of ticker symbols.
        matrix: Symmetric correlation matrix (n×n) as list of lists.
        method: Correlation computation method.
        window: Rolling window size (None = full series).
    """
    tickers: List[str]
    matrix: List[List[float]]
    method: CorrelationMethod
    window: Optional[int]

    def get(self, ticker_a: str, ticker_b: str) -> Optional[float]:
        """Return correlation between two tickers.

        Args:
            ticker_a: First ticker.
            ticker_b: Second ticker.

        Returns:
            Correlation coefficient or None if not found.
        """
        try:
            i = self.tickers.index(ticker_a)
            j = self.tickers.index(ticker_b)
            return self.matrix[i][j]
        except ValueError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "tickers": self.tickers,
            "matrix": self.matrix,
            "method": self.method.value,
            "window": self.window,
        }


@dataclass
class RollingCorrelation:
    """Time-series of rolling correlations between two assets.

    Attributes:
        ticker_a: First ticker.
        ticker_b: Second ticker.
        window: Rolling window size.
        correlations: Correlation values per period.
        mean_correlation: Average over the series.
        min_correlation: Minimum correlation.
        max_correlation: Maximum correlation.
    """
    ticker_a: str
    ticker_b: str
    window: int
    correlations: List[float]
    mean_correlation: float
    min_correlation: float
    max_correlation: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker_a": self.ticker_a,
            "ticker_b": self.ticker_b,
            "window": self.window,
            "correlations": self.correlations,
            "mean_correlation": round(self.mean_correlation, 6),
            "min_correlation": round(self.min_correlation, 6),
            "max_correlation": round(self.max_correlation, 6),
        }


@dataclass
class DynamicBeta:
    """Rolling beta of an asset against a benchmark.

    Attributes:
        ticker: Asset ticker.
        benchmark: Benchmark ticker.
        window: Rolling window.
        betas: Beta values per rolling period.
        mean_beta: Average beta.
        current_beta: Most recent beta value.
    """
    ticker: str
    benchmark: str
    window: int
    betas: List[float]
    mean_beta: float
    current_beta: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "benchmark": self.benchmark,
            "window": self.window,
            "betas": self.betas,
            "mean_beta": round(self.mean_beta, 6),
            "current_beta": round(self.current_beta, 6),
        }


@dataclass
class RelativeStrength:
    """Relative strength of an asset vs a benchmark.

    Attributes:
        ticker: Asset ticker.
        benchmark: Benchmark ticker.
        period: Number of periods analysed.
        rs_ratio: Asset cumulative return / benchmark cumulative return.
        active_return: Cumulative excess return.
        tracking_error: Annualised tracking error.
        information_ratio: Active return / tracking error.
        outperforming: Whether asset outperformed benchmark.
    """
    ticker: str
    benchmark: str
    period: int
    rs_ratio: float
    active_return: float
    tracking_error: float
    information_ratio: float
    outperforming: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker": self.ticker,
            "benchmark": self.benchmark,
            "period": self.period,
            "rs_ratio": round(self.rs_ratio, 6),
            "active_return": round(self.active_return, 6),
            "tracking_error": round(self.tracking_error, 6),
            "information_ratio": round(self.information_ratio, 6),
            "outperforming": self.outperforming,
        }


@dataclass
class SpilloverResult:
    """Directional return spillover between a source and target.

    Attributes:
        source: Source ticker.
        target: Target ticker.
        lag: Lead/lag in periods.
        correlation_at_lag: Correlation at the specified lag.
        spillover_score: Normalised spillover magnitude [0, 1].
        direction: Positive (source leads positively) or negative.
    """
    source: str
    target: str
    lag: int
    correlation_at_lag: float
    spillover_score: float
    direction: str  # "positive" | "negative" | "neutral"

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "lag": self.lag,
            "correlation_at_lag": round(self.correlation_at_lag, 6),
            "spillover_score": round(self.spillover_score, 6),
            "direction": self.direction,
        }


@dataclass
class LeadLagResult:
    """Lead-lag relationship scan between two assets.

    Attributes:
        ticker_a: First ticker.
        ticker_b: Second ticker.
        max_lag: Maximum lag tested.
        correlations_by_lag: Dict mapping lag -> correlation.
        optimal_lag: Lag with highest absolute correlation.
        optimal_correlation: Correlation at optimal lag.
        leader: Ticker that leads ('a', 'b', or 'neither').
    """
    ticker_a: str
    ticker_b: str
    max_lag: int
    correlations_by_lag: Dict[int, float]
    optimal_lag: int
    optimal_correlation: float
    leader: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "ticker_a": self.ticker_a,
            "ticker_b": self.ticker_b,
            "max_lag": self.max_lag,
            "correlations_by_lag": {str(k): round(v, 6) for k, v in self.correlations_by_lag.items()},
            "optimal_lag": self.optimal_lag,
            "optimal_correlation": round(self.optimal_correlation, 6),
            "leader": self.leader,
        }


@dataclass
class RiskTransmissionMatrix:
    """Matrix of pairwise risk transmission scores.

    Attributes:
        tickers: Ordered ticker list.
        matrix: n×n transmission scores (source i → target j).
        net_transmitters: Tickers that transmit more risk than they receive.
        net_receivers: Tickers that receive more risk than they transmit.
    """
    tickers: List[str]
    matrix: List[List[float]]
    net_transmitters: List[str]
    net_receivers: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to plain dictionary."""
        return {
            "tickers": self.tickers,
            "matrix": [[round(v, 6) for v in row] for row in self.matrix],
            "net_transmitters": self.net_transmitters,
            "net_receivers": self.net_receivers,
        }


# ---------------------------------------------------------------------------
# CrossAssetEngine
# ---------------------------------------------------------------------------

class CrossAssetEngine:
    """Deterministic cross-asset analytics engine.

    Computes correlation matrices, rolling betas, relative strength,
    lead-lag relationships, spillover scores, and risk transmission matrices
    using pure Python arithmetic with no external dependencies.
    """

    # ------------------------------------------------------------------
    # Correlation matrix
    # ------------------------------------------------------------------

    def correlation_matrix(
        self,
        returns_map: Dict[str, List[float]],
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        window: Optional[int] = None,
    ) -> CorrelationMatrix:
        """Compute pairwise correlation matrix.

        Args:
            returns_map: Dict mapping ticker -> daily return series.
            method: Correlation method.
            window: Optional tail window; None = full series.

        Returns:
            CorrelationMatrix with n×n values.
        """
        tickers = sorted(returns_map.keys())
        n = len(tickers)
        series = {t: returns_map[t][-window:] if window else returns_map[t] for t in tickers}

        if method == CorrelationMethod.RANK:
            series = {t: self._rank_series(series[t]) for t in tickers}

        mat = [[0.0] * n for _ in range(n)]
        for i in range(n):
            mat[i][i] = 1.0
            for j in range(i + 1, n):
                c = _correlation(series[tickers[i]], series[tickers[j]])
                mat[i][j] = round(c, 6)
                mat[j][i] = round(c, 6)
        return CorrelationMatrix(tickers=tickers, matrix=mat, method=method, window=window)

    def _rank_series(self, values: List[float]) -> List[float]:
        """Convert a value series to rank series (Spearman base).

        Args:
            values: Numeric series.

        Returns:
            Rank series (1-based).
        """
        indexed = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0.0] * len(values)
        for rank, (idx, _) in enumerate(indexed, start=1):
            ranks[idx] = float(rank)
        return ranks

    # ------------------------------------------------------------------
    # Rolling correlation
    # ------------------------------------------------------------------

    def rolling_correlation(
        self,
        returns_a: List[float],
        returns_b: List[float],
        ticker_a: str,
        ticker_b: str,
        window: int = 20,
    ) -> RollingCorrelation:
        """Compute rolling Pearson correlation between two return series.

        Args:
            returns_a: Return series for asset A.
            returns_b: Return series for asset B.
            ticker_a: Ticker of asset A.
            ticker_b: Ticker of asset B.
            window: Rolling window size.

        Returns:
            RollingCorrelation with per-period values.
        """
        n = min(len(returns_a), len(returns_b))
        corrs: List[float] = []
        for i in range(window, n + 1):
            c = _correlation(returns_a[i - window:i], returns_b[i - window:i])
            corrs.append(round(c, 6))
        if not corrs:
            corrs = [0.0]
        return RollingCorrelation(
            ticker_a=ticker_a,
            ticker_b=ticker_b,
            window=window,
            correlations=corrs,
            mean_correlation=round(_mean(corrs), 6),
            min_correlation=round(min(corrs), 6),
            max_correlation=round(max(corrs), 6),
        )

    # ------------------------------------------------------------------
    # Dynamic beta
    # ------------------------------------------------------------------

    def dynamic_beta(
        self,
        asset_returns: List[float],
        benchmark_returns: List[float],
        ticker: str,
        benchmark: str,
        window: int = 20,
    ) -> DynamicBeta:
        """Compute rolling OLS beta of asset against benchmark.

        Args:
            asset_returns: Return series for the asset.
            benchmark_returns: Return series for the benchmark.
            ticker: Asset ticker.
            benchmark: Benchmark ticker.
            window: Rolling window size.

        Returns:
            DynamicBeta with rolling beta time-series.
        """
        n = min(len(asset_returns), len(benchmark_returns))
        betas: List[float] = []
        for i in range(window, n + 1):
            b = _ols_beta(asset_returns[i - window:i], benchmark_returns[i - window:i])
            betas.append(round(b, 6))
        if not betas:
            betas = [0.0]
        return DynamicBeta(
            ticker=ticker,
            benchmark=benchmark,
            window=window,
            betas=betas,
            mean_beta=round(_mean(betas), 6),
            current_beta=betas[-1],
        )

    def static_beta(
        self,
        asset_returns: List[float],
        benchmark_returns: List[float],
    ) -> float:
        """Compute full-period OLS beta.

        Args:
            asset_returns: Asset return series.
            benchmark_returns: Benchmark return series.

        Returns:
            Beta coefficient.
        """
        return round(_ols_beta(asset_returns, benchmark_returns), 6)

    # ------------------------------------------------------------------
    # Relative strength
    # ------------------------------------------------------------------

    def relative_strength(
        self,
        asset_returns: List[float],
        benchmark_returns: List[float],
        ticker: str,
        benchmark: str,
    ) -> RelativeStrength:
        """Compute relative strength and information ratio.

        Args:
            asset_returns: Asset return series.
            benchmark_returns: Benchmark return series.
            ticker: Asset ticker.
            benchmark: Benchmark ticker.

        Returns:
            RelativeStrength with cumulative return comparison.
        """
        n = min(len(asset_returns), len(benchmark_returns))
        a = asset_returns[:n]
        b = benchmark_returns[:n]

        cum_asset = sum(a)
        cum_bench = sum(b)
        active_returns = [a[i] - b[i] for i in range(n)]
        active_return = sum(active_returns)
        te = _std(active_returns) * math.sqrt(252) if len(active_returns) > 1 else 0.0
        ir = (active_return / te) if te > 0 else 0.0
        rs_ratio = (1 + cum_asset) / (1 + cum_bench) if cum_bench != -1.0 else 0.0

        return RelativeStrength(
            ticker=ticker,
            benchmark=benchmark,
            period=n,
            rs_ratio=round(rs_ratio, 6),
            active_return=round(active_return, 6),
            tracking_error=round(te, 6),
            information_ratio=round(ir, 6),
            outperforming=active_return > 0,
        )

    # ------------------------------------------------------------------
    # Lead-Lag analysis
    # ------------------------------------------------------------------

    def lead_lag_analysis(
        self,
        returns_a: List[float],
        returns_b: List[float],
        ticker_a: str,
        ticker_b: str,
        max_lag: int = 5,
    ) -> LeadLagResult:
        """Scan lead-lag correlations between two series.

        A positive optimal_lag means ticker_a leads ticker_b.
        A negative optimal_lag means ticker_b leads ticker_a.

        Args:
            returns_a: Return series for asset A.
            returns_b: Return series for asset B.
            ticker_a: Ticker A.
            ticker_b: Ticker B.
            max_lag: Maximum absolute lag to test.

        Returns:
            LeadLagResult with optimal lag and direction.
        """
        n = min(len(returns_a), len(returns_b))
        corrs_by_lag: Dict[int, float] = {}

        for lag in range(-max_lag, max_lag + 1):
            if lag == 0:
                c = _correlation(returns_a[:n], returns_b[:n])
            elif lag > 0:
                # a leads b by lag periods
                c = _correlation(returns_a[:n - lag], returns_b[lag:n])
            else:
                # b leads a by abs(lag) periods
                c = _correlation(returns_a[-lag:n], returns_b[:n + lag])
            corrs_by_lag[lag] = round(c, 6)

        optimal_lag = max(corrs_by_lag, key=lambda k: abs(corrs_by_lag[k]))
        opt_corr = corrs_by_lag[optimal_lag]

        if optimal_lag > 0:
            leader = "a"
        elif optimal_lag < 0:
            leader = "b"
        else:
            leader = "neither"

        return LeadLagResult(
            ticker_a=ticker_a,
            ticker_b=ticker_b,
            max_lag=max_lag,
            correlations_by_lag=corrs_by_lag,
            optimal_lag=optimal_lag,
            optimal_correlation=opt_corr,
            leader=leader,
        )

    # ------------------------------------------------------------------
    # Spillover
    # ------------------------------------------------------------------

    def spillover_score(
        self,
        source_returns: List[float],
        target_returns: List[float],
        source: str,
        target: str,
        lag: int = 1,
    ) -> SpilloverResult:
        """Compute directional return spillover from source to target at given lag.

        Args:
            source_returns: Source asset return series.
            target_returns: Target asset return series.
            source: Source ticker.
            target: Target ticker.
            lag: Lag in periods.

        Returns:
            SpilloverResult with correlation and spillover score.
        """
        n = min(len(source_returns), len(target_returns))
        if lag >= n:
            lag = 1
        c = _correlation(source_returns[:n - lag], target_returns[lag:n])
        score = round(abs(c), 6)
        direction = "positive" if c > 0.05 else "negative" if c < -0.05 else "neutral"
        return SpilloverResult(
            source=source,
            target=target,
            lag=lag,
            correlation_at_lag=round(c, 6),
            spillover_score=score,
            direction=direction,
        )

    def spillover_matrix(
        self,
        returns_map: Dict[str, List[float]],
        lag: int = 1,
    ) -> Dict[str, Any]:
        """Compute full n×n spillover matrix.

        Args:
            returns_map: Dict ticker -> returns.
            lag: Spillover lag in periods.

        Returns:
            Dict with tickers, matrix, and top spillover pairs.
        """
        tickers = sorted(returns_map.keys())
        n = len(tickers)
        mat = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    res = self.spillover_score(
                        returns_map[tickers[i]], returns_map[tickers[j]], tickers[i], tickers[j], lag
                    )
                    mat[i][j] = res.spillover_score
        return {
            "tickers": tickers,
            "matrix": [[round(v, 6) for v in row] for row in mat],
            "lag": lag,
        }

    # ------------------------------------------------------------------
    # Risk Transmission Matrix
    # ------------------------------------------------------------------

    def risk_transmission_matrix(
        self,
        returns_map: Dict[str, List[float]],
        volatility_window: int = 20,
    ) -> RiskTransmissionMatrix:
        """Compute n×n risk transmission matrix using volatility spillover.

        Entry [i][j] = how much of asset i's volatility shock transmits to j.
        Based on rolling correlation of absolute returns.

        Args:
            returns_map: Dict ticker -> return series.
            volatility_window: Window for volatility estimation.

        Returns:
            RiskTransmissionMatrix with net transmitters/receivers.
        """
        tickers = sorted(returns_map.keys())
        n = len(tickers)
        abs_returns = {t: [abs(r) for r in returns_map[t]] for t in tickers}

        mat = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    mat[i][j] = 0.0
                else:
                    c = _correlation(abs_returns[tickers[i]], abs_returns[tickers[j]])
                    mat[i][j] = round(max(0.0, c), 6)

        row_sums = [sum(mat[i]) for i in range(n)]
        col_sums = [sum(mat[i][j] for i in range(n)) for j in range(n)]

        net_transmitters = [tickers[i] for i in range(n) if row_sums[i] > col_sums[i]]
        net_receivers = [tickers[i] for i in range(n) if col_sums[i] > row_sums[i]]

        return RiskTransmissionMatrix(
            tickers=tickers,
            matrix=mat,
            net_transmitters=net_transmitters,
            net_receivers=net_receivers,
        )

    # ------------------------------------------------------------------
    # Market synchronization
    # ------------------------------------------------------------------

    def market_synchronization(self, returns_map: Dict[str, List[float]]) -> Dict[str, Any]:
        """Compute pairwise average correlation as a synchronization score.

        Args:
            returns_map: Dict ticker -> return series.

        Returns:
            Dict with synchronization_score [0,1] and pairwise summary.
        """
        tickers = sorted(returns_map.keys())
        n = len(tickers)
        if n < 2:
            return {"synchronization_score": 0.0, "n_assets": n, "avg_pairwise_correlation": 0.0}

        total = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                c = _correlation(returns_map[tickers[i]], returns_map[tickers[j]])
                total += c
                count += 1

        avg = total / count if count else 0.0
        sync_score = round(max(0.0, min(1.0, (avg + 1) / 2)), 6)
        return {
            "synchronization_score": sync_score,
            "n_assets": n,
            "avg_pairwise_correlation": round(avg, 6),
        }

    # ------------------------------------------------------------------
    # Cross-market dependency graph
    # ------------------------------------------------------------------

    def dependency_graph(
        self,
        returns_map: Dict[str, List[float]],
        threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """Build a dependency graph where edges indicate |correlation| ≥ threshold.

        Args:
            returns_map: Dict ticker -> returns.
            threshold: Minimum absolute correlation for an edge.

        Returns:
            Dict with nodes, edges, and cluster assignments.
        """
        tickers = sorted(returns_map.keys())
        n = len(tickers)
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                c = _correlation(returns_map[tickers[i]], returns_map[tickers[j]])
                if abs(c) >= threshold:
                    edges.append({
                        "source": tickers[i],
                        "target": tickers[j],
                        "weight": round(c, 6),
                    })
        # Degree centrality
        degrees = {t: 0 for t in tickers}
        for e in edges:
            degrees[e["source"]] += 1
            degrees[e["target"]] += 1

        return {
            "nodes": [{"ticker": t, "degree": degrees[t]} for t in tickers],
            "edges": edges,
            "n_nodes": n,
            "n_edges": len(edges),
            "threshold": threshold,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_cross_asset_engine: Optional[CrossAssetEngine] = None


def get_cross_asset_engine() -> CrossAssetEngine:
    """Return the singleton CrossAssetEngine instance.

    Returns:
        Shared CrossAssetEngine instance.
    """
    global _default_cross_asset_engine
    if _default_cross_asset_engine is None:
        _default_cross_asset_engine = CrossAssetEngine()
    return _default_cross_asset_engine
