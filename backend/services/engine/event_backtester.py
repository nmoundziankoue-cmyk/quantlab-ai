"""M11 Phase 1 — Event-driven backtester.

``EventDrivenBacktester`` wraps the existing ``run_backtest()`` function and
reconstructs the full event sequence from its output.  This preserves 100%
backward compatibility: ``run_backtest()`` is never modified.

Design
------
1. ``run()`` calls ``run_backtest(config)`` to obtain the deterministic
   ``BacktestResult`` (equity curve + closed trades).
2. It then replays the result as a chronological stream of typed events,
   firing registered callbacks at each step.
3. Callbacks are optional — callers that only need the ``BacktestResult``
   pay no overhead beyond a single ``run_backtest()`` call.

Callback protocol
-----------------
Each callback receives the event object and nothing else::

    def my_on_bar(event: MarketEvent) -> None: ...
    def my_on_signal(event: SignalEvent) -> None: ...
    def my_on_fill(event: FillEvent) -> None: ...
    def my_on_portfolio(event: PortfolioEvent) -> None: ...

    bt = EventDrivenBacktester(config)
    bt.on_bar(my_on_bar)
    bt.on_fill(my_on_fill)
    result = bt.run()
"""

from __future__ import annotations

from typing import Callable, List, Optional

from services.backtest import BacktestConfig, BacktestResult, run_backtest
from services.engine.event_queue import EventQueue
from services.engine.events import (
    FillEvent,
    MarketEvent,
    OrderEvent,
    PortfolioEvent,
    SignalEvent,
)

_BarCallback = Callable[[MarketEvent], None]
_SignalCallback = Callable[[SignalEvent], None]
_OrderCallback = Callable[[OrderEvent], None]
_FillCallback = Callable[[FillEvent], None]
_PortfolioCallback = Callable[[PortfolioEvent], None]


