"""
Event-driven backtesting engine.

Fill model:
  • Signals generated using Close prices on day T (no look-ahead).
  • Trade entries and exits execute at day T+1's Open price (standard EOD practice).
  • Daily equity is marked-to-market at day T's Close.

Position sizing:
  • position_size_pct fraction of current equity is deployed per trade.
  • Fractional shares are floored to whole shares.

Costs:
  • Commission deducted at fill time on gross notional.
  • Slippage applied to fill price: BUY fills at Open * (1 + slippage_pct),
    SELL fills at Open * (1 - slippage_pct).

Long-only: strategies generate BUY/SELL/HOLD; SELL means exit all positions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from services.strategy import Signal, get_strategy


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BacktestConfig:
    ticker: str
    benchmark: str
    start_date: date
    end_date: date
    initial_capital: float
    commission_pct: float
    slippage_pct: float
    position_size_pct: float
    strategy_name: str
    strategy_params: Dict[str, Any]


@dataclass
class OpenPosition:
    """Tracks a single open long position."""

    entry_date: str
    entry_price: float
    shares: float
    cost_basis: float  # total cash deployed (excl. commission)
    commissions_paid: float


@dataclass
class ClosedTrade:
    entry_date: str
    exit_date: str
    direction: str
    entry_price: float
    exit_price: float
    shares: float
    gross_pnl: float
    net_pnl: float
    pnl_pct: float
    duration_days: int
    commissions_paid: float


@dataclass
class EquitySnapshot:
    date: str
    equity: float
    cash: float
    position_value: float
    drawdown_pct: float


@dataclass
class BacktestMetrics:
    total_return_pct: float
    annual_return_pct: float
    benchmark_return_pct: float
    alpha: float
    beta: float
    volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    avg_trade_duration_days: float
    best_trade_pct: float
    worst_trade_pct: float
    time_in_market_pct: float
    final_equity: float


@dataclass
class BacktestResult:
    config: BacktestConfig
    equity_curve: List[EquitySnapshot]
    trades: List[ClosedTrade]
    metrics: BacktestMetrics
    monthly_returns: Dict[str, Dict[str, float]]


# ---------------------------------------------------------------------------
# OHLCV fetching helpers
# ---------------------------------------------------------------------------


def _download_ohlcv(ticker: str, start: date, end: date) -> pd.DataFrame:
    """
    Fetch daily OHLCV from yfinance, normalise MultiIndex columns, drop NaN rows.
    Adds 30 calendar days before start to ensure rolling indicators warm up correctly.
    """
    # Extra lookback for indicator warm-up (longest common indicator: SMA-200 = 200 bars)
    warmup_start = pd.Timestamp(start) - pd.Timedelta(days=300)
    raw = yf.download(
        ticker,
        start=warmup_start.date(),
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if raw.empty:
        raise ValueError(f"No price data returned for '{ticker}'")

    # yfinance 1.1.x returns MultiIndex columns when downloading a single ticker via download()
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)

    raw = raw[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    return raw


def _benchmark_returns(ticker: str, start: date, end: date) -> pd.Series:
    """Daily percentage returns for the benchmark over [start, end]."""
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if raw.empty:
            return pd.Series(dtype=float)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.droplevel(1)
        return raw["Close"].dropna().pct_change().dropna()
    except Exception:
        return pd.Series(dtype=float)


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

_TRADING_DAYS_PER_YEAR = 252
_RISK_FREE_DAILY = 0.02 / _TRADING_DAYS_PER_YEAR


def _compute_metrics(
    equity_curve: List[EquitySnapshot],
    trades: List[ClosedTrade],
    config: BacktestConfig,
    benchmark_rets: pd.Series,
) -> BacktestMetrics:
    initial = config.initial_capital
    final = equity_curve[-1].equity if equity_curve else initial

    total_return_pct = (final / initial - 1.0) * 100.0

    # Annualised return (CAGR)
    n_days = max((config.end_date - config.start_date).days, 1)
    years = n_days / 365.25
    annual_return_pct = ((final / initial) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0

    # Daily equity returns
    equities = pd.Series(
        [s.equity for s in equity_curve],
        index=pd.to_datetime([s.date for s in equity_curve]),
    )
    daily_rets = equities.pct_change().dropna()

    # Volatility (annualised)
    volatility_pct = float(daily_rets.std() * math.sqrt(_TRADING_DAYS_PER_YEAR) * 100) if len(daily_rets) > 1 else 0.0

    # Sharpe
    excess = daily_rets - _RISK_FREE_DAILY
    sharpe = float(excess.mean() / excess.std() * math.sqrt(_TRADING_DAYS_PER_YEAR)) if excess.std() > 0 else 0.0

    # Sortino — downside deviation only
    downside = daily_rets[daily_rets < _RISK_FREE_DAILY]
    down_std = float(downside.std() * math.sqrt(_TRADING_DAYS_PER_YEAR)) if len(downside) > 1 else 0.0
    annual_excess = (annual_return_pct / 100.0) - 0.02
    sortino = annual_excess / down_std if down_std > 0 else 0.0

    # Max drawdown
    peak = equities.cummax()
    drawdown = (equities - peak) / peak.replace(0, np.nan)
    max_dd_pct = float(drawdown.min() * 100)
    max_dd_days = _max_drawdown_duration(equities)

    # Calmar
    calmar = (annual_return_pct / 100.0) / abs(max_dd_pct / 100.0) if max_dd_pct != 0 else 0.0

    # Benchmark return
    if not benchmark_rets.empty:
        bench_total = float((1 + benchmark_rets).prod() - 1) * 100.0
    else:
        bench_total = 0.0

    # Beta & Alpha
    beta, alpha = _compute_alpha_beta(daily_rets, benchmark_rets)

    # Trade statistics
    total_trades = len(trades)
    win_pcts = [t.pnl_pct for t in trades if t.net_pnl > 0]
    loss_pcts = [t.pnl_pct for t in trades if t.net_pnl <= 0]
    winning = len(win_pcts)
    losing = len(loss_pcts)
    win_rate_pct = (winning / total_trades * 100.0) if total_trades > 0 else 0.0
    avg_win_pct = float(np.mean(win_pcts)) if win_pcts else 0.0
    avg_loss_pct = float(np.mean(loss_pcts)) if loss_pcts else 0.0
    gross_wins = sum(t.gross_pnl for t in trades if t.gross_pnl > 0)
    gross_losses = abs(sum(t.gross_pnl for t in trades if t.gross_pnl < 0))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    durations = [t.duration_days for t in trades]
    avg_duration = float(np.mean(durations)) if durations else 0.0
    best_trade = max((t.pnl_pct for t in trades), default=0.0)
    worst_trade = min((t.pnl_pct for t in trades), default=0.0)

    # Time in market — days with open position / total bars
    in_market_days = sum(1 for s in equity_curve if s.position_value > 0)
    total_bar_days = len(equity_curve)
    time_in_market_pct = (in_market_days / total_bar_days * 100.0) if total_bar_days > 0 else 0.0

    return BacktestMetrics(
        total_return_pct=round(total_return_pct, 4),
        annual_return_pct=round(annual_return_pct, 4),
        benchmark_return_pct=round(bench_total, 4),
        alpha=round(alpha * 100, 4),
        beta=round(beta, 4),
        volatility_pct=round(volatility_pct, 4),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        calmar_ratio=round(calmar, 4),
        max_drawdown_pct=round(max_dd_pct, 4),
        max_drawdown_duration_days=max_dd_days,
        total_trades=total_trades,
        winning_trades=winning,
        losing_trades=losing,
        win_rate_pct=round(win_rate_pct, 2),
        avg_win_pct=round(avg_win_pct, 4),
        avg_loss_pct=round(avg_loss_pct, 4),
        profit_factor=round(profit_factor, 4),
        avg_trade_duration_days=round(avg_duration, 1),
        best_trade_pct=round(best_trade, 4),
        worst_trade_pct=round(worst_trade, 4),
        time_in_market_pct=round(time_in_market_pct, 2),
        final_equity=round(final, 2),
    )


def _max_drawdown_duration(equity: pd.Series) -> int:
    """Return the longest drawdown in calendar days (peak-to-recovery or peak-to-end)."""
    if equity.empty:
        return 0
    peak = equity.iloc[0]
    peak_date = equity.index[0]
    max_dur = 0
    for dt, val in zip(equity.index, equity.values):
        if val >= peak:
            # New peak — reset the drawdown clock
            peak = val
            peak_date = dt
        else:
            # Still in drawdown — measure duration from last peak
            dur = (dt - peak_date).days
            max_dur = max(max_dur, dur)
    return max_dur


def _compute_alpha_beta(
    strategy_rets: pd.Series, benchmark_rets: pd.Series
) -> tuple[float, float]:
    """Compute beta and alpha (annualised) vs the benchmark."""
    if benchmark_rets.empty or len(strategy_rets) < 10:
        return 0.0, 0.0

    aligned = pd.concat([strategy_rets, benchmark_rets], axis=1, join="inner")
    aligned.columns = ["strat", "bench"]
    aligned = aligned.dropna()

    if len(aligned) < 10:
        return 0.0, 0.0

    var_bench = aligned["bench"].var()
    if var_bench == 0:
        return 0.0, 0.0

    beta = float(aligned.cov().iloc[0, 1] / var_bench)
    alpha = float(
        aligned["strat"].mean() * _TRADING_DAYS_PER_YEAR
        - 0.02
        - beta * (aligned["bench"].mean() * _TRADING_DAYS_PER_YEAR - 0.02)
    )
    return beta, alpha


# ---------------------------------------------------------------------------
# Monthly returns helper
# ---------------------------------------------------------------------------


def _monthly_returns(equity_curve: List[EquitySnapshot]) -> Dict[str, Dict[str, float]]:
    if not equity_curve:
        return {}
    series = pd.Series(
        {s.date: s.equity for s in equity_curve},
    )
    series.index = pd.to_datetime(series.index)
    monthly = series.resample("ME").last()
    monthly_pct = monthly.pct_change() * 100.0

    result: Dict[str, Dict[str, float]] = {}
    for dt, val in monthly_pct.items():
        if pd.isna(val):
            continue
        y = str(dt.year)
        m = str(dt.month)
        result.setdefault(y, {})[m] = round(float(val), 2)
    return result


# ---------------------------------------------------------------------------
# Core simulation loop
# ---------------------------------------------------------------------------


def run_backtest(config: BacktestConfig) -> BacktestResult:
    """
    Execute the full backtest pipeline:
      1. Fetch OHLCV with warmup period.
      2. Generate signals from the strategy.
      3. Simulate fills bar-by-bar (signal on T, fill at T+1 open).
      4. Build equity curve and trade journal.
      5. Compute performance metrics.
    """
    # --- 1. Data ---
    full_data = _download_ohlcv(config.ticker, config.start_date, config.end_date)

    # Separate warmup from evaluation window
    eval_start = pd.Timestamp(config.start_date)
    eval_end = pd.Timestamp(config.end_date)

    # --- 2. Generate signals on full data (ensures warm indicators) ---
    strategy = get_strategy(config.strategy_name, config.strategy_params)
    all_signals: pd.Series = strategy.generate_signals(full_data)

    # Trim to evaluation window
    eval_data = full_data.loc[eval_start:eval_end]
    if eval_data.empty:
        raise ValueError(
            f"No price data for '{config.ticker}' in [{config.start_date}, {config.end_date}]"
        )
    signals = all_signals.loc[eval_data.index]

    # --- 3. Benchmark data ---
    benchmark_rets = _benchmark_returns(config.benchmark, config.start_date, config.end_date)

    # --- 4. Simulation ---
    cash = config.initial_capital
    position: Optional[OpenPosition] = None
    equity_curve: List[EquitySnapshot] = []
    closed_trades: List[ClosedTrade] = []
    peak_equity = cash

    dates = eval_data.index.tolist()
    n = len(dates)

    for i, dt in enumerate(dates):
        row = eval_data.loc[dt]
        close_price = float(row["Close"])

        # --- Mark-to-market equity at today's close ---
        pos_value = position.shares * close_price if position else 0.0
        equity = cash + pos_value
        drawdown_pct = ((equity - peak_equity) / peak_equity * 100.0) if peak_equity > 0 else 0.0
        if equity > peak_equity:
            peak_equity = equity

        equity_curve.append(
            EquitySnapshot(
                date=dt.strftime("%Y-%m-%d"),
                equity=round(equity, 2),
                cash=round(cash, 2),
                position_value=round(pos_value, 2),
                drawdown_pct=round(drawdown_pct, 4),
            )
        )

        # --- Check if next bar exists for execution ---
        if i >= n - 1:
            # Last bar — force close any open position at today's close (no future open available)
            if position:
                fill = close_price * (1.0 - config.slippage_pct)
                gross = position.shares * fill
                commission = gross * config.commission_pct
                net = gross - commission - position.cost_basis
                pnl_pct = (fill / position.entry_price - 1.0) * 100.0
                duration = (dt.date() - datetime.strptime(position.entry_date, "%Y-%m-%d").date()).days

                closed_trades.append(
                    ClosedTrade(
                        entry_date=position.entry_date,
                        exit_date=dt.strftime("%Y-%m-%d"),
                        direction="LONG",
                        entry_price=round(position.entry_price, 4),
                        exit_price=round(fill, 4),
                        shares=round(position.shares, 4),
                        gross_pnl=round(position.shares * (fill - position.entry_price), 4),
                        net_pnl=round(net, 4),
                        pnl_pct=round(pnl_pct, 4),
                        duration_days=duration,
                        commissions_paid=round(position.commissions_paid + commission, 4),
                    )
                )
                cash += gross - commission
                position = None
            continue

        # --- Process signal: execute on NEXT bar's open ---
        signal = signals.iloc[i]
        next_dt = dates[i + 1]
        next_row = eval_data.loc[next_dt]
        next_open = float(next_row["Open"])

        if signal == Signal.BUY and position is None:
            # Enter long
            buy_fill = next_open * (1.0 + config.slippage_pct)
            deploy = cash * config.position_size_pct
            shares = math.floor(deploy / buy_fill)
            if shares < 1:
                continue
            gross_cost = shares * buy_fill
            commission = gross_cost * config.commission_pct
            total_cost = gross_cost + commission
            if total_cost > cash:
                continue  # Insufficient funds — skip
            cash -= total_cost
            position = OpenPosition(
                entry_date=next_dt.strftime("%Y-%m-%d"),
                entry_price=buy_fill,
                shares=float(shares),
                cost_basis=gross_cost,
                commissions_paid=commission,
            )

        elif signal == Signal.SELL and position is not None:
            # Exit long
            sell_fill = next_open * (1.0 - config.slippage_pct)
            gross_proceeds = position.shares * sell_fill
            commission = gross_proceeds * config.commission_pct
            net_proceeds = gross_proceeds - commission

            gross_pnl = position.shares * (sell_fill - position.entry_price)
            net_pnl = gross_proceeds - commission - position.cost_basis
            pnl_pct = (sell_fill / position.entry_price - 1.0) * 100.0
            duration = (
                next_dt.date() - datetime.strptime(position.entry_date, "%Y-%m-%d").date()
            ).days

            closed_trades.append(
                ClosedTrade(
                    entry_date=position.entry_date,
                    exit_date=next_dt.strftime("%Y-%m-%d"),
                    direction="LONG",
                    entry_price=round(position.entry_price, 4),
                    exit_price=round(sell_fill, 4),
                    shares=round(position.shares, 4),
                    gross_pnl=round(gross_pnl, 4),
                    net_pnl=round(net_pnl, 4),
                    pnl_pct=round(pnl_pct, 4),
                    duration_days=duration,
                    commissions_paid=round(position.commissions_paid + commission, 4),
                )
            )
            cash += net_proceeds
            position = None

    # --- 5. Metrics ---
    metrics = _compute_metrics(equity_curve, closed_trades, config, benchmark_rets)
    monthly = _monthly_returns(equity_curve)

    return BacktestResult(
        config=config,
        equity_curve=equity_curve,
        trades=closed_trades,
        metrics=metrics,
        monthly_returns=monthly,
    )
