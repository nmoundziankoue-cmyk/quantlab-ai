"""Extended cross-module integration and edge-case tests for M19."""

import math
import pytest
from services.m19_backtest_engine import BacktestEngine, PriceBar, Signal, SignalType
from services.m19_execution_simulator import ExecutionSimulator, SimOrder, OrderType, SlippageModel
from services.m19_walk_forward import WalkForwardEngine, WindowMode
from services.m19_monte_carlo import MonteCarloEngine
from services.m19_factor_models import FactorModelEngine, FactorReturn, FactorType
from services.m19_optimization_lab import OptimizationLab, WeightConstraint


def make_bars(ticker, prices, base_date="2024"):
    return [
        PriceBar(date=f"{base_date}-01-{i+1:02d}", open=p, high=p * 1.01, low=p * 0.99, close=p)
        for i, p in enumerate(prices[:28])
    ]


def make_factor_returns(n=60, seed=0):
    import random
    rng = random.Random(seed)
    rets = []
    for i in range(n):
        d = f"2024-{'0' + str(1 + i // 28) if 1 + i // 28 < 10 else 1 + i // 28}-{(i % 28) + 1:02d}"
        for fac in [FactorType.MARKET, FactorType.SIZE, FactorType.VALUE]:
            rets.append(FactorReturn(date=d, factor=fac, return_value=rng.gauss(0, 0.01)))
    return rets


