"""Performance analytics service.

Computes:
- Daily NAV time series (portfolio + benchmark), normalised to 100 at inception
- Return metrics (1D, 1W, 1M, YTD, total, annualised)
- Risk metrics (volatility, Sharpe ratio, maximum drawdown)
- Sector-level allocation breakdown

The NAV calculation is vectorised: transaction changes are accumulated with
``cumsum()`` and multiplied by aligned price matrices.  This avoids row-level
Python loops over large date ranges.
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from config import settings
from models.portfolio import Transaction, TransactionType
from schemas.portfolio import (
    AllocationItem,
    AllocationRead,
    NavPoint,
    PerformanceRead,
)
from services.market_data import get_price_history, get_sector
from services.portfolio import get_portfolio


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TRADING_DAYS_PER_YEAR: int = 252


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_performance(
    db: Session,
    portfolio_id: uuid.UUID,
) -> PerformanceRead:
    """Build the full performance report for a portfolio.

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID.

    Returns:
        PerformanceRead containing the NAV series and all return/risk metrics.

    Raises:
        ValueError:   If the portfolio has no transactions.
        RuntimeError: If price history cannot be fetched.
    """
    portfolio = get_portfolio(db, portfolio_id)
    benchmark = portfolio.benchmark

    txs: Sequence[Transaction] = (
        db.query(Transaction)
        .filter(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
        .all()
    )

    if not txs:
        return _empty_performance(portfolio_id, benchmark)

    equity_tickers = sorted({tx.ticker for tx in txs if tx.ticker})
    first_date: date = min(tx.transaction_date for tx in txs)
    today: date = date.today()

    # All symbols to download: portfolio tickers + benchmark
    symbols_to_fetch = list(
        dict.fromkeys(equity_tickers + [benchmark])  # preserve order, deduplicate
    )

    prices = get_price_history(symbols_to_fetch, start=first_date, end=today)

    if prices.empty:
        return _empty_performance(portfolio_id, benchmark)

    # Align to business-day calendar
    bday_range = pd.bdate_range(start=first_date, end=today)
    prices = prices.reindex(bday_range, method="ffill")

    # Build cumulative quantity and cash series
    qty_df, cash_series = _build_position_series(txs, equity_tickers, bday_range)

    # Compute daily equity value + cash = portfolio NAV
    equity_prices = prices[equity_tickers] if equity_tickers else pd.DataFrame(index=bday_range)
    daily_equity = (qty_df * equity_prices).sum(axis=1)
    portfolio_nav = daily_equity + cash_series

    # Normalise to 100 at inception
    first_nav = portfolio_nav.iloc[0]
    if first_nav == 0 or pd.isna(first_nav):
        first_nav = 1.0
    norm_nav = portfolio_nav / first_nav * 100

    # Normalise benchmark to 100 at inception
    norm_benchmark: Optional[pd.Series] = None
    if benchmark in prices.columns:
        bmark = prices[benchmark]
        first_bmark = bmark.iloc[0]
        if first_bmark and not pd.isna(first_bmark) and first_bmark > 0:
            norm_benchmark = bmark / first_bmark * 100

    # Build NavPoint list
    nav_series: list[NavPoint] = []
    for ts in bday_range:
        nav_val = norm_nav.get(ts)
        if nav_val is None or pd.isna(nav_val):
            continue
        bmark_val: Optional[float] = None
        if norm_benchmark is not None:
            bv = norm_benchmark.get(ts)
            bmark_val = round(float(bv), 4) if bv is not None and not pd.isna(bv) else None
        nav_series.append(
            NavPoint(
                date=ts.date().isoformat(),
                nav=round(float(nav_val), 4),
                benchmark_nav=bmark_val,
            )
        )

    metrics = _compute_metrics(norm_nav)

    return PerformanceRead(
        portfolio_id=portfolio_id,
        benchmark=benchmark,
        nav_series=nav_series,
        **metrics,
    )


def compute_allocation(
    db: Session,
    portfolio_id: uuid.UUID,
) -> AllocationRead:
    """Return ticker-level and sector-level allocation for a portfolio.

    Sectors are sourced from yfinance ``Ticker.info`` with a 24-hour cache.

    Args:
        db:           Active SQLAlchemy session.
        portfolio_id: Portfolio UUID.

    Returns:
        AllocationRead with ``by_ticker`` and ``by_sector`` breakdowns.
    """
    # Import here to avoid a circular dependency with transaction service
    from services.transaction import compute_portfolio_summary

    summary = compute_portfolio_summary(db, portfolio_id)
    holdings = summary.holdings

    if not holdings or summary.total_equity_value == 0:
        return AllocationRead(
            portfolio_id=portfolio_id,
            by_ticker=[],
            by_sector=[],
        )

    total = summary.total_equity_value

    by_ticker = [
        AllocationItem(
            label=h.ticker,
            market_value=h.market_value,
            weight_pct=h.weight_pct,
        )
        for h in holdings
    ]

    # Aggregate by sector
    sector_values: dict[str, float] = defaultdict(float)
    for h in holdings:
        sector = get_sector(h.ticker)
        sector_values[sector] += h.market_value

    by_sector = sorted(
        [
            AllocationItem(
                label=sector,
                market_value=round(val, 2),
                weight_pct=round(val / total * 100, 2),
            )
            for sector, val in sector_values.items()
        ],
        key=lambda x: x.market_value,
        reverse=True,
    )

    return AllocationRead(
        portfolio_id=portfolio_id,
        by_ticker=by_ticker,
        by_sector=by_sector,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_position_series(
    transactions: Sequence[Transaction],
    equity_tickers: list[str],
    bday_range: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build vectorised daily quantity and cash series from the transaction ledger.

    Returns:
        qty_df:      DataFrame (date × ticker) of cumulative share quantities.
        cash_series: Series (date) of cumulative cash balance.
    """
    qty_changes: dict[str, dict[date, float]] = {t: {} for t in equity_tickers}
    cash_changes: dict[date, float] = {}

    for tx in transactions:
        d = tx.transaction_date
        qty = float(tx.quantity)
        price = float(tx.price)
        fees = float(tx.fees)

        match tx.transaction_type:
            case TransactionType.BUY if tx.ticker:
                qty_changes[tx.ticker][d] = qty_changes[tx.ticker].get(d, 0.0) + qty
                cash_changes[d] = cash_changes.get(d, 0.0) - (qty * price + fees)
            case TransactionType.SELL if tx.ticker:
                qty_changes[tx.ticker][d] = qty_changes[tx.ticker].get(d, 0.0) - qty
                cash_changes[d] = cash_changes.get(d, 0.0) + (qty * price - fees)
            case TransactionType.DEPOSIT:
                cash_changes[d] = cash_changes.get(d, 0.0) + qty * price
            case TransactionType.WITHDRAWAL:
                cash_changes[d] = cash_changes.get(d, 0.0) - qty * price
            case TransactionType.DIVIDEND:
                cash_changes[d] = cash_changes.get(d, 0.0) + qty * price

    # Build quantity DataFrame via cumulative sum
    qty_df = pd.DataFrame(0.0, index=bday_range, columns=equity_tickers or ["__empty__"])
    for ticker in equity_tickers:
        raw = qty_changes.get(ticker, {})
        if raw:
            s = pd.Series(raw, dtype=float)
            s.index = pd.DatetimeIndex(s.index)
            s = s.groupby(level=0).sum().reindex(bday_range, fill_value=0.0)
            qty_df[ticker] = s.cumsum()

    # Build cash series
    if cash_changes:
        cs = pd.Series(cash_changes, dtype=float)
        cs.index = pd.DatetimeIndex(cs.index)
        cs = cs.groupby(level=0).sum().reindex(bday_range, fill_value=0.0)
        cash_series = cs.cumsum()
    else:
        cash_series = pd.Series(0.0, index=bday_range)

    return qty_df, cash_series


