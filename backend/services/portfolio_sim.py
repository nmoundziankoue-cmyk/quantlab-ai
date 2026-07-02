"""
M11 Phase 3 — Multi-asset institutional portfolio simulation engine.

Design contract
---------------
* ``run_backtest()`` is NOT called or modified.
* ``services/performance.py`` is NOT touched (it operates on DB transactions).
* ``services/risk_analytics.py`` is imported for metric computation.
* ``services/strategy.py`` ``get_strategy()`` is used for signal generation.
* When ``price_data`` is supplied the function is 100 % deterministic and
  makes zero network calls — used by tests.

Accounting model (cash-based)
------------------------------
Long entry  : cash -= qty × fill + commission
Long exit   : cash += qty × fill - commission;  realized_pnl += gross_pnl - commissions
Short entry : cash += qty × fill - commission   (receive proceeds)
Short exit  : cash -= qty × fill + commission;  realized_pnl += gross_pnl - commissions
Dividends   : cash += daily_dividend_per_share × long_qty   (uniform annual yield)

Equity (mark-to-market)
    = cash + long_market_value - short_liability
where
    long_market_value  = Σ qty_long  × current_price
    short_liability    = Σ qty_short × current_price

Unrealized P&L
    = equity - initial_capital - realized_pnl
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from services.risk_analytics import (
    annual_volatility,
    beta_alpha,
    calmar_ratio,
    information_ratio,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    var_historical,
)
from services.strategy import Signal, get_strategy


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class PortfolioSimConfig:
    """Full specification for a multi-asset portfolio simulation.

    ``tickers``, ``strategy_names``, and ``strategy_params`` must have the
    same length.  Each index *i* defines the ticker, strategy, and params
    for slot *i*.
    """

    tickers: List[str]
    strategy_names: List[str]
    strategy_params: List[Dict[str, Any]]
    start_date: date
    end_date: date
    benchmark: str = "SPY"
    initial_capital: float = 100_000.0
    commission_pct: float = 0.001
    slippage_pct: float = 0.001
    position_size_pct: float = 1.0       # fraction of equity deployed per entry
    allow_short: bool = False
    margin_multiplier: float = 1.0        # 1.0 = no margin; 2.0 = up to 2× equity
    annual_dividend_yield: float = 0.0    # uniform daily dividend accrual (approx)

    def __post_init__(self) -> None:
        n = len(self.tickers)
        if len(self.strategy_names) != n:
            raise ValueError("strategy_names length must match tickers")
        if len(self.strategy_params) != n:
            raise ValueError("strategy_params length must match tickers")
        if not self.tickers:
            raise ValueError("tickers must not be empty")
        if self.position_size_pct <= 0 or self.position_size_pct > 1.0:
            raise ValueError("position_size_pct must be in (0, 1]")


# ---------------------------------------------------------------------------
# Internal position state
# ---------------------------------------------------------------------------


@dataclass
class _OpenPosition:
    ticker: str
    direction: str    # "LONG" / "SHORT"
    quantity: float
    entry_price: float
    entry_date: str
    cost_basis: float          # total gross cash at entry (qty × fill price)
    commissions_paid: float


# ---------------------------------------------------------------------------
# Public output types
# ---------------------------------------------------------------------------


@dataclass
class PositionState:
    """Snapshot of a single open position at a point in time."""

    ticker: str
    direction: str
    quantity: float
    entry_price: float
    current_price: float
    market_value: float        # qty × current_price (always positive)
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class SimTransaction:
    """A single execution record.

    ``net_cash_change > 0`` means cash was received (sell / short entry).
    ``net_cash_change < 0`` means cash was spent (buy / cover).
    """

    date: str
    ticker: str
    action: str       # BUY | SELL | SHORT | COVER | DIVIDEND
    quantity: float
    price: float
    commission: float
    net_cash_change: float


@dataclass
class PortfolioSnapshot:
    """Daily mark-to-market state of the whole portfolio."""

    date: str
    cash: float
    equity: float
    long_exposure: float
    short_exposure: float
    gross_exposure: float
    net_exposure: float       # long_exposure - short_exposure
    leverage: float           # gross_exposure / equity (0 when equity ≤ 0)
    buying_power: float       # cash (+ margin allowance)
    realized_pnl: float       # cumulative
    unrealized_pnl: float
    total_pnl: float          # realized + unrealized
    drawdown_pct: float       # vs all-time peak equity
    num_positions: int


@dataclass
class PortfolioMetrics:
    """Aggregate performance metrics for the simulation."""

    total_return_pct: float
    annual_return_pct: float
    benchmark_return_pct: float
    alpha: float
    beta: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    volatility_pct: float
    information_ratio: float
    var_95: float
    total_transactions: int
    total_commissions: float
    final_equity: float


@dataclass
class PortfolioSimResult:
    """Complete output from a portfolio simulation run."""

    config: PortfolioSimConfig
    snapshots: List[PortfolioSnapshot]
    transactions: List[SimTransaction]
    metrics: PortfolioMetrics

    @property
    def equity_curve(self) -> List[Tuple[str, float]]:
        """(date, equity) pairs ordered chronologically."""
        return [(s.date, s.equity) for s in self.snapshots]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

_WARMUP_DAYS = 300   # calendar days prepended for indicator warm-up


def _download(ticker: str, start: date, end: date) -> pd.DataFrame:
    """Download OHLCV from yfinance with warm-up buffer. Normalises MultiIndex."""
    import yfinance as yf  # lazy import — not needed in tests

    warmup_start = pd.Timestamp(start) - pd.Timedelta(days=_WARMUP_DAYS)
    raw = yf.download(
        ticker,
        start=warmup_start.date(),
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)
    return raw[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])


def _trim_to_eval(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    return df.loc[pd.Timestamp(start): pd.Timestamp(end)]


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------


def run_portfolio_sim(
    config: PortfolioSimConfig,
    *,
    price_data: Optional[Dict[str, pd.DataFrame]] = None,
) -> PortfolioSimResult:
    """Run a multi-asset portfolio simulation.

    Parameters
    ----------
    config:
        Full simulation specification.
    price_data:
        Optional pre-loaded OHLCV DataFrames keyed by ticker symbol (including
        benchmark).  When provided no network calls are made — the data is
        used as-is after trimming to [start_date, end_date].
        When ``None`` data is downloaded from yfinance with a warmup buffer.

    Returns
    -------
    PortfolioSimResult
        Snapshots, transaction log, and performance metrics.
    """
    # ------------------------------------------------------------------ #
    # 1. Load price data
    # ------------------------------------------------------------------ #
    all_tickers = list(dict.fromkeys(config.tickers + [config.benchmark]))

    if price_data is not None:
        # Use provided data (trim to eval window)
        full_data: Dict[str, pd.DataFrame] = {
            t: _trim_to_eval(price_data[t], config.start_date, config.end_date)
            for t in all_tickers
            if t in price_data
        }
    else:
        full_data = {
            t: _download(t, config.start_date, config.end_date)
            for t in all_tickers
        }
        full_data = {
            t: _trim_to_eval(df, config.start_date, config.end_date)
            for t, df in full_data.items()
        }

    # Separate benchmark
    bench_df: Optional[pd.DataFrame] = full_data.pop(config.benchmark, None)

    # Validate all requested tickers have data
    for t in config.tickers:
        if t not in full_data or full_data[t].empty:
            raise ValueError(f"No price data for ticker '{t}'")

    # ------------------------------------------------------------------ #
    # 2. Generate signals for every ticker
    # ------------------------------------------------------------------ #
    # Signals are generated on full (warmup-inclusive) data then trimmed,
    # when data is provided already trimmed this is equivalent.
    all_signals: Dict[str, pd.Series] = {}
    for i, ticker in enumerate(config.tickers):
        strategy = get_strategy(config.strategy_names[i], config.strategy_params[i])
        # When price_data is provided it may already be trimmed; that is fine —
        # the strategy will have reduced warmup.  In live mode the full downloaded
        # frame (with warmup) is used, then trimmed above.
        all_signals[ticker] = strategy.generate_signals(full_data[ticker])

    # ------------------------------------------------------------------ #
    # 3. Find common evaluation dates
    # ------------------------------------------------------------------ #
    date_sets = [set(full_data[t].index) for t in config.tickers]
    common_dates = sorted(set.intersection(*date_sets))
    if not common_dates:
        raise ValueError("No overlapping dates found across all tickers")

    # ------------------------------------------------------------------ #
    # 4. Simulation loop
    # ------------------------------------------------------------------ #
    cash = config.initial_capital
    positions: Dict[str, _OpenPosition] = {}   # ticker → open position
    transactions: List[SimTransaction] = []
    snapshots: List[PortfolioSnapshot] = []
    realized_pnl = 0.0
    total_commissions = 0.0
    peak_equity = cash

    daily_div_yield = config.annual_dividend_yield / 252.0

    n = len(common_dates)

    for i, dt in enumerate(common_dates):
        # ---- Accrue dividends on long positions at today's close ----
        for ticker, pos in list(positions.items()):
            if pos.direction == "LONG" and daily_div_yield > 0:
                close_px = float(full_data[ticker].loc[dt, "Close"])
                div = daily_div_yield * close_px * pos.quantity
                cash += div
                transactions.append(SimTransaction(
                    date=dt.strftime("%Y-%m-%d"),
                    ticker=ticker,
                    action="DIVIDEND",
                    quantity=pos.quantity,
                    price=close_px,
                    commission=0.0,
                    net_cash_change=div,
                ))

        # ---- Mark-to-market equity ----
        long_exp, short_exp = 0.0, 0.0
        position_states: List[PositionState] = []

        for ticker, pos in list(positions.items()):
            if ticker not in full_data or dt not in full_data[ticker].index:
                continue
            cp = float(full_data[ticker].loc[dt, "Close"])
            mktval = pos.quantity * cp
            if pos.direction == "LONG":
                long_exp += mktval
                upnl = (cp - pos.entry_price) * pos.quantity
                upnl_pct = (cp / pos.entry_price - 1.0) * 100.0 if pos.entry_price else 0.0
            else:  # SHORT
                short_exp += mktval   # liability
                upnl = (pos.entry_price - cp) * pos.quantity
                upnl_pct = (pos.entry_price / cp - 1.0) * 100.0 if cp else 0.0
            position_states.append(PositionState(
                ticker=ticker,
                direction=pos.direction,
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                current_price=cp,
                market_value=round(mktval, 4),
                unrealized_pnl=round(upnl, 4),
                unrealized_pnl_pct=round(upnl_pct, 4),
            ))

        equity = cash + long_exp - short_exp
        unrealized_pnl = equity - config.initial_capital - realized_pnl
        total_pnl = realized_pnl + unrealized_pnl
        gross_exp = long_exp + short_exp
        net_exp = long_exp - short_exp
        leverage = gross_exp / equity if equity > 0 else 0.0
        buying_power = cash + max(0.0, (config.margin_multiplier - 1.0) * equity)

        if equity > peak_equity:
            peak_equity = equity
        dd_pct = ((equity - peak_equity) / peak_equity * 100.0) if peak_equity > 0 else 0.0

        snapshots.append(PortfolioSnapshot(
            date=dt.strftime("%Y-%m-%d"),
            cash=round(cash, 4),
            equity=round(equity, 4),
            long_exposure=round(long_exp, 4),
            short_exposure=round(short_exp, 4),
            gross_exposure=round(gross_exp, 4),
            net_exposure=round(net_exp, 4),
            leverage=round(leverage, 6),
            buying_power=round(buying_power, 4),
            realized_pnl=round(realized_pnl, 4),
            unrealized_pnl=round(unrealized_pnl, 4),
            total_pnl=round(total_pnl, 4),
            drawdown_pct=round(dd_pct, 4),
            num_positions=len(positions),
        ))

        # ---- No next bar — skip execution ----
        if i >= n - 1:
            break

        # ---- Process signals → execute on next bar's open ----
        next_dt = common_dates[i + 1]

        for ticker in config.tickers:
            if ticker not in all_signals:
                continue
            sig_series = all_signals[ticker]
            if dt not in sig_series.index:
                continue
            signal = sig_series.loc[dt]
            if next_dt not in full_data[ticker].index:
                continue

            next_open = float(full_data[ticker].loc[next_dt, "Open"])
            current_pos = positions.get(ticker)

            # ---------- BUY SIGNAL ----------
            if signal == Signal.BUY:
                if current_pos is None:
                    # Open new long — size conservatively so gross+commission fits deploy
                    fill = next_open * (1.0 + config.slippage_pct)
                    deploy = equity * config.position_size_pct
                    cost_per_share = fill * (1.0 + config.commission_pct)
                    shares = math.floor(deploy / cost_per_share) if cost_per_share > 0 else 0
                    if shares < 1:
                        continue
                    gross_cost = shares * fill
                    commission = gross_cost * config.commission_pct
                    total_cost = gross_cost + commission
                    if total_cost > buying_power:
                        continue   # insufficient funds
                    cash -= total_cost
                    total_commissions += commission
                    positions[ticker] = _OpenPosition(
                        ticker=ticker,
                        direction="LONG",
                        quantity=float(shares),
                        entry_price=fill,
                        entry_date=next_dt.strftime("%Y-%m-%d"),
                        cost_basis=gross_cost,
                        commissions_paid=commission,
                    )
                    transactions.append(SimTransaction(
                        date=next_dt.strftime("%Y-%m-%d"),
                        ticker=ticker,
                        action="BUY",
                        quantity=float(shares),
                        price=round(fill, 4),
                        commission=round(commission, 4),
                        net_cash_change=round(-total_cost, 4),
                    ))

                elif current_pos.direction == "SHORT" and config.allow_short:
                    # Cover short
                    fill = next_open * (1.0 + config.slippage_pct)
                    gross = current_pos.quantity * fill
                    commission = gross * config.commission_pct
                    cash -= gross + commission
                    total_commissions += commission
                    rpnl = (current_pos.entry_price - fill) * current_pos.quantity - (
                        current_pos.commissions_paid + commission
                    )
                    realized_pnl += rpnl
                    transactions.append(SimTransaction(
                        date=next_dt.strftime("%Y-%m-%d"),
                        ticker=ticker,
                        action="COVER",
                        quantity=current_pos.quantity,
                        price=round(fill, 4),
                        commission=round(commission, 4),
                        net_cash_change=round(-(gross + commission), 4),
                    ))
                    del positions[ticker]

            # ---------- SELL SIGNAL ----------
            elif signal == Signal.SELL:
                if current_pos is not None and current_pos.direction == "LONG":
                    # Close long
                    fill = next_open * (1.0 - config.slippage_pct)
                    gross = current_pos.quantity * fill
                    commission = gross * config.commission_pct
                    proceeds = gross - commission
                    cash += proceeds
                    total_commissions += commission
                    rpnl = (fill - current_pos.entry_price) * current_pos.quantity - (
                        current_pos.commissions_paid + commission
                    )
                    realized_pnl += rpnl
                    transactions.append(SimTransaction(
                        date=next_dt.strftime("%Y-%m-%d"),
                        ticker=ticker,
                        action="SELL",
                        quantity=current_pos.quantity,
                        price=round(fill, 4),
                        commission=round(commission, 4),
                        net_cash_change=round(proceeds, 4),
                    ))
                    del positions[ticker]

                elif current_pos is None and config.allow_short:
                    # Open short
                    fill = next_open * (1.0 - config.slippage_pct)
                    deploy = equity * config.position_size_pct
                    shares = math.floor(deploy / fill) if fill > 0 else 0
                    if shares < 1:
                        continue
                    gross = shares * fill
                    commission = gross * config.commission_pct
                    proceeds = gross - commission
                    cash += proceeds
                    total_commissions += commission
                    positions[ticker] = _OpenPosition(
                        ticker=ticker,
                        direction="SHORT",
                        quantity=float(shares),
                        entry_price=fill,
                        entry_date=next_dt.strftime("%Y-%m-%d"),
                        cost_basis=gross,
                        commissions_paid=commission,
                    )
                    transactions.append(SimTransaction(
                        date=next_dt.strftime("%Y-%m-%d"),
                        ticker=ticker,
                        action="SHORT",
                        quantity=float(shares),
                        price=round(fill, 4),
                        commission=round(commission, 4),
                        net_cash_change=round(proceeds, 4),
                    ))

    # ------------------------------------------------------------------ #
    # 5. Force-close all open positions at last close
    # ------------------------------------------------------------------ #
    if snapshots and positions:
        last_dt = common_dates[-1]
        for ticker, pos in list(positions.items()):
            if ticker not in full_data or last_dt not in full_data[ticker].index:
                continue
            close_px = float(full_data[ticker].loc[last_dt, "Close"])
            commission = pos.quantity * close_px * config.commission_pct
            if pos.direction == "LONG":
                proceeds = pos.quantity * close_px - commission
                cash += proceeds
                rpnl = (close_px - pos.entry_price) * pos.quantity - (
                    pos.commissions_paid + commission
                )
                action = "SELL"
                ncash = proceeds
            else:
                cost = pos.quantity * close_px + commission
                cash -= cost
                rpnl = (pos.entry_price - close_px) * pos.quantity - (
                    pos.commissions_paid + commission
                )
                action = "COVER"
                ncash = -cost
            realized_pnl += rpnl
            total_commissions += commission
            transactions.append(SimTransaction(
                date=last_dt.strftime("%Y-%m-%d"),
                ticker=ticker,
                action=action,
                quantity=pos.quantity,
                price=round(close_px, 4),
                commission=round(commission, 4),
                net_cash_change=round(ncash, 4),
            ))
        # Update last snapshot equity after forced close
        if snapshots:
            last = snapshots[-1]
            snapshots[-1] = PortfolioSnapshot(
                date=last.date,
                cash=round(cash, 4),
                equity=round(cash, 4),     # all positions closed → equity = cash
                long_exposure=0.0,
                short_exposure=0.0,
                gross_exposure=0.0,
                net_exposure=0.0,
                leverage=0.0,
                buying_power=round(cash, 4),
                realized_pnl=round(realized_pnl, 4),
                unrealized_pnl=0.0,
                total_pnl=round(realized_pnl, 4),
                drawdown_pct=last.drawdown_pct,
                num_positions=0,
            )

    # ------------------------------------------------------------------ #
    # 6. Compute metrics
    # ------------------------------------------------------------------ #
    metrics = _compute_metrics(
        snapshots=snapshots,
        config=config,
        bench_df=bench_df,
        total_commissions=total_commissions,
        total_transactions=len([t for t in transactions if t.action != "DIVIDEND"]),
    )

    return PortfolioSimResult(
        config=config,
        snapshots=snapshots,
        transactions=transactions,
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

_ANN = 252


def _compute_metrics(
    snapshots: List[PortfolioSnapshot],
    config: PortfolioSimConfig,
    bench_df: Optional[pd.DataFrame],
    total_commissions: float,
    total_transactions: int,
) -> PortfolioMetrics:
    initial = config.initial_capital

    if not snapshots:
        return _zero_metrics(initial, total_commissions, total_transactions)

    final = snapshots[-1].equity

    # NAV series
    nav = pd.Series(
        [s.equity for s in snapshots],
        index=pd.to_datetime([s.date for s in snapshots]),
        dtype=float,
    )
    daily_rets = nav.pct_change().dropna()

    # Return
    total_return_pct = (final / initial - 1.0) * 100.0 if initial > 0 else 0.0
    n_days = max((config.end_date - config.start_date).days, 1)
    years = n_days / 365.25
    annual_return_pct = (
        ((final / initial) ** (1.0 / years) - 1.0) * 100.0
        if years > 0 and initial > 0 and final > 0
        else 0.0
    )

    # Benchmark
    bench_total = 0.0
    bench_rets = pd.Series(dtype=float)
    if bench_df is not None and not bench_df.empty:
        bench_close = bench_df["Close"].loc[
            pd.Timestamp(config.start_date): pd.Timestamp(config.end_date)
        ]
        if len(bench_close) >= 2:
            bench_total = (bench_close.iloc[-1] / bench_close.iloc[0] - 1.0) * 100.0
            bench_rets = bench_close.pct_change().dropna()

    beta_val, alpha_val = 0.0, 0.0
    if len(daily_rets) >= 10 and len(bench_rets) >= 10:
        try:
            beta_val, alpha_val = beta_alpha(daily_rets, bench_rets)
        except Exception:
            pass

    ir = 0.0
    if len(daily_rets) >= 10 and len(bench_rets) >= 10:
        try:
            ir = information_ratio(daily_rets, bench_rets)
        except Exception:
            pass

    # Risk metrics
    sharpe = sharpe_ratio(daily_rets) if len(daily_rets) > 1 else 0.0
    sortino = sortino_ratio(daily_rets) if len(daily_rets) > 1 else 0.0
    mdd = max_drawdown(nav) if len(nav) > 1 else 0.0
    calmar = calmar_ratio(daily_rets, nav) if len(daily_rets) > 1 else 0.0
    vol = annual_volatility(daily_rets) if len(daily_rets) > 1 else 0.0
    var95 = var_historical(daily_rets) if len(daily_rets) > 1 else 0.0

    return PortfolioMetrics(
        total_return_pct=round(total_return_pct, 4),
        annual_return_pct=round(annual_return_pct, 4),
        benchmark_return_pct=round(bench_total, 4),
        alpha=round(alpha_val * 100, 4),
        beta=round(beta_val, 4),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        calmar_ratio=round(calmar, 4),
        max_drawdown_pct=round(mdd * 100, 4),
        volatility_pct=round(vol * 100, 4),
        information_ratio=round(ir, 4),
        var_95=round(var95, 6),
        total_transactions=total_transactions,
        total_commissions=round(total_commissions, 4),
        final_equity=round(final, 2),
    )


def _zero_metrics(
    initial: float,
    total_commissions: float,
    total_transactions: int,
) -> PortfolioMetrics:
    return PortfolioMetrics(
        total_return_pct=0.0,
        annual_return_pct=0.0,
        benchmark_return_pct=0.0,
        alpha=0.0,
        beta=0.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        calmar_ratio=0.0,
        max_drawdown_pct=0.0,
        volatility_pct=0.0,
        information_ratio=0.0,
        var_95=0.0,
        total_transactions=total_transactions,
        total_commissions=round(total_commissions, 4),
        final_equity=round(initial, 2),
    )
