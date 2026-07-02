"""Tests for M19 Pydantic v2 schemas."""

import pytest
from pydantic import ValidationError
from schemas.m19_research import (
    PriceBarSchema,
    SignalSchema,
    BacktestRunRequest,
    BacktestCompareRequest,
    BacktestMetricsResponse,
    BacktestSummaryResponse,
    TradeResponse,
    EquityPointResponse,
    BacktestResultResponse,
    MonthlyReturnsResponse,
    SimOrderSchema,
    ExecutionSimulateRequest,
    ExecutionBatchRequest,
    FillModelRequest,
    ImplementationShortfallRequest,
    FillResponse,
    SlippageReportResponse,
    SimpleSignalConfig,
    WalkForwardRunRequest,
    WFWindowResponse,
    StabilityMetricsResponse,
    WalkForwardSummaryResponse,
    MCBootstrapRequest,
    MCGBMRequest,
    MCSensitivityRequest,
    ConfidenceIntervalResponse,
    MCResultResponse,
    MCPathResponse,
    FactorReturnSchema,
    AddFactorReturnsRequest,
    RegressRequest,
    AttributionRequest,
    PortfolioBetaRequest,
    FactorCorrelationRequest,
    FactorExposureResponse,
    FactorAttributionResponse,
    FactorCorrelationResponse,
    WeightConstraintSchema,
    MeanVarianceRequest,
    MinVarianceRequest,
    MaxSharpeRequest,
    RiskParityRequest,
    FrontierRequest,
    FactorConstrainedRequest,
    OptimizationResultResponse,
    FrontierPointResponse,
    FrontierResponse,
)


class TestPriceBarSchema:
    def test_valid(self):
        b = PriceBarSchema(date="2024-01-01", open=100.0, high=105.0, low=98.0, close=102.0)
        assert b.date == "2024-01-01"

    def test_negative_open_fails(self):
        with pytest.raises(ValidationError):
            PriceBarSchema(date="2024-01-01", open=-1.0, high=105.0, low=98.0, close=102.0)

    def test_default_volume(self):
        b = PriceBarSchema(date="2024-01-01", open=100.0, high=105.0, low=98.0, close=102.0)
        assert b.volume == 0.0


class TestSignalSchema:
    def test_valid(self):
        s = SignalSchema(date="2024-01-01", ticker="AAPL", signal_type="LONG")
        assert s.signal_type == "LONG"

    def test_strength_defaults_to_one(self):
        s = SignalSchema(date="2024-01-01", ticker="AAPL", signal_type="FLAT")
        assert s.strength == 1.0

    def test_strength_above_one_fails(self):
        with pytest.raises(ValidationError):
            SignalSchema(date="2024-01-01", ticker="AAPL", signal_type="LONG", strength=1.5)


class TestBacktestRunRequest:
    def _bar(self):
        return PriceBarSchema(date="2024-01-01", open=100, high=105, low=98, close=102)

    def _signal(self):
        return SignalSchema(date="2024-01-01", ticker="AAPL", signal_type="LONG")

    def test_valid(self):
        req = BacktestRunRequest(
            strategy_name="s",
            signals=[self._signal()],
            price_data={"AAPL": [self._bar()]},
        )
        assert req.strategy_name == "s"

    def test_empty_strategy_name_fails(self):
        with pytest.raises(ValidationError):
            BacktestRunRequest(
                strategy_name="",
                signals=[self._signal()],
                price_data={"AAPL": [self._bar()]},
            )

    def test_default_initial_capital(self):
        req = BacktestRunRequest(
            strategy_name="s",
            signals=[self._signal()],
            price_data={"AAPL": [self._bar()]},
        )
        assert req.initial_capital == 100_000.0

    def test_negative_capital_fails(self):
        with pytest.raises(ValidationError):
            BacktestRunRequest(
                strategy_name="s",
                signals=[self._signal()],
                price_data={"AAPL": [self._bar()]},
                initial_capital=-1000.0,
            )


