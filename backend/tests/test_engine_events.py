"""M11 Phase 1 — Tests for the event-driven backtesting engine.

All tests are pure unit tests: no network calls, no database.
run_backtest() is patched to return deterministic synthetic data.

Test coverage:
  - Event dataclass construction and field access
  - Event priority constants
  - FillEvent computed properties (gross_value, net_value)
  - EventQueue: push, pop, peek, is_empty, len, clear
  - EventQueue: priority ordering within mixed pushes
  - EventQueue: drain_by_type
  - EventQueue: iter (destructive drain)
  - EventQueue: typed pushers (push_market, push_signal, ...)
  - EventDrivenBacktester: on_bar, on_fill, on_portfolio callbacks
  - EventDrivenBacktester: on_signal, on_order callbacks
  - EventDrivenBacktester: run() returns identical result to run_backtest()
  - EventDrivenBacktester: bar callback fires once per equity snapshot
  - EventDrivenBacktester: portfolio callback fires once per equity snapshot
  - EventDrivenBacktester: fill callbacks match trade count (2 legs per trade)
  - EventDrivenBacktester: zero-trade result produces no fills
  - EventDrivenBacktester: no callbacks registered — still returns valid result
  - EventDrivenBacktester: method chaining (on_bar().on_fill().run())
  - EventDrivenBacktester: signal BUY/SELL present for each trade leg
  - EventDrivenBacktester: chronological order of bar events
  - Package-level imports from services.engine work
"""

from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.engine import (
    EventDrivenBacktester,
    EventQueue,
    FillEvent,
    MarketEvent,
    OrderEvent,
    PortfolioEvent,
    SignalEvent,
)
from services.engine.events import (
    PRIORITY_FILL,
    PRIORITY_MARKET,
    PRIORITY_ORDER,
    PRIORITY_PORTFOLIO,
    PRIORITY_SIGNAL,
)
from services.backtest import (
    BacktestConfig,
    BacktestMetrics,
    BacktestResult,
    ClosedTrade,
    EquitySnapshot,
)


# ---------------------------------------------------------------------------
# Helpers — synthetic BacktestResult builders
# ---------------------------------------------------------------------------

def _make_config(ticker: str = "TEST") -> BacktestConfig:
    return BacktestConfig(
        ticker=ticker,
        benchmark="SPY",
        start_date=date(2022, 1, 3),
        end_date=date(2022, 3, 31),
        initial_capital=100_000.0,
        commission_pct=0.001,
        slippage_pct=0.001,
        position_size_pct=1.0,
        strategy_name="sma_crossover",
        strategy_params={"fast_period": 5, "slow_period": 10},
    )


def _make_metrics(**overrides) -> BacktestMetrics:
    defaults = dict(
        total_return_pct=5.0,
        annual_return_pct=20.0,
        benchmark_return_pct=3.0,
        alpha=2.0,
        beta=0.9,
        volatility_pct=15.0,
        sharpe_ratio=1.2,
        sortino_ratio=1.5,
        calmar_ratio=1.0,
        max_drawdown_pct=-8.0,
        max_drawdown_duration_days=30,
        total_trades=2,
        winning_trades=1,
        losing_trades=1,
        win_rate_pct=50.0,
        avg_win_pct=3.0,
        avg_loss_pct=-2.0,
        profit_factor=1.5,
        avg_trade_duration_days=10.0,
        best_trade_pct=3.0,
        worst_trade_pct=-2.0,
        time_in_market_pct=60.0,
        final_equity=105_000.0,
    )
    defaults.update(overrides)
    return BacktestMetrics(**defaults)


def _make_trade(
    entry_date: str,
    exit_date: str,
    entry_price: float = 100.0,
    exit_price: float = 103.0,
    shares: float = 100.0,
    net_pnl: float = 280.0,
) -> ClosedTrade:
    gross_pnl = shares * (exit_price - entry_price)
    commission = shares * (entry_price + exit_price) * 0.001
    pnl_pct = (exit_price / entry_price - 1.0) * 100.0
    return ClosedTrade(
        entry_date=entry_date,
        exit_date=exit_date,
        direction="LONG",
        entry_price=entry_price,
        exit_price=exit_price,
        shares=shares,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        pnl_pct=pnl_pct,
        duration_days=5,
        commissions_paid=commission,
    )


