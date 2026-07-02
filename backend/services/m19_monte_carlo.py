"""Monte Carlo simulation engine for strategy return distribution analysis."""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MCPath:
    """A single simulated equity path.

    Attributes:
        path_id: Integer index of this path.
        equity_values: List of portfolio values at each simulated step.
        final_equity: Terminal portfolio value.
        total_return: Fractional return of this path.
        max_drawdown: Maximum peak-to-trough drawdown on this path.
    """

    path_id: int
    equity_values: List[float]
    final_equity: float
    total_return: float
    max_drawdown: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict (equity_values omitted for brevity)."""
        return {
            "path_id": self.path_id,
            "final_equity": self.final_equity,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
        }


@dataclass
class ConfidenceInterval:
    """Confidence interval for a simulated metric.

    Attributes:
        metric: Name of the metric (e.g. 'final_equity').
        p5: 5th percentile value.
        p25: 25th percentile value.
        p50: Median value.
        p75: 75th percentile value.
        p95: 95th percentile value.
        mean: Mean across all paths.
        std: Standard deviation across all paths.
    """

    metric: str
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float
    std: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return self.__dict__.copy()


@dataclass
class MCResult:
    """Full Monte Carlo simulation result.

    Attributes:
        simulation_id: Unique run identifier.
        num_paths: Number of paths simulated.
        num_steps: Number of time steps per path.
        initial_equity: Starting portfolio value.
        var_95: Value at Risk at 95% confidence (loss fraction).
        var_99: Value at Risk at 99% confidence (loss fraction).
        expected_shortfall_95: CVaR at 95%: mean of worst 5% outcomes.
        max_drawdown_p50: Median maximum drawdown across paths.
        max_drawdown_p95: 95th-percentile maximum drawdown.
        probability_of_ruin: Fraction of paths reaching zero equity.
        probability_of_profit: Fraction of paths with positive return.
        confidence_intervals: Per-metric confidence intervals.
        method: Simulation method used ('bootstrap' or 'gbm').
    """

    simulation_id: str
    num_paths: int
    num_steps: int
    initial_equity: float
    var_95: float
    var_99: float
    expected_shortfall_95: float
    max_drawdown_p50: float
    max_drawdown_p95: float
    probability_of_ruin: float
    probability_of_profit: float
    confidence_intervals: List[ConfidenceInterval]
    method: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "simulation_id": self.simulation_id,
            "num_paths": self.num_paths,
            "num_steps": self.num_steps,
            "initial_equity": self.initial_equity,
            "var_95": self.var_95,
            "var_99": self.var_99,
            "expected_shortfall_95": self.expected_shortfall_95,
            "max_drawdown_p50": self.max_drawdown_p50,
            "max_drawdown_p95": self.max_drawdown_p95,
            "probability_of_ruin": self.probability_of_ruin,
            "probability_of_profit": self.probability_of_profit,
            "confidence_intervals": [ci.to_dict() for ci in self.confidence_intervals],
            "method": self.method,
        }


class MonteCarloEngine:
    """Generates and analyses Monte Carlo simulations of strategy return paths.

    Supports two simulation methods:
    - bootstrap: Resamples from historical daily returns (non-parametric).
    - gbm: Geometric Brownian Motion using historical mean and volatility.

    Results are cached by simulation_id.

    Attributes:
        _results: Cached MCResult objects.
        _paths: Cached MCPath lists (large; stored separately for memory).
        _rng: Seeded random number generator.
    """

    def __init__(self, seed: int = 0) -> None:
        self._results: Dict[str, MCResult] = {}
        self._paths: Dict[str, List[MCPath]] = {}
        self._rng = random.Random(seed)

    def reset(self) -> None:
        """Clear all cached simulation results and paths."""
        self._results.clear()
        self._paths.clear()

    def run_bootstrap(
        self,
        daily_returns: List[float],
        num_paths: int = 1000,
        num_steps: int = 252,
        initial_equity: float = 100_000.0,
        block_size: int = 1,
    ) -> MCResult:
        """Run a bootstrap Monte Carlo simulation.

        Resamples from the provided daily_returns with replacement. If
        block_size > 1, consecutive blocks are drawn to preserve
        autocorrelation (stationary block bootstrap).

        Args:
            daily_returns: Historical daily return fractions.
            num_paths: Number of independent simulation paths.
            num_steps: Trading days per path.
            initial_equity: Starting portfolio value.
            block_size: Resampling block length (1 = i.i.d. bootstrap).

        Returns:
            MCResult with statistical summaries of the distribution.
        """
        sim_id = str(uuid.uuid4())
        paths: List[MCPath] = []

        for path_id in range(num_paths):
            equity = initial_equity
            values = [equity]
            peak = equity
            max_dd = 0.0
            step = 0
            while step < num_steps:
                if block_size <= 1:
                    r = self._rng.choice(daily_returns) if daily_returns else 0.0
                    equity *= (1.0 + r)
                    step += 1
                else:
                    start = self._rng.randint(0, max(0, len(daily_returns) - block_size))
                    block = daily_returns[start: start + block_size]
                    for r in block:
                        if step >= num_steps:
                            break
                        equity *= (1.0 + r)
                        step += 1
                        if equity < 0:
                            equity = 0.0
                equity = max(0.0, equity)
                values.append(round(equity, 4))
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak if peak > 0 else 0.0
                if dd > max_dd:
                    max_dd = dd

            final = values[-1]
            tr = (final - initial_equity) / initial_equity if initial_equity > 0 else 0.0
            paths.append(MCPath(
                path_id=path_id,
                equity_values=values,
                final_equity=round(final, 4),
                total_return=round(tr, 6),
                max_drawdown=round(max_dd, 6),
            ))

        result = self._build_result(sim_id, paths, num_steps, initial_equity, "bootstrap")
        self._results[sim_id] = result
        self._paths[sim_id] = paths
        return result

    def run_gbm(
        self,
        mean_daily_return: float,
        daily_volatility: float,
        num_paths: int = 1000,
        num_steps: int = 252,
        initial_equity: float = 100_000.0,
    ) -> MCResult:
        """Run a Geometric Brownian Motion Monte Carlo simulation.

        Uses the log-normal return model: S(t+1) = S(t) * exp((μ - σ²/2) + σ*Z)
        where Z ~ N(0,1).

        Args:
            mean_daily_return: Mean daily return fraction (drift).
            daily_volatility: Daily return standard deviation.
            num_paths: Number of simulation paths.
            num_steps: Trading days per path.
            initial_equity: Starting portfolio value.

        Returns:
            MCResult with statistical summaries of the distribution.
        """
        sim_id = str(uuid.uuid4())
        paths: List[MCPath] = []
        drift = mean_daily_return - 0.5 * daily_volatility ** 2

        for path_id in range(num_paths):
            equity = initial_equity
            values = [equity]
            peak = equity
            max_dd = 0.0
            for _ in range(num_steps):
                z = self._rng.gauss(0.0, 1.0)
                r = math.exp(drift + daily_volatility * z) - 1.0
                equity = max(0.0, equity * (1.0 + r))
                values.append(round(equity, 4))
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak if peak > 0 else 0.0
                if dd > max_dd:
                    max_dd = dd

            final = values[-1]
            tr = (final - initial_equity) / initial_equity if initial_equity > 0 else 0.0
            paths.append(MCPath(
                path_id=path_id,
                equity_values=values,
                final_equity=round(final, 4),
                total_return=round(tr, 6),
                max_drawdown=round(max_dd, 6),
            ))

        result = self._build_result(sim_id, paths, num_steps, initial_equity, "gbm")
        self._results[sim_id] = result
        self._paths[sim_id] = paths
        return result

    def _build_result(
        self,
        sim_id: str,
        paths: List[MCPath],
        num_steps: int,
        initial_equity: float,
        method: str,
    ) -> MCResult:
        """Compile MCResult from the generated paths.

        Args:
            sim_id: Unique simulation identifier.
            paths: All simulated MCPath objects.
            num_steps: Number of steps per path.
            initial_equity: Starting equity.
            method: 'bootstrap' or 'gbm'.

        Returns:
            Populated MCResult.
        """
        returns = sorted(p.total_return for p in paths)
        drawdowns = sorted(p.max_drawdown for p in paths)
        finals = sorted(p.final_equity for p in paths)
        n = len(paths)

        def pct(lst: List[float], p: float) -> float:
            if not lst:
                return 0.0
            idx = max(0, min(n - 1, int(p * n)))
            return lst[idx]

        var_95 = -pct(returns, 0.05)
        var_99 = -pct(returns, 0.01)
        tail = returns[:max(1, n // 20)]
        es_95 = -sum(tail) / len(tail) if tail else 0.0

        p_ruin = sum(1 for p in paths if p.final_equity <= 0) / n if n else 0.0
        p_profit = sum(1 for p in paths if p.total_return > 0) / n if n else 0.0

        mean_r = sum(returns) / n if n else 0.0
        var_r = sum((r - mean_r) ** 2 for r in returns) / max(n - 1, 1)
        std_r = math.sqrt(var_r)

        mean_f = sum(finals) / n if n else 0.0
        var_f = sum((f - mean_f) ** 2 for f in finals) / max(n - 1, 1)
        std_f = math.sqrt(var_f)

        ci_returns = ConfidenceInterval(
            metric="total_return",
            p5=round(pct(returns, 0.05), 6),
            p25=round(pct(returns, 0.25), 6),
            p50=round(pct(returns, 0.50), 6),
            p75=round(pct(returns, 0.75), 6),
            p95=round(pct(returns, 0.95), 6),
            mean=round(mean_r, 6),
            std=round(std_r, 6),
        )
        ci_equity = ConfidenceInterval(
            metric="final_equity",
            p5=round(pct(finals, 0.05), 4),
            p25=round(pct(finals, 0.25), 4),
            p50=round(pct(finals, 0.50), 4),
            p75=round(pct(finals, 0.75), 4),
            p95=round(pct(finals, 0.95), 4),
            mean=round(mean_f, 4),
            std=round(std_f, 4),
        )
        ci_drawdown = ConfidenceInterval(
            metric="max_drawdown",
            p5=round(pct(drawdowns, 0.05), 6),
            p25=round(pct(drawdowns, 0.25), 6),
            p50=round(pct(drawdowns, 0.50), 6),
            p75=round(pct(drawdowns, 0.75), 6),
            p95=round(pct(drawdowns, 0.95), 6),
            mean=round(sum(drawdowns) / n if n else 0.0, 6),
            std=round(math.sqrt(sum((d - sum(drawdowns) / n) ** 2 for d in drawdowns) / max(n - 1, 1)), 6),
        )

        return MCResult(
            simulation_id=sim_id,
            num_paths=n,
            num_steps=num_steps,
            initial_equity=initial_equity,
            var_95=round(var_95, 6),
            var_99=round(var_99, 6),
            expected_shortfall_95=round(es_95, 6),
            max_drawdown_p50=round(pct(drawdowns, 0.50), 6),
            max_drawdown_p95=round(pct(drawdowns, 0.95), 6),
            probability_of_ruin=round(p_ruin, 6),
            probability_of_profit=round(p_profit, 6),
            confidence_intervals=[ci_returns, ci_equity, ci_drawdown],
            method=method,
        )

    def get_result(self, simulation_id: str) -> Optional[MCResult]:
        """Retrieve a cached simulation result.

        Args:
            simulation_id: UUID from a previous run call.

        Returns:
            MCResult or None if not found.
        """
        return self._results.get(simulation_id)

    def get_paths(self, simulation_id: str, max_paths: int = 100) -> List[MCPath]:
        """Retrieve a subset of simulated paths (for charting).

        Args:
            simulation_id: UUID of the simulation.
            max_paths: Maximum number of paths to return.

        Returns:
            List of MCPath objects (equity_values included).
        """
        paths = self._paths.get(simulation_id, [])
        return paths[:max_paths]

    def get_distribution(self, simulation_id: str) -> Dict[str, Any]:
        """Return the return distribution summary for a simulation.

        Args:
            simulation_id: UUID of the simulation.

        Returns:
            Dict with sorted final returns and equity values.
        """
        paths = self._paths.get(simulation_id, [])
        if not paths:
            return {"returns": [], "final_equities": []}
        returns = sorted(p.total_return for p in paths)
        finals = sorted(p.final_equity for p in paths)
        return {
            "returns": [round(r, 6) for r in returns],
            "final_equities": [round(f, 4) for f in finals],
        }

    def get_confidence_intervals(self, simulation_id: str) -> List[Dict[str, Any]]:
        """Return confidence intervals for a simulation result.

        Args:
            simulation_id: UUID of the simulation.

        Returns:
            List of confidence interval dicts.
        """
        result = self._results.get(simulation_id)
        if not result:
            return []
        return [ci.to_dict() for ci in result.confidence_intervals]

    def list_results(self) -> List[Dict[str, Any]]:
        """Summarise all cached Monte Carlo simulations.

        Returns:
            List of summary dicts per simulation.
        """
        return [
            {
                "simulation_id": sid,
                "num_paths": r.num_paths,
                "method": r.method,
                "var_95": r.var_95,
                "probability_of_profit": r.probability_of_profit,
            }
            for sid, r in self._results.items()
        ]

    def sensitivity_analysis(
        self,
        daily_returns: List[float],
        drift_shocks: List[float],
        vol_shocks: List[float],
        num_paths: int = 500,
        num_steps: int = 252,
        initial_equity: float = 100_000.0,
    ) -> List[Dict[str, Any]]:
        """Run GBM simulations across a grid of drift and volatility shocks.

        Args:
            daily_returns: Historical returns used to estimate base mean/vol.
            drift_shocks: List of additive shocks to mean daily return.
            vol_shocks: List of multiplicative shocks to daily volatility.
            num_paths: Paths per simulation cell.
            num_steps: Steps per path.
            initial_equity: Starting equity.

        Returns:
            List of {drift_shock, vol_shock, var_95, probability_of_profit} dicts.
        """
        n = len(daily_returns)
        base_mean = sum(daily_returns) / n if n else 0.0
        base_var = sum((r - base_mean) ** 2 for r in daily_returns) / max(n - 1, 1)
        base_vol = math.sqrt(base_var) if base_var > 0 else 0.01

        rows: List[Dict[str, Any]] = []
        for ds in drift_shocks:
            for vs in vol_shocks:
                res = self.run_gbm(
                    mean_daily_return=base_mean + ds,
                    daily_volatility=max(0.0001, base_vol * vs),
                    num_paths=num_paths,
                    num_steps=num_steps,
                    initial_equity=initial_equity,
                )
                rows.append({
                    "drift_shock": ds,
                    "vol_shock": vs,
                    "var_95": res.var_95,
                    "var_99": res.var_99,
                    "probability_of_profit": res.probability_of_profit,
                    "simulation_id": res.simulation_id,
                })
        return rows
