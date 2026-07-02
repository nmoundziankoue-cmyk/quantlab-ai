"""Tests for M17 Paper Trading Simulator."""
import pytest
from services.paper_trading_sim import (
    PaperTradingSimulator, SimulatorConfig, SimFillModel, SimFillResult, SimAccount,
)
from services.order_management import OrderSide, OrderStatus


def _sim(cash=500_000.0):
    cfg = SimulatorConfig(initial_cash=cash, commission_per_share=0.005, spread_bps=2.0, slippage_bps=2.0)
    return PaperTradingSimulator(cfg)


# ---------------------------------------------------------------------------
# initial state
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_initial_cash(self):
        s = _sim(500_000)
        acct = s.account_state()
        assert acct.cash == pytest.approx(500_000.0)

    def test_initial_no_positions(self):
        s = _sim()
        assert len(s.open_positions()) == 0

    def test_initial_no_fills(self):
        s = _sim()
        assert len(s.get_fills()) == 0

    def test_initial_trade_count_zero(self):
        s = _sim()
        acct = s.account_state()
        assert acct.trade_count == 0


# ---------------------------------------------------------------------------
# submit_market_order — BUY fills
# ---------------------------------------------------------------------------

class TestMarketOrderBuy:
    def test_market_buy_fills_immediately(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        r = s.submit_market_order("AAPL", OrderSide.BUY, 100)
        assert r.is_filled
        assert r.filled_qty == 100

    def test_market_buy_fill_price_above_market(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        r = s.submit_market_order("AAPL", OrderSide.BUY, 100)
        assert r.fill_price > 175.0

    def test_market_buy_reduces_cash(self):
        s = _sim(500_000)
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        acct = s.account_state()
        assert acct.cash < 500_000.0

    def test_market_buy_creates_position(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        positions = s.open_positions()
        assert any(p["ticker"] == "AAPL" for p in positions)

    def test_market_buy_no_price_raises(self):
        s = _sim()
        with pytest.raises(ValueError):
            s.submit_market_order("AAPL", OrderSide.BUY, 100)

    def test_market_buy_commission_charged(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        r = s.submit_market_order("AAPL", OrderSide.BUY, 100)
        assert r.commission > 0

    def test_market_buy_recorded_in_fills(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        assert len(s.get_fills()) == 1

    def test_market_buy_returns_sim_fill_result(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        r = s.submit_market_order("AAPL", OrderSide.BUY, 100)
        assert isinstance(r, SimFillResult)


# ---------------------------------------------------------------------------
# submit_market_order — SELL
# ---------------------------------------------------------------------------

class TestMarketOrderSell:
    def test_market_sell_after_buy(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.update_prices({"AAPL": 180.0})
        r = s.submit_market_order("AAPL", OrderSide.SELL, 100)
        assert r.is_filled

    def test_market_sell_increases_cash(self):
        s = _sim(500_000)
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        cash_after_buy = s.account_state().cash
        s.update_prices({"AAPL": 180.0})
        s.submit_market_order("AAPL", OrderSide.SELL, 100)
        cash_after_sell = s.account_state().cash
        assert cash_after_sell > cash_after_buy

    def test_market_sell_removes_position(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.update_prices({"AAPL": 180.0})
        s.submit_market_order("AAPL", OrderSide.SELL, 100)
        positions = s.open_positions()
        assert not any(p["ticker"] == "AAPL" for p in positions)


# ---------------------------------------------------------------------------
# submit_limit_order
# ---------------------------------------------------------------------------

class TestLimitOrder:
    def test_limit_buy_fills_when_market_at_limit(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        r = s.submit_limit_order("AAPL", OrderSide.BUY, 100, 176.0)
        assert r.status == OrderStatus.FILLED

    def test_limit_buy_no_fill_when_price_above_limit(self):
        s = _sim()
        s.update_prices({"AAPL": 180.0})
        r = s.submit_limit_order("AAPL", OrderSide.BUY, 100, 175.0)
        assert r.status != OrderStatus.FILLED

    def test_limit_sell_fills_when_market_at_limit(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.update_prices({"AAPL": 180.0})
        r = s.submit_limit_order("AAPL", OrderSide.SELL, 100, 178.0)
        assert r.status == OrderStatus.FILLED

    def test_limit_sell_no_fill_when_market_below_limit(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        r = s.submit_limit_order("AAPL", OrderSide.SELL, 100, 185.0)
        assert r.status != OrderStatus.FILLED


# ---------------------------------------------------------------------------
# account_state
# ---------------------------------------------------------------------------

class TestAccountState:
    def test_equity_includes_position_value(self):
        s = _sim(500_000)
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.update_prices({"AAPL": 180.0})
        acct = s.account_state()
        assert acct.equity > acct.cash

    def test_unrealised_pnl_long_above_cost(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.update_prices({"AAPL": 185.0})
        acct = s.account_state()
        assert acct.unrealised_pnl > 0

    def test_account_returns_sim_account(self):
        s = _sim()
        acct = s.account_state()
        assert isinstance(acct, SimAccount)

    def test_trade_count_increments(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        acct = s.account_state()
        assert acct.trade_count == 1


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_positions(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.reset()
        assert len(s.open_positions()) == 0

    def test_reset_restores_initial_cash(self):
        s = _sim(500_000)
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.reset()
        acct = s.account_state()
        assert acct.cash == pytest.approx(500_000.0)

    def test_reset_clears_fills(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.reset()
        assert len(s.get_fills()) == 0


# ---------------------------------------------------------------------------
# closed trades
# ---------------------------------------------------------------------------

class TestClosedTrades:
    def test_closed_trade_after_buy_sell(self):
        s = _sim()
        s.update_prices({"AAPL": 175.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.update_prices({"AAPL": 180.0})
        s.submit_market_order("AAPL", OrderSide.SELL, 100)
        trades = s.get_closed_trades()
        assert len(trades) >= 1

    def test_closed_trade_pnl_positive(self):
        s = _sim()
        s.update_prices({"AAPL": 170.0})
        s.submit_market_order("AAPL", OrderSide.BUY, 100)
        s.update_prices({"AAPL": 200.0})
        s.submit_market_order("AAPL", OrderSide.SELL, 100)
        trades = s.get_closed_trades()
        assert any(t.pnl > 0 for t in trades)
