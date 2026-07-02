"""M9 Phase 5 — Walk-forward backtesting, parameter sweep, and rolling optimization.

Provides:
- ``walk_forward_test`` — in-sample/out-of-sample windowed strategy validation
- ``parameter_sweep`` — exhaustive grid search with metrics
- ``rolling_optimization`` — periodic re-optimization over a rolling window
- ``kelly_criterion`` — position sizing helper
"""
from __future__ import annotations

import itertools
import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Core metrics helpers
# ---------------------------------------------------------------------------

def _sharpe(returns: List[float], rf: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    avg = statistics.mean(returns) - rf / 252
    std = statistics.stdev(returns)
    return (avg / std * math.sqrt(252)) if std > 1e-10 else 0.0


def _max_drawdown(equity: List[float]) -> float:
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def _cagr(equity: List[float], periods_per_year: float = 252) -> float:
    if len(equity) < 2 or equity[0] <= 0:
        return 0.0
    years = len(equity) / periods_per_year
    return (equity[-1] / equity[0]) ** (1 / years) - 1 if years > 0 else 0.0


def compute_metrics(returns: List[float]) -> dict:
    if not returns:
        return {"sharpe": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "total_return": 0.0, "n": 0}
    equity = [1.0]
    for r in returns:
        equity.append(equity[-1] * (1 + r))
    return {
        "sharpe": round(_sharpe(returns), 4),
        "cagr": round(_cagr(equity), 4),
        "max_drawdown": round(_max_drawdown(equity), 4),
        "total_return": round(equity[-1] - 1, 4),
        "n": len(returns),
    }


# ---------------------------------------------------------------------------
# Walk-forward test
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardResult:
    windows: List[dict] = field(default_factory=list)
    aggregate: dict = field(default_factory=dict)


def walk_forward_test(
    prices: List[float],
    strategy_fn: Callable[[List[float], Dict], List[float]],
    params: Dict[str, Any],
    in_sample_size: int = 126,   # trading days (~6 months)
    out_sample_size: int = 21,   # ~1 month
) -> WalkForwardResult:
    """Run a strategy over rolling in-sample/out-of-sample windows.

    strategy_fn(prices_window, params) -> list[float] daily returns
    """
    n = len(prices)
    results = WalkForwardResult()
    combined_oos_returns: List[float] = []

    step = out_sample_size
    start = 0
    window_idx = 0

    while start + in_sample_size + out_sample_size <= n:
        is_slice = prices[start : start + in_sample_size]
        oos_slice = prices[start + in_sample_size : start + in_sample_size + out_sample_size]

        is_returns = strategy_fn(is_slice, params)
        oos_returns = strategy_fn(oos_slice, params)

        combined_oos_returns.extend(oos_returns)

        results.windows.append({
            "window": window_idx,
            "is_start": start,
            "is_end": start + in_sample_size,
            "oos_start": start + in_sample_size,
            "oos_end": start + in_sample_size + out_sample_size,
            "in_sample": compute_metrics(is_returns),
            "out_of_sample": compute_metrics(oos_returns),
        })

        start += step
        window_idx += 1

    results.aggregate = {
        "oos_combined": compute_metrics(combined_oos_returns),
        "n_windows": len(results.windows),
        "consistency": _consistency_ratio(results.windows),
    }
    return results


def _consistency_ratio(windows: List[dict]) -> float:
    """Fraction of OOS windows that are profitable."""
    if not windows:
        return 0.0
    profitable = sum(1 for w in windows if w["out_of_sample"]["total_return"] > 0)
    return round(profitable / len(windows), 4)


# ---------------------------------------------------------------------------
# Parameter sweep
# ---------------------------------------------------------------------------

@dataclass
class SweepResult:
    best_params: Dict[str, Any]
    best_metric: float
    all_results: List[dict]


def parameter_sweep(
    prices: List[float],
    strategy_fn: Callable[[List[float], Dict], List[float]],
    param_grid: Dict[str, List[Any]],
    metric: str = "sharpe",
) -> SweepResult:
    """Grid-search over param_grid, rank by metric."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    all_results: List[dict] = []

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        returns = strategy_fn(prices, params)
        m = compute_metrics(returns)
        all_results.append({"params": params, "metrics": m})

    all_results.sort(key=lambda r: r["metrics"].get(metric, 0.0), reverse=True)
    best = all_results[0] if all_results else {"params": {}, "metrics": {}}
    return SweepResult(
        best_params=best["params"],
        best_metric=best["metrics"].get(metric, 0.0),
        all_results=all_results,
    )


# ---------------------------------------------------------------------------
# Rolling optimization
# ---------------------------------------------------------------------------

def rolling_optimization(
    prices: List[float],
    strategy_fn: Callable[[List[float], Dict], List[float]],
    param_grid: Dict[str, List[Any]],
    optimization_window: int = 126,
    apply_window: int = 21,
    metric: str = "sharpe",
) -> dict:
    """Periodically re-optimize params on a rolling window, then apply OOS.

    Returns combined OOS metrics and param history.
    """
    n = len(prices)
    combined_returns: List[float] = []
    param_history: List[dict] = []

    start = 0
    while start + optimization_window + apply_window <= n:
        opt_prices = prices[start : start + optimization_window]
        sweep = parameter_sweep(opt_prices, strategy_fn, param_grid, metric)

        apply_prices = prices[start + optimization_window : start + optimization_window + apply_window]
        oos_returns = strategy_fn(apply_prices, sweep.best_params)
        combined_returns.extend(oos_returns)

        param_history.append({
            "period_start": start,
            "best_params": sweep.best_params,
            "best_is_metric": sweep.best_metric,
            "oos": compute_metrics(oos_returns),
        })
        start += apply_window

    return {
        "aggregate": compute_metrics(combined_returns),
        "param_history": param_history,
    }


# ---------------------------------------------------------------------------
# Kelly Criterion
# ---------------------------------------------------------------------------

def kelly_criterion(win_prob: float, win_return: float, loss_return: float) -> dict:
    """Full and fractional Kelly sizing.

    Returns:
        full_kelly: fraction of bankroll to risk
        half_kelly: conservative 50% Kelly
        quarter_kelly: ultra-conservative
        expected_log_growth: per-trade expected log growth at full Kelly
    """
    if loss_return <= 0 or win_prob <= 0 or win_prob >= 1:
        return {"full_kelly": 0.0, "half_kelly": 0.0, "quarter_kelly": 0.0, "expected_log_growth": 0.0}

    b = win_return / abs(loss_return)
    p = win_prob
    q = 1 - p
    kelly = (b * p - q) / b
    kelly = max(0.0, kelly)
    elg = p * math.log(1 + kelly * b) + q * math.log(1 - kelly) if kelly < 1 else 0.0
    return {
        "full_kelly": round(kelly, 4),
        "half_kelly": round(kelly * 0.5, 4),
        "quarter_kelly": round(kelly * 0.25, 4),
        "expected_log_growth": round(elg, 6),
    }