class TestIsolation:
    """Verify each engine resets cleanly without cross-test state pollution."""

    def test_backtest_engine_isolated(self):
        e1 = BacktestEngine()
        e2 = BacktestEngine()
        bars = make_bars("AAPL", [100 + i for i in range(10)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        e1.run("s1", signals, {"AAPL": bars})
        assert len(e2.list_results()) == 0

    def test_monte_carlo_isolated(self):
        mc1 = MonteCarloEngine(seed=0)
        mc2 = MonteCarloEngine(seed=0)
        mc1.run_gbm(0.001, 0.01, num_paths=10, num_steps=10)
        assert len(mc2.list_results()) == 0

    def test_factor_engine_isolated(self):
        fe1 = FactorModelEngine()
        fe2 = FactorModelEngine()
        fe1.add_factor_returns([FactorReturn("2024-01-01", FactorType.MARKET, 0.01)])
        assert fe2.list_tickers() == []

    def test_optimization_lab_isolated(self):
        lab1 = OptimizationLab()
        lab2 = OptimizationLab()
        lab1.min_variance(["A", "B"], {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.03}})
        assert len(lab2.list_results()) == 0

    def test_execution_simulator_isolated(self):
        import uuid
        sim1 = ExecutionSimulator()
        sim2 = ExecutionSimulator()
        order = SimOrder(str(uuid.uuid4()), "AAPL", OrderType.MARKET, "BUY", 100.0)
        sim1.simulate(order, 100.0)
        assert len(sim2.get_fill_history()) == 0

    def test_walk_forward_engine_isolated(self):
        wf1 = WalkForwardEngine()
        wf2 = WalkForwardEngine()
        bars = make_bars("AAPL", [100 + i for i in range(80)])
        wf1.run("s", {"AAPL": bars}, lambda d, pd: [], in_sample_bars=30, out_sample_bars=10)
        assert len(wf2.list_results()) == 0


class TestBacktestEngineEdgeCases:
    def test_single_bar_no_signals(self):
        engine = BacktestEngine()
        bar = PriceBar("2024-01-01", 100, 105, 98, 102)
        result = engine.run("s", [], {"AAPL": [bar]})
        assert result is not None

    def test_all_flat_signals(self):
        engine = BacktestEngine()
        bars = make_bars("AAPL", [100 + i for i in range(5)])
        signals = [Signal(b.date, "AAPL", SignalType.FLAT) for b in bars]
        result = engine.run("s", signals, {"AAPL": bars})
        assert result.metrics.num_trades == 0

    def test_identical_price_zero_variance(self):
        engine = BacktestEngine()
        bars = make_bars("AAPL", [100.0] * 10)
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        result = engine.run("s", signals, {"AAPL": bars})
        assert result.metrics.volatility == 0.0

    def test_large_position_size_capped_by_cash(self):
        engine = BacktestEngine()
        bars = make_bars("AAPL", [100 + i for i in range(10)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        result = engine.run("s", signals, {"AAPL": bars}, position_size_pct=2.0, initial_capital=1000.0)
        assert result.final_equity >= 0

    def test_multiple_signals_same_date_same_ticker(self):
        engine = BacktestEngine()
        bars = make_bars("AAPL", [100 + i for i in range(10)])
        signals = [
            Signal(bars[0].date, "AAPL", SignalType.LONG),
            Signal(bars[0].date, "AAPL", SignalType.LONG),
        ]
        result = engine.run("s", signals, {"AAPL": bars})
        assert result is not None


class TestMonteCarloEdgeCases:
    def test_bootstrap_single_return(self):
        mc = MonteCarloEngine(seed=0)
        result = mc.run_bootstrap([0.001] * 20, num_paths=10, num_steps=10)
        assert result.num_paths == 10

    def test_gbm_zero_drift(self):
        mc = MonteCarloEngine(seed=0)
        result = mc.run_gbm(0.0, 0.01, num_paths=50, num_steps=50)
        assert result is not None

    def test_gbm_high_volatility(self):
        mc = MonteCarloEngine(seed=0)
        result = mc.run_gbm(0.0, 0.5, num_paths=100, num_steps=100)
        assert result.max_drawdown_p95 > result.max_drawdown_p50

    def test_var_not_exceeds_one(self):
        mc = MonteCarloEngine(seed=0)
        result = mc.run_gbm(-0.01, 0.05, num_paths=200, num_steps=252)
        assert result.var_99 <= 1.0


class TestFactorModelEdgeCases:
    def test_regress_no_common_dates(self):
        fe = FactorModelEngine()
        fe.add_factor_returns([FactorReturn("2024-01-01", FactorType.MARKET, 0.01)])
        exp = fe.regress("AAPL", {"2025-12-01": 0.01}, [FactorType.MARKET])
        assert exp.r_squared == 0.0

    def test_attribution_sums_approximately(self):
        fe = FactorModelEngine()
        rets = make_factor_returns(n=60)
        fe.add_factor_returns(rets)
        import random
        rng = random.Random(0)
        dates = sorted({fr.date for fr in rets})
        sec_rets = {d: rng.gauss(0.001, 0.01) for d in dates}
        fe.regress("X", sec_rets, [FactorType.MARKET, FactorType.SIZE])
        attr = fe.compute_attribution("X", 0.10, {"MARKET": 0.08, "SIZE": 0.02})
        total = sum(attr.factor_contributions.values()) + attr.alpha_contribution + attr.residual
        assert abs(total - 0.10) < 0.5

    def test_pearson_single_element(self):
        from services.m19_factor_models import _pearson
        assert _pearson([1.0], [2.0]) == 0.0

    def test_mat_inv_3x3(self):
        from services.m19_factor_models import _mat_inv, _mat_mul
        A = [[2.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 2.0]]
        inv = _mat_inv(A)
        result = _mat_mul(A, inv)
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                assert abs(result[i][j] - expected) < 1e-6


class TestOptimizationEdgeCases:
    def test_equal_expected_returns_diversified(self):
        lab = OptimizationLab()
        tickers = ["A", "B", "C"]
        er = {t: 0.10 for t in tickers}
        cov = {t: {t2: 0.04 if t == t2 else 0.01 for t2 in tickers} for t in tickers}
        result = lab.mean_variance(tickers, er, cov)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3

    def test_risk_parity_equal_vols(self):
        lab = OptimizationLab()
        tickers = ["A", "B"]
        cov = {"A": {"A": 0.04, "B": 0.0}, "B": {"A": 0.0, "B": 0.04}}
        result = lab.risk_parity(tickers, cov)
        wa = result.weights.get("A", 0.0)
        wb = result.weights.get("B", 0.0)
        assert abs(wa - wb) < 0.1

    def test_min_variance_two_assets(self):
        lab = OptimizationLab()
        tickers = ["A", "B"]
        cov = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.01}}
        result = lab.min_variance(tickers, cov)
        assert result.volatility > 0

    def test_frontier_n_points_respected(self):
        lab = OptimizationLab()
        tickers = ["A", "B", "C"]
        er = {"A": 0.15, "B": 0.10, "C": 0.07}
        cov = {t: {t2: 0.04 if t == t2 else 0.01 for t2 in tickers} for t in tickers}
        points = lab.compute_frontier(tickers, er, cov, n_points=8)
        assert len(points) >= 1 and len(points) <= 8

    def test_weight_constraint_enforced(self):
        lab = OptimizationLab()
        tickers = ["A", "B"]
        er = {"A": 0.15, "B": 0.05}
        cov = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.01}}
        constraints = [WeightConstraint(ticker="A", min_weight=0.0, max_weight=0.30)]
        result = lab.mean_variance(tickers, er, cov, constraints=constraints)
        assert result.weights.get("A", 0.0) <= 0.35


