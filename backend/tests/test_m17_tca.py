"""Tests for M17 Transaction Cost Analysis Engine."""
import pytest
from services.tca import (
    TCAEngine, TCABenchmark, TradeCostBreakdown, BrokerScorecard, TCAReport,
)


def _eng():
    return TCAEngine()


def _record(engine, trade_id="TCA001", ticker="AAPL", side="BUY", qty=1000,
            arrival=175.0, fill=175.35, commission=5.0, spread_bps=4.0, broker_id="GS"):
    engine.record_trade(
        trade_id=trade_id,
        ticker=ticker,
        side=side,
        quantity=qty,
        arrival_price=arrival,
        avg_fill_price=fill,
        commission_usd=commission,
        spread_bps=spread_bps,
        broker_id=broker_id,
    )


def _analyse(engine, trade_id="ANA001", ticker="AAPL", side="BUY", qty=1000,
             decision=175.0, arrival=175.0, fill=175.35, commission=5.0,
             spread_bps=4.0, benchmark=175.0):
    return engine.analyse_trade(
        trade_id=trade_id,
        ticker=ticker,
        side=side,
        quantity=qty,
        decision_price=decision,
        arrival_price=arrival,
        avg_fill_price=fill,
        commission_usd=commission,
        spread_bps=spread_bps,
        benchmark_price=benchmark,
    )


# ---------------------------------------------------------------------------
# record_trade
# ---------------------------------------------------------------------------

class TestRecordTrade:
    def test_record_trade_stored(self):
        e = _eng()
        _record(e)
        records = e.get_records()
        assert len(records) == 1

    def test_record_multiple_trades(self):
        e = _eng()
        for i in range(5):
            _record(e, trade_id=f"T{i}")
        assert len(e.get_records()) == 5

    def test_record_trade_stores_correct_ticker(self):
        e = _eng()
        _record(e, ticker="NVDA")
        assert e.get_records()[0].ticker == "NVDA"

    def test_record_trade_stores_side(self):
        e = _eng()
        _record(e, side="SELL")
        assert e.get_records()[0].side == "SELL"


# ---------------------------------------------------------------------------
# analyse_trade
# ---------------------------------------------------------------------------

class TestAnalyseTrade:
    def test_analyse_returns_cost_breakdown(self):
        e = _eng()
        r = _analyse(e)
        assert isinstance(r, TradeCostBreakdown)

    def test_spread_cost_positive(self):
        e = _eng()
        r = _analyse(e)
        assert r.spread_cost_bps > 0

    def test_slippage_bps_positive_for_high_fill(self):
        e = _eng()
        r = _analyse(e, fill=176.0)
        assert r.slippage_bps > 0

    def test_commission_bps_positive(self):
        e = _eng()
        r = _analyse(e, commission=10.0)
        assert r.commission_bps > 0

    def test_is_vs_benchmark_positive_for_unfavourable(self):
        e = _eng()
        r = _analyse(e, fill=175.50)
        assert r.is_vs_benchmark_bps > 0

    def test_delay_cost_in_result(self):
        e = _eng()
        r = _analyse(e)
        assert hasattr(r, "delay_cost_bps")

    def test_opportunity_cost_in_result(self):
        e = _eng()
        r = _analyse(e)
        assert hasattr(r, "opportunity_cost_bps")

    def test_spread_cost_increases_with_wider_spread(self):
        e = _eng()
        r_tight = _analyse(e, spread_bps=2.0)
        r_wide = _analyse(e, spread_bps=10.0)
        assert r_wide.spread_cost_bps > r_tight.spread_cost_bps


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_report_returns_tca_report(self):
        e = _eng()
        _record(e)
        r = e.generate_report()
        assert isinstance(r, TCAReport)

    def test_report_total_trades(self):
        e = _eng()
        _record(e, trade_id="T1")
        _record(e, trade_id="T2")
        r = e.generate_report()
        assert r.trade_count == 2

    def test_report_avg_is_bps_nonneg(self):
        e = _eng()
        _record(e)
        r = e.generate_report()
        assert r.avg_total_cost_bps >= 0

    def test_report_avg_commission_bps_positive(self):
        e = _eng()
        _record(e, commission=5.0)
        r = e.generate_report()
        assert r.avg_commission_bps > 0

    def test_report_empty_engine_raises(self):
        e = _eng()
        with pytest.raises(ValueError):
            e.generate_report()

    def test_report_avg_spread_cost_positive(self):
        e = _eng()
        _record(e, spread_bps=4.0)
        r = e.generate_report()
        assert r.avg_spread_cost_bps > 0


# ---------------------------------------------------------------------------
# broker scorecards
# ---------------------------------------------------------------------------

class TestBrokerScorecards:
    def test_scorecards_in_report(self):
        e = _eng()
        _record(e, broker_id="GS", trade_id="T1")
        _record(e, broker_id="JPM", trade_id="T2")
        r = e.generate_report()
        assert len(r.broker_scorecards) == 2

    def test_scorecard_quality_score_range(self):
        e = _eng()
        _record(e)
        r = e.generate_report()
        for sc in r.broker_scorecards:
            assert 0 <= sc.quality_score <= 100

    def test_scorecard_fill_rate_between_0_1(self):
        e = _eng()
        _record(e)
        r = e.generate_report()
        for sc in r.broker_scorecards:
            assert 0.0 <= sc.fill_rate <= 1.0

    def test_scorecard_returns_broker_scorecard(self):
        e = _eng()
        _record(e)
        r = e.generate_report()
        for sc in r.broker_scorecards:
            assert isinstance(sc, BrokerScorecard)

    def test_multiple_trades_same_broker_aggregated(self):
        e = _eng()
        _record(e, trade_id="T1", broker_id="GS")
        _record(e, trade_id="T2", broker_id="GS")
        r = e.generate_report()
        gs = next((sc for sc in r.broker_scorecards if sc.broker_id == "GS"), None)
        assert gs is not None
        assert gs.trade_count == 2


# ---------------------------------------------------------------------------
# spread_cost / slippage_vs_arrival helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_spread_cost_wider_spread_higher_usd(self):
        e = _eng()
        tight = e.spread_cost(1000, 175.0, 2.0)
        wide = e.spread_cost(1000, 175.0, 10.0)
        assert wide > tight

    def test_spread_cost_formula(self):
        e = _eng()
        cost = e.spread_cost(1000, 100.0, 4.0)
        expected = 0.5 * (4.0 / 10000.0) * 100.0 * 1000
        assert cost == pytest.approx(expected, rel=1e-5)

    def test_slippage_vs_arrival_buy_adverse(self):
        e = _eng()
        bps, usd = e.slippage_vs_arrival(175.35, 175.0, 1000, is_buy=True)
        assert bps > 0
        assert usd > 0

    def test_slippage_vs_arrival_sell_adverse(self):
        e = _eng()
        bps, usd = e.slippage_vs_arrival(174.65, 175.0, 1000, is_buy=False)
        assert bps > 0

    def test_slippage_vs_arrival_no_slippage(self):
        e = _eng()
        bps, usd = e.slippage_vs_arrival(175.0, 175.0, 1000, is_buy=True)
        assert bps == pytest.approx(0.0)