class TestBacktestCompareRequest:
    def test_valid(self):
        req = BacktestCompareRequest(backtest_ids=["id1", "id2"])
        assert len(req.backtest_ids) == 2

    def test_single_id_fails(self):
        with pytest.raises(ValidationError):
            BacktestCompareRequest(backtest_ids=["id1"])


class TestSimOrderSchema:
    def test_valid_market_buy(self):
        o = SimOrderSchema(ticker="AAPL", side="BUY", quantity=100.0)
        assert o.order_type == "MARKET"

    def test_zero_quantity_fails(self):
        with pytest.raises(ValidationError):
            SimOrderSchema(ticker="AAPL", side="BUY", quantity=0.0)

    def test_limit_order_needs_limit_price(self):
        o = SimOrderSchema(ticker="AAPL", side="BUY", quantity=100.0, order_type="LIMIT", limit_price=95.0)
        assert o.limit_price == 95.0


class TestExecutionSimulateRequest:
    def test_valid(self):
        order = SimOrderSchema(ticker="AAPL", side="BUY", quantity=100.0)
        req = ExecutionSimulateRequest(order=order, market_price=100.0)
        assert req.market_price == 100.0

    def test_negative_market_price_fails(self):
        order = SimOrderSchema(ticker="AAPL", side="BUY", quantity=100.0)
        with pytest.raises(ValidationError):
            ExecutionSimulateRequest(order=order, market_price=-1.0)


class TestFillModelRequest:
    def test_valid(self):
        req = FillModelRequest(model_name="test")
        assert req.model_name == "test"

    def test_fill_probability_above_one_fails(self):
        with pytest.raises(ValidationError):
            FillModelRequest(model_name="m", fill_probability=1.5)

    def test_default_fill_probability(self):
        req = FillModelRequest(model_name="m")
        assert req.fill_probability == 0.95


class TestWalkForwardRunRequest:
    def _bar(self):
        return PriceBarSchema(date="2024-01-01", open=100, high=105, low=98, close=102)

    def test_valid(self):
        req = WalkForwardRunRequest(
            strategy_name="s",
            price_data={"AAPL": [self._bar()]},
        )
        assert req.strategy_name == "s"

    def test_default_in_sample_bars(self):
        req = WalkForwardRunRequest(strategy_name="s", price_data={"AAPL": [self._bar()]})
        assert req.in_sample_bars == 252

    def test_negative_in_sample_bars_fails(self):
        with pytest.raises(ValidationError):
            WalkForwardRunRequest(strategy_name="s", price_data={"AAPL": [self._bar()]}, in_sample_bars=-1)


class TestMCBootstrapRequest:
    def test_valid(self):
        req = MCBootstrapRequest(daily_returns=[0.001] * 30, num_paths=100)
        assert req.num_paths == 100

    def test_too_few_returns_fails(self):
        with pytest.raises(ValidationError):
            MCBootstrapRequest(daily_returns=[0.001] * 5)

    def test_too_many_paths_fails(self):
        with pytest.raises(ValidationError):
            MCBootstrapRequest(daily_returns=[0.001] * 30, num_paths=100_000)


class TestMCGBMRequest:
    def test_valid(self):
        req = MCGBMRequest()
        assert req.daily_volatility == 0.01

    def test_zero_vol_fails(self):
        with pytest.raises(ValidationError):
            MCGBMRequest(daily_volatility=0.0)


class TestFactorReturnSchema:
    def test_valid(self):
        fr = FactorReturnSchema(date="2024-01-01", factor="MARKET", return_value=0.01)
        assert fr.factor == "MARKET"


class TestRegressRequest:
    def test_valid(self):
        req = RegressRequest(
            ticker="AAPL",
            security_returns={"2024-01-01": 0.01, "2024-01-02": -0.005},
        )
        assert req.ticker == "AAPL"

    def test_default_factors(self):
        req = RegressRequest(ticker="AAPL", security_returns={"2024-01-01": 0.01})
        assert "MARKET" in req.factors


class TestWeightConstraintSchema:
    def test_valid(self):
        wc = WeightConstraintSchema(ticker="AAPL", min_weight=0.1, max_weight=0.4)
        assert wc.ticker == "AAPL"

    def test_min_above_one_fails(self):
        with pytest.raises(ValidationError):
            WeightConstraintSchema(min_weight=1.5)

    def test_defaults(self):
        wc = WeightConstraintSchema()
        assert wc.min_weight == 0.0
        assert wc.max_weight == 1.0