def _make_equity_curve(n: int = 10, start_equity: float = 100_000.0) -> list[EquitySnapshot]:
    """Build a monotonically increasing equity curve of length *n*."""
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    snapshots = []
    equity = start_equity
    for i, dt in enumerate(dates):
        equity *= 1.001
        snapshots.append(
            EquitySnapshot(
                date=dt.strftime("%Y-%m-%d"),
                equity=round(equity, 2),
                cash=round(equity * 0.0 if i > 3 else equity, 2),
                position_value=round(equity if i > 3 else 0.0, 2),
                drawdown_pct=0.0,
            )
        )
    return snapshots


def _make_result(n_bars: int = 10, trades: list[ClosedTrade] | None = None) -> BacktestResult:
    config = _make_config()
    equity_curve = _make_equity_curve(n_bars)
    if trades is None:
        trades = [
            _make_trade("2022-01-05", "2022-01-10"),
        ]
    return BacktestResult(
        config=config,
        equity_curve=equity_curve,
        trades=trades,
        metrics=_make_metrics(total_trades=len(trades)),
        monthly_returns={"2022": {"1": 1.5}},
    )


# ---------------------------------------------------------------------------
# 1–5: Event dataclass construction
# ---------------------------------------------------------------------------

class TestEventConstruction:
    def test_market_event_fields(self):
        e = MarketEvent(ticker="AAPL", timestamp="2024-01-02",
                        open=180.0, high=185.0, low=179.0, close=184.0, volume=1_000_000.0)
        assert e.ticker == "AAPL"
        assert e.timestamp == "2024-01-02"
        assert e.close == 184.0
        assert e.event_type == "MARKET"
        assert e.priority == PRIORITY_MARKET

    def test_signal_event_fields(self):
        e = SignalEvent(ticker="MSFT", timestamp="2024-01-03", signal="BUY",
                        strength=0.8, source="sma_crossover")
        assert e.signal == "BUY"
        assert e.strength == 0.8
        assert e.source == "sma_crossover"
        assert e.event_type == "SIGNAL"
        assert e.priority == PRIORITY_SIGNAL

    def test_order_event_fields(self):
        e = OrderEvent(ticker="GOOG", timestamp="2024-01-04",
                       direction="BUY", order_type="LIMIT",
                       quantity=50.0, limit_price=140.0)
        assert e.order_type == "LIMIT"
        assert e.limit_price == 140.0
        assert e.stop_price is None
        assert e.event_type == "ORDER"
        assert e.priority == PRIORITY_ORDER

    def test_fill_event_fields_and_properties(self):
        e = FillEvent(ticker="TSLA", timestamp="2024-01-05",
                      direction="BUY", quantity=10.0, fill_price=200.0,
                      commission=2.0, slippage=0.2)
        assert e.event_type == "FILL"
        assert e.priority == PRIORITY_FILL
        assert e.gross_value == pytest.approx(2000.0)
        assert e.net_value == pytest.approx(2002.0)

    def test_fill_event_sell_net_value(self):
        e = FillEvent(ticker="TSLA", timestamp="2024-01-06",
                      direction="SELL", quantity=10.0, fill_price=210.0,
                      commission=2.1, slippage=0.21)
        # SELL: net_value is negative (cash received)
        assert e.net_value == pytest.approx(-(2100.0 - 2.1))

    def test_portfolio_event_fields(self):
        e = PortfolioEvent(timestamp="2024-01-05", equity=105_000.0,
                           cash=5_000.0, position_value=100_000.0,
                           drawdown_pct=-1.5, peak_equity=106_000.0)
        assert e.event_type == "PORTFOLIO"
        assert e.priority == PRIORITY_PORTFOLIO
        assert e.peak_equity == 106_000.0


# ---------------------------------------------------------------------------
# 6–7: Priority constants are ordered correctly
# ---------------------------------------------------------------------------

class TestPriorityConstants:
    def test_priority_order(self):
        assert PRIORITY_MARKET < PRIORITY_SIGNAL
        assert PRIORITY_SIGNAL < PRIORITY_ORDER
        assert PRIORITY_ORDER < PRIORITY_FILL
        assert PRIORITY_FILL < PRIORITY_PORTFOLIO

    def test_event_priority_matches_constant(self):
        assert MarketEvent().priority == PRIORITY_MARKET
        assert SignalEvent().priority == PRIORITY_SIGNAL
        assert OrderEvent().priority == PRIORITY_ORDER
        assert FillEvent().priority == PRIORITY_FILL
        assert PortfolioEvent().priority == PRIORITY_PORTFOLIO