class EventDrivenBacktester:
    """Wraps ``run_backtest()`` and replays results as a typed event stream.

    Parameters
    ----------
    config:
        Standard ``BacktestConfig`` — identical to what ``run_backtest()`` takes.

    Example
    -------
    ::

        config = BacktestConfig(ticker="AAPL", ...)
        bt = EventDrivenBacktester(config)
        fills: list[FillEvent] = []
        bt.on_fill(fills.append)
        result = bt.run()
        print(f"{len(fills)} fills recorded")
        print(f"Sharpe: {result.metrics.sharpe_ratio}")
    """

    def __init__(self, config: BacktestConfig) -> None:
        self._config = config
        self._bar_callbacks: List[_BarCallback] = []
        self._signal_callbacks: List[_SignalCallback] = []
        self._order_callbacks: List[_OrderCallback] = []
        self._fill_callbacks: List[_FillCallback] = []
        self._portfolio_callbacks: List[_PortfolioCallback] = []

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def on_bar(self, callback: _BarCallback) -> "EventDrivenBacktester":
        """Register a callback fired for each ``MarketEvent`` (one per bar)."""
        self._bar_callbacks.append(callback)
        return self

    def on_signal(self, callback: _SignalCallback) -> "EventDrivenBacktester":
        """Register a callback fired for each ``SignalEvent``.

        One ``SignalEvent`` is emitted per closed trade (entry signal).
        """
        self._signal_callbacks.append(callback)
        return self

    def on_order(self, callback: _OrderCallback) -> "EventDrivenBacktester":
        """Register a callback fired for each ``OrderEvent`` (one per fill)."""
        self._order_callbacks.append(callback)
        return self

    def on_fill(self, callback: _FillCallback) -> "EventDrivenBacktester":
        """Register a callback fired for each ``FillEvent`` (one per trade leg)."""
        self._fill_callbacks.append(callback)
        return self

    def on_portfolio(self, callback: _PortfolioCallback) -> "EventDrivenBacktester":
        """Register a callback fired for each ``PortfolioEvent`` (one per bar)."""
        self._portfolio_callbacks.append(callback)
        return self

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> BacktestResult:
        """Execute the backtest and replay events through registered callbacks.

        Returns the standard ``BacktestResult`` — identical to calling
        ``run_backtest(config)`` directly.
        """
        result = run_backtest(self._config)
        self._replay(result)
        return result

    # ------------------------------------------------------------------
    # Event reconstruction from BacktestResult
    # ------------------------------------------------------------------

    def _replay(self, result: BacktestResult) -> None:
        """Reconstruct the event stream from the finished BacktestResult.

        Strategy:
        - Equity curve snapshots → one MarketEvent + one PortfolioEvent per bar.
        - Closed trades → one SignalEvent + one OrderEvent + one FillEvent for
          the entry, and one SignalEvent + one OrderEvent + one FillEvent for
          the exit.  Events are inserted at the correct bar timestamps.
        """
        if not result.equity_curve:
            return

        queue = EventQueue()
        ticker = result.config.ticker

        # --- Index trades by date for O(1) lookup ---
        # entry_fills[date] = list of FillEvent (BUY legs)
        # exit_fills[date]  = list of FillEvent (SELL legs)
        entry_fills: dict[str, list[FillEvent]] = {}
        exit_fills: dict[str, list[FillEvent]] = {}

        for trade in result.trades:
            entry_commission = trade.commissions_paid / 2.0
            exit_commission = trade.commissions_paid / 2.0

            entry_slippage = trade.entry_price * self._config.slippage_pct
            exit_slippage = trade.exit_price * self._config.slippage_pct

            entry_fill = FillEvent(
                ticker=ticker,
                timestamp=trade.entry_date,
                direction="BUY",
                quantity=trade.shares,
                fill_price=trade.entry_price,
                commission=entry_commission,
                slippage=entry_slippage,
            )
            exit_fill = FillEvent(
                ticker=ticker,
                timestamp=trade.exit_date,
                direction="SELL",
                quantity=trade.shares,
                fill_price=trade.exit_price,
                commission=exit_commission,
                slippage=exit_slippage,
            )
            entry_fills.setdefault(trade.entry_date, []).append(entry_fill)
            exit_fills.setdefault(trade.exit_date, []).append(exit_fill)

        # --- Build event sequence bar by bar ---
        peak = result.config.initial_capital

        for snapshot in result.equity_curve:
            ts = snapshot.date

            # 1. MarketEvent (open/high/low/close are approximated from the
            #    snapshot — exact OHLC is not stored in EquitySnapshot, so
            #    we use close for all price fields; strategies in Phase 2 will
            #    pass real OHLCV via a richer event)
            market = MarketEvent(
                ticker=ticker,
                timestamp=ts,
                open=snapshot.equity / max(snapshot.equity, 1) * snapshot.equity,
                high=snapshot.equity,
                low=snapshot.equity,
                close=snapshot.equity,
                volume=0.0,
            )
            queue.push(market)

            # 2. SignalEvents + OrderEvents + FillEvents at this bar
            for fill in entry_fills.get(ts, []):
                queue.push(
                    SignalEvent(
                        ticker=ticker,
                        timestamp=ts,
                        signal="BUY",
                        strength=1.0,
                        source=result.config.strategy_name,
                    )
                )
                queue.push(
                    OrderEvent(
                        ticker=ticker,
                        timestamp=ts,
                        direction="BUY",
                        order_type="MARKET",
                        quantity=fill.quantity,
                    )
                )
                queue.push(fill)

            for fill in exit_fills.get(ts, []):
                queue.push(
                    SignalEvent(
                        ticker=ticker,
                        timestamp=ts,
                        signal="SELL",
                        strength=1.0,
                        source=result.config.strategy_name,
                    )
                )
                queue.push(
                    OrderEvent(
                        ticker=ticker,
                        timestamp=ts,
                        direction="SELL",
                        order_type="MARKET",
                        quantity=fill.quantity,
                    )
                )
                queue.push(fill)

            # 3. PortfolioEvent (mark-to-market)
            if snapshot.equity > peak:
                peak = snapshot.equity
            portfolio = PortfolioEvent(
                timestamp=ts,
                equity=snapshot.equity,
                cash=snapshot.cash,
                position_value=snapshot.position_value,
                drawdown_pct=snapshot.drawdown_pct,
                peak_equity=peak,
            )
            queue.push(portfolio)

        # --- Drain queue, fire callbacks ---
        for event in queue:
            if event.event_type == "MARKET":
                for cb in self._bar_callbacks:
                    cb(event)  # type: ignore[arg-type]
            elif event.event_type == "SIGNAL":
                for cb in self._signal_callbacks:
                    cb(event)  # type: ignore[arg-type]
            elif event.event_type == "ORDER":
                for cb in self._order_callbacks:
                    cb(event)  # type: ignore[arg-type]
            elif event.event_type == "FILL":
                for cb in self._fill_callbacks:
                    cb(event)  # type: ignore[arg-type]
            elif event.event_type == "PORTFOLIO":
                for cb in self._portfolio_callbacks:
                    cb(event)  # type: ignore[arg-type]
