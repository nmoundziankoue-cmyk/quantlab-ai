"""
Unit tests for services/strategy.py.

Deterministic synthetic price series are used to trigger known crossovers,
allowing exact signal verification without network calls.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.strategy import (
    BollingerBandMeanReversion,
    MACDMomentum,
    RSIMeanReversion,
    SMACrossover,
    Signal,
    get_strategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_df(close_values: list, n_leading: int = 0) -> pd.DataFrame:
    """Create a minimal OHLCV DataFrame from a close prices list."""
    all_close = [close_values[0]] * n_leading + list(close_values)
    n = len(all_close)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(all_close, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": [1_000_000.0] * n,
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# SMA Crossover
# ---------------------------------------------------------------------------


class TestSMACrossover:
    def test_golden_cross_generates_buy(self):
        """
        Create a price series where the fast SMA (3) crosses above the slow SMA (5).
        The strategy should emit a BUY on the cross date.
        """
        strategy = SMACrossover({"fast_period": 3, "slow_period": 5})
        # 20 bars of flat, then 20 bars of rising — golden cross should appear
        flat = [100.0] * 20
        rising = [100.0 + i * 3 for i in range(20)]
        df = _make_df(flat + rising)
        signals = strategy.generate_signals(df)
        assert Signal.BUY in signals.tolist(), "Expected at least one BUY signal on golden cross"

    def test_death_cross_generates_sell(self):
        """Price series that rises then falls should produce a SELL on the death cross."""
        strategy = SMACrossover({"fast_period": 3, "slow_period": 5})
        rising = [100.0 + i * 3 for i in range(20)]
        falling = [160.0 - i * 3 for i in range(20)]
        df = _make_df(rising + falling)
        signals = strategy.generate_signals(df)
        assert Signal.SELL in signals.tolist(), "Expected at least one SELL signal on death cross"

    def test_flat_market_no_crossover(self):
        """Perfectly flat price → no SMA crossover → only HOLD signals."""
        strategy = SMACrossover({"fast_period": 3, "slow_period": 5})
        df = _make_df([100.0] * 50)
        signals = strategy.generate_signals(df)
        assert set(signals.tolist()) == {Signal.HOLD}

    def test_output_length_matches_input(self):
        strategy = SMACrossover({"fast_period": 3, "slow_period": 5})
        df = _make_df([100.0 + i for i in range(60)])
        signals = strategy.generate_signals(df)
        assert len(signals) == len(df)


# ---------------------------------------------------------------------------
# RSI Mean Reversion
# ---------------------------------------------------------------------------


class TestRSIMeanReversion:
    def test_sell_signal_after_strong_rally(self):
        """
        A series that declines first (pushing RSI below 70) then surges sharply
        (RSI crosses back above 70) must produce a SELL signal.
        """
        strategy = RSIMeanReversion({"period": 5, "oversold": 30, "overbought": 70})
        # Decline enough to drive RSI below 70, then rally sharply above 70
        decline = [100.0 - i * 0.5 for i in range(20)]   # mild decline, RSI ~30-50
        surge = [decline[-1] + i * 4 for i in range(20)]  # sharp rally → RSI shoots above 70
        df = _make_df(decline + surge)
        signals = strategy.generate_signals(df)
        assert Signal.SELL in signals.tolist(), "Expected SELL after RSI crosses overbought"

    def test_buy_signal_after_sharp_decline(self):
        """A sustained decline drives RSI below 30 → BUY when it recovers above 30."""
        strategy = RSIMeanReversion({"period": 5, "oversold": 30, "overbought": 70})
        flat = [100.0] * 15
        decline = [100.0 - i * 3 for i in range(15)]
        recovery = [100.0 - 45.0 + i * 2 for i in range(10)]
        df = _make_df(flat + decline + recovery)
        signals = strategy.generate_signals(df)
        assert Signal.BUY in signals.tolist(), "Expected BUY on RSI recovery from oversold"

    def test_output_dtype(self):
        strategy = RSIMeanReversion({})
        df = _make_df([100.0 + i * 0.5 for i in range(60)])
        signals = strategy.generate_signals(df)
        for sig in signals.tolist():
            assert isinstance(sig, Signal)


# ---------------------------------------------------------------------------
# MACD Momentum
# ---------------------------------------------------------------------------


class TestMACDMomentum:
    def test_buy_on_bullish_crossover(self):
        """
        Accelerating uptrend → MACD line crosses above signal line → BUY.
        """
        strategy = MACDMomentum({"fast": 3, "slow": 6, "signal": 2})
        flat = [100.0] * 20
        accel = [100.0 + i ** 1.5 for i in range(30)]
        df = _make_df(flat + accel)
        signals = strategy.generate_signals(df)
        assert Signal.BUY in signals.tolist()

    def test_output_length(self):
        strategy = MACDMomentum({"fast": 3, "slow": 6, "signal": 2})
        df = _make_df([100.0] * 80)
        signals = strategy.generate_signals(df)
        assert len(signals) == len(df)


# ---------------------------------------------------------------------------
# Bollinger Band Mean Reversion
# ---------------------------------------------------------------------------


class TestBollingerBandMeanReversion:
    def test_buy_signal_on_lower_band_touch(self):
        """A price that crosses below the lower BB band triggers a BUY signal."""
        strategy = BollingerBandMeanReversion({"period": 10, "std_dev": 1.5})
        # Oscillating base creates non-zero std (required for Bollinger Bands to have spread)
        import math as _math
        base = [100.0 + _math.sin(i * 0.5) * 3 for i in range(30)]
        # Sharp single-bar drop well below the lower band
        crash = [base[-1] - 20.0, base[-1] - 22.0, base[-1] - 18.0]
        recover = [base[-1] - 18.0 + i * 1.5 for i in range(20)]
        df = _make_df(base + crash + recover)
        signals = strategy.generate_signals(df)
        assert Signal.BUY in signals.tolist()

    def test_output_only_valid_signals(self):
        strategy = BollingerBandMeanReversion({})
        df = _make_df([100.0 + np.sin(i * 0.3) * 5 for i in range(80)])
        signals = strategy.generate_signals(df)
        for sig in signals.tolist():
            assert sig in (Signal.BUY, Signal.SELL, Signal.HOLD)


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------


class TestStrategyRegistry:
    def test_all_strategies_registered(self):
        for name in ["sma_crossover", "rsi_mean_reversion", "macd_momentum", "bollinger_band"]:
            strat = get_strategy(name, {})
            assert strat is not None

    def test_unknown_strategy_raises(self):
        with pytest.raises(KeyError):
            get_strategy("nonexistent_strategy", {})

    def test_strategy_names_match_registry_keys(self):
        for name in ["sma_crossover", "rsi_mean_reversion", "macd_momentum", "bollinger_band"]:
            strat = get_strategy(name, {})
            assert strat.name == name
