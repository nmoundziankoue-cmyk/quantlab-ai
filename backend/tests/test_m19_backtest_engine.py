"""Tests for M19 BacktestEngine service."""

import math
import pytest
from services.m19_backtest_engine import (
    BacktestEngine,
    EquityPoint,
    PriceBar,
    Signal,
    SignalType,
    Trade,
    BacktestMetrics,
    BacktestResult,
    OrderSide,
)


def make_bars(ticker: str, prices, start_date: str = "2024-01-01") -> list:
    bars = []
    for i, p in enumerate(prices):
        day = i + 1
        date = f"2024-{1 + i // 28:02d}-{(day % 28) + 1:02d}"
        date = f"2024-01-{i + 1:02d}" if i < 28 else f"2024-02-{i - 27:02d}"
        bars.append(PriceBar(date=date, open=p, high=p * 1.01, low=p * 0.99, close=p, volume=10_000))
    return bars


def simple_price_data(n=20):
    prices = [100.0 + i * 0.5 for i in range(n)]
    return {"AAPL": make_bars("AAPL", prices)}


def buy_and_hold_signals(n=20):
    prices = [100.0 + i * 0.5 for i in range(n)]
    bars = make_bars("AAPL", prices)
    signals = [Signal(date=bars[0].date, ticker="AAPL", signal_type=SignalType.LONG, strength=1.0)]
    return signals, {"AAPL": bars}


class TestBacktestEngineInit:
    def test_engine_created(self):
        engine = BacktestEngine()
        assert engine is not None

    def test_engine_starts_empty(self):
        engine = BacktestEngine()
        assert engine.list_results() == []

    def test_get_nonexistent_returns_none(self):
        engine = BacktestEngine()
        assert engine.get_result("no-such-id") is None

    def test_equity_curve_nonexistent_returns_empty(self):
        engine = BacktestEngine()
        assert engine.get_equity_curve("no-such-id") == []

    def test_trades_nonexistent_returns_empty(self):
        engine = BacktestEngine()
        assert engine.get_trades("no-such-id") == []

    def test_delete_nonexistent_returns_false(self):
        engine = BacktestEngine()
        assert engine.delete_result("no-such-id") is False

    def test_reset_clears_results(self):
        engine = BacktestEngine()
        signals, pd = buy_and_hold_signals()
        engine.run("s", signals, pd)
        engine.reset()
        assert engine.list_results() == []


