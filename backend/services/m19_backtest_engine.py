"""Backtesting engine for quantitative strategy simulation on historical data."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalType(str, Enum):
    """Direction of a trading signal."""

    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class OrderSide(str, Enum):
    """Side of a trade execution."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class PriceBar:
    """OHLCV bar for a single trading session.

    Attributes:
        date: ISO date string (YYYY-MM-DD).
        open: Opening price.
        high: Intraday high price.
        low: Intraday low price.
        close: Closing price.
        volume: Share/contract volume traded.
    """

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Signal:
    """Trading signal emitted by a strategy.

    Attributes:
        date: ISO date when the signal is generated.
        ticker: Target instrument symbol.
        signal_type: LONG, SHORT, or FLAT.
        strength: Scalar in [0, 1] scaling position size.
        metadata: Arbitrary extra context from the strategy.
    """

    date: str
    ticker: str
    signal_type: SignalType
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trade:
    """Completed round-trip trade record.

    Attributes:
        trade_id: Unique identifier.
        ticker: Instrument symbol.
        entry_date: Entry date string.
        exit_date: Exit date string.
        entry_price: Execution price at entry (after slippage).
        exit_price: Execution price at exit (after slippage).
        quantity: Number of units traded.
        side: LONG or SHORT.
        gross_pnl: PnL before costs.
        commission: Total commission paid.
        slippage: Total slippage cost.
        net_pnl: PnL after all costs.
        return_pct: Return expressed as a fraction (e.g. 0.05 = 5%).
        holding_days: Number of bars between entry and exit.
    """

    trade_id: str
    ticker: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    quantity: float
    side: str
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    return_pct: float
    holding_days: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trade to a plain dict."""
        return {
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "entry_date": self.entry_date,
            "exit_date": self.exit_date,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "side": self.side,
            "gross_pnl": self.gross_pnl,
            "commission": self.commission,
            "slippage": self.slippage,
            "net_pnl": self.net_pnl,
            "return_pct": self.return_pct,
            "holding_days": self.holding_days,
        }


@dataclass
class EquityPoint:
    """Single point on the portfolio equity curve.

    Attributes:
        date: ISO date string.
        equity: Total portfolio value (cash + positions).
        cash: Uninvested cash balance.
        positions_value: Mark-to-market value of open positions.
        drawdown: Absolute drawdown from peak equity.
        drawdown_pct: Fractional drawdown from peak equity.
    """

    date: str
    equity: float
    cash: float
    positions_value: float
    drawdown: float
    drawdown_pct: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "date": self.date,
            "equity": self.equity,
            "cash": self.cash,
            "positions_value": self.positions_value,
            "drawdown": self.drawdown,
            "drawdown_pct": self.drawdown_pct,
        }


@dataclass
class BacktestMetrics:
    """Aggregate performance metrics for a completed backtest.

    Attributes:
        total_return: Fractional total return over the period.
        annualized_return: CAGR assuming 252 trading days per year.
        volatility: Annualised daily return standard deviation.
        sharpe_ratio: Risk-adjusted return (annualised, rf=4%).
        sortino_ratio: Downside-deviation-adjusted Sharpe.
        max_drawdown: Peak-to-trough drawdown expressed as a fraction.
        max_drawdown_duration_days: Longest drawdown duration in bars.
        calmar_ratio: Annualised return divided by max drawdown.
        win_rate: Fraction of trades with positive net PnL.
        profit_factor: Gross wins divided by gross losses.
        avg_trade_return: Mean per-trade return fraction.
        num_trades: Total number of completed trades.
        num_winning: Count of winning trades.
        num_losing: Count of losing trades.
        best_trade: Highest single-trade return fraction.
        worst_trade: Lowest single-trade return fraction.
        avg_holding_days: Average bars held per trade.
    """

    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration_days: int
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    num_trades: int
    num_winning: int
    num_losing: int
    best_trade: float
    worst_trade: float
    avg_holding_days: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return self.__dict__.copy()


@dataclass
class BacktestResult:
    """Complete result of a single backtest run.

    Attributes:
        backtest_id: Unique run identifier.
        strategy_name: Human-readable label.
        start_date: First simulation date.
        end_date: Last simulation date.
        initial_capital: Starting capital in USD.
        final_equity: Ending portfolio value.
        trades: All completed round-trip trades.
        equity_curve: Daily equity curve points.
        metrics: Aggregate performance metrics.
        config: Configuration parameters used for this run.
    """

    backtest_id: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    trades: List[Trade]
    equity_curve: List[EquityPoint]
    metrics: BacktestMetrics
    config: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "backtest_id": self.backtest_id,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_equity": self.final_equity,
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": [e.to_dict() for e in self.equity_curve],
            "metrics": self.metrics.to_dict(),
            "config": self.config,
        }


class BacktestEngine:
    """Simulates a trading strategy against historical OHLCV data.

    Supports long and short signals, fractional position sizing,
    per-trade commission, and configurable slippage. Results are
    cached in memory by backtest_id for subsequent retrieval.

    Attributes:
        _results: Cache of completed BacktestResult objects.
    """

    def __init__(self) -> None:
        self._results: Dict[str, BacktestResult] = {}

    def reset(self) -> None:
        """Clear all cached backtest results."""
        self._results.clear()

    def run(
        self,
        strategy_name: str,
        signals: List[Signal],
        price_data: Dict[str, List[PriceBar]],
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        position_size_pct: float = 0.10,
        allow_short: bool = False,
        start_date: str = "",
        end_date: str = "",
    ) -> BacktestResult:
        """Run a full backtest simulation.

        Signals are processed chronologically. On each bar, FLAT signals
        close existing positions first, then LONG/SHORT signals open new ones.
        Positions are force-closed on the final bar.

        Args:
            strategy_name: Human-readable strategy label stored in the result.
            signals: Trading signals; multiple tickers and dates supported.
            price_data: Mapping of ticker symbol to list of PriceBar objects.
            initial_capital: Starting capital in USD.
            commission_rate: Fractional commission per leg (e.g. 0.001 = 10 bps).
            slippage_bps: One-way slippage in basis points applied at each fill.
            position_size_pct: Fraction of current equity allocated per signal.
            allow_short: If False, SHORT signals are silently ignored.
            start_date: Exclude bars before this ISO date string.
            end_date: Exclude bars after this ISO date string.

        Returns:
            BacktestResult with equity curve, trades, and performance metrics.
        """
        backtest_id = str(uuid.uuid4())
        slippage_rate = slippage_bps / 10_000.0

        price_index: Dict[str, Dict[str, PriceBar]] = {}
        all_dates: set = set()
        for ticker, bars in price_data.items():
            price_index[ticker] = {bar.date: bar for bar in bars}
            all_dates.update(bar.date for bar in bars)

        sorted_dates = sorted(all_dates)
        if start_date:
            sorted_dates = [d for d in sorted_dates if d >= start_date]
        if end_date:
            sorted_dates = [d for d in sorted_dates if d <= end_date]
        if not sorted_dates:
            sorted_dates = []

        signal_index: Dict[str, Dict[str, Signal]] = {}
        for sig in signals:
            signal_index.setdefault(sig.date, {})[sig.ticker] = sig

        cash = initial_capital
        positions: Dict[str, Dict[str, Any]] = {}
        trades: List[Trade] = []
        equity_curve: List[EquityPoint] = []
        peak_equity = initial_capital

        for date_str in sorted_dates:
            day_signals = signal_index.get(date_str, {})

            for ticker, sig in list(day_signals.items()):
                if sig.signal_type == SignalType.FLAT and ticker in positions:
                    bar = price_index.get(ticker, {}).get(date_str)
                    if bar is None:
                        continue
                    pos = positions[ticker]
                    exit_price = bar.close
                    slip = exit_price * slippage_rate
                    if pos["side"] == "LONG":
                        exit_price = max(exit_price - slip, 0.0)
                        cash += pos["qty"] * exit_price
                    else:
                        exit_price = exit_price + slip
                        cash += pos["qty"] * exit_price
                    comm = pos["qty"] * exit_price * commission_rate
                    cash -= comm
                    if pos["side"] == "LONG":
                        gross = (exit_price - pos["entry_price"]) * pos["qty"]
                    else:
                        gross = (pos["entry_price"] - exit_price) * pos["qty"]
                    slip_cost = pos["qty"] * slip
                    net = gross - comm - slip_cost
                    entry_idx = sorted_dates.index(pos["entry_date"]) if pos["entry_date"] in sorted_dates else 0
                    exit_idx = sorted_dates.index(date_str)
                    holding = max(1, exit_idx - entry_idx)
                    cost_basis = pos["entry_price"] * pos["qty"]
                    ret_pct = gross / cost_basis if cost_basis else 0.0
                    trades.append(Trade(
                        trade_id=str(uuid.uuid4()),
                        ticker=ticker,
                        entry_date=pos["entry_date"],
                        exit_date=date_str,
                        entry_price=round(pos["entry_price"], 6),
                        exit_price=round(exit_price, 6),
                        quantity=round(pos["qty"], 6),
                        side=pos["side"],
                        gross_pnl=round(gross, 4),
                        commission=round(comm, 4),
                        slippage=round(slip_cost, 4),
                        net_pnl=round(net, 4),
                        return_pct=round(ret_pct, 6),
                        holding_days=holding,
                    ))
                    del positions[ticker]

            for ticker, sig in day_signals.items():
                if sig.signal_type not in (SignalType.LONG, SignalType.SHORT):
                    continue
                if ticker in positions:
                    continue
                if sig.signal_type == SignalType.SHORT and not allow_short:
                    continue
                bar = price_index.get(ticker, {}).get(date_str)
                if bar is None:
                    continue

                positions_value = sum(
                    p["qty"] * (price_index.get(t, {}).get(date_str, PriceBar(date_str, 0, 0, 0, p["entry_price"])).close)
                    for t, p in positions.items()
                )
                equity_now = cash + positions_value
                alloc = equity_now * position_size_pct * max(0.0, min(1.0, sig.strength))
                entry_price = bar.open if bar.open > 0 else bar.close
                slip = entry_price * slippage_rate
                if sig.signal_type == SignalType.LONG:
                    entry_price = entry_price + slip
                else:
                    entry_price = max(entry_price - slip, 0.0)
                if entry_price <= 0:
                    continue
                qty = alloc / entry_price
                comm = qty * entry_price * commission_rate
                cost = qty * entry_price + comm
                if cost > cash and cash > 0:
                    qty = (cash * (1 - commission_rate)) / entry_price
                    cost = qty * entry_price * (1 + commission_rate)
                if qty <= 1e-8:
                    continue
                cash -= cost
                positions[ticker] = {
                    "qty": qty,
                    "entry_price": entry_price,
                    "entry_date": date_str,
                    "side": sig.signal_type.value,
                }

            positions_value = 0.0
            for ticker, pos in positions.items():
                bar = price_index.get(ticker, {}).get(date_str)
                if bar:
                    positions_value += pos["qty"] * bar.close

            equity = cash + positions_value
            if equity > peak_equity:
                peak_equity = equity
            dd_abs = max(0.0, peak_equity - equity)
            dd_pct = dd_abs / peak_equity if peak_equity > 0 else 0.0
            equity_curve.append(EquityPoint(
                date=date_str,
                equity=round(equity, 4),
                cash=round(cash, 4),
                positions_value=round(positions_value, 4),
                drawdown=round(dd_abs, 4),
                drawdown_pct=round(dd_pct, 6),
            ))

        last_date = sorted_dates[-1] if sorted_dates else ""
        for ticker, pos in list(positions.items()):
            bar = price_index.get(ticker, {}).get(last_date)
            if bar:
                exit_price = bar.close
                slip = exit_price * slippage_rate
                if pos["side"] == "LONG":
                    ep = max(exit_price - slip, 0.0)
                    gross = (ep - pos["entry_price"]) * pos["qty"]
                    cash += pos["qty"] * ep
                else:
                    ep = exit_price + slip
                    gross = (pos["entry_price"] - ep) * pos["qty"]
                    cash += pos["qty"] * ep
                comm = pos["qty"] * ep * commission_rate
                cash -= comm
                slip_cost = pos["qty"] * slip
                net = gross - comm - slip_cost
                cost_basis = pos["entry_price"] * pos["qty"]
                ret_pct = gross / cost_basis if cost_basis else 0.0
                trades.append(Trade(
                    trade_id=str(uuid.uuid4()),
                    ticker=ticker,
                    entry_date=pos["entry_date"],
                    exit_date=last_date,
                    entry_price=round(pos["entry_price"], 6),
                    exit_price=round(ep, 6),
                    quantity=round(pos["qty"], 6),
                    side=pos["side"],
                    gross_pnl=round(gross, 4),
                    commission=round(comm, 4),
                    slippage=round(slip_cost, 4),
                    net_pnl=round(net, 4),
                    return_pct=round(ret_pct, 6),
                    holding_days=1,
                ))

        metrics = self._compute_metrics(initial_capital, cash, equity_curve, trades)
        result = BacktestResult(
            backtest_id=backtest_id,
            strategy_name=strategy_name,
            start_date=sorted_dates[0] if sorted_dates else start_date,
            end_date=sorted_dates[-1] if sorted_dates else end_date,
            initial_capital=initial_capital,
            final_equity=round(cash, 4),
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics,
            config={
                "commission_rate": commission_rate,
                "slippage_bps": slippage_bps,
                "position_size_pct": position_size_pct,
                "allow_short": allow_short,
            },
        )
        self._results[backtest_id] = result
        return result

    def _compute_metrics(
        self,
        initial_capital: float,
        final_equity: float,
        equity_curve: List[EquityPoint],
        trades: List[Trade],
    ) -> BacktestMetrics:
        """Derive aggregate performance metrics from simulation output.

        Args:
            initial_capital: Starting portfolio value.
            final_equity: Ending portfolio value.
            equity_curve: Sequence of daily equity snapshots.
            trades: All completed round-trip trades.

        Returns:
            BacktestMetrics populated with return, risk, and trade statistics.
        """
        n = len(equity_curve)
        total_return = (final_equity - initial_capital) / initial_capital if initial_capital else 0.0
        trading_days = max(n, 1)
        years = trading_days / 252.0
        ann_ret = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0

        daily_rets = []
        for i in range(1, n):
            prev = equity_curve[i - 1].equity
            curr = equity_curve[i].equity
            if prev > 0:
                daily_rets.append((curr - prev) / prev)

        mean_r = sum(daily_rets) / len(daily_rets) if daily_rets else 0.0
        var_r = sum((r - mean_r) ** 2 for r in daily_rets) / max(len(daily_rets) - 1, 1)
        vol = math.sqrt(var_r) * math.sqrt(252.0) if var_r > 0 else 0.0

        neg_rets = [r for r in daily_rets if r < 0]
        down_var = sum(r ** 2 for r in neg_rets) / max(len(neg_rets), 1)
        down_vol = math.sqrt(down_var) * math.sqrt(252.0) if down_var > 0 else 0.0

        rf = 0.04
        sharpe = (ann_ret - rf) / vol if vol > 0 else 0.0
        sortino = (ann_ret - rf) / down_vol if down_vol > 0 else 0.0

        max_dd = max((ep.drawdown_pct for ep in equity_curve), default=0.0)
        calmar = ann_ret / max_dd if max_dd > 0 else 0.0

        in_dd = False
        cur_dur = 0
        max_dd_dur = 0
        for ep in equity_curve:
            if ep.drawdown_pct > 0:
                in_dd = True
                cur_dur += 1
                max_dd_dur = max(max_dd_dur, cur_dur)
            else:
                in_dd = False
                cur_dur = 0

        winning = [t for t in trades if t.net_pnl > 0]
        losing = [t for t in trades if t.net_pnl <= 0]
        win_rate = len(winning) / len(trades) if trades else 0.0
        g_win = sum(t.gross_pnl for t in winning)
        g_loss = abs(sum(t.gross_pnl for t in losing))
        pf = g_win / g_loss if g_loss > 0 else 0.0
        avg_tr = sum(t.return_pct for t in trades) / len(trades) if trades else 0.0
        best = max((t.return_pct for t in trades), default=0.0)
        worst = min((t.return_pct for t in trades), default=0.0)
        avg_hold = sum(t.holding_days for t in trades) / len(trades) if trades else 0.0

        return BacktestMetrics(
            total_return=round(total_return, 6),
            annualized_return=round(ann_ret, 6),
            volatility=round(vol, 6),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            max_drawdown=round(max_dd, 6),
            max_drawdown_duration_days=max_dd_dur,
            calmar_ratio=round(calmar, 4),
            win_rate=round(win_rate, 4),
            profit_factor=round(pf, 4),
            avg_trade_return=round(avg_tr, 6),
            num_trades=len(trades),
            num_winning=len(winning),
            num_losing=len(losing),
            best_trade=round(best, 6),
            worst_trade=round(worst, 6),
            avg_holding_days=round(avg_hold, 2),
        )

    def get_result(self, backtest_id: str) -> Optional[BacktestResult]:
        """Retrieve a cached BacktestResult by ID.

        Args:
            backtest_id: UUID string from a previous run call.

        Returns:
            The BacktestResult, or None if not found.
        """
        return self._results.get(backtest_id)

    def get_equity_curve(self, backtest_id: str) -> List[EquityPoint]:
        """Return the equity curve for a stored backtest.

        Args:
            backtest_id: UUID of the backtest run.

        Returns:
            List of EquityPoint objects, empty if ID not found.
        """
        result = self._results.get(backtest_id)
        return result.equity_curve if result else []

    def get_trades(self, backtest_id: str) -> List[Trade]:
        """Return completed trades for a stored backtest.

        Args:
            backtest_id: UUID of the backtest run.

        Returns:
            List of Trade objects, empty if ID not found.
        """
        result = self._results.get(backtest_id)
        return result.trades if result else []

    def compare(self, backtest_ids: List[str]) -> Dict[str, Any]:
        """Compare metrics across multiple backtests.

        Args:
            backtest_ids: List of backtest UUIDs to compare.

        Returns:
            Dict mapping each found backtest_id to its strategy name and metrics.
        """
        return {
            bid: {
                "strategy_name": r.strategy_name,
                "total_return": r.metrics.total_return,
                "sharpe_ratio": r.metrics.sharpe_ratio,
                "max_drawdown": r.metrics.max_drawdown,
                "num_trades": r.metrics.num_trades,
                "metrics": r.metrics.to_dict(),
            }
            for bid in backtest_ids
            if (r := self._results.get(bid)) is not None
        }

    def delete_result(self, backtest_id: str) -> bool:
        """Remove a cached backtest result.

        Args:
            backtest_id: UUID to remove.

        Returns:
            True if deleted, False if not found.
        """
        if backtest_id in self._results:
            del self._results[backtest_id]
            return True
        return False

    def list_results(self) -> List[Dict[str, Any]]:
        """Summarise all cached backtests.

        Returns:
            List of dicts with backtest_id, strategy_name, dates, and key metrics.
        """
        return [
            {
                "backtest_id": bid,
                "strategy_name": r.strategy_name,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "total_return": r.metrics.total_return,
                "sharpe_ratio": r.metrics.sharpe_ratio,
                "num_trades": r.metrics.num_trades,
            }
            for bid, r in self._results.items()
        ]

    def get_drawdown_series(self, backtest_id: str) -> List[Dict[str, Any]]:
        """Extract date and drawdown_pct series for charting.

        Args:
            backtest_id: UUID of the backtest run.

        Returns:
            List of {date, drawdown_pct} dicts.
        """
        result = self._results.get(backtest_id)
        if not result:
            return []
        return [{"date": ep.date, "drawdown_pct": ep.drawdown_pct} for ep in result.equity_curve]

    def get_monthly_returns(self, backtest_id: str) -> Dict[str, float]:
        """Aggregate daily equity curve into monthly returns.

        Args:
            backtest_id: UUID of the backtest run.

        Returns:
            Dict mapping YYYY-MM strings to fractional monthly returns.
        """
        result = self._results.get(backtest_id)
        if not result or not result.equity_curve:
            return {}
        monthly: Dict[str, List[float]] = {}
        for ep in result.equity_curve:
            month = ep.date[:7]
            monthly.setdefault(month, []).append(ep.equity)
        out: Dict[str, float] = {}
        months = sorted(monthly.keys())
        prev_end = result.initial_capital
        for month in months:
            vals = monthly[month]
            end = vals[-1]
            out[month] = round((end - prev_end) / prev_end, 6) if prev_end else 0.0
            prev_end = end
        return out
