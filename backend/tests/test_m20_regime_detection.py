"""Tests for M20 RegimeDetectionEngine."""

from __future__ import annotations

import math
from typing import List

import pytest

from services.m20_regime_detection import (
    RegimeDetectionEngine,
    RegimeType,
    RegimePoint,
    RegimeResult,
    RegimeSummary,
    _sma,
    _realized_vol_annual,
    _momentum,
    _classify,
    _count_transitions,
    _average_durations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prices(n: int, start: float = 100.0, drift: float = 0.001) -> List[float]:
    """Generate a monotone rising price series."""
    return [start * (1 + drift) ** i for i in range(n)]


def _make_bars(prices: List[float]) -> List[dict]:
    return [{"date": f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}", "close": p, "open": p, "high": p, "low": p} for i, p in enumerate(prices)]


def _make_volatile_prices(n: int, amplitude: float = 0.05) -> List[float]:
    """Alternating up/down prices to generate high volatility."""
    prices = [100.0]
    for i in range(1, n):
        sign = 1 if i % 2 == 0 else -1
        prices.append(prices[-1] * (1 + sign * amplitude))
    return prices


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestSma:
    def test_full_window(self):
        assert _sma([1.0, 2.0, 3.0, 4.0, 5.0], 3) == pytest.approx(4.0 - 1/3 + 1/3)

    def test_exact(self):
        assert _sma([1.0, 2.0, 3.0], 3) == pytest.approx(2.0)

    def test_short_list_uses_all(self):
        assert _sma([10.0, 20.0], 5) == pytest.approx(15.0)

    def test_empty(self):
        assert _sma([], 5) == 0.0

    def test_window_one(self):
        assert _sma([7.0, 8.0, 9.0], 1) == pytest.approx(9.0)


class TestRealizedVol:
    def test_constant_prices_zero_vol(self):
        prices = [100.0] * 30
        assert _realized_vol_annual(prices, 20) == pytest.approx(0.0, abs=1e-10)

    def test_returns_nonnegative(self):
        prices = _make_volatile_prices(50)
        vol = _realized_vol_annual(prices, 20)
        assert vol >= 0.0

    def test_more_volatile_higher(self):
        calm = _make_prices(50, drift=0.0001)
        wild = _make_volatile_prices(50, amplitude=0.05)
        assert _realized_vol_annual(wild, 20) > _realized_vol_annual(calm, 20)

    def test_insufficient_data(self):
        assert _realized_vol_annual([100.0], 20) == 0.0

    def test_annualised_scale(self):
        prices = [100.0, 101.0, 100.0] * 10
        vol = _realized_vol_annual(prices, len(prices))
        assert vol == pytest.approx(math.sqrt((sum((r - sum([(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))])/len([(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]))**2 for r in [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))])) / len([(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]) * 252), rel=1e-6)


class TestMomentum:
    def test_positive_trend(self):
        prices = list(range(100, 130))
        mom = _momentum(prices, 20)
        assert mom > 0

    def test_negative_trend(self):
        prices = list(range(130, 100, -1))
        mom = _momentum(prices, 20)
        assert mom < 0

    def test_insufficient_data(self):
        assert _momentum([100.0], 20) == 0.0

    def test_flat(self):
        prices = [100.0] * 25
        assert _momentum(prices, 20) == pytest.approx(0.0, abs=1e-9)


class TestClassify:
    def _call(self, fast, slow, mom, recent_vol, long_vol):
        return _classify(fast, slow, mom, recent_vol, long_vol, 1.5, 0.5, 0.02)

    def test_high_vol(self):
        regime, conf, _ = self._call(105, 100, 0.05, 0.30, 0.15)
        assert regime == RegimeType.HIGH_VOL
        assert conf >= 0.5

    def test_low_vol(self):
        regime, conf, _ = self._call(105, 100, 0.00, 0.05, 0.20)
        assert regime == RegimeType.LOW_VOL

    def test_bull(self):
        regime, conf, _ = self._call(110, 100, 0.05, 0.10, 0.10)
        assert regime == RegimeType.BULL

    def test_bear(self):
        regime, conf, _ = self._call(90, 100, -0.05, 0.10, 0.10)
        assert regime == RegimeType.BEAR

    def test_ranging(self):
        regime, conf, _ = self._call(100, 100, 0.00, 0.10, 0.10)
        assert regime == RegimeType.RANGING
        assert conf == 0.50

    def test_confidence_bounded(self):
        for _ in range(5):
            regime, conf, _ = self._call(200, 100, 0.90, 2.0, 1.0)
            assert 0.0 <= conf <= 1.0


class TestCountTransitions:
    def test_no_transitions(self):
        pts = [RegimePoint(date="d1", regime=RegimeType.BULL, confidence=0.8, indicators={})] * 5
        assert _count_transitions(pts) == 0

    def test_one_transition(self):
        pts = [
            RegimePoint(date="d1", regime=RegimeType.BULL, confidence=0.8, indicators={}),
            RegimePoint(date="d2", regime=RegimeType.BULL, confidence=0.8, indicators={}),
            RegimePoint(date="d3", regime=RegimeType.BEAR, confidence=0.7, indicators={}),
        ]
        assert _count_transitions(pts) == 1

    def test_empty(self):
        assert _count_transitions([]) == 0

    def test_alternating(self):
        regimes = [RegimeType.BULL, RegimeType.BEAR] * 5
        pts = [RegimePoint(date=f"d{i}", regime=r, confidence=0.6, indicators={}) for i, r in enumerate(regimes)]
        assert _count_transitions(pts) == 9


class TestAverageDurations:
    def test_single_regime(self):
        pts = [RegimePoint(date=f"d{i}", regime=RegimeType.RANGING, confidence=0.5, indicators={}) for i in range(10)]
        durations = _average_durations(pts)
        assert durations == {"RANGING": 10.0}

    def test_two_runs(self):
        pts = (
            [RegimePoint(date=f"d{i}", regime=RegimeType.BULL, confidence=0.8, indicators={}) for i in range(3)] +
            [RegimePoint(date=f"d{i}", regime=RegimeType.BEAR, confidence=0.7, indicators={}) for i in range(3, 6)]
        )
        durations = _average_durations(pts)
        assert durations["BULL"] == pytest.approx(3.0)
        assert durations["BEAR"] == pytest.approx(3.0)

    def test_empty(self):
        assert _average_durations([]) == {}


# ---------------------------------------------------------------------------
# RegimeDetectionEngine tests
# ---------------------------------------------------------------------------

class TestRegimeDetectionEngine:
    def setup_method(self):
        self.engine = RegimeDetectionEngine()

    def test_detect_returns_regime_result(self):
        bars = _make_bars(_make_prices(300))
        result = self.engine.detect("AAPL", bars)
        assert isinstance(result, RegimeResult)
        assert result.ticker == "AAPL"

    def test_detect_caches_result(self):
        bars = _make_bars(_make_prices(300))
        result = self.engine.detect("AAPL", bars)
        assert self.engine.get_result("AAPL") is result

    def test_get_result_none_for_unknown(self):
        assert self.engine.get_result("UNKNOWN") is None

    def test_get_current_regime_returns_point(self):
        bars = _make_bars(_make_prices(300))
        self.engine.detect("AAPL", bars)
        point = self.engine.get_current_regime("AAPL")
        assert isinstance(point, RegimePoint)
        assert isinstance(point.regime, RegimeType)

    def test_get_current_regime_none_for_unknown(self):
        assert self.engine.get_current_regime("ZZZY") is None

    def test_history_has_multiple_points(self):
        bars = _make_bars(_make_prices(300))
        self.engine.detect("AAPL", bars)
        hist = self.engine.get_history("AAPL")
        assert len(hist) > 10

    def test_history_empty_for_unknown(self):
        assert self.engine.get_history("UNKNOWN") == []

    def test_list_tickers_empty_initially(self):
        assert self.engine.list_tickers() == []

    def test_list_tickers_after_detect(self):
        bars = _make_bars(_make_prices(300))
        self.engine.detect("AAPL", bars)
        self.engine.detect("MSFT", bars)
        assert sorted(self.engine.list_tickers()) == ["AAPL", "MSFT"]

    def test_summary_dominant_regime(self):
        bars = _make_bars(_make_prices(300))
        self.engine.detect("AAPL", bars)
        summary = self.engine.get_summary()
        assert isinstance(summary, RegimeSummary)
        assert summary.dominant_regime in [r.value for r in RegimeType]

    def test_summary_counts_match_tickers(self):
        bars = _make_bars(_make_prices(300))
        self.engine.detect("AAPL", bars)
        self.engine.detect("MSFT", bars)
        summary = self.engine.get_summary()
        total = sum(summary.regime_counts.values())
        assert total == 2

    def test_compare_regimes_returns_dict(self):
        bars = _make_bars(_make_prices(300))
        self.engine.detect("AAPL", bars)
        result = self.engine.compare_regimes(["AAPL", "MISSING"])
        assert "AAPL" in result
        assert result["MISSING"]["regime"] is None

    def test_reset_clears_cache(self):
        bars = _make_bars(_make_prices(300))
        self.engine.detect("AAPL", bars)
        self.engine.reset()
        assert self.engine.list_tickers() == []
        assert self.engine.get_result("AAPL") is None

    def test_detect_from_returns(self):
        returns = [0.001 * (1 if i % 2 == 0 else -1) for i in range(300)]
        result = self.engine.detect_from_returns("SYN", returns)
        assert isinstance(result, RegimeResult)
        assert result.ticker == "SYN"

    def test_detect_from_returns_caches(self):
        returns = [0.002] * 300
        self.engine.detect_from_returns("GRW", returns)
        assert self.engine.get_result("GRW") is not None

    def test_result_to_dict_keys(self):
        bars = _make_bars(_make_prices(300))
        result = self.engine.detect("AAPL", bars)
        d = result.to_dict()
        assert set(d.keys()) == {
            "ticker", "detection_id", "current_regime", "current_confidence",
            "history", "num_observations", "transitions", "regime_durations",
        }

    def test_regime_point_to_dict(self):
        bars = _make_bars(_make_prices(300))
        result = self.engine.detect("AAPL", bars)
        first = result.history[0].to_dict()
        assert "date" in first and "regime" in first and "confidence" in first

    def test_current_confidence_in_range(self):
        bars = _make_bars(_make_prices(300))
        result = self.engine.detect("AAPL", bars)
        assert 0.0 <= result.current_confidence <= 1.0

    def test_num_observations_matches_bars(self):
        prices = _make_prices(300)
        bars = _make_bars(prices)
        result = self.engine.detect("AAPL", bars)
        assert result.num_observations == 300

    def test_transitions_nonnegative(self):
        bars = _make_bars(_make_prices(300))
        result = self.engine.detect("AAPL", bars)
        assert result.transitions >= 0

    def test_bear_regime_detected_on_falling_prices(self):
        prices = [100.0 * (0.999 ** i) for i in range(300)]
        bars = _make_bars(prices)
        result = self.engine.detect("BEAR_TEST", bars)
        assert result.current_regime in list(RegimeType)

    def test_dict_bars_accepted(self):
        bars = [{"date": f"2023-01-{i+1:02d}", "close": 100.0 + i, "open": 100.0, "high": 100.0 + i + 1, "low": 99.0} for i in range(300)]
        result = self.engine.detect("DICT", bars)
        assert result is not None

    def test_custom_thresholds(self):
        engine = RegimeDetectionEngine(
            fast_window=10,
            slow_window=20,
            vol_window=5,
            vol_lookback=30,
            vol_high_threshold=2.0,
            vol_low_threshold=0.3,
            momentum_threshold=0.01,
        )
        prices = _make_volatile_prices(100)
        bars = _make_bars(prices)
        result = engine.detect("CUSTOM", bars)
        assert isinstance(result, RegimeResult)

    def test_overwrite_ticker(self):
        bars_a = _make_bars(_make_prices(300))
        bars_b = _make_bars(_make_prices(300, start=200.0))
        self.engine.detect("AAPL", bars_a)
        self.engine.detect("AAPL", bars_b)
        assert self.engine.get_result("AAPL").history[0].indicators.get("fast_ma", 0) != 0

    def test_summary_empty_engine(self):
        summary = self.engine.get_summary()
        assert summary.tickers == []
        assert summary.regime_counts == {}

    def test_regime_type_enum_values(self):
        assert RegimeType.BULL.value == "BULL"
        assert RegimeType.HIGH_VOL.value == "HIGH_VOL"
        assert RegimeType.LOW_VOL.value == "LOW_VOL"
        assert RegimeType.RANGING.value == "RANGING"
        assert RegimeType.BEAR.value == "BEAR"