def _compute_metrics(nav: pd.Series) -> dict:
    """Derive return and risk metrics from a normalised NAV series.

    Args:
        nav: Daily NAV series normalised to 100 at inception.

    Returns:
        Dict of metric names → values, matching the fields of PerformanceRead
        (excluding ``portfolio_id``, ``benchmark``, and ``nav_series``).
    """
    if len(nav) < 2:
        return _zero_metrics()

    daily_returns: pd.Series = nav.pct_change().dropna()

    if daily_returns.empty:
        return _zero_metrics()

    # Total return
    total_return_pct = round(float((nav.iloc[-1] / nav.iloc[0] - 1) * 100), 2)

    # Annualised return (CAGR)
    n_days = len(nav)
    n_years = n_days / _TRADING_DAYS_PER_YEAR
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1.0 / max(n_years, 1.0 / _TRADING_DAYS_PER_YEAR)) - 1
    ann_return_pct = round(float(cagr * 100), 2)

    # Annualised volatility
    vol = float(daily_returns.std(ddof=1) * math.sqrt(_TRADING_DAYS_PER_YEAR)) if len(daily_returns) > 1 else 0.0
    vol_pct = round(vol * 100, 2)

    # Sharpe ratio (annualised, using configured risk-free rate)
    rf_daily = (1.0 + settings.risk_free_rate_annual) ** (1.0 / _TRADING_DAYS_PER_YEAR) - 1
    excess = daily_returns - rf_daily
    sharpe = (
        float((excess.mean() / excess.std(ddof=1)) * math.sqrt(_TRADING_DAYS_PER_YEAR))
        if excess.std() > 0
        else 0.0
    )

    # Maximum drawdown
    rolling_max = nav.cummax()
    drawdown = (nav / rolling_max) - 1.0
    max_dd_pct = round(float(drawdown.min() * 100), 2)

    # Period returns — look back from the last observation
    last_ts = nav.index[-1]

    def _period_return(trading_days: int) -> float:
        cutoff = last_ts - pd.Timedelta(days=int(trading_days * 1.45))  # calendar buffer
        past = nav[nav.index <= cutoff]
        if past.empty:
            return 0.0
        return round(float((nav.iloc[-1] / past.iloc[-1] - 1) * 100), 2)

    ytd_nav = nav[nav.index.year == last_ts.year]
    ytd_pct = round(float((nav.iloc[-1] / ytd_nav.iloc[0] - 1) * 100), 2) if not ytd_nav.empty else 0.0

    return {
        "return_1d_pct": _period_return(1),
        "return_1w_pct": _period_return(5),
        "return_1m_pct": _period_return(21),
        "return_ytd_pct": ytd_pct,
        "return_total_pct": total_return_pct,
        "return_annualized_pct": ann_return_pct,
        "volatility_pct": vol_pct,
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": max_dd_pct,
    }


def _zero_metrics() -> dict:
    """Return a zero-filled metrics dict when the NAV series is too short."""
    return {
        "return_1d_pct": 0.0,
        "return_1w_pct": 0.0,
        "return_1m_pct": 0.0,
        "return_ytd_pct": 0.0,
        "return_total_pct": 0.0,
        "return_annualized_pct": 0.0,
        "volatility_pct": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown_pct": 0.0,
    }


def _empty_performance(portfolio_id: uuid.UUID, benchmark: str) -> PerformanceRead:
    """Return a zero-filled PerformanceRead for a portfolio with no transactions."""
    return PerformanceRead(
        portfolio_id=portfolio_id,
        benchmark=benchmark,
        nav_series=[],
        **_zero_metrics(),
    )
