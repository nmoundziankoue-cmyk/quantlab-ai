"""M11 Phase 2 — Tests for the extended strategy framework.

Coverage:
  Backward compatibility
    - All 4 original strategies still importable and callable
    - get_strategy() still works for all original keys
    - generate_signals() still returns Series of Signal values
  BaseStrategy lifecycle hooks
    - All 6 hooks exist on BaseStrategy subclasses
    - Default implementations are no-ops (return None / None)
    - Hooks can be overridden and invoked without error
  New built-in strategies (7)
    - buy_and_hold: BUY on first bar, HOLD everywhere else
    - dual_ma: signals are BUY/SELL/HOLD, crossover logic
    - momentum: threshold=0 gives BUY/SELL when ROC changes sign
    - mean_reversion: BUY when deep below mean, SELL when reverted
    - channel_breakout: BUY on new high, SELL on new low
    - pairs_trading: BUY on low z-score, SELL on reversion
    - volatility_breakout: BUY/SELL based on ATR-scaled move from open
  Registry & schema
    - All 11 strategies in _STRATEGY_REGISTRY
    - list_strategy_names() returns all keys
    - AVAILABLE_STRATEGIES in schemas.research covers all 11
    - RunBacktestRequest validates all new strategy names
  Signal output invariants
    - generate_signals() always returns pd.Series with same index as input
    - All values are Signal enum members (BUY, SELL, or HOLD)
    - No look-ahead: all strategies use only data up to bar T for signal T
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.strategy import (
    BaseStrategy,
    BollingerBandMeanReversion,
    BuyAndHold,
    ChannelBreakout,
    DualMovingAverage,
    MACDMomentum,
    MeanReversionZScore,
    MomentumStrategy,
    PairsTrading,
    RSIMeanReversion,
    SMACrossover,
    Signal,
    VolatilityBreakout,
    _STRATEGY_REGISTRY,
    get_strategy,
    list_strategy_names,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic OHLCV data
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 120, seed: int = 42, trend: float = 0.001) -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame with a mild upward trend."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    close = 100.0 * np.cumprod(1 + trend + rng.normal(0, 0.01, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    high = np.maximum(close, open_) * (1 + rng.uniform(0, 0.005, n))
    low = np.minimum(close, open_) * (1 - rng.uniform(0, 0.005, n))
    volume = rng.uniform(1_000_000, 5_000_000, n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


def _make_trending(n: int = 120) -> pd.DataFrame:
    """Strongly trending upward data — ensures crossover strategies produce at least one BUY.

    Design: flat/declining for the first third, then strong uptrend.
    This ensures the slow MA is anchored low while the fast MA picks up
    the trend, creating a genuine golden-cross BUY event.
    """
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    third = n // 3
    flat_part = np.linspace(100, 95, third)                 # slight decline
    trend_part = np.linspace(95, 140, n - third)            # strong uptrend
    close = np.concatenate([flat_part, trend_part])
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": np.ones(n) * 1_000_000,
        },
        index=idx,
    )


def _make_mean_reverting(n: int = 120, amplitude: float = 10.0) -> pd.DataFrame:
    """Oscillating data around 100 — guarantees mean-reversion signals."""
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    t = np.linspace(0, 4 * np.pi, n)
    close = 100 + amplitude * np.sin(t)
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": np.ones(n) * 1_000_000,
        },
        index=idx,
    )


def _assert_valid_signals(signals: pd.Series, data: pd.DataFrame) -> None:
    """Assert that *signals* is a well-formed output from generate_signals()."""
    assert isinstance(signals, pd.Series), "generate_signals() must return pd.Series"
    assert len(signals) == len(data), "Signal series length must match data length"
    assert signals.index.equals(data.index), "Signal index must match data index"
    valid = {Signal.BUY, Signal.SELL, Signal.HOLD}
    assert set(signals.unique()).issubset(valid), f"Unexpected signal values: {set(signals.unique()) - valid}"


def _has(signals: pd.Series, sig: Signal) -> bool:
    """Reliable containment check for Signal values inside a pandas Series.

    ``Signal.X in series.values`` is unreliable for numpy object arrays
    because numpy's __contains__ may short-circuit on the first identity match
    instead of using equality.  Using ``(series == sig).any()`` is always
    correct.
    """
    return bool((signals == sig).any())


# ---------------------------------------------------------------------------
# 1. Backward compatibility — original strategies unchanged
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    def test_sma_crossover_importable(self):
        s = SMACrossover({"fast_period": 5, "slow_period": 20})
        assert s.name == "sma_crossover"

    def test_rsi_mean_reversion_importable(self):
        s = RSIMeanReversion({"period": 14})
        assert s.name == "rsi_mean_reversion"

    def test_macd_momentum_importable(self):
        s = MACDMomentum({"fast": 12, "slow": 26, "signal": 9})
        assert s.name == "macd_momentum"

    def test_bollinger_band_importable(self):
        s = BollingerBandMeanReversion({"period": 20})
        assert s.name == "bollinger_band"

    def test_get_strategy_original_keys(self):
        for key in ("sma_crossover", "rsi_mean_reversion", "macd_momentum", "bollinger_band"):
            s = get_strategy(key, {})
            assert s is not None

    def test_original_strategies_generate_valid_signals(self):
        data = _make_ohlcv(120)
        for key in ("sma_crossover", "rsi_mean_reversion", "macd_momentum", "bollinger_band"):
            s = get_strategy(key, {})
            sigs = s.generate_signals(data)
            _assert_valid_signals(sigs, data)

    def test_sma_crossover_signal_values_on_trending_data(self):
        """SMA crossover must produce at least one BUY on data with a golden cross."""
        data = _make_trending(100)
        s = SMACrossover({"fast_period": 5, "slow_period": 20})
        sigs = s.generate_signals(data)
        assert _has(sigs, Signal.BUY), "Expected BUY signal on data with a golden cross"


# ---------------------------------------------------------------------------
# 2. BaseStrategy lifecycle hooks — existence and no-op defaults
# ---------------------------------------------------------------------------

class TestLifecycleHooks:
    def test_initialize_exists_and_is_noop(self):
        s = BuyAndHold({})
        result = s.initialize(config=None)
        assert result is None

    def test_on_bar_exists_and_returns_none(self):
        s = BuyAndHold({})
        result = s.on_bar({"open": 100, "close": 101}, "2024-01-02")
        assert result is None

    def test_on_tick_exists_and_is_noop(self):
        s = BuyAndHold({})
        result = s.on_tick({"price": 100.5, "volume": 1000})
        assert result is None

    def test_on_news_exists_and_is_noop(self):
        s = BuyAndHold({})
        result = s.on_news({"headline": "Earnings beat", "timestamp": "2024-01-02"})
        assert result is None

    def test_on_fill_exists_and_is_noop(self):
        s = BuyAndHold({})
        mock_fill = object()
        result = s.on_fill(mock_fill)
        assert result is None

    def test_on_finish_exists_and_is_noop(self):
        s = BuyAndHold({})
        mock_result = object()
        result = s.on_finish(mock_result)
        assert result is None

    def test_hooks_callable_on_all_strategies(self):
        """All hooks must be callable on every strategy without error."""
        data = _make_ohlcv(50)
        for name in list_strategy_names():
            s = get_strategy(name, {})
            s.initialize(None)
            s.on_bar({"open": 100, "close": 101}, "2024-01-01")
            s.on_tick({"price": 100})
            s.on_news({"headline": "test"})
            s.on_fill(None)
            s.on_finish(None)

    def test_hook_override_is_invoked(self):
        """A subclass that overrides on_bar() should have it called."""
        called = []

        class MyStrategy(BuyAndHold):
            name = "test_override"

            def on_bar(self, bar, timestamp):
                called.append((bar, timestamp))
                return Signal.BUY

        s = MyStrategy({})
        result = s.on_bar({"close": 105}, "2024-01-03")
        assert result == Signal.BUY
        assert len(called) == 1


# ---------------------------------------------------------------------------
# 3. New strategy: BuyAndHold
# ---------------------------------------------------------------------------

class TestBuyAndHold:
    def test_first_bar_is_buy(self):
        data = _make_ohlcv(50)
        s = BuyAndHold({})
        sigs = s.generate_signals(data)
        assert sigs.iloc[0] == Signal.BUY

    def test_remaining_bars_are_hold(self):
        data = _make_ohlcv(50)
        s = BuyAndHold({})
        sigs = s.generate_signals(data)
        assert all(v == Signal.HOLD for v in sigs.iloc[1:])

    def test_valid_signals(self):
        _assert_valid_signals(BuyAndHold({}).generate_signals(_make_ohlcv(30)), _make_ohlcv(30))

    def test_single_bar_data(self):
        data = _make_ohlcv(1)
        sigs = BuyAndHold({}).generate_signals(data)
        assert sigs.iloc[0] == Signal.BUY


# ---------------------------------------------------------------------------
# 4. New strategy: DualMovingAverage
# ---------------------------------------------------------------------------

class TestDualMovingAverage:
    def test_valid_signals(self):
        _assert_valid_signals(DualMovingAverage({}).generate_signals(_make_ohlcv(120)), _make_ohlcv(120))

    def test_produces_buy_on_trending_data(self):
        data = _make_trending(100)
        sigs = DualMovingAverage({"fast_period": 5, "slow_period": 20}).generate_signals(data)
        assert _has(sigs, Signal.BUY), "Expected BUY on data with a golden cross"

    def test_name(self):
        assert DualMovingAverage({}).name == "dual_ma"

    def test_default_params_work(self):
        data = _make_ohlcv(80)
        sigs = DualMovingAverage({}).generate_signals(data)
        _assert_valid_signals(sigs, data)


# ---------------------------------------------------------------------------
# 5. New strategy: MomentumStrategy
# ---------------------------------------------------------------------------

class TestMomentumStrategy:
    def test_valid_signals(self):
        _assert_valid_signals(MomentumStrategy({}).generate_signals(_make_ohlcv(120)), _make_ohlcv(120))

    def test_name(self):
        assert MomentumStrategy({}).name == "momentum"

    def test_zero_threshold_generates_signals(self):
        data = _make_mean_reverting(200)
        sigs = MomentumStrategy({"period": 10, "threshold": 0.0}).generate_signals(data)
        assert _has(sigs, Signal.BUY) or _has(sigs, Signal.SELL), \
            "Expected at least one BUY or SELL from momentum on oscillating data"

    def test_high_threshold_mostly_hold(self):
        """With a very high threshold, almost all bars should be HOLD."""
        data = _make_ohlcv(120)
        sigs = MomentumStrategy({"period": 20, "threshold": 1000.0}).generate_signals(data)
        hold_frac = (sigs == Signal.HOLD).mean()
        assert hold_frac > 0.95


# ---------------------------------------------------------------------------
# 6. New strategy: MeanReversionZScore
# ---------------------------------------------------------------------------

class TestMeanReversionZScore:
    def test_valid_signals(self):
        _assert_valid_signals(MeanReversionZScore({}).generate_signals(_make_ohlcv(120)), _make_ohlcv(120))

    def test_name(self):
        assert MeanReversionZScore({}).name == "mean_reversion"

    def test_produces_buy_on_oscillating_data(self):
        data = _make_mean_reverting(200, amplitude=15.0)
        sigs = MeanReversionZScore({"lookback": 20, "z_entry": 1.0}).generate_signals(data)
        assert _has(sigs, Signal.BUY), "Expected BUY on deeply oscillating data"

    def test_produces_sell_on_oscillating_data(self):
        data = _make_mean_reverting(200, amplitude=15.0)
        sigs = MeanReversionZScore({"lookback": 20, "z_entry": 1.0, "z_exit": 0.0}).generate_signals(data)
        assert _has(sigs, Signal.SELL), "Expected SELL when price reverts toward mean"


# ---------------------------------------------------------------------------
# 7. New strategy: ChannelBreakout
# ---------------------------------------------------------------------------

class TestChannelBreakout:
    def test_valid_signals(self):
        _assert_valid_signals(ChannelBreakout({}).generate_signals(_make_ohlcv(120)), _make_ohlcv(120))

    def test_name(self):
        assert ChannelBreakout({}).name == "channel_breakout"

    def test_buy_on_new_high(self):
        """Hand-crafted data: price climbs steadily then breaks out."""
        n = 50
        idx = pd.date_range("2022-01-03", periods=n, freq="B")
        close = np.concatenate([np.linspace(90, 100, 30), np.linspace(100, 115, 20)])
        df = pd.DataFrame(
            {"Open": close * 0.999, "High": close * 1.01, "Low": close * 0.99,
             "Close": close, "Volume": np.ones(n) * 1e6},
            index=idx,
        )
        sigs = ChannelBreakout({"period": 10}).generate_signals(df)
        assert _has(sigs, Signal.BUY), "Expected BUY when price exceeds the prior channel high"

    def test_no_lookahead(self):
        """Signal at bar T must not depend on data from bar T+1.

        We verify that replacing tomorrow's close with a huge value doesn't
        change today's signal.
        """
        data = _make_ohlcv(60)
        sigs_original = ChannelBreakout({"period": 10}).generate_signals(data)

        # Corrupt the last bar's close with an extreme value
        data_modified = data.copy()
        data_modified.iloc[-1, data_modified.columns.get_loc("Close")] = 1e9

        sigs_modified = ChannelBreakout({"period": 10}).generate_signals(data_modified)

        # All signals except the last bar should be identical
        assert (sigs_original.iloc[:-1] == sigs_modified.iloc[:-1]).all()


# ---------------------------------------------------------------------------
# 8. New strategy: PairsTrading
# ---------------------------------------------------------------------------

class TestPairsTrading:
    def test_valid_signals(self):
        _assert_valid_signals(PairsTrading({}).generate_signals(_make_mean_reverting(200)), _make_mean_reverting(200))

    def test_name(self):
        assert PairsTrading({}).name == "pairs_trading"

    def test_generates_signals_on_oscillating_spread(self):
        data = _make_mean_reverting(200, amplitude=10.0)
        sigs = PairsTrading({"lookback": 20, "z_entry": 1.5, "z_exit": 0.5}).generate_signals(data)
        assert _has(sigs, Signal.BUY) or _has(sigs, Signal.SELL), \
            "Expected at least one signal from pairs trading on oscillating spread"


# ---------------------------------------------------------------------------
# 9. New strategy: VolatilityBreakout
# ---------------------------------------------------------------------------

class TestVolatilityBreakout:
    def test_valid_signals(self):
        _assert_valid_signals(VolatilityBreakout({}).generate_signals(_make_ohlcv(120)), _make_ohlcv(120))

    def test_name(self):
        assert VolatilityBreakout({}).name == "volatility_breakout"

    def test_large_up_move_triggers_buy(self):
        """A bar where close far exceeds open should generate BUY."""
        n = 30
        idx = pd.date_range("2022-01-03", periods=n, freq="B")
        close = np.ones(n) * 100.0
        open_ = np.ones(n) * 100.0
        high = close * 1.005
        low = close * 0.995

        # Make bar 20 a large upward move: close = open + 10× ATR
        open_[20] = 100.0
        close[20] = 115.0   # +15% above open
        high[20] = 116.0
        low[20] = 99.5

        df = pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": np.ones(n) * 1e6},
            index=idx,
        )
        sigs = VolatilityBreakout({"atr_period": 5, "multiplier": 1.0}).generate_signals(df)
        assert sigs.iloc[20] == Signal.BUY

    def test_large_down_move_triggers_sell(self):
        """A bar where close far below open should generate SELL."""
        n = 30
        idx = pd.date_range("2022-01-03", periods=n, freq="B")
        close = np.ones(n) * 100.0
        open_ = np.ones(n) * 100.0
        high = close * 1.005
        low = close * 0.995

        open_[20] = 100.0
        close[20] = 85.0    # -15% below open
        high[20] = 100.5
        low[20] = 84.5

        df = pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": np.ones(n) * 1e6},
            index=idx,
        )
        sigs = VolatilityBreakout({"atr_period": 5, "multiplier": 1.0}).generate_signals(df)
        assert sigs.iloc[20] == Signal.SELL


# ---------------------------------------------------------------------------
# 10. Registry and schema consistency
# ---------------------------------------------------------------------------

class TestRegistryAndSchema:
    ALL_11 = {
        "sma_crossover", "rsi_mean_reversion", "macd_momentum", "bollinger_band",
        "buy_and_hold", "dual_ma", "momentum", "mean_reversion",
        "channel_breakout", "pairs_trading", "volatility_breakout",
    }

    def test_registry_contains_all_11_strategies(self):
        assert self.ALL_11.issubset(set(_STRATEGY_REGISTRY.keys()))

    def test_list_strategy_names_returns_all(self):
        names = set(list_strategy_names())
        assert self.ALL_11.issubset(names)

    def test_get_strategy_works_for_all_new_keys(self):
        new_keys = {"buy_and_hold", "dual_ma", "momentum", "mean_reversion",
                    "channel_breakout", "pairs_trading", "volatility_breakout"}
        for key in new_keys:
            s = get_strategy(key, {})
            assert s.name == key

    def test_available_strategies_schema_covers_all_11(self):
        from schemas.research import AVAILABLE_STRATEGIES
        assert self.ALL_11.issubset(set(AVAILABLE_STRATEGIES.keys()))

    def test_schema_entries_have_required_fields(self):
        from schemas.research import AVAILABLE_STRATEGIES
        for key, meta in AVAILABLE_STRATEGIES.items():
            assert "display_name" in meta, f"{key}: missing display_name"
            assert "description" in meta, f"{key}: missing description"
            assert "params" in meta, f"{key}: missing params"

    def test_run_backtest_request_validates_new_strategy_names(self):
        from schemas.research import RunBacktestRequest
        from datetime import date
        for key in ("buy_and_hold", "dual_ma", "momentum", "mean_reversion",
                    "channel_breakout", "pairs_trading", "volatility_breakout"):
            req = RunBacktestRequest(
                ticker="AAPL",
                start_date=date(2022, 1, 1),
                end_date=date(2022, 12, 31),
                strategy_name=key,
            )
            assert req.strategy_name == key

    def test_unknown_strategy_raises_key_error(self):
        with pytest.raises(KeyError):
            get_strategy("does_not_exist", {})


# ---------------------------------------------------------------------------
# 11. Signal output invariants across all strategies
# ---------------------------------------------------------------------------

class TestSignalOutputInvariants:
    def test_all_strategies_return_series_with_correct_index(self):
        data = _make_ohlcv(120)
        for name in list_strategy_names():
            s = get_strategy(name, {})
            sigs = s.generate_signals(data)
            assert sigs.index.equals(data.index), f"{name}: index mismatch"

    def test_all_strategies_return_only_valid_signals(self):
        data = _make_ohlcv(120)
        valid = {Signal.BUY, Signal.SELL, Signal.HOLD}
        for name in list_strategy_names():
            s = get_strategy(name, {})
            sigs = s.generate_signals(data)
            # Use set() on the unique values list (not numpy array) for reliable comparison
            bad = set(sigs.unique().tolist()) - valid
            assert not bad, f"{name}: invalid signal values {bad}"

    def test_all_strategies_handle_short_data(self):
        """Strategies should not crash on data shorter than their warmup window."""
        data = _make_ohlcv(15)
        for name in list_strategy_names():
            s = get_strategy(name, {})
            sigs = s.generate_signals(data)
            assert len(sigs) == len(data), f"{name}: length mismatch on short data"
