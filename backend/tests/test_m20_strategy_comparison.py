"""Tests for M20 StrategyComparisonEngine."""

from __future__ import annotations

from typing import Dict, List

import pytest

from services.m19_backtest_engine import BacktestEngine, PriceBar, SignalType
from services.m20_strategy_comparison import (
    StrategyComparisonEngine,
    StrategyMetrics,
    ComparisonResult,
    ComparisonRow,
    VALID_METRICS,
    _annualized_vol,
    _annualized_return,
    _sortino_ratio,
    _calmar_ratio,
    _profit_factor,
    _expectancy,
    _pearson_corr,
    _align_curves,
    _normalize_min_max,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bars(n: int, start: float = 100.0, drift: float = 0.002) -> List[PriceBar]:
    return [
        PriceBar(
            date=f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}",
            open=start * (1 + drift) ** i,
            high=start * (1 + drift) ** i * 1.005,
            low=start * (1 + drift) ** i * 0.995,
            close=start * (1 + drift) ** i,
            volume=1000.0,
        )
        for i in range(n)
    ]


def _make_signals(n: int, signal: SignalType = SignalType.LONG) -> Dict[str, SignalType]:
    dates = [f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}" for i in range(n)]
    return {d: signal for d in dates}


def _run_backtest_and_register(
    engine: StrategyComparisonEngine,
    name: str,
    n: int = 200,
    drift: float = 0.002,
    signal: SignalType = SignalType.LONG,
) -> str:
    bars = _make_bars(n, drift=drift)
    ticker = "SIM"
    price_data = {ticker: bars}
    signals = _make_signals(n, signal=signal)
    return engine.run_and_register(
        strategy_name=name,
        ticker=ticker,
        price_data=price_data,
        signals=signals,
        initial_capital=100_000.0,
        commission_rate=0.001,
    )


