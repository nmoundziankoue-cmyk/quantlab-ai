"""Tests for M20 Pydantic v2 schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.m20_research import (
    AddReturnsBatchRequest,
    AddReturnsRequest,
    BestByMetricRequest,
    ClusterRequest,
    CompareRequest,
    CovarianceMatrixRequest,
    CorrelationMatrixRequest,
    HeadToHeadRequest,
    LeastCorrelatedRequest,
    MostCorrelatedRequest,
    OHLCVBar,
    PairwiseCorrelationRequest,
    RankByMetricRequest,
    RegimeCompareRequest,
    RegimeDetectFromReturnsRequest,
    RegimeDetectRequest,
    RegisterResultRequest,
    ReturnSeriesEntry,
    RollingCorrelationRequest,
    RunAndRegisterRequest,
)


class TestOHLCVBar:
    def test_valid_bar(self):
        bar = OHLCVBar(date="2023-01-01", open=100.0, high=105.0, low=99.0, close=102.0)
        assert bar.close == 102.0

    def test_default_volume(self):
        bar = OHLCVBar(date="2023-01-01", open=100.0, high=105.0, low=99.0, close=102.0)
        assert bar.volume == 0.0

    def test_high_lt_low_raises(self):
        with pytest.raises(ValidationError):
            OHLCVBar(date="2023-01-01", open=100.0, high=90.0, low=99.0, close=95.0)

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            OHLCVBar(date="2023-01-01", open=-1.0, high=105.0, low=99.0, close=102.0)

    def test_zero_close_raises(self):
        with pytest.raises(ValidationError):
            OHLCVBar(date="2023-01-01", open=100.0, high=105.0, low=99.0, close=0.0)


class TestRegimeDetectRequest:
    def _bar(self):
        return {"date": "2023-01-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0}

    def test_valid(self):
        req = RegimeDetectRequest(ticker="AAPL", bars=[self._bar(), self._bar()])
        assert req.ticker == "AAPL"
        assert req.fast_window == 50
        assert req.slow_window == 200

    def test_empty_ticker_raises(self):
        with pytest.raises(ValidationError):
            RegimeDetectRequest(ticker="", bars=[self._bar(), self._bar()])

    def test_single_bar_raises(self):
        with pytest.raises(ValidationError):
            RegimeDetectRequest(ticker="AAPL", bars=[self._bar()])

    def test_defaults(self):
        req = RegimeDetectRequest(ticker="AAPL", bars=[self._bar(), self._bar()])
        assert req.vol_high_threshold == 1.5
        assert req.vol_low_threshold == 0.5
        assert req.momentum_threshold == 0.02

    def test_vol_high_must_gt_one(self):
        with pytest.raises(ValidationError):
            RegimeDetectRequest(
                ticker="AAPL", bars=[self._bar(), self._bar()], vol_high_threshold=0.9
            )


class TestRegimeDetectFromReturnsRequest:
    def test_valid(self):
        req = RegimeDetectFromReturnsRequest(ticker="SYN", daily_returns=[0.01, 0.02, -0.01])
        assert req.start_price == 100.0

    def test_single_return_raises(self):
        with pytest.raises(ValidationError):
            RegimeDetectFromReturnsRequest(ticker="SYN", daily_returns=[0.01])

    def test_negative_start_price_raises(self):
        with pytest.raises(ValidationError):
            RegimeDetectFromReturnsRequest(ticker="SYN", daily_returns=[0.01, 0.02], start_price=-10.0)


class TestAddReturnsRequest:
    def test_valid(self):
        req = AddReturnsRequest(ticker="AAPL", returns={"2023-01-01": 0.01, "2023-01-02": -0.01})
        assert req.ticker == "AAPL"

    def test_empty_ticker_raises(self):
        with pytest.raises(ValidationError):
            AddReturnsRequest(ticker="", returns={"2023-01-01": 0.01})


class TestReturnSeriesEntry:
    def test_valid(self):
        entry = ReturnSeriesEntry(ticker="A", returns={"2023-01-01": 0.01, "2023-01-02": 0.02})
        assert entry.ticker == "A"

    def test_single_obs_raises(self):
        with pytest.raises(ValidationError):
            ReturnSeriesEntry(ticker="A", returns={"2023-01-01": 0.01})


class TestAddReturnsBatchRequest:
    def test_valid(self):
        req = AddReturnsBatchRequest(entries=[
            {"ticker": "A", "returns": {"2023-01-01": 0.01, "2023-01-02": 0.02}},
            {"ticker": "B", "returns": {"2023-01-01": 0.03, "2023-01-02": -0.01}},
        ])
        assert len(req.entries) == 2

    def test_empty_entries_raises(self):
        with pytest.raises(ValidationError):
            AddReturnsBatchRequest(entries=[])


class TestCorrelationMatrixRequest:
    def test_valid(self):
        req = CorrelationMatrixRequest(tickers=["A", "B"])
        assert req.tickers == ["A", "B"]

    def test_single_ticker_raises(self):
        with pytest.raises(ValidationError):
            CorrelationMatrixRequest(tickers=["A"])


class TestCovarianceMatrixRequest:
    def test_valid(self):
        req = CovarianceMatrixRequest(tickers=["A", "B"])
        assert req.annualize is True

    def test_no_annualize(self):
        req = CovarianceMatrixRequest(tickers=["A", "B"], annualize=False)
        assert req.annualize is False


class TestRollingCorrelationRequest:
    def test_valid(self):
        req = RollingCorrelationRequest(ticker_a="A", ticker_b="B", window=60)
        assert req.window == 60

    def test_window_below_minimum_raises(self):
        with pytest.raises(ValidationError):
            RollingCorrelationRequest(ticker_a="A", ticker_b="B", window=2)


class TestClusterRequest:
    def test_valid(self):
        req = ClusterRequest(tickers=["A", "B", "C"], threshold=0.70)
        assert req.threshold == 0.70

    def test_threshold_above_one_raises(self):
        with pytest.raises(ValidationError):
            ClusterRequest(tickers=["A", "B"], threshold=1.5)

    def test_single_ticker_raises(self):
        with pytest.raises(ValidationError):
            ClusterRequest(tickers=["A"])


class TestCompareRequest:
    def test_valid(self):
        req = CompareRequest(strategy_ids=["id1", "id2"])
        assert req.primary_metric == "sharpe_ratio"
        assert req.include_correlation is True

    def test_single_id_raises(self):
        with pytest.raises(ValidationError):
            CompareRequest(strategy_ids=["id1"])


class TestBestByMetricRequest:
    def test_valid(self):
        req = BestByMetricRequest(strategy_ids=["id1"])
        assert req.metric == "sharpe_ratio"


class TestRankByMetricRequest:
    def test_valid(self):
        req = RankByMetricRequest(strategy_ids=["id1", "id2"], metric="calmar_ratio")
        assert req.metric == "calmar_ratio"


class TestHeadToHeadRequest:
    def test_valid(self):
        req = HeadToHeadRequest(strategy_id_a="a", strategy_id_b="b")
        assert req.strategy_id_a == "a"


class TestRegimeCompareRequest:
    def test_valid(self):
        req = RegimeCompareRequest(tickers=["AAPL", "MSFT"])
        assert req.tickers == ["AAPL", "MSFT"]

    def test_empty_tickers_raises(self):
        with pytest.raises(ValidationError):
            RegimeCompareRequest(tickers=[])


class TestRegisterResultRequest:
    def test_valid(self):
        req = RegisterResultRequest(strategy_name="Alpha", backtest_id="some-uuid")
        assert req.backtest_id == "some-uuid"


class TestRunAndRegisterRequest:
    def test_valid(self):
        req = RunAndRegisterRequest(
            strategy_name="Trend",
            ticker="AAPL",
            price_data={"AAPL": [{"date": "2023-01-01", "close": 100.0}]},
            signals={"2023-01-01": "LONG"},
        )
        assert req.initial_capital == 100_000.0
        assert req.commission_rate == 0.001

    def test_empty_ticker_raises(self):
        with pytest.raises(ValidationError):
            RunAndRegisterRequest(
                strategy_name="T",
                ticker="",
                price_data={},
                signals={},
            )
