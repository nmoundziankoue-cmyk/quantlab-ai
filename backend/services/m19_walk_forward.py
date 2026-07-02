"""Walk-forward validation engine for out-of-sample strategy robustness testing."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from services.m19_backtest_engine import (
    BacktestEngine,
    BacktestResult,
    PriceBar,
    Signal,
    SignalType,
)


class WindowMode(str, Enum):
    """Determines how in-sample windows grow over time."""

    ROLLING = "ROLLING"
    EXPANDING = "EXPANDING"


@dataclass
class WFWindow:
    """A single in-sample / out-of-sample window pair.

    Attributes:
        window_index: Zero-based ordinal of this window.
        in_sample_start: First date of the in-sample period.
        in_sample_end: Last date of the in-sample period.
        out_sample_start: First date of the out-of-sample period.
        out_sample_end: Last date of the out-of-sample period.
        in_sample_sharpe: Sharpe ratio achieved in-sample.
        out_sample_sharpe: Sharpe ratio achieved out-of-sample.
        in_sample_return: Total return in-sample.
        out_sample_return: Total return out-of-sample.
        efficiency: Ratio of OOS to IS Sharpe (1.0 = perfect transfer).
        backtest_id: ID of the OOS BacktestResult stored in the engine.
    """

    window_index: int
    in_sample_start: str
    in_sample_end: str
    out_sample_start: str
    out_sample_end: str
    in_sample_sharpe: float
    out_sample_sharpe: float
    in_sample_return: float
    out_sample_return: float
    efficiency: float
    backtest_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize window to a plain dict."""
        return self.__dict__.copy()


@dataclass
class StabilityMetrics:
    """Aggregate stability statistics over all walk-forward windows.

    Attributes:
        num_windows: Total number of windows tested.
        avg_oos_sharpe: Mean OOS Sharpe across windows.
        std_oos_sharpe: Standard deviation of OOS Sharpe.
        avg_efficiency: Mean IS→OOS efficiency ratio.
        pct_windows_positive: Fraction of windows with positive OOS return.
        stability_score: Composite 0–1 score (higher = more stable).
        avg_oos_return: Mean OOS total return per window.
        degradation: Mean IS return minus mean OOS return (lower = better).
    """

    num_windows: int
    avg_oos_sharpe: float
    std_oos_sharpe: float
    avg_efficiency: float
    pct_windows_positive: float
    stability_score: float
    avg_oos_return: float
    degradation: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return self.__dict__.copy()


@dataclass
class WalkForwardResult:
    """Full result of a walk-forward analysis run.

    Attributes:
        run_id: Unique identifier for this WF analysis.
        strategy_name: Label from the originating backtest config.
        windows: All window-level results.
        stability: Aggregate stability metrics.
        window_mode: ROLLING or EXPANDING.
        in_sample_bars: Number of bars used for each IS window.
        out_sample_bars: Number of bars used for each OOS window.
    """

    run_id: str
    strategy_name: str
    windows: List[WFWindow]
    stability: StabilityMetrics
    window_mode: WindowMode
    in_sample_bars: int
    out_sample_bars: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "run_id": self.run_id,
            "strategy_name": self.strategy_name,
            "windows": [w.to_dict() for w in self.windows],
            "stability": self.stability.to_dict(),
            "window_mode": self.window_mode.value,
            "in_sample_bars": self.in_sample_bars,
            "out_sample_bars": self.out_sample_bars,
        }


SignalGenerator = Callable[[List[str], Dict[str, List[PriceBar]]], List[Signal]]


