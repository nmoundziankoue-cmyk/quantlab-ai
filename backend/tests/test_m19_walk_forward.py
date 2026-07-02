"""Tests for M19 WalkForwardEngine service."""

import pytest
from services.m19_backtest_engine import PriceBar, Signal, SignalType
from services.m19_walk_forward import (
    WalkForwardEngine,
    WalkForwardResult,
    WFWindow,
    StabilityMetrics,
    WindowMode,
)


def make_trending_bars(ticker: str, n: int = 80, start_price: float = 100.0, drift: float = 0.5) -> list:
    bars = []
    price = start_price
    for i in range(n):
        price += drift
        month = 1 + i // 28
        day = (i % 28) + 1
        bars.append(PriceBar(date=f"2024-{month:02d}-{day:02d}", open=price, high=price * 1.01,
                              low=price * 0.99, close=price, volume=100_000))
    return bars


def simple_signal_gen(dates, price_data):
    signals = []
    for ticker, bars in price_data.items():
        date_set = set(dates)
        filtered = sorted([b for b in bars if b.date in date_set], key=lambda b: b.date)
        if filtered:
            signals.append(Signal(filtered[0].date, ticker, SignalType.LONG, 1.0))
    return signals


class TestWalkForwardEngineInit:
    def test_created(self):
        engine = WalkForwardEngine()
        assert engine is not None

    def test_starts_empty(self):
        engine = WalkForwardEngine()
        assert engine.list_results() == []

    def test_reset_clears_results(self):
        engine = WalkForwardEngine()
        bars = make_trending_bars("AAPL", n=80)
        engine.run("s", {"AAPL": bars}, simple_signal_gen, in_sample_bars=30, out_sample_bars=10)
        engine.reset()
        assert engine.list_results() == []

    def test_get_nonexistent_returns_none(self):
        engine = WalkForwardEngine()
        assert engine.get_result("fake") is None

    def test_get_windows_nonexistent_returns_empty(self):
        engine = WalkForwardEngine()
        assert engine.get_windows("fake") == []

    def test_get_stability_nonexistent_returns_none(self):
        engine = WalkForwardEngine()
        assert engine.get_stability("fake") is None


class TestWalkForwardRun:
    def setup_method(self):
        self.engine = WalkForwardEngine()
        self.bars = make_trending_bars("AAPL", n=80)

    def test_run_returns_result(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert result is not None

    def test_run_produces_run_id(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert len(result.run_id) > 0

    def test_run_stores_strategy_name(self):
        result = self.engine.run("my_wf", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert result.strategy_name == "my_wf"

    def test_run_produces_windows(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert len(result.windows) > 0

    def test_run_produces_stability(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert result.stability is not None

    def test_run_cached(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        cached = self.engine.get_result(result.run_id)
        assert cached is not None
        assert cached.run_id == result.run_id

    def test_run_different_ids_each_call(self):
        r1 = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen, in_sample_bars=30, out_sample_bars=10)
        r2 = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen, in_sample_bars=30, out_sample_bars=10)
        assert r1.run_id != r2.run_id

    def test_run_expanding_mode(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10, window_mode=WindowMode.EXPANDING)
        assert result.window_mode == WindowMode.EXPANDING

    def test_run_rolling_mode(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10, window_mode=WindowMode.ROLLING)
        assert result.window_mode == WindowMode.ROLLING

    def test_run_stores_in_sample_bars(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert result.in_sample_bars == 30

    def test_run_stores_out_sample_bars(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert result.out_sample_bars == 10

    def test_run_insufficient_data_produces_no_windows(self):
        short_bars = make_trending_bars("AAPL", n=10)
        result = self.engine.run("s", {"AAPL": short_bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert len(result.windows) == 0


class TestWFWindow:
    def setup_method(self):
        self.engine = WalkForwardEngine()
        self.bars = make_trending_bars("AAPL", n=80)

    def test_window_has_indices(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        for i, w in enumerate(result.windows):
            assert w.window_index == i

    def test_window_has_dates(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        for w in result.windows:
            assert w.in_sample_start != ""
            assert w.out_sample_end != ""

    def test_window_has_sharpe_values(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        for w in result.windows:
            assert isinstance(w.in_sample_sharpe, float)
            assert isinstance(w.out_sample_sharpe, float)

    def test_window_has_returns(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        for w in result.windows:
            assert isinstance(w.in_sample_return, float)
            assert isinstance(w.out_sample_return, float)

    def test_window_has_backtest_id(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        for w in result.windows:
            assert len(w.backtest_id) > 0

    def test_window_to_dict(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        if result.windows:
            d = result.windows[0].to_dict()
            assert "window_index" in d and "efficiency" in d


class TestStabilityMetrics:
    def setup_method(self):
        self.engine = WalkForwardEngine()
        self.bars = make_trending_bars("AAPL", n=80)

    def test_stability_has_num_windows(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert result.stability.num_windows >= 0

    def test_stability_score_in_range(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert 0.0 <= result.stability.stability_score <= 1.0

    def test_pct_windows_positive_in_range(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        assert 0.0 <= result.stability.pct_windows_positive <= 1.0

    def test_stability_to_dict(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        d = result.stability.to_dict()
        assert "stability_score" in d and "avg_oos_sharpe" in d

    def test_empty_stability_metrics(self):
        sm = StabilityMetrics(
            num_windows=0, avg_oos_sharpe=0.0, std_oos_sharpe=0.0, avg_efficiency=0.0,
            pct_windows_positive=0.0, stability_score=0.0, avg_oos_return=0.0, degradation=0.0
        )
        assert sm.num_windows == 0
        assert sm.stability_score == 0.0


class TestWalkForwardRetrieval:
    def setup_method(self):
        self.engine = WalkForwardEngine()
        self.bars = make_trending_bars("AAPL", n=80)

    def test_get_windows_returns_list(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        windows = self.engine.get_windows(result.run_id)
        assert isinstance(windows, list)

    def test_get_stability_returns_metrics(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        stability = self.engine.get_stability(result.run_id)
        assert stability is not None

    def test_list_results_contains_summary(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        lst = self.engine.list_results()
        assert any(r["run_id"] == result.run_id for r in lst)

    def test_list_result_has_stability_score(self):
        result = self.engine.run("s", {"AAPL": self.bars}, simple_signal_gen,
                                  in_sample_bars=30, out_sample_bars=10)
        lst = self.engine.list_results()
        row = next(r for r in lst if r["run_id"] == result.run_id)
        assert "stability_score" in row


class TestWalkForwardToDict:
    def test_result_to_dict(self):
        engine = WalkForwardEngine()
        bars = make_trending_bars("AAPL", n=80)
        result = engine.run("s", {"AAPL": bars}, simple_signal_gen, in_sample_bars=30, out_sample_bars=10)
        d = result.to_dict()
        assert "run_id" in d
        assert "windows" in d
        assert "stability" in d
        assert isinstance(d["windows"], list)

    def test_window_mode_serialized(self):
        engine = WalkForwardEngine()
        bars = make_trending_bars("AAPL", n=80)
        result = engine.run("s", {"AAPL": bars}, simple_signal_gen, in_sample_bars=30,
                             out_sample_bars=10, window_mode=WindowMode.EXPANDING)
        d = result.to_dict()
        assert d["window_mode"] == "EXPANDING"