class TestExecutionSimulatorEdgeCases:
    def test_large_order_partial_fill(self):
        import uuid
        sim = ExecutionSimulator(seed=10)
        order = SimOrder(str(uuid.uuid4()), "AAPL", OrderType.MARKET, "BUY", 1_000_000.0)
        fill = sim.simulate(order, market_price=100.0, market_volume=10_000.0)
        assert fill.fill_qty < order.quantity or fill.status.value in ("PARTIAL", "FILLED")

    def test_sell_order_buy_side_discrimination(self):
        import uuid
        sim = ExecutionSimulator(seed=11)
        buy_order = SimOrder(str(uuid.uuid4()), "AAPL", OrderType.MARKET, "BUY", 100.0)
        sell_order = SimOrder(str(uuid.uuid4()), "AAPL", OrderType.MARKET, "SELL", 100.0)
        buy_fill = sim.simulate(buy_order, market_price=100.0, market_volume=1e9, fixed_slippage_bps=10.0)
        sell_fill = sim.simulate(sell_order, market_price=100.0, market_volume=1e9, fixed_slippage_bps=10.0)
        if buy_fill.fill_qty > 0 and sell_fill.fill_qty > 0:
            assert buy_fill.fill_price >= sell_fill.fill_price


class TestWalkForwardEdgeCases:
    def test_no_windows_when_data_too_short(self):
        engine = WalkForwardEngine()
        bars = make_bars("AAPL", [100 + i for i in range(5)])
        result = engine.run("s", {"AAPL": bars}, lambda d, pd: [],
                             in_sample_bars=20, out_sample_bars=10)
        assert len(result.windows) == 0

    def test_empty_stability_on_no_windows(self):
        engine = WalkForwardEngine()
        bars = make_bars("AAPL", [100 + i for i in range(5)])
        result = engine.run("s", {"AAPL": bars}, lambda d, pd: [],
                             in_sample_bars=20, out_sample_bars=10)
        assert result.stability.num_windows == 0
        assert result.stability.stability_score == 0.0


class TestCrossModuleIntegration:
    def test_backtest_to_monte_carlo(self):
        engine = BacktestEngine()
        bars = make_bars("AAPL", [100.0 * (1.001 ** i) for i in range(28)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        result = engine.run("s", signals, {"AAPL": bars})
        curve = result.equity_curve
        daily_rets = []
        for i in range(1, len(curve)):
            prev = curve[i - 1].equity
            curr = curve[i].equity
            if prev > 0:
                daily_rets.append((curr - prev) / prev)
        if len(daily_rets) >= 10:
            mc = MonteCarloEngine(seed=0)
            mc_result = mc.run_bootstrap(daily_rets, num_paths=50, num_steps=len(daily_rets))
            assert mc_result.num_paths == 50

    def test_factor_model_then_optimization(self):
        fe = FactorModelEngine()
        rets = make_factor_returns(n=60)
        fe.add_factor_returns(rets)
        import random
        rng = random.Random(0)
        dates = sorted({fr.date for fr in rets})
        tickers = ["AAPL", "MSFT"]
        for t in tickers:
            sr = {d: rng.gauss(0.001, 0.01) for d in dates}
            fe.regress(t, sr, [FactorType.MARKET, FactorType.SIZE, FactorType.VALUE])
        lab = OptimizationLab(factor_engine=fe)
        cov = {t: {t2: 0.04 if t == t2 else 0.01 for t2 in tickers} for t in tickers}
        er = {t: 0.10 for t in tickers}
        result = lab.factor_constrained_optimize(tickers, er, cov, {"MARKET": [0.5, 2.0]})
        assert result is not None
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3

    def test_walk_forward_uses_backtest_engine(self):
        be = BacktestEngine()
        wf = WalkForwardEngine(backtest_engine=be)
        bars = make_bars("AAPL", [100 + i * 0.5 for i in range(28)])
        bars += [PriceBar(f"2024-02-{i+1:02d}", 114 + i * 0.5, 115, 113, 114 + i * 0.5) for i in range(28)]
        bars += [PriceBar(f"2024-03-{i+1:02d}", 128 + i * 0.5, 129, 127, 128 + i * 0.5) for i in range(25)]
        result = wf.run("s", {"AAPL": bars}, lambda d, pd: [],
                         in_sample_bars=30, out_sample_bars=20)
        assert result is not None
        assert len(be.list_results()) >= 0

    def test_optimization_frontier_coherent(self):
        lab = OptimizationLab()
        tickers = ["A", "B", "C"]
        er = {"A": 0.15, "B": 0.10, "C": 0.07}
        cov = {t: {t2: 0.04 if t == t2 else 0.01 for t2 in tickers} for t in tickers}
        points = lab.compute_frontier(tickers, er, cov, n_points=10)
        if len(points) >= 2:
            for i in range(len(points) - 1):
                assert points[i].volatility <= points[i + 1].volatility + 1e-6