# ---------------------------------------------------------------------------
# 8–14: EventQueue
# ---------------------------------------------------------------------------

class TestEventQueue:
    def test_empty_on_creation(self):
        q = EventQueue()
        assert q.is_empty()
        assert len(q) == 0

    def test_push_pop_single(self):
        q = EventQueue()
        e = MarketEvent(ticker="X", timestamp="2024-01-01")
        q.push(e)
        assert not q.is_empty()
        assert len(q) == 1
        out = q.pop()
        assert out.event_type == "MARKET"
        assert q.is_empty()

    def test_pop_empty_raises(self):
        q = EventQueue()
        with pytest.raises(IndexError):
            q.pop()

    def test_peek_empty_raises(self):
        q = EventQueue()
        with pytest.raises(IndexError):
            q.peek()

    def test_priority_ordering(self):
        """Events inserted in reverse priority order must come out in correct order."""
        q = EventQueue()
        q.push(PortfolioEvent(timestamp="2024-01-01"))
        q.push(FillEvent(timestamp="2024-01-01"))
        q.push(OrderEvent(timestamp="2024-01-01"))
        q.push(SignalEvent(timestamp="2024-01-01"))
        q.push(MarketEvent(timestamp="2024-01-01"))

        types = [q.pop().event_type for _ in range(5)]
        assert types == ["MARKET", "SIGNAL", "ORDER", "FILL", "PORTFOLIO"]

    def test_insertion_order_preserved_same_priority(self):
        """Two events at the same priority must come out in insertion order."""
        q = EventQueue()
        e1 = SignalEvent(ticker="A", timestamp="2024-01-01", signal="BUY")
        e2 = SignalEvent(ticker="B", timestamp="2024-01-01", signal="SELL")
        q.push(e1)
        q.push(e2)
        assert q.pop().ticker == "A"
        assert q.pop().ticker == "B"

    def test_drain_by_type(self):
        q = EventQueue()
        q.push(MarketEvent(ticker="A"))
        q.push(SignalEvent(ticker="B"))
        q.push(MarketEvent(ticker="C"))
        markets = q.drain_by_type("MARKET")
        assert len(markets) == 2
        assert len(q) == 1
        assert q.pop().event_type == "SIGNAL"

    def test_clear(self):
        q = EventQueue()
        q.push(MarketEvent())
        q.push(SignalEvent())
        q.clear()
        assert q.is_empty()

    def test_iter_drains_in_order(self):
        q = EventQueue()
        q.push(PortfolioEvent())
        q.push(MarketEvent())
        q.push(FillEvent())
        types = [e.event_type for e in q]
        assert types == ["MARKET", "FILL", "PORTFOLIO"]
        assert q.is_empty()

    def test_typed_pushers(self):
        q = EventQueue()
        q.push_market(ticker="AAPL", timestamp="2024-01-02")
        q.push_signal(ticker="AAPL", timestamp="2024-01-02", signal="BUY")
        q.push_portfolio(timestamp="2024-01-02", equity=100_000.0)
        assert len(q) == 3
        assert q.pop().event_type == "MARKET"

    def test_peek_does_not_remove(self):
        q = EventQueue()
        q.push(MarketEvent(ticker="Z"))
        top = q.peek()
        assert top.event_type == "MARKET"
        assert len(q) == 1


# ---------------------------------------------------------------------------
# 15–24: EventDrivenBacktester
# ---------------------------------------------------------------------------