class TestMeanVarianceRequest:
    def test_valid(self):
        req = MeanVarianceRequest(
            tickers=["A", "B"],
            expected_returns={"A": 0.1, "B": 0.08},
            covariance_matrix={"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.03}},
        )
        assert len(req.tickers) == 2

    def test_single_ticker_fails(self):
        with pytest.raises(ValidationError):
            MeanVarianceRequest(
                tickers=["A"],
                expected_returns={"A": 0.1},
                covariance_matrix={"A": {"A": 0.04}},
            )

    def test_negative_risk_aversion_fails(self):
        with pytest.raises(ValidationError):
            MeanVarianceRequest(
                tickers=["A", "B"],
                expected_returns={"A": 0.1, "B": 0.08},
                covariance_matrix={"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.03}},
                risk_aversion=-1.0,
            )


class TestFrontierRequest:
    def test_valid(self):
        req = FrontierRequest(
            tickers=["A", "B"],
            expected_returns={"A": 0.1, "B": 0.08},
            covariance_matrix={"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.03}},
        )
        assert req.n_points == 20

    def test_too_few_points_fails(self):
        with pytest.raises(ValidationError):
            FrontierRequest(
                tickers=["A", "B"],
                expected_returns={"A": 0.1, "B": 0.08},
                covariance_matrix={"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.03}},
                n_points=1,
            )


class TestResponseSchemas:
    def test_backtest_metrics_response(self):
        r = BacktestMetricsResponse(
            total_return=0.1, annualized_return=0.12, volatility=0.15, sharpe_ratio=0.8,
            sortino_ratio=1.0, max_drawdown=0.1, max_drawdown_duration_days=20,
            calmar_ratio=1.2, win_rate=0.6, profit_factor=1.5, avg_trade_return=0.02,
            num_trades=10, num_winning=6, num_losing=4, best_trade=0.05, worst_trade=-0.03,
            avg_holding_days=5.0,
        )
        assert r.total_return == 0.1

    def test_optimization_result_response(self):
        r = OptimizationResultResponse(
            result_id="R1", optimization_type="MEAN_VARIANCE", weights={"A": 0.5, "B": 0.5},
            expected_return=0.1, volatility=0.15, sharpe_ratio=0.8, diversification_ratio=1.1,
            max_weight=0.5, min_weight=0.5, num_assets=2, risk_contributions={"A": 0.5, "B": 0.5},
            iterations=100,
        )
        assert r.num_assets == 2

    def test_frontier_response_optional_fields(self):
        p = FrontierPointResponse(expected_return=0.1, volatility=0.15, sharpe_ratio=0.8, weights={"A": 1.0})
        r = FrontierResponse(n_points=1, points=[p], min_variance_point=None, max_sharpe_point=None)
        assert r.min_variance_point is None

    def test_mc_result_response(self):
        r = MCResultResponse(
            simulation_id="S1", num_paths=1000, num_steps=252, initial_equity=100_000,
            var_95=0.05, var_99=0.08, expected_shortfall_95=0.07, max_drawdown_p50=0.15,
            max_drawdown_p95=0.30, probability_of_ruin=0.01, probability_of_profit=0.75, method="gbm",
        )
        assert r.method == "gbm"

    def test_slippage_report_response(self):
        r = SlippageReportResponse(
            num_fills=5, total_slippage=1.5, avg_slippage_bps=3.0, max_slippage_bps=10.0,
            total_commission=0.5, total_market_impact=0.001, fill_rate=0.95
        )
        assert r.fill_rate == 0.95

    def test_stability_metrics_response(self):
        r = StabilityMetricsResponse(
            num_windows=4, avg_oos_sharpe=0.8, std_oos_sharpe=0.2, avg_efficiency=0.7,
            pct_windows_positive=0.75, stability_score=0.65, avg_oos_return=0.05, degradation=0.02
        )
        assert r.stability_score == 0.65
