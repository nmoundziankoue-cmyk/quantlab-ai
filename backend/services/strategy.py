"""
Strategy framework — abstract base class, lifecycle hooks, and eleven built-in strategies.

Each strategy receives a clean OHLCV DataFrame and returns a pandas Series of
Signal values indexed by date.  Signals are always generated without look-ahead
bias: signal on bar T uses only data from bars 0..T.

M11 Phase 2 additions
---------------------
* BaseStrategy gains six default no-op lifecycle hooks:
    initialize(), on_bar(), on_tick(), on_news(), on_fill(), on_finish()
  All are optional overrides — the existing generate_signals() interface is
  unchanged and all four original strategies continue to work unmodified.

* Seven new built-in strategies added to _STRATEGY_REGISTRY:
    buy_and_hold, dual_ma, momentum, mean_reversion,
    channel_breakout, pairs_trading, volatility_breakout
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Type

import numpy as np
import pandas as pd

from services.indicators import (
    atr as compute_atr,
    bollinger_bands,
    ema,
    macd as compute_macd,
    roc as compute_roc,
    rsi as compute_rsi,
    sma,
)


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class BaseStrategy(ABC):
    """Abstract base for all strategies.

    Subclasses must implement:
        - ``name`` property
        - ``generate_signals(data)``

    Lifecycle hooks (optional overrides, all default to no-ops):
        - ``initialize(config)``  — called once before the backtest starts
        - ``on_bar(bar, timestamp)`` — called for each bar during replay
        - ``on_tick(tick)``         — called for each intraday tick
        - ``on_news(news)``         — called when news arrives
        - ``on_fill(fill_event)``   — called after an order is filled
        - ``on_finish(result)``     — called when the backtest completes

    The lifecycle hooks are designed for use by the event-driven backtester
    (Phase 1+).  Strategies that only implement ``generate_signals()`` work
    identically to before — the hooks are pure additions with no side effects.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        self.params = params

    @property
    @abstractmethod
    def name(self) -> str:
        """Machine-readable identifier, e.g. 'sma_crossover'."""

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return a Series of Signal values with the same DatetimeIndex as *data*.

        The caller guarantees that *data* has columns: Open, High, Low, Close, Volume.
        NaN rows are already dropped.
        """

    # ------------------------------------------------------------------
    # Lifecycle hooks — default no-ops.  Override freely.
    # ------------------------------------------------------------------

    def initialize(self, config: Any = None) -> None:
        """Called once before the backtest starts.

        Override to set up per-run state (e.g. reset internal position
        trackers, load reference data, validate params).

        Args:
            config: The ``BacktestConfig`` for the current run, or None.
        """

    def on_bar(self, bar: Dict[str, Any], timestamp: str) -> Optional[Signal]:
        """Called for each bar during event-driven replay.

        Override to react to individual bars (e.g. update incremental
        indicator state without reprocessing the whole history).

        Args:
            bar:       Mapping with keys ``open``, ``high``, ``low``,
                       ``close``, ``volume``.
            timestamp: ISO-8601 date string for this bar.

        Returns:
            An optional ``Signal`` override.  Returning ``None`` means the
            event-driven backtester should fall back to the value from
            ``generate_signals()``.
        """
        return None

    def on_tick(self, tick: Dict[str, Any]) -> None:
        """Called for each intraday tick.

        No-op for daily strategies.  Override for strategies that
        need sub-bar resolution.

        Args:
            tick: Mapping with at minimum ``price``, ``volume``, ``timestamp``.
        """

    def on_news(self, news: Dict[str, Any]) -> None:
        """Called when a news event arrives.

        Override to adjust signal strength or force an immediate
        order based on sentiment or keywords.

        Args:
            news: Mapping with at minimum ``headline``, ``timestamp``,
                  and optionally ``sentiment``, ``ticker``.
        """

    def on_fill(self, fill_event: Any) -> None:
        """Called after an order is filled.

        Override to update internal position state (e.g. average
        entry price, remaining open quantity).

        Args:
            fill_event: A ``FillEvent`` from ``services.engine.events``
                        or any duck-typed equivalent.
        """

    def on_finish(self, result: Any) -> None:
        """Called when the backtest completes.

        Override for cleanup, logging, or post-run analysis.

        Args:
            result: The ``BacktestResult`` from ``services.backtest``.
        """


# ---------------------------------------------------------------------------
# Original four strategies — UNCHANGED
# ---------------------------------------------------------------------------


class SMACrossover(BaseStrategy):
    """
    Trend-following strategy — golden/death cross on two SMAs.

    BUY  when fast SMA crosses ABOVE slow SMA.
    SELL when fast SMA crosses BELOW slow SMA.
    """

    name = "sma_crossover"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        fast_period = int(self.params.get("fast_period", 10))
        slow_period = int(self.params.get("slow_period", 30))

        fast = sma(data["Close"], fast_period)
        slow = sma(data["Close"], slow_period)

        prev_fast = fast.shift(1)
        prev_slow = slow.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)
        cross_up = (fast > slow) & (prev_fast <= prev_slow)
        cross_down = (fast < slow) & (prev_fast >= prev_slow)

        signals[cross_up] = Signal.BUY
        signals[cross_down] = Signal.SELL
        return signals


class RSIMeanReversion(BaseStrategy):
    """
    Mean-reversion strategy based on RSI extremes.

    BUY  when RSI crosses ABOVE the oversold threshold (e.g. 30).
    SELL when RSI crosses ABOVE the overbought threshold (e.g. 70).
    """

    name = "rsi_mean_reversion"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        period = int(self.params.get("period", 14))
        oversold = float(self.params.get("oversold", 30))
        overbought = float(self.params.get("overbought", 70))

        rsi_vals = compute_rsi(data["Close"], period)
        prev_rsi = rsi_vals.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)
        signals[(rsi_vals > oversold) & (prev_rsi <= oversold)] = Signal.BUY
        signals[(rsi_vals > overbought) & (prev_rsi <= overbought)] = Signal.SELL
        return signals


class MACDMomentum(BaseStrategy):
    """
    Momentum strategy — MACD line / signal line crossovers.

    BUY  when MACD line crosses ABOVE signal line (bullish momentum).
    SELL when MACD line crosses BELOW signal line (bearish momentum).
    """

    name = "macd_momentum"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        fast = int(self.params.get("fast", 12))
        slow = int(self.params.get("slow", 26))
        signal_period = int(self.params.get("signal", 9))

        md = compute_macd(data["Close"], fast, slow, signal_period)
        macd_line = md["macd"]
        signal_line = md["signal"]

        prev_macd = macd_line.shift(1)
        prev_signal = signal_line.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)
        signals[(macd_line > signal_line) & (prev_macd <= prev_signal)] = Signal.BUY
        signals[(macd_line < signal_line) & (prev_macd >= prev_signal)] = Signal.SELL
        return signals


class BollingerBandMeanReversion(BaseStrategy):
    """
    Mean-reversion on Bollinger Bands.

    BUY  when close touches or crosses below the lower band.
    SELL when close reaches the middle band (mean reversion target).
    """

    name = "bollinger_band"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        period = int(self.params.get("period", 20))
        std_dev = float(self.params.get("std_dev", 2.0))

        bb = bollinger_bands(data["Close"], period, std_dev)
        close = data["Close"]
        prev_close = close.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)

        touch_lower = (close <= bb["lower"]) & (prev_close > bb["lower"].shift(1))
        cross_middle = (close >= bb["middle"]) & (prev_close < bb["middle"].shift(1))

        signals[touch_lower] = Signal.BUY
        signals[cross_middle] = Signal.SELL
        return signals


# ---------------------------------------------------------------------------
# M11 Phase 2 — Seven new built-in strategies
# ---------------------------------------------------------------------------


class BuyAndHold(BaseStrategy):
    """Buy on the very first bar and hold to the end.

    This is the simplest possible strategy and serves as a benchmark:
    any active strategy should outperform buy-and-hold on a risk-adjusted basis.

    Params: (none)
    """

    name = "buy_and_hold"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)
        if not data.empty:
            signals.iloc[0] = Signal.BUY
        return signals


class DualMovingAverage(BaseStrategy):
    """Trend-following crossover using an EMA (fast) and SMA (slow).

    BUY  when the fast EMA crosses above the slow SMA.
    SELL when the fast EMA crosses below the slow SMA.

    The asymmetry between EMA and SMA means the fast line reacts to recent
    moves more aggressively than a pure SMA crossover, reducing lag on entries.

    Params:
        fast_period (int, default 10): EMA lookback.
        slow_period (int, default 30): SMA lookback.
    """

    name = "dual_ma"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        fast_period = int(self.params.get("fast_period", 10))
        slow_period = int(self.params.get("slow_period", 30))

        fast = ema(data["Close"], fast_period)
        slow = sma(data["Close"], slow_period)

        prev_fast = fast.shift(1)
        prev_slow = slow.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)
        cross_up = (fast > slow) & (prev_fast <= prev_slow)
        cross_down = (fast < slow) & (prev_fast >= prev_slow)

        signals[cross_up] = Signal.BUY
        signals[cross_down] = Signal.SELL
        return signals


class MomentumStrategy(BaseStrategy):
    """Rate-of-change momentum strategy.

    BUY  when ROC rises above +threshold (positive momentum confirmed).
    SELL when ROC falls below -threshold (negative momentum confirmed).

    A threshold of 0 means any positive ROC triggers a buy — useful for
    markets with persistent trends.  A higher threshold filters out noise
    at the cost of later entries.

    Params:
        period    (int,   default 20):  ROC lookback window.
        threshold (float, default 0.0): Minimum |ROC| to trigger a signal (%).
    """

    name = "momentum"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        period = int(self.params.get("period", 20))
        threshold = float(self.params.get("threshold", 0.0))

        roc = compute_roc(data["Close"], period)
        prev_roc = roc.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)

        # BUY: ROC crosses above +threshold from below
        cross_bull = (roc > threshold) & (prev_roc <= threshold)
        # SELL: ROC crosses below -threshold from above
        cross_bear = (roc < -threshold) & (prev_roc >= -threshold)

        signals[cross_bull] = Signal.BUY
        signals[cross_bear] = Signal.SELL
        return signals


class MeanReversionZScore(BaseStrategy):
    """Z-score mean-reversion strategy.

    Computes the rolling z-score of the close price over a lookback window.
    Buys when price is significantly below the mean (oversold) and sells
    when it reverts back toward the mean.

    BUY  when z-score crosses below -z_entry (price is z_entry std devs below mean).
    SELL when z-score crosses above +z_exit  (price reverts toward mean).

    Params:
        lookback (int,   default 20):  Rolling window for mean and std.
        z_entry  (float, default 1.5): Z-score threshold to enter (positive value).
        z_exit   (float, default 0.0): Z-score threshold to exit.
    """

    name = "mean_reversion"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        lookback = int(self.params.get("lookback", 20))
        z_entry = float(self.params.get("z_entry", 1.5))
        z_exit = float(self.params.get("z_exit", 0.0))

        close = data["Close"]
        roll_mean = close.rolling(lookback).mean()
        roll_std = close.rolling(lookback).std(ddof=1)
        z = (close - roll_mean) / roll_std.replace(0.0, np.nan)
        prev_z = z.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)

        # BUY: z crosses below -z_entry (price becomes deeply oversold)
        cross_oversold = (z < -z_entry) & (prev_z >= -z_entry)
        # SELL: z crosses above +z_exit (price reverts toward mean)
        cross_revert = (z > z_exit) & (prev_z <= z_exit)

        signals[cross_oversold] = Signal.BUY
        signals[cross_revert] = Signal.SELL
        return signals


class ChannelBreakout(BaseStrategy):
    """Donchian channel breakout strategy.

    BUY  when today's close exceeds the highest close of the previous *period* bars.
    SELL when today's close falls below the lowest close of the previous *period* bars.

    This captures sustained trending moves and avoids whipsaws by requiring
    a genuine new extreme rather than a minor crossover.

    Params:
        period (int, default 20): Lookback for the channel high/low.
    """

    name = "channel_breakout"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        period = int(self.params.get("period", 20))

        close = data["Close"]
        # Shift by 1 so signal on day T uses only data from days 0..T-1 (no look-ahead)
        upper = close.shift(1).rolling(period).max()
        lower = close.shift(1).rolling(period).min()

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)

        signals[close > upper] = Signal.BUY
        signals[close < lower] = Signal.SELL
        return signals


class PairsTrading(BaseStrategy):
    """Z-score pairs trading strategy on a pre-computed spread series.

    Treats the ``Close`` column as the spread (or log-ratio) between two
    co-integrated assets.  The caller is responsible for passing the correct
    spread DataFrame.  This design keeps ``generate_signals()`` interface
    unchanged and avoids network calls inside the service.

    BUY  (go long spread) when spread z-score < -z_entry (spread is cheap).
    SELL (go short spread) when spread z-score >  z_entry (spread is expensive).
    EXIT when |z-score| < z_exit (spread reverts to normal).

    In practice the backtester treats SELL as "exit long", so this strategy
    works for long-only mode by treating the spread as a synthetic asset.

    Params:
        lookback (int,   default 60):  Rolling window for z-score computation.
        z_entry  (float, default 2.0): Z-score threshold to enter.
        z_exit   (float, default 0.5): |Z-score| threshold to exit.
    """

    name = "pairs_trading"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        lookback = int(self.params.get("lookback", 60))
        z_entry = float(self.params.get("z_entry", 2.0))
        z_exit = float(self.params.get("z_exit", 0.5))

        spread = data["Close"]
        roll_mean = spread.rolling(lookback).mean()
        roll_std = spread.rolling(lookback).std(ddof=1)
        z = (spread - roll_mean) / roll_std.replace(0.0, np.nan)
        prev_z = z.shift(1)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)

        # BUY: z drops below -z_entry (spread is unusually cheap)
        cross_long = (z < -z_entry) & (prev_z >= -z_entry)
        # SELL: |z| reverts inside z_exit band from outside it, OR z rises above +z_entry
        cross_exit = (
            ((z.abs() < z_exit) & (prev_z.abs() >= z_exit))
            | ((z > z_entry) & (prev_z <= z_entry))
        )

        signals[cross_long] = Signal.BUY
        signals[cross_exit] = Signal.SELL
        return signals


class VolatilityBreakout(BaseStrategy):
    """ATR-based intraday volatility breakout strategy.

    Uses the Average True Range to measure expected daily volatility and
    triggers trades when the day's move from open exceeds a multiple of ATR.

    BUY  when Close > Open + multiplier × ATR (strong upward breakout).
    SELL when Close < Open - multiplier × ATR (strong downward breakout).

    Params:
        atr_period  (int,   default 14):  ATR lookback.
        multiplier  (float, default 1.5): ATR multiple for the breakout threshold.
    """

    name = "volatility_breakout"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        atr_period = int(self.params.get("atr_period", 14))
        multiplier = float(self.params.get("multiplier", 1.5))

        atr_vals = compute_atr(data["High"], data["Low"], data["Close"], atr_period)

        # Use previous bar's ATR to avoid look-ahead on today's range
        prev_atr = atr_vals.shift(1)
        threshold = multiplier * prev_atr

        close = data["Close"]
        open_ = data["Open"]
        move = close - open_

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=object)
        signals[move > threshold] = Signal.BUY
        signals[move < -threshold] = Signal.SELL
        return signals


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    # Original four (unchanged)
    "sma_crossover": SMACrossover,
    "rsi_mean_reversion": RSIMeanReversion,
    "macd_momentum": MACDMomentum,
    "bollinger_band": BollingerBandMeanReversion,
    # M11 Phase 2 — seven new strategies
    "buy_and_hold": BuyAndHold,
    "dual_ma": DualMovingAverage,
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionZScore,
    "channel_breakout": ChannelBreakout,
    "pairs_trading": PairsTrading,
    "volatility_breakout": VolatilityBreakout,
}


def get_strategy(name: str, params: Dict[str, Any]) -> BaseStrategy:
    """Instantiate a strategy by name.  Raises KeyError for unknown names."""
    cls = _STRATEGY_REGISTRY[name]
    return cls(params)


def list_strategy_names() -> list[str]:
    """Return all registered strategy keys."""
    return sorted(_STRATEGY_REGISTRY.keys())
