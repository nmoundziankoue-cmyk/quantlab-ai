"""Tests for M17 Position Engine (FIFO/LIFO/AVERAGE_COST/SPECIFIC_LOT)."""
import pytest
from services.position_engine import (
    PositionEngine, CostBasisMethod, PositionSide,
    Position, Lot, ClosedLot, ExposureReport,
)


def _fifo():
    return PositionEngine(CostBasisMethod.FIFO)


def _lifo():
    return PositionEngine(CostBasisMethod.LIFO)


def _avg():
    return PositionEngine(CostBasisMethod.AVERAGE_COST)


# ---------------------------------------------------------------------------
# open_position
# ---------------------------------------------------------------------------

class TestOpenPosition:
    def test_open_creates_position(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        p = e.get_position("AAPL", 175.0)
        assert p is not None
        assert p.quantity == 100

    def test_open_side_is_long(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        assert e.get_position("AAPL", 175.0).side == PositionSide.LONG

    def test_open_multiple_buys_accumulates(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        e.open_position("AAPL", 50, 180.0)
        assert e.get_position("AAPL", 175.0).quantity == 150

    def test_open_returns_lot(self):
        e = _fifo()
        lot = e.open_position("AAPL", 100, 175.0)
        assert isinstance(lot, Lot)

    def test_open_lot_cost_per_share(self):
        e = _fifo()
        lot = e.open_position("AAPL", 100, 175.0)
        assert lot.cost_per_share == pytest.approx(175.0)

    def test_open_zero_quantity_raises(self):
        e = _fifo()
        with pytest.raises(ValueError):
            e.open_position("AAPL", 0, 175.0)

    def test_open_negative_quantity_raises(self):
        e = _fifo()
        with pytest.raises(ValueError):
            e.open_position("AAPL", -100, 175.0)

    def test_open_ticker_uppercase(self):
        e = _fifo()
        e.open_position("aapl", 100, 175.0)
        p = e.get_position("AAPL", 175.0)
        assert p.quantity == 100

    def test_open_lot_quantity(self):
        e = _fifo()
        lot = e.open_position("AAPL", 100, 175.0)
        assert lot.quantity == 100


# ---------------------------------------------------------------------------
# close_position — FIFO
# ---------------------------------------------------------------------------

class TestCloseFIFO:
    def test_close_returns_tuple(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        result = e.close_position("AAPL", 100, 180.0)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_close_full_position_realised_pnl(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        closed_lots, total_pnl = e.close_position("AAPL", 100, 180.0)
        assert total_pnl == pytest.approx(500.0, rel=1e-5)

    def test_close_full_position_one_closed_lot(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        closed_lots, _ = e.close_position("AAPL", 100, 180.0)
        assert len(closed_lots) == 1

    def test_close_partial_position(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        e.close_position("AAPL", 50, 180.0)
        assert e.get_position("AAPL", 175.0).quantity == 50

    def test_fifo_closes_oldest_lot_first(self):
        e = _fifo()
        e.open_position("AAPL", 100, 170.0)
        e.open_position("AAPL", 100, 180.0)
        closed_lots, _ = e.close_position("AAPL", 100, 175.0)
        assert closed_lots[0].cost_per_share == pytest.approx(170.0)

    def test_close_more_than_held_raises(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        with pytest.raises(ValueError):
            e.close_position("AAPL", 200, 180.0)

    def test_close_nonexistent_position_raises(self):
        e = _fifo()
        with pytest.raises((ValueError, KeyError)):
            e.close_position("ZZZZ", 100, 100.0)

    def test_closed_lots_recorded(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        e.close_position("AAPL", 100, 180.0)
        closed = e.get_closed_lots()
        assert len(closed) >= 1

    def test_closed_lot_pnl_correct(self):
        e = _fifo()
        e.open_position("AAPL", 100, 170.0)
        closed_lots, _ = e.close_position("AAPL", 100, 180.0)
        assert closed_lots[0].realised_pnl == pytest.approx(1000.0, rel=1e-5)

    def test_position_flat_after_full_close(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        e.close_position("AAPL", 100, 180.0)
        p = e.get_position("AAPL", 180.0)
        assert p.side == PositionSide.FLAT


# ---------------------------------------------------------------------------
# LIFO cost basis
# ---------------------------------------------------------------------------

class TestCloseLIFO:
    def test_lifo_closes_newest_lot_first(self):
        e = _lifo()
        e.open_position("AAPL", 100, 170.0)
        e.open_position("AAPL", 100, 180.0)
        closed_lots, _ = e.close_position("AAPL", 100, 175.0)
        assert closed_lots[0].cost_per_share == pytest.approx(180.0)

    def test_lifo_realised_pnl(self):
        e = _lifo()
        e.open_position("AAPL", 100, 180.0)
        e.open_position("AAPL", 100, 170.0)
        closed_lots, total_pnl = e.close_position("AAPL", 100, 175.0)
        assert total_pnl == pytest.approx(500.0, rel=1e-5)


# ---------------------------------------------------------------------------
# Average cost basis
# ---------------------------------------------------------------------------

class TestAverageCost:
    def test_avg_cost_computed(self):
        e = _avg()
        e.open_position("AAPL", 100, 170.0)
        e.open_position("AAPL", 100, 190.0)
        p = e.get_position("AAPL", 180.0)
        assert p.avg_cost == pytest.approx(180.0, rel=1e-5)

    def test_avg_cost_realised_pnl(self):
        e = _avg()
        e.open_position("AAPL", 100, 170.0)
        e.open_position("AAPL", 100, 190.0)
        _, total_pnl = e.close_position("AAPL", 100, 180.0)
        assert isinstance(total_pnl, float)


# ---------------------------------------------------------------------------
# get_position / unrealised P&L
# ---------------------------------------------------------------------------

class TestGetPosition:
    def test_get_position_returns_position(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        p = e.get_position("AAPL", 175.0)
        assert isinstance(p, Position)

    def test_unrealised_pnl_positive_when_price_up(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        p = e.get_position("AAPL", 185.0)
        assert p.unrealised_pnl == pytest.approx(1000.0, rel=1e-5)

    def test_unrealised_pnl_negative_when_price_down(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        p = e.get_position("AAPL", 165.0)
        assert p.unrealised_pnl == pytest.approx(-1000.0, rel=1e-5)

    def test_market_value_correct(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        p = e.get_position("AAPL", 180.0)
        assert p.market_value == pytest.approx(18000.0, rel=1e-5)

    def test_flat_position_for_unknown_ticker(self):
        e = _fifo()
        p = e.get_position("ZZZZ", 100.0)
        assert p.side == PositionSide.FLAT

    def test_avg_cost_single_lot(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        p = e.get_position("AAPL", 175.0)
        assert p.avg_cost == pytest.approx(175.0)

    def test_holding_days_ge_zero(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        p = e.get_position("AAPL", 175.0)
        assert p.holding_days >= 0


# ---------------------------------------------------------------------------
# all_positions
# ---------------------------------------------------------------------------

class TestAllPositions:
    def test_all_positions_empty(self):
        e = _fifo()
        assert e.all_positions({}) == []

    def test_all_positions_single(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        positions = e.all_positions({"AAPL": 175.0})
        assert len(positions) == 1

    def test_all_positions_multiple(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        e.open_position("MSFT", 50, 420.0)
        positions = e.all_positions({"AAPL": 175.0, "MSFT": 420.0})
        assert len(positions) == 2

    def test_all_positions_excludes_flat(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        e.close_position("AAPL", 100, 180.0)
        positions = e.all_positions({"AAPL": 180.0})
        assert len(positions) == 0


# ---------------------------------------------------------------------------
# realised_pnl
# ---------------------------------------------------------------------------

class TestRealisedPnL:
    def test_realised_pnl_zero_before_close(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        assert e.realised_pnl() == pytest.approx(0.0)

    def test_realised_pnl_after_close(self):
        e = _fifo()
        e.open_position("AAPL", 100, 170.0)
        e.close_position("AAPL", 100, 180.0)
        assert e.realised_pnl() == pytest.approx(1000.0, rel=1e-5)

    def test_realised_pnl_per_ticker(self):
        e = _fifo()
        e.open_position("AAPL", 100, 170.0)
        e.close_position("AAPL", 100, 180.0)
        e.open_position("MSFT", 50, 400.0)
        e.close_position("MSFT", 50, 420.0)
        assert e.realised_pnl("AAPL") == pytest.approx(1000.0, rel=1e-5)
        assert e.realised_pnl("MSFT") == pytest.approx(1000.0, rel=1e-5)
        assert e.realised_pnl() == pytest.approx(2000.0, rel=1e-5)


# ---------------------------------------------------------------------------
# exposure_report
# ---------------------------------------------------------------------------

class TestExposureReport:
    def test_exposure_report_returns_report(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        report = e.exposure_report({"AAPL": 175.0}, nav=100000.0)
        assert isinstance(report, ExposureReport)

    def test_gross_exposure_positive(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        report = e.exposure_report({"AAPL": 175.0}, nav=100000.0)
        assert report.gross_exposure > 0

    def test_net_exposure_positive_for_long(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        report = e.exposure_report({"AAPL": 175.0}, nav=100000.0)
        assert report.net_exposure > 0

    def test_gross_leverage(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        report = e.exposure_report({"AAPL": 175.0}, nav=100000.0)
        assert report.leverage == pytest.approx(17500.0 / 100000.0, rel=1e-5)


# ---------------------------------------------------------------------------
# aged_positions / snapshot
# ---------------------------------------------------------------------------

class TestAgedPositions:
    def test_aged_positions_after_open(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        aged = e.aged_positions({"AAPL": 175.0}, min_holding_days=0)
        assert len(aged) == 1

    def test_aged_positions_min_days_filter(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        aged = e.aged_positions({"AAPL": 175.0}, min_holding_days=365)
        assert len(aged) == 0

    def test_snapshot_returns_dict(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        snap = e.snapshot({"AAPL": 180.0})
        assert isinstance(snap, dict)
        assert "positions" in snap

    def test_open_lots_returned(self):
        e = _fifo()
        e.open_position("AAPL", 100, 175.0)
        e.open_position("AAPL", 100, 180.0)
        lots = e.get_open_lots("AAPL")
        assert len(lots) == 2
