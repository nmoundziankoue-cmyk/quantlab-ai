"""M20 — Strategy Comparison Engine.

Ranks multiple backtested strategies by Sharpe, Sortino, Calmar and other
risk-adjusted metrics.  Produces comparison tables, best-strategy selection,
and head-to-head analyses.  Consumes M19 BacktestEngine by composition.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from services.m19_backtest_engine import BacktestEngine, BacktestResult, Signal, SignalType


# ---------------------------------------------------------------------------
# Domain dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StrategyMetrics:
    """Performance metrics for a single strategy.

    Attributes:
        strategy_id: Unique identifier for this strategy run.
        strategy_name: Human-readable label.
        total_return: Cumulative return over the backtest period.
        annualized_return: Annualised return (CAGR-style).
        sharpe_ratio: Annualised Sharpe (excess return / annual vol).
        sortino_ratio: Sharpe variant penalising only downside volatility.
        calmar_ratio: Annualised return / maximum drawdown (absolute).
        max_drawdown: Worst peak-to-trough decline (negative value).
        win_rate: Fraction of profitable periods.
        volatility: Annualised portfolio volatility.
        num_trades: Total number of completed trades.
        profit_factor: Gross profit / gross loss (0 if no losses).
        expectancy: Average return per trade.
    """

    strategy_id: str
    strategy_name: str
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    volatility: float
    num_trades: int
    profit_factor: float
    expectancy: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "volatility": self.volatility,
            "num_trades": self.num_trades,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
        }


@dataclass
class ComparisonRow:
    """A single row in the strategy comparison table.

    Attributes:
        rank: Position in the ranking for the primary metric.
        strategy_name: Human-readable label.
        metrics: Full metrics object.
        score: Composite normalised score used for ranking.
    """

    rank: int
    strategy_name: str
    metrics: StrategyMetrics
    score: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "rank": self.rank,
            "strategy_name": self.strategy_name,
            "score": round(self.score, 4),
            **self.metrics.to_dict(),
        }


@dataclass
class ComparisonResult:
    """Full multi-strategy comparison result.

    Attributes:
        comparison_id: Unique UUID for this comparison run.
        strategies: All strategy metrics included.
        ranked_table: Rows sorted by the primary ranking metric.
        best_strategy: Name of the top-ranked strategy.
        primary_metric: Metric used for ranking (e.g. ``"sharpe_ratio"``).
        correlation_matrix: Pairwise equity-curve correlation (if available).
    """

    comparison_id: str
    strategies: List[StrategyMetrics]
    ranked_table: List[ComparisonRow]
    best_strategy: str
    primary_metric: str
    correlation_matrix: Optional[List[List[float]]]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "comparison_id": self.comparison_id,
            "strategies": [s.to_dict() for s in self.strategies],
            "ranked_table": [r.to_dict() for r in self.ranked_table],
            "best_strategy": self.best_strategy,
            "primary_metric": self.primary_metric,
            "correlation_matrix": self.correlation_matrix,
        }


# ---------------------------------------------------------------------------
# Metric helpers (pure Python)
# ---------------------------------------------------------------------------

def _annualized_vol(equity_curve: List[float], periods_per_year: int = 252) -> float:
    """Compute annualised volatility from an equity curve.

    Args:
        equity_curve: Ordered equity values.
        periods_per_year: Trading periods per year.

    Returns:
        Annualised standard deviation of daily returns.
    """
    if len(equity_curve) < 2:
        return 0.0
    rets = [(equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve)) if equity_curve[i - 1] > 0]
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return math.sqrt(var * periods_per_year)


def _annualized_return(equity_curve: List[float], periods_per_year: int = 252) -> float:
    """Compute annualised return from an equity curve.

    Args:
        equity_curve: Ordered equity values.
        periods_per_year: Trading periods per year.

    Returns:
        Annualised geometric return (CAGR-style).
    """
    if len(equity_curve) < 2 or equity_curve[0] <= 0:
        return 0.0
    n = len(equity_curve)
    total = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
    exponent = periods_per_year / max(n - 1, 1)
    return (1.0 + total) ** exponent - 1.0


def _sortino_ratio(equity_curve: List[float], risk_free: float = 0.0, periods_per_year: int = 252) -> float:
    """Compute Sortino ratio penalising only downside returns.

    Args:
        equity_curve: Ordered equity values.
        risk_free: Daily risk-free rate.
        periods_per_year: Trading periods per year.

    Returns:
        Annualised Sortino ratio.
    """
    if len(equity_curve) < 2:
        return 0.0
    rets = [(equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve)) if equity_curve[i - 1] > 0]
    if not rets:
        return 0.0
    excess = [r - risk_free for r in rets]
    mean_excess = sum(excess) / len(excess)
    downside = [min(r, 0.0) for r in excess]
    downside_var = sum(r ** 2 for r in downside) / len(downside)
    downside_std = math.sqrt(downside_var * periods_per_year)
    if downside_std < 1e-9:
        return 0.0
    return (mean_excess * periods_per_year) / downside_std


def _calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
    """Compute Calmar ratio.

    Args:
        annualized_return: Annualised portfolio return.
        max_drawdown: Maximum drawdown (negative value or positive magnitude).

    Returns:
        Calmar ratio (positive means good).
    """
    dd = abs(max_drawdown)
    if dd < 1e-9:
        return 0.0
    return annualized_return / dd


def _profit_factor(equity_curve: List[float]) -> float:
    """Compute gross profit / gross loss from equity curve.

    Args:
        equity_curve: Ordered equity values.

    Returns:
        Profit factor, or 0 if no losing periods.
    """
    if len(equity_curve) < 2:
        return 0.0
    gains = sum(max(equity_curve[i] - equity_curve[i - 1], 0.0) for i in range(1, len(equity_curve)))
    losses = sum(max(equity_curve[i - 1] - equity_curve[i], 0.0) for i in range(1, len(equity_curve)))
    return gains / losses if losses > 1e-9 else 0.0


def _expectancy(equity_curve: List[float]) -> float:
    """Average return per bar from equity curve.

    Args:
        equity_curve: Ordered equity values.

    Returns:
        Mean period return.
    """
    if len(equity_curve) < 2:
        return 0.0
    rets = [(equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve)) if equity_curve[i - 1] > 0]
    return sum(rets) / len(rets) if rets else 0.0


def _pearson_corr(x: List[float], y: List[float]) -> float:
    """Pearson correlation between two equal-length series."""
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return num / (sx * sy)


def _align_curves(curves: List[List[float]]) -> List[List[float]]:
    """Align equity curves to the same length by truncating from the end.

    Args:
        curves: List of equity curve lists.

    Returns:
        List of curves all truncated to the length of the shortest.
    """
    if not curves:
        return []
    min_len = min(len(c) for c in curves)
    return [c[:min_len] for c in curves]


def _normalize_min_max(values: List[float]) -> List[float]:
    """Min-max normalise a list to [0, 1].

    Args:
        values: Input values.

    Returns:
        Normalised values; all-equal inputs become 0.5.
    """
    lo = min(values)
    hi = max(values)
    span = hi - lo
    if span < 1e-12:
        return [0.5] * len(values)
    return [(v - lo) / span for v in values]


VALID_METRICS = {
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "total_return",
    "annualized_return",
    "max_drawdown",
    "win_rate",
    "volatility",
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class StrategyComparisonEngine:
    """Ranks and compares multiple backtested strategies.

    Consumes M19 BacktestEngine by composition.  Each strategy is registered
    either as a pre-computed BacktestResult or via a fresh backtest run.
    """

    def __init__(self, backtest_engine: Optional[BacktestEngine] = None) -> None:
        """Initialise with an optional shared BacktestEngine.

        Args:
            backtest_engine: Shared BacktestEngine instance.  If None a new
                one is created internally.
        """
        self._backtest_engine: BacktestEngine = backtest_engine or BacktestEngine()
        self._results: Dict[str, BacktestResult] = {}
        self._metrics_cache: Dict[str, StrategyMetrics] = {}
        self._comparison_cache: Dict[str, ComparisonResult] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_result(self, strategy_name: str, result: BacktestResult) -> str:
        """Register a pre-computed BacktestResult for comparison.

        Args:
            strategy_name: Human-readable label.
            result: BacktestResult produced by M19 BacktestEngine.

        Returns:
            Generated strategy_id.
        """
        sid = str(uuid.uuid4())
        result_copy = result
        self._results[sid] = result_copy
        self._metrics_cache[sid] = self._compute_metrics(sid, strategy_name, result)
        return sid

    def run_and_register(
        self,
        strategy_name: str,
        ticker: str,
        price_data: Any,
        signals: Any,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
    ) -> str:
        """Run a backtest and register the result for comparison.

        Accepts signals as either a ``Dict[str, SignalType]`` (date → signal) or a
        ``List[Signal]``.  Dicts are converted to Signal objects using ``ticker``.

        Args:
            strategy_name: Human-readable label.
            ticker: Primary ticker (used when converting dict signals).
            price_data: Mapping of ticker → List[PriceBar].
            signals: Trading signals — dict or list accepted.
            initial_capital: Starting portfolio capital.
            commission_rate: Per-trade commission fraction.

        Returns:
            Generated strategy_id.
        """
        if isinstance(signals, dict):
            signal_list: List[Signal] = [
                Signal(date=date, ticker=ticker, signal_type=sig_type)
                for date, sig_type in signals.items()
            ]
        else:
            signal_list = list(signals)

        self._backtest_engine.reset()
        result = self._backtest_engine.run(
            strategy_name=strategy_name,
            signals=signal_list,
            price_data=price_data,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
        )
        return self.register_result(strategy_name, result)

    # ------------------------------------------------------------------
    # Metrics computation
    # ------------------------------------------------------------------

    def _compute_metrics(
        self, strategy_id: str, strategy_name: str, result: BacktestResult
    ) -> StrategyMetrics:
        """Derive StrategyMetrics from a BacktestResult.

        Args:
            strategy_id: UUID for this strategy.
            strategy_name: Human-readable label.
            result: BacktestResult from M19 BacktestEngine.

        Returns:
            StrategyMetrics dataclass.
        """
        curve: List[float] = [ep.equity for ep in result.equity_curve]
        m = result.metrics
        ann_ret = _annualized_return(curve)
        vol = _annualized_vol(curve)
        sharpe = (ann_ret - 0.0) / vol if vol > 1e-9 else 0.0
        sortino = _sortino_ratio(curve)
        calmar = _calmar_ratio(ann_ret, m.max_drawdown)

        return StrategyMetrics(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            total_return=round(m.total_return, 6),
            annualized_return=round(ann_ret, 6),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            calmar_ratio=round(calmar, 4),
            max_drawdown=round(m.max_drawdown, 6),
            win_rate=round(m.win_rate, 4),
            volatility=round(vol, 6),
            num_trades=m.num_trades,
            profit_factor=round(_profit_factor(curve), 4),
            expectancy=round(_expectancy(curve), 6),
        )

    def get_metrics(self, strategy_id: str) -> Optional[StrategyMetrics]:
        """Retrieve metrics for a registered strategy.

        Args:
            strategy_id: UUID of the strategy.

        Returns:
            StrategyMetrics, or None if not found.
        """
        return self._metrics_cache.get(strategy_id)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def compare(
        self,
        strategy_ids: List[str],
        primary_metric: str = "sharpe_ratio",
        include_correlation: bool = True,
    ) -> ComparisonResult:
        """Produce a ranked comparison table for the given strategies.

        Args:
            strategy_ids: IDs of strategies to compare.
            primary_metric: Metric to rank by (one of the VALID_METRICS set).
            include_correlation: If True, compute pairwise equity-curve
                correlation matrix.

        Returns:
            ComparisonResult with ranked table and best strategy name.

        Raises:
            ValueError: If any strategy_id is unknown or metric is invalid.
        """
        if primary_metric not in VALID_METRICS:
            raise ValueError(
                f"Unknown metric '{primary_metric}'. Valid: {sorted(VALID_METRICS)}"
            )
        for sid in strategy_ids:
            if sid not in self._metrics_cache:
                raise ValueError(f"Unknown strategy_id '{sid}'")

        metrics_list = [self._metrics_cache[sid] for sid in strategy_ids]

        # Build composite score: normalised Sharpe + Sortino + Calmar − |drawdown|
        sharpes = [m.sharpe_ratio for m in metrics_list]
        sortinos = [m.sortino_ratio for m in metrics_list]
        calmars = [m.calmar_ratio for m in metrics_list]
        dds = [m.max_drawdown for m in metrics_list]

        n_sharpe = _normalize_min_max(sharpes)
        n_sortino = _normalize_min_max(sortinos)
        n_calmar = _normalize_min_max(calmars)
        n_dd = _normalize_min_max([-d for d in dds])  # less negative = better

        scores = [
            0.40 * n_sharpe[i] + 0.25 * n_sortino[i] + 0.20 * n_calmar[i] + 0.15 * n_dd[i]
            for i in range(len(metrics_list))
        ]

        # Rank by primary metric (descending), break ties by composite score
        reverse = primary_metric != "max_drawdown" and primary_metric != "volatility"
        sign = -1.0 if not reverse else 1.0

        indexed = list(enumerate(metrics_list))
        indexed.sort(
            key=lambda t: (sign * getattr(t[1], primary_metric), scores[t[0]]),
            reverse=True,
        )

        rows: List[ComparisonRow] = []
        for rank, (orig_idx, m) in enumerate(indexed, start=1):
            rows.append(ComparisonRow(
                rank=rank,
                strategy_name=m.strategy_name,
                metrics=m,
                score=scores[orig_idx],
            ))

        # Equity-curve correlation matrix
        corr_matrix: Optional[List[List[float]]] = None
        if include_correlation and len(strategy_ids) > 1:
            curves = [[ep.equity for ep in self._results[sid].equity_curve] for sid in strategy_ids]
            aligned = _align_curves(curves)
            k = len(aligned)
            corr_matrix = [[0.0] * k for _ in range(k)]
            for i in range(k):
                corr_matrix[i][i] = 1.0
                for j in range(i + 1, k):
                    c = round(_pearson_corr(aligned[i], aligned[j]), 4)
                    corr_matrix[i][j] = c
                    corr_matrix[j][i] = c

        cid = str(uuid.uuid4())
        result = ComparisonResult(
            comparison_id=cid,
            strategies=metrics_list,
            ranked_table=rows,
            best_strategy=rows[0].strategy_name if rows else "",
            primary_metric=primary_metric,
            correlation_matrix=corr_matrix,
        )
        self._comparison_cache[cid] = result
        return result

    def get_comparison(self, comparison_id: str) -> Optional[ComparisonResult]:
        """Retrieve a previously computed ComparisonResult.

        Args:
            comparison_id: UUID of the comparison.

        Returns:
            ComparisonResult, or None if not found.
        """
        return self._comparison_cache.get(comparison_id)

    # ------------------------------------------------------------------
    # Best strategy selectors
    # ------------------------------------------------------------------

    def best_by_metric(self, strategy_ids: List[str], metric: str) -> Optional[StrategyMetrics]:
        """Return the strategy with the best value for a single metric.

        For ``max_drawdown`` and ``volatility`` lowest is best; for all others
        highest is best.

        Args:
            strategy_ids: IDs to evaluate.
            metric: One of the VALID_METRICS.

        Returns:
            Best StrategyMetrics, or None if strategy_ids is empty.

        Raises:
            ValueError: If metric is invalid or any strategy_id is unknown.
        """
        if metric not in VALID_METRICS:
            raise ValueError(f"Unknown metric '{metric}'")
        for sid in strategy_ids:
            if sid not in self._metrics_cache:
                raise ValueError(f"Unknown strategy_id '{sid}'")
        if not strategy_ids:
            return None
        reverse = metric not in ("max_drawdown", "volatility")
        return max(
            (self._metrics_cache[sid] for sid in strategy_ids),
            key=lambda m: getattr(m, metric) * (1.0 if reverse else -1.0),
        )

    def rank_by_metric(
        self, strategy_ids: List[str], metric: str
    ) -> List[Tuple[int, StrategyMetrics]]:
        """Return all strategies ranked by a single metric.

        Args:
            strategy_ids: IDs to rank.
            metric: One of the VALID_METRICS.

        Returns:
            List of (rank, StrategyMetrics) tuples sorted best-first.
        """
        if metric not in VALID_METRICS:
            raise ValueError(f"Unknown metric '{metric}'")
        reverse = metric not in ("max_drawdown", "volatility")
        sorted_metrics = sorted(
            [self._metrics_cache[sid] for sid in strategy_ids if sid in self._metrics_cache],
            key=lambda m: getattr(m, metric),
            reverse=reverse,
        )
        return [(rank, m) for rank, m in enumerate(sorted_metrics, start=1)]

    # ------------------------------------------------------------------
    # Head-to-head
    # ------------------------------------------------------------------

    def head_to_head(self, strategy_id_a: str, strategy_id_b: str) -> Dict[str, Any]:
        """Produce a head-to-head comparison between two strategies.

        Args:
            strategy_id_a: First strategy UUID.
            strategy_id_b: Second strategy UUID.

        Returns:
            Dict with per-metric winner and delta, plus overall winner.

        Raises:
            ValueError: If either strategy_id is unknown.
        """
        for sid in (strategy_id_a, strategy_id_b):
            if sid not in self._metrics_cache:
                raise ValueError(f"Unknown strategy_id '{sid}'")

        ma = self._metrics_cache[strategy_id_a]
        mb = self._metrics_cache[strategy_id_b]
        lower_better = {"max_drawdown", "volatility"}

        results: Dict[str, Dict[str, Any]] = {}
        wins_a = 0
        wins_b = 0

        for metric in VALID_METRICS:
            va = getattr(ma, metric)
            vb = getattr(mb, metric)
            if metric in lower_better:
                winner = ma.strategy_name if va < vb else mb.strategy_name
                if va < vb:
                    wins_a += 1
                elif vb < va:
                    wins_b += 1
            else:
                winner = ma.strategy_name if va > vb else mb.strategy_name
                if va > vb:
                    wins_a += 1
                elif vb > va:
                    wins_b += 1
            results[metric] = {
                "strategy_a": round(va, 6),
                "strategy_b": round(vb, 6),
                "delta": round(va - vb, 6),
                "winner": winner,
            }

        overall = ma.strategy_name if wins_a >= wins_b else mb.strategy_name
        return {
            "strategy_a": ma.strategy_name,
            "strategy_b": mb.strategy_name,
            "metrics": results,
            "wins_a": wins_a,
            "wins_b": wins_b,
            "overall_winner": overall,
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def list_strategies(self) -> List[Dict[str, str]]:
        """Return all registered strategies.

        Returns:
            List of {strategy_id, strategy_name} dicts.
        """
        return [
            {"strategy_id": sid, "strategy_name": m.strategy_name}
            for sid, m in self._metrics_cache.items()
        ]

    def reset(self) -> None:
        """Clear all registered strategies and cached comparisons."""
        self._results.clear()
        self._metrics_cache.clear()
        self._comparison_cache.clear()