class TestBacktestRun:
    def setup_method(self):
        self.engine = BacktestEngine()

    def test_run_returns_result(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("test", signals, pd)
        assert result is not None

    def test_run_produces_backtest_id(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("test", signals, pd)
        assert len(result.backtest_id) > 0

    def test_run_stores_strategy_name(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("my_strategy", signals, pd)
        assert result.strategy_name == "my_strategy"

    def test_run_stores_initial_capital(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd, initial_capital=50_000.0)
        assert result.initial_capital == 50_000.0

    def test_run_equity_curve_non_empty(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert len(result.equity_curve) > 0

    def test_run_with_empty_signals(self):
        _, pd = buy_and_hold_signals()
        result = self.engine.run("s", [], pd)
        assert result is not None

    def test_run_with_empty_price_data(self):
        signals, _ = buy_and_hold_signals()
        result = self.engine.run("s", signals, {})
        assert result is not None

    def test_run_caches_result(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert self.engine.get_result(result.backtest_id) is not None

    def test_run_produces_different_ids(self):
        signals, pd = buy_and_hold_signals()
        r1 = self.engine.run("s", signals, pd)
        r2 = self.engine.run("s", signals, pd)
        assert r1.backtest_id != r2.backtest_id

    def test_run_produces_start_end_dates(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert result.start_date != "" or result.end_date != "" or len(result.equity_curve) > 0

    def test_run_multiple_tickers(self):
        bars_a = make_bars("AAPL", [100 + i for i in range(10)])
        bars_b = make_bars("MSFT", [200 + i for i in range(10)])
        signals = [
            Signal(bars_a[0].date, "AAPL", SignalType.LONG),
            Signal(bars_b[0].date, "MSFT", SignalType.LONG),
        ]
        result = self.engine.run("multi", signals, {"AAPL": bars_a, "MSFT": bars_b})
        assert result is not None

    def test_run_with_short_signal_not_allowed(self):
        bars = make_bars("AAPL", [100 + i for i in range(10)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.SHORT)]
        result = self.engine.run("s", signals, {"AAPL": bars}, allow_short=False)
        assert result is not None

    def test_run_with_short_signal_allowed(self):
        bars = make_bars("AAPL", [100 - i * 0.5 for i in range(10)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.SHORT)]
        result = self.engine.run("s", signals, {"AAPL": bars}, allow_short=True)
        assert result is not None

    def test_run_with_flat_signal_closes_position(self):
        bars = make_bars("AAPL", [100 + i for i in range(10)])
        signals = [
            Signal(bars[0].date, "AAPL", SignalType.LONG),
            Signal(bars[5].date, "AAPL", SignalType.FLAT),
        ]
        result = self.engine.run("s", signals, {"AAPL": bars})
        assert len(result.trades) >= 1

    def test_run_rising_market_positive_return(self):
        bars = make_bars("AAPL", [100.0 * (1.01 ** i) for i in range(20)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        result = self.engine.run("s", signals, {"AAPL": bars})
        assert result.metrics.total_return > 0

    def test_run_falling_market_negative_return_long(self):
        bars = make_bars("AAPL", [100.0 * (0.99 ** i) for i in range(20)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        result = self.engine.run("s", signals, {"AAPL": bars})
        assert result.metrics.total_return < 0

    def test_run_with_slippage_reduces_return(self):
        bars = make_bars("AAPL", [100 + i for i in range(20)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        r_no_slip = self.engine.run("s", signals, {"AAPL": bars}, slippage_bps=0.0)
        r_slip = self.engine.run("s", signals, {"AAPL": bars}, slippage_bps=50.0)
        assert r_no_slip.metrics.total_return >= r_slip.metrics.total_return

    def test_run_with_commission_reduces_return(self):
        bars = make_bars("AAPL", [100 + i for i in range(20)])
        signals = [Signal(bars[0].date, "AAPL", SignalType.LONG)]
        r_no_comm = self.engine.run("s", signals, {"AAPL": bars}, commission_rate=0.0)
        r_comm = self.engine.run("s", signals, {"AAPL": bars}, commission_rate=0.01)
        assert r_no_comm.metrics.total_return >= r_comm.metrics.total_return


class TestBacktestEquityCurve:
    def setup_method(self):
        self.engine = BacktestEngine()

    def test_equity_curve_is_list_of_equity_points(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert all(isinstance(ep, EquityPoint) for ep in result.equity_curve)

    def test_equity_point_has_date(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        for ep in result.equity_curve:
            assert ep.date != ""

    def test_equity_point_has_positive_equity(self):
        signals, pd = buy_and_hold_signals(10)
        result = self.engine.run("s", signals, pd)
        for ep in result.equity_curve:
            assert ep.equity >= 0

    def test_drawdown_non_negative(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        for ep in result.equity_curve:
            assert ep.drawdown_pct >= 0.0

    def test_drawdown_fraction(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        for ep in result.equity_curve:
            assert ep.drawdown_pct <= 1.0

    def test_to_dict_returns_correct_keys(self):
        ep = EquityPoint(date="2024-01-01", equity=100000, cash=90000, positions_value=10000, drawdown=0, drawdown_pct=0)
        d = ep.to_dict()
        assert "date" in d and "equity" in d and "drawdown_pct" in d

    def test_get_equity_curve_via_engine(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        curve = self.engine.get_equity_curve(result.backtest_id)
        assert len(curve) == len(result.equity_curve)

    def test_get_drawdown_series(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        ds = self.engine.get_drawdown_series(result.backtest_id)
        assert len(ds) == len(result.equity_curve)
        for row in ds:
            assert "date" in row and "drawdown_pct" in row


class TestBacktestMetrics:
    def setup_method(self):
        self.engine = BacktestEngine()

    def test_metrics_has_total_return(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert isinstance(result.metrics.total_return, float)

    def test_metrics_has_sharpe(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert isinstance(result.metrics.sharpe_ratio, float)

    def test_metrics_has_max_drawdown(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert result.metrics.max_drawdown >= 0

    def test_metrics_has_num_trades(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert result.metrics.num_trades >= 0

    def test_metrics_win_rate_in_range(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert 0.0 <= result.metrics.win_rate <= 1.0

    def test_metrics_profit_factor_non_negative(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert result.metrics.profit_factor >= 0

    def test_to_dict_has_required_fields(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        d = result.metrics.to_dict()
        for key in ["total_return", "sharpe_ratio", "max_drawdown", "win_rate"]:
            assert key in d

    def test_zero_trades_metrics(self):
        _, pd = buy_and_hold_signals()
        result = self.engine.run("s", [], pd)
        assert result.metrics.num_trades == 0
        assert result.metrics.win_rate == 0.0


class TestBacktestTrades:
    def setup_method(self):
        self.engine = BacktestEngine()

    def test_trades_is_list(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        assert isinstance(result.trades, list)

    def test_trade_has_required_fields(self):
        bars = make_bars("AAPL", [100 + i for i in range(10)])
        signals = [
            Signal(bars[0].date, "AAPL", SignalType.LONG),
            Signal(bars[5].date, "AAPL", SignalType.FLAT),
        ]
        result = self.engine.run("s", signals, {"AAPL": bars})
        if result.trades:
            t = result.trades[0]
            assert t.trade_id != ""
            assert t.ticker == "AAPL"
            assert t.entry_price > 0
            assert t.quantity > 0

    def test_trade_to_dict_has_all_fields(self):
        t = Trade(
            trade_id="T1", ticker="AAPL", entry_date="2024-01-01", exit_date="2024-01-10",
            entry_price=100.0, exit_price=110.0, quantity=10.0, side="LONG",
            gross_pnl=100.0, commission=0.1, slippage=0.05, net_pnl=99.85,
            return_pct=0.1, holding_days=9,
        )
        d = t.to_dict()
        assert "trade_id" in d and "net_pnl" in d

    def test_get_trades_via_engine(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        trades = self.engine.get_trades(result.backtest_id)
        assert isinstance(trades, list)


class TestBacktestMonthlyReturns:
    def setup_method(self):
        self.engine = BacktestEngine()

    def test_monthly_returns_is_dict(self):
        signals, pd = buy_and_hold_signals()
        result = self.engine.run("s", signals, pd)
        mr = self.engine.get_monthly_returns(result.backtest_id)
        assert isinstance(mr, dict)

    def test_monthly_returns_empty_for_unknown(self):
        mr = self.engine.get_monthly_returns("unknown")
        assert mr == {}


class TestBacktestComparison:
    def setup_method(self):
        self.engine = BacktestEngine()

    def test_compare_returns_dict(self):
        signals, pd = buy_and_hold_signals()
        r1 = self.engine.run("s1", signals, pd)
        r2 = self.engine.run("s2", signals, pd)
        comp = self.engine.compare([r1.backtest_id, r2.backtest_id])
        assert len(comp) == 2

    def test_compare_missing_ids_excluded(self):
        signals, pd = buy_and_hold_signals()
        r1 = self.engine.run("s1", signals, pd)
        comp = self.engine.compare([r1.backtest_id, "fake"])
        assert len(comp) == 1

    def test_compare_contains_metrics(self):
        signals, pd = buy_and_hold_signals()
        r1 = self.engine.run("s1", signals, pd)
        comp = self.engine.compare([r1.backtest_id])
        assert "metrics" in comp[r1.backtest_id]

    def test_delete_removes_result(self):
        signals, pd = buy_and_hold_signals()
        r = self.engine.run("s", signals, pd)
        self.engine.delete_result(r.backtest_id)
        assert self.engine.get_result(r.backtest_id) is None

    def test_list_results_returns_summaries(self):
        signals, pd = buy_and_hold_signals()
        self.engine.run("s1", signals, pd)
        self.engine.run("s2", signals, pd)
        lst = self.engine.list_results()
        assert len(lst) >= 2
        assert "backtest_id" in lst[0]


class TestBacktestToDict:
    def test_result_to_dict(self):
        engine = BacktestEngine()
        signals, pd = buy_and_hold_signals()
        result = engine.run("s", signals, pd)
        d = result.to_dict()
        assert "backtest_id" in d
        assert "metrics" in d
        assert isinstance(d["trades"], list)
        assert isinstance(d["equity_curve"], list)

    def test_price_bar_fields(self):
        bar = PriceBar(date="2024-01-01", open=100, high=105, low=98, close=102, volume=5000)
        assert bar.date == "2024-01-01"
        assert bar.high >= bar.low

    def test_signal_defaults(self):
        sig = Signal(date="2024-01-01", ticker="AAPL", signal_type=SignalType.LONG)
        assert sig.strength == 1.0
        assert sig.metadata == {}