class WalkForwardEngine:
    """Validates a trading strategy using sliding in-sample/out-of-sample windows.

    Each IS window is used to "fit" parameters (via the caller-supplied
    signal_generator), and the OOS window measures live performance.
    Results are cached by run_id.

    Attributes:
        _engine: Underlying BacktestEngine instance shared across windows.
        _results: Cached WalkForwardResult objects keyed by run_id.
    """

    def __init__(self, backtest_engine: Optional[BacktestEngine] = None) -> None:
        self._engine = backtest_engine or BacktestEngine()
        self._results: Dict[str, WalkForwardResult] = {}

    def reset(self) -> None:
        """Clear all cached walk-forward results."""
        self._results.clear()

    def run(
        self,
        strategy_name: str,
        price_data: Dict[str, List[PriceBar]],
        signal_generator: SignalGenerator,
        in_sample_bars: int = 252,
        out_sample_bars: int = 63,
        window_mode: WindowMode = WindowMode.ROLLING,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        position_size_pct: float = 0.10,
    ) -> WalkForwardResult:
        """Execute a walk-forward analysis.

        The signal_generator callable receives the in-sample date list and
        price data, then returns signals for the out-of-sample period.  The
        BacktestEngine is called with only the OOS price bars to measure
        genuine out-of-sample performance.

        Args:
            strategy_name: Human-readable strategy label.
            price_data: Full historical price bars per ticker.
            signal_generator: Callable(dates, price_data) -> List[Signal].
            in_sample_bars: Length of the in-sample window in trading days.
            out_sample_bars: Length of the out-of-sample window in trading days.
            window_mode: ROLLING (fixed IS length) or EXPANDING (grows over time).
            initial_capital: Starting capital per window run.
            commission_rate: Fractional commission per trade.
            slippage_bps: One-way slippage in basis points.
            position_size_pct: Fraction of equity per position.

        Returns:
            WalkForwardResult containing per-window and aggregate statistics.
        """
        run_id = str(uuid.uuid4())

        all_dates: list = sorted({
            bar.date
            for bars in price_data.values()
            for bar in bars
        })

        total_bars = len(all_dates)
        windows: List[WFWindow] = []
        idx = 0

        while idx + in_sample_bars + out_sample_bars <= total_bars:
            if window_mode == WindowMode.ROLLING:
                is_start = idx
            else:
                is_start = 0
            is_end = idx + in_sample_bars - 1
            oos_start = is_end + 1
            oos_end = min(oos_start + out_sample_bars - 1, total_bars - 1)

            is_dates = all_dates[is_start: is_end + 1]
            oos_dates = all_dates[oos_start: oos_end + 1]

            is_price_data = self._slice_price_data(price_data, all_dates, is_start, is_end)
            oos_price_data = self._slice_price_data(price_data, all_dates, oos_start, oos_end)

            is_signals = signal_generator(is_dates, is_price_data)
            is_result = self._engine.run(
                strategy_name=strategy_name,
                signals=is_signals,
                price_data=is_price_data,
                initial_capital=initial_capital,
                commission_rate=commission_rate,
                slippage_bps=slippage_bps,
                position_size_pct=position_size_pct,
            )

            oos_signals = signal_generator(oos_dates, oos_price_data)
            oos_result = self._engine.run(
                strategy_name=strategy_name,
                signals=oos_signals,
                price_data=oos_price_data,
                initial_capital=initial_capital,
                commission_rate=commission_rate,
                slippage_bps=slippage_bps,
                position_size_pct=position_size_pct,
            )

            oos_sharpe = oos_result.metrics.sharpe_ratio
            is_sharpe = is_result.metrics.sharpe_ratio
            efficiency = oos_sharpe / is_sharpe if is_sharpe != 0 else 0.0

            windows.append(WFWindow(
                window_index=len(windows),
                in_sample_start=is_dates[0] if is_dates else "",
                in_sample_end=is_dates[-1] if is_dates else "",
                out_sample_start=oos_dates[0] if oos_dates else "",
                out_sample_end=oos_dates[-1] if oos_dates else "",
                in_sample_sharpe=round(is_sharpe, 4),
                out_sample_sharpe=round(oos_sharpe, 4),
                in_sample_return=round(is_result.metrics.total_return, 6),
                out_sample_return=round(oos_result.metrics.total_return, 6),
                efficiency=round(efficiency, 4),
                backtest_id=oos_result.backtest_id,
            ))

            idx += out_sample_bars

        stability = self._compute_stability(windows)
        result = WalkForwardResult(
            run_id=run_id,
            strategy_name=strategy_name,
            windows=windows,
            stability=stability,
            window_mode=window_mode,
            in_sample_bars=in_sample_bars,
            out_sample_bars=out_sample_bars,
        )
        self._results[run_id] = result
        return result

    def _slice_price_data(
        self,
        price_data: Dict[str, List[PriceBar]],
        all_dates: List[str],
        start_idx: int,
        end_idx: int,
    ) -> Dict[str, List[PriceBar]]:
        """Extract a date-range slice from price_data.

        Args:
            price_data: Full price data per ticker.
            all_dates: Globally sorted date list.
            start_idx: Inclusive start index into all_dates.
            end_idx: Inclusive end index into all_dates.

        Returns:
            Price data restricted to the selected date range.
        """
        date_set = set(all_dates[start_idx: end_idx + 1])
        return {
            ticker: [bar for bar in bars if bar.date in date_set]
            for ticker, bars in price_data.items()
        }

    def _compute_stability(self, windows: List[WFWindow]) -> StabilityMetrics:
        """Derive aggregate stability metrics from window results.

        Args:
            windows: All completed WFWindow objects.

        Returns:
            StabilityMetrics summarising OOS performance stability.
        """
        if not windows:
            return StabilityMetrics(
                num_windows=0,
                avg_oos_sharpe=0.0,
                std_oos_sharpe=0.0,
                avg_efficiency=0.0,
                pct_windows_positive=0.0,
                stability_score=0.0,
                avg_oos_return=0.0,
                degradation=0.0,
            )
        oos_sharpes = [w.out_sample_sharpe for w in windows]
        is_returns = [w.in_sample_return for w in windows]
        oos_returns = [w.out_sample_return for w in windows]
        efficiencies = [w.efficiency for w in windows]

        n = len(windows)
        avg_oos = sum(oos_sharpes) / n
        mean_sq = sum(s ** 2 for s in oos_sharpes) / n
        std_oos = math.sqrt(max(0.0, mean_sq - avg_oos ** 2))
        avg_eff = sum(efficiencies) / n
        pct_pos = sum(1 for r in oos_returns if r > 0) / n
        avg_oos_ret = sum(oos_returns) / n
        avg_is_ret = sum(is_returns) / n
        degradation = avg_is_ret - avg_oos_ret

        consistency = 1.0 / (1.0 + std_oos) if std_oos >= 0 else 0.0
        stability = 0.4 * pct_pos + 0.3 * min(1.0, max(0.0, avg_eff)) + 0.3 * consistency

        return StabilityMetrics(
            num_windows=n,
            avg_oos_sharpe=round(avg_oos, 4),
            std_oos_sharpe=round(std_oos, 4),
            avg_efficiency=round(avg_eff, 4),
            pct_windows_positive=round(pct_pos, 4),
            stability_score=round(stability, 4),
            avg_oos_return=round(avg_oos_ret, 6),
            degradation=round(degradation, 6),
        )

    def get_result(self, run_id: str) -> Optional[WalkForwardResult]:
        """Retrieve a cached walk-forward result.

        Args:
            run_id: UUID returned by a previous run call.

        Returns:
            WalkForwardResult or None if not found.
        """
        return self._results.get(run_id)

    def get_windows(self, run_id: str) -> List[WFWindow]:
        """Return the list of window results for a run.

        Args:
            run_id: UUID of the walk-forward analysis.

        Returns:
            List of WFWindow objects, empty if run not found.
        """
        result = self._results.get(run_id)
        return result.windows if result else []

    def get_stability(self, run_id: str) -> Optional[StabilityMetrics]:
        """Return stability metrics for a run.

        Args:
            run_id: UUID of the walk-forward analysis.

        Returns:
            StabilityMetrics or None if run not found.
        """
        result = self._results.get(run_id)
        return result.stability if result else None

    def list_results(self) -> List[Dict[str, Any]]:
        """Summarise all cached walk-forward results.

        Returns:
            List of dicts with run_id, strategy_name, and stability score.
        """
        return [
            {
                "run_id": run_id,
                "strategy_name": r.strategy_name,
                "num_windows": r.stability.num_windows,
                "stability_score": r.stability.stability_score,
                "avg_oos_sharpe": r.stability.avg_oos_sharpe,
            }
            for run_id, r in self._results.items()
        ]