class TestEventDrivenBacktester:
    def _patched_run(self, result: BacktestResult):
        """Return a context manager that patches run_backtest to return *result*."""
        return patch(
            "services.engine.event_backtester.run_backtest",
            return_value=result,
        )

    def test_run_returns_identical_result(self):
        expected = _make_result(n_bars=10)
        with self._patched_run(expected):
            bt = EventDrivenBacktester(_make_config())
            actual = bt.run()
        assert actual is expected

    def test_no_callbacks_still_returns_result(self):
        expected = _make_result(n_bars=5, trades=[])
        with self._patched_run(expected):
            result = EventDrivenBacktester(_make_config()).run()
        assert result is expected

    def test_on_bar_fires_once_per_snapshot(self):
        n = 12
        result = _make_result(n_bars=n, trades=[])
        bars: list[MarketEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_bar(bars.append).run()
        assert len(bars) == n

    def test_on_portfolio_fires_once_per_snapshot(self):
        n = 8
        result = _make_result(n_bars=n, trades=[])
        portfolios: list[PortfolioEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_portfolio(portfolios.append).run()
        assert len(portfolios) == n

    def test_fill_callbacks_two_legs_per_trade(self):
        """Each trade produces one BUY fill and one SELL fill.

        Dates are chosen to be business days (Mon–Fri) that appear in the
        synthetic equity curve (which uses freq="B" from 2022-01-03).
        """
        # Business days in the 15-bar equity curve: 03,04,05,06,07,10,11,12,13,14,...
        trades = [
            _make_trade("2022-01-03", "2022-01-05"),
            _make_trade("2022-01-06", "2022-01-10"),
            _make_trade("2022-01-11", "2022-01-13"),
        ]
        n_trades = len(trades)
        result = _make_result(n_bars=15, trades=trades)
        fills: list[FillEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_fill(fills.append).run()
        assert len(fills) == n_trades * 2

    def test_fill_directions_are_buy_and_sell(self):
        trade = _make_trade("2022-01-05", "2022-01-10")
        result = _make_result(n_bars=10, trades=[trade])
        fills: list[FillEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_fill(fills.append).run()
        directions = {f.direction for f in fills}
        assert "BUY" in directions
        assert "SELL" in directions

    def test_zero_trades_no_fills(self):
        result = _make_result(n_bars=10, trades=[])
        fills: list[FillEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_fill(fills.append).run()
        assert fills == []

    def test_signal_events_match_trade_legs(self):
        """One SignalEvent per fill: 2 signals per trade."""
        trades = [
            _make_trade("2022-01-05", "2022-01-10"),
            _make_trade("2022-01-12", "2022-01-18"),
        ]
        result = _make_result(n_bars=15, trades=trades)
        signals: list[SignalEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_signal(signals.append).run()
        assert len(signals) == len(trades) * 2

    def test_signal_types_are_buy_and_sell(self):
        trade = _make_trade("2022-01-05", "2022-01-10")
        result = _make_result(n_bars=10, trades=[trade])
        signals: list[SignalEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_signal(signals.append).run()
        signal_values = {s.signal for s in signals}
        assert "BUY" in signal_values
        assert "SELL" in signal_values

    def test_order_callbacks_match_fills(self):
        """One OrderEvent per FillEvent."""
        trades = [_make_trade("2022-01-05", "2022-01-10")]
        result = _make_result(n_bars=10, trades=trades)
        orders: list[OrderEvent] = []
        fills: list[FillEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_order(orders.append).on_fill(fills.append).run()
        assert len(orders) == len(fills)

    def test_bar_timestamps_are_chronological(self):
        result = _make_result(n_bars=10, trades=[])
        bars: list[MarketEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_bar(bars.append).run()
        timestamps = [b.timestamp for b in bars]
        assert timestamps == sorted(timestamps)

    def test_method_chaining(self):
        """on_bar().on_fill().on_portfolio() should return self for chaining."""
        bt = EventDrivenBacktester(_make_config())
        returned = bt.on_bar(lambda e: None).on_fill(lambda e: None).on_portfolio(lambda e: None)
        assert returned is bt

    def test_fill_ticker_matches_config(self):
        trade = _make_trade("2022-01-05", "2022-01-10")
        config = _make_config(ticker="AAPL")
        result = BacktestResult(
            config=config,
            equity_curve=_make_equity_curve(10),
            trades=[trade],
            metrics=_make_metrics(total_trades=1),
            monthly_returns={},
        )
        fills: list[FillEvent] = []
        with patch("services.engine.event_backtester.run_backtest", return_value=result):
            EventDrivenBacktester(config).on_fill(fills.append).run()
        assert all(f.ticker == "AAPL" for f in fills)

    def test_portfolio_equity_matches_snapshot(self):
        n = 5
        result = _make_result(n_bars=n, trades=[])
        portfolios: list[PortfolioEvent] = []
        with self._patched_run(result):
            EventDrivenBacktester(_make_config()).on_portfolio(portfolios.append).run()
        for i, pev in enumerate(portfolios):
            assert pev.equity == pytest.approx(result.equity_curve[i].equity)

    def test_package_import(self):
        """All public names importable from services.engine."""
        from services.engine import (
            EventDrivenBacktester,
            EventQueue,
            FillEvent,
            MarketEvent,
            OrderEvent,
            PortfolioEvent,
            SignalEvent,
        )
        assert EventDrivenBacktester is not None
        assert EventQueue is not None