# ---------------------------------------------------------------------------
# Metric helper tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_annualized_vol_constant(self):
        curve = [100.0] * 200
        assert _annualized_vol(curve) == pytest.approx(0.0, abs=1e-9)

    def test_annualized_vol_positive(self):
        curve = [100.0 * (1.001 ** i) for i in range(200)]
        vol = _annualized_vol(curve)
        assert vol >= 0

    def test_annualized_return_uptrend(self):
        curve = [100.0 * (1.001 ** i) for i in range(252)]
        ann_ret = _annualized_return(curve)
        assert ann_ret > 0

    def test_annualized_return_short_curve(self):
        assert _annualized_return([100.0]) == 0.0

    def test_sortino_flat(self):
        curve = [100.0] * 100
        assert _sortino_ratio(curve) == 0.0

    def test_sortino_uptrend(self):
        curve = [100.0 * (1.001 ** i) for i in range(252)]
        sortino = _sortino_ratio(curve)
        assert isinstance(sortino, float)

    def test_calmar_zero_drawdown(self):
        assert _calmar_ratio(0.10, 0.0) == 0.0

    def test_calmar_positive(self):
        calmar = _calmar_ratio(0.20, -0.10)
        assert calmar == pytest.approx(2.0)

    def test_profit_factor_short_curve(self):
        assert _profit_factor([100.0]) == 0.0

    def test_profit_factor_all_gains(self):
        curve = [100.0, 110.0, 120.0]
        pf = _profit_factor(curve)
        assert pf == 0.0  # no losses → division by zero guard → 0

    def test_profit_factor_mixed(self):
        curve = [100.0, 110.0, 105.0, 115.0]
        pf = _profit_factor(curve)
        assert pf > 0

    def test_expectancy_uptrend(self):
        curve = [100.0 * (1.001 ** i) for i in range(50)]
        exp = _expectancy(curve)
        assert exp > 0

    def test_pearson_corr_perfect(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert _pearson_corr(x, y) == pytest.approx(1.0)

    def test_pearson_corr_anticorrelated(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert _pearson_corr(x, y) == pytest.approx(-1.0)

    def test_pearson_corr_short(self):
        assert _pearson_corr([1.0], [2.0]) == 0.0

    def test_align_curves_equal_length(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0, 7.0]
        aligned = _align_curves([a, b])
        assert len(aligned[0]) == 3
        assert len(aligned[1]) == 3

    def test_align_curves_empty(self):
        assert _align_curves([]) == []

    def test_normalize_min_max_range(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = _normalize_min_max(values)
        assert min(normalized) == pytest.approx(0.0)
        assert max(normalized) == pytest.approx(1.0)

    def test_normalize_min_max_constant(self):
        normalized = _normalize_min_max([3.0, 3.0, 3.0])
        assert normalized == [0.5, 0.5, 0.5]


# ---------------------------------------------------------------------------
# StrategyComparisonEngine tests
# ---------------------------------------------------------------------------

class TestStrategyComparisonEngine:
    def setup_method(self):
        self.engine = StrategyComparisonEngine()

    # ------ run_and_register ------

    def test_run_and_register_returns_id(self):
        sid = _run_backtest_and_register(self.engine, "Bull Strategy")
        assert isinstance(sid, str) and len(sid) > 0

    def test_run_and_register_stores_metrics(self):
        sid = _run_backtest_and_register(self.engine, "Bull Strategy")
        metrics = self.engine.get_metrics(sid)
        assert metrics is not None
        assert metrics.strategy_name == "Bull Strategy"

    def test_run_and_register_distinct_ids(self):
        sid1 = _run_backtest_and_register(self.engine, "S1")
        sid2 = _run_backtest_and_register(self.engine, "S2", drift=0.001)
        assert sid1 != sid2

    # ------ register_result ------

    def test_register_result_from_backtest(self):
        be = BacktestEngine()
        bars = _make_bars(200)
        from services.m19_backtest_engine import Signal
        signal_list = [Signal(date=d, ticker="X", signal_type=SignalType.LONG) for d in _make_signals(200).keys()]
        result = be.run(strategy_name="X", signals=signal_list, price_data={"X": bars}, initial_capital=100_000.0, commission_rate=0.001)
        sid = self.engine.register_result("External", result)
        assert sid is not None
        assert self.engine.get_metrics(sid).strategy_name == "External"

    # ------ get_metrics ------

    def test_get_metrics_none_for_unknown(self):
        assert self.engine.get_metrics("unknown-id") is None

    def test_metrics_fields(self):
        sid = _run_backtest_and_register(self.engine, "Test")
        m = self.engine.get_metrics(sid)
        assert hasattr(m, "sharpe_ratio")
        assert hasattr(m, "sortino_ratio")
        assert hasattr(m, "calmar_ratio")
        assert hasattr(m, "max_drawdown")
        assert hasattr(m, "win_rate")

    def test_metrics_to_dict_keys(self):
        sid = _run_backtest_and_register(self.engine, "Test")
        d = self.engine.get_metrics(sid).to_dict()
        required = {
            "strategy_id", "strategy_name", "total_return", "annualized_return",
            "sharpe_ratio", "sortino_ratio", "calmar_ratio", "max_drawdown",
            "win_rate", "volatility", "num_trades", "profit_factor", "expectancy",
        }
        assert required.issubset(set(d.keys()))

    # ------ compare ------

    def test_compare_returns_result(self):
        sid1 = _run_backtest_and_register(self.engine, "Bull", drift=0.003)
        sid2 = _run_backtest_and_register(self.engine, "Bear", drift=-0.001)
        result = self.engine.compare([sid1, sid2])
        assert isinstance(result, ComparisonResult)

    def test_compare_ranked_table_length(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}", drift=0.001 * (i + 1)) for i in range(3)]
        result = self.engine.compare(ids)
        assert len(result.ranked_table) == 3

    def test_compare_ranks_are_sequential(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}") for i in range(3)]
        result = self.engine.compare(ids)
        ranks = [row.rank for row in result.ranked_table]
        assert ranks == [1, 2, 3]

    def test_compare_best_strategy_in_table(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}") for i in range(2)]
        result = self.engine.compare(ids)
        assert result.best_strategy in {result.ranked_table[0].strategy_name}

    def test_compare_cached(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}") for i in range(2)]
        result = self.engine.compare(ids)
        retrieved = self.engine.get_comparison(result.comparison_id)
        assert retrieved is result

    def test_compare_unknown_metric_raises(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}") for i in range(2)]
        with pytest.raises(ValueError, match="Unknown metric"):
            self.engine.compare(ids, primary_metric="nonexistent_metric")

    def test_compare_unknown_strategy_id_raises(self):
        _run_backtest_and_register(self.engine, "S1")
        with pytest.raises(ValueError, match="Unknown strategy_id"):
            self.engine.compare(["valid-but-not-real-uuid"])

    def test_compare_with_correlation(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}") for i in range(2)]
        result = self.engine.compare(ids, include_correlation=True)
        assert result.correlation_matrix is not None
        assert len(result.correlation_matrix) == 2

    def test_compare_without_correlation(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}") for i in range(2)]
        result = self.engine.compare(ids, include_correlation=False)
        assert result.correlation_matrix is None

    def test_compare_to_dict(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}") for i in range(2)]
        result = self.engine.compare(ids)
        d = result.to_dict()
        assert "comparison_id" in d and "ranked_table" in d and "best_strategy" in d

    def test_get_comparison_none_for_missing(self):
        assert self.engine.get_comparison("no-such-id") is None

    # ------ best_by_metric / rank_by_metric ------

    def test_best_by_metric_sharpe(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}", drift=0.001 * (i + 1)) for i in range(3)]
        best = self.engine.best_by_metric(ids, "sharpe_ratio")
        assert isinstance(best, StrategyMetrics)

    def test_best_by_metric_invalid_raises(self):
        sid = _run_backtest_and_register(self.engine, "S")
        with pytest.raises(ValueError, match="Unknown metric"):
            self.engine.best_by_metric([sid], "fake_metric")

    def test_best_by_metric_returns_none_empty(self):
        result = self.engine.best_by_metric([], "sharpe_ratio")
        assert result is None

    def test_rank_by_metric_order(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}", drift=0.001 * (i + 1)) for i in range(3)]
        ranked = self.engine.rank_by_metric(ids, "annualized_return")
        assert len(ranked) == 3
        returns = [m.annualized_return for _, m in ranked]
        assert returns == sorted(returns, reverse=True)

    def test_rank_by_metric_drawdown_lower_better(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}", drift=0.001 * (i + 1)) for i in range(3)]
        ranked = self.engine.rank_by_metric(ids, "max_drawdown")
        dds = [m.max_drawdown for _, m in ranked]
        assert dds == sorted(dds, reverse=True)

    # ------ head_to_head ------

    def test_head_to_head_returns_dict(self):
        sid1 = _run_backtest_and_register(self.engine, "Bull", drift=0.003)
        sid2 = _run_backtest_and_register(self.engine, "Bear", drift=-0.001)
        result = self.engine.head_to_head(sid1, sid2)
        assert "overall_winner" in result
        assert "metrics" in result

    def test_head_to_head_wins_add_up(self):
        sid1 = _run_backtest_and_register(self.engine, "A", drift=0.002)
        sid2 = _run_backtest_and_register(self.engine, "B", drift=0.003)
        result = self.engine.head_to_head(sid1, sid2)
        total = result["wins_a"] + result["wins_b"]
        assert total <= len(VALID_METRICS)

    def test_head_to_head_unknown_raises(self):
        _run_backtest_and_register(self.engine, "A")
        with pytest.raises(ValueError, match="Unknown strategy_id"):
            self.engine.head_to_head("bad-id", "also-bad")

    def test_head_to_head_metric_keys(self):
        sid1 = _run_backtest_and_register(self.engine, "A")
        sid2 = _run_backtest_and_register(self.engine, "B")
        result = self.engine.head_to_head(sid1, sid2)
        for metric in VALID_METRICS:
            assert metric in result["metrics"]

    # ------ list_strategies / reset ------

    def test_list_strategies_empty(self):
        assert self.engine.list_strategies() == []

    def test_list_strategies_after_register(self):
        _run_backtest_and_register(self.engine, "S1")
        _run_backtest_and_register(self.engine, "S2")
        listing = self.engine.list_strategies()
        assert len(listing) == 2
        names = {s["strategy_name"] for s in listing}
        assert "S1" in names and "S2" in names

    def test_reset_clears_all(self):
        _run_backtest_and_register(self.engine, "S1")
        self.engine.reset()
        assert self.engine.list_strategies() == []

    # ------ all valid metrics are exercised ------

    def test_valid_metrics_set_non_empty(self):
        assert len(VALID_METRICS) > 0

    def test_compare_all_valid_metrics(self):
        ids = [_run_backtest_and_register(self.engine, f"S{i}", drift=0.001 * (i + 1)) for i in range(2)]
        for metric in VALID_METRICS:
            result = self.engine.compare(ids, primary_metric=metric)
            assert result.primary_metric == metric
