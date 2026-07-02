"""
M3 — Quantitative Research Engine API.

Endpoints:
  POST   /research/indicators              — compute indicator overlays for a ticker
  GET    /research/strategies/available    — list all built-in strategies and their params
  GET    /research/strategies              — list saved strategies
  POST   /research/strategies             — save a named strategy configuration
  GET    /research/strategies/{id}        — get a saved strategy
  DELETE /research/strategies/{id}        — delete a saved strategy
  POST   /research/backtest/run           — run a backtest (saves to DB)
  GET    /research/backtest               — list all backtest summaries
  GET    /research/backtest/{id}          — get full backtest result
  DELETE /research/backtest/{id}          — delete a backtest record
"""

from __future__ import annotations

import uuid
from typing import List

import pandas as pd
import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.research import Backtest as BacktestORM
from models.research import Strategy as StrategyORM
from schemas.research import (
    AVAILABLE_STRATEGIES,
    AvailableStrategy,
    BacktestResult,
    BacktestSummary,
    EquityPoint,
    IndicatorRequest,
    IndicatorResponse,
    OHLCVBar,
    RunBacktestRequest,
    StrategyCreate,
    StrategyRead,
    TradeRecord,
    BacktestMetrics,
)
from services.backtest import BacktestConfig, run_backtest
from services.indicators import compute_indicators

router = APIRouter(prefix="/research", tags=["research"])


# ---------------------------------------------------------------------------
# Indicator overlay
# ---------------------------------------------------------------------------


@router.post("/indicators", response_model=IndicatorResponse)
def get_indicators(req: IndicatorRequest) -> IndicatorResponse:
    """
    Fetch OHLCV data for *ticker* and compute all requested technical indicators.

    Returns the raw OHLCV bars alongside computed indicator series, ready for
    charting. Multi-output indicators (MACD, Bollinger Bands) are returned as
    nested dicts.
    """
    try:
        raw = yf.download(
            req.ticker,
            period=req.period,
            interval=req.interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Market data fetch failed: {exc}") from exc

    if raw is None or raw.empty:
        raise HTTPException(status_code=404, detail=f"No data found for ticker '{req.ticker}'")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)

    raw = raw[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])

    if raw.empty:
        raise HTTPException(status_code=404, detail=f"No usable price data for '{req.ticker}'")

    # Build OHLCV bars
    ohlcv_bars = [
        OHLCVBar(
            time=str(dt.date()),
            open=round(float(row["Open"]), 4),
            high=round(float(row["High"]), 4),
            low=round(float(row["Low"]), 4),
            close=round(float(row["Close"]), 4),
            volume=float(row["Volume"]),
        )
        for dt, row in raw.iterrows()
    ]

    # Convert IndicatorSpec objects to plain dicts for the service layer
    plain_specs = {
        ind_type: [s.model_dump(exclude_none=True) for s in spec_list]
        for ind_type, spec_list in req.indicators.items()
    }

    indicators = compute_indicators(raw, plain_specs)

    return IndicatorResponse(
        ticker=req.ticker,
        period=req.period,
        interval=req.interval,
        ohlcv=ohlcv_bars,
        indicators=indicators,
    )


# ---------------------------------------------------------------------------
# Available strategies
# ---------------------------------------------------------------------------


@router.get("/strategies/available", response_model=List[AvailableStrategy])
def list_available_strategies() -> List[AvailableStrategy]:
    """Return all built-in strategies with their configurable parameters."""
    return [
        AvailableStrategy(
            key=key,
            display_name=meta["display_name"],
            description=meta["description"],
            params=meta["params"],
        )
        for key, meta in AVAILABLE_STRATEGIES.items()
    ]


# ---------------------------------------------------------------------------
# Saved strategies CRUD
# ---------------------------------------------------------------------------


@router.get("/strategies", response_model=List[StrategyRead])
def list_strategies(db: Session = Depends(get_db)) -> List[StrategyRead]:
    """List all user-saved strategy configurations."""
    rows = db.query(StrategyORM).order_by(StrategyORM.created_at.desc()).all()
    return [StrategyRead.model_validate(r) for r in rows]


@router.post("/strategies", response_model=StrategyRead, status_code=status.HTTP_201_CREATED)
def create_strategy(body: StrategyCreate, db: Session = Depends(get_db)) -> StrategyRead:
    """Save a named strategy configuration for later reuse."""
    existing = db.query(StrategyORM).filter(StrategyORM.name == body.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A strategy named '{body.name}' already exists.",
        )
    row = StrategyORM(
        name=body.name,
        strategy_type=body.strategy_type,
        description=body.description,
        params=body.params,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return StrategyRead.model_validate(row)


@router.get("/strategies/{strategy_id}", response_model=StrategyRead)
def get_strategy_by_id(strategy_id: uuid.UUID, db: Session = Depends(get_db)) -> StrategyRead:
    row = db.query(StrategyORM).filter(StrategyORM.id == strategy_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyRead.model_validate(row)


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(strategy_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.query(StrategyORM).filter(StrategyORM.id == strategy_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Strategy not found")
    db.delete(row)
    db.commit()


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------


@router.post("/backtest/run", response_model=BacktestResult, status_code=status.HTTP_201_CREATED)
def run_backtest_endpoint(req: RunBacktestRequest, db: Session = Depends(get_db)) -> BacktestResult:
    """
    Execute a backtest and persist the full result to the database.

    The response includes the complete equity curve, trade journal, and all
    performance metrics. Large results (>2 years of daily data) may take up to
    15 seconds due to market data fetching.
    """
    config = BacktestConfig(
        ticker=req.ticker,
        benchmark=req.benchmark,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        commission_pct=req.commission_pct,
        slippage_pct=req.slippage_pct,
        position_size_pct=req.position_size_pct,
        strategy_name=req.strategy_name,
        strategy_params=req.strategy_params,
    )

    try:
        result = run_backtest(config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Backtest failed: {exc}") from exc

    m = result.metrics

    # Persist to database
    orm_row = BacktestORM(
        ticker=req.ticker,
        benchmark=req.benchmark,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        commission_pct=req.commission_pct,
        slippage_pct=req.slippage_pct,
        position_size_pct=req.position_size_pct,
        strategy_name=req.strategy_name,
        strategy_params=req.strategy_params,
        status="completed",
        total_return_pct=m.total_return_pct,
        annual_return_pct=m.annual_return_pct,
        benchmark_return_pct=m.benchmark_return_pct,
        sharpe_ratio=m.sharpe_ratio,
        sortino_ratio=m.sortino_ratio,
        calmar_ratio=m.calmar_ratio,
        max_drawdown_pct=m.max_drawdown_pct,
        win_rate_pct=m.win_rate_pct,
        profit_factor=m.profit_factor if m.profit_factor != float("inf") else 9999.0,
        total_trades=m.total_trades,
        equity_curve=[e.__dict__ for e in result.equity_curve],
        trades=[t.__dict__ for t in result.trades],
        monthly_returns=result.monthly_returns,
    )
    db.add(orm_row)
    db.commit()
    db.refresh(orm_row)

    return _orm_to_result(orm_row)


@router.get("/backtest", response_model=List[BacktestSummary])
def list_backtests(db: Session = Depends(get_db)) -> List[BacktestSummary]:
    """Return all backtest metadata (no equity curve or trades for performance)."""
    rows = db.query(BacktestORM).order_by(BacktestORM.created_at.desc()).all()
    return [BacktestSummary.model_validate(r) for r in rows]


@router.get("/backtest/{backtest_id}", response_model=BacktestResult)
def get_backtest(backtest_id: uuid.UUID, db: Session = Depends(get_db)) -> BacktestResult:
    """Return the full backtest result including equity curve and trades."""
    row = db.query(BacktestORM).filter(BacktestORM.id == backtest_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return _orm_to_result(row)


@router.delete("/backtest/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backtest(backtest_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.query(BacktestORM).filter(BacktestORM.id == backtest_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Backtest not found")
    db.delete(row)
    db.commit()


# ---------------------------------------------------------------------------
# ORM → schema conversion helper
# ---------------------------------------------------------------------------


def _orm_to_result(row: BacktestORM) -> BacktestResult:
    """Convert a persisted BacktestORM row to a BacktestResult response schema."""
    equity_curve = [
        EquityPoint(**pt) if isinstance(pt, dict) else EquityPoint(**pt.__dict__)
        for pt in (row.equity_curve or [])
    ]
    trades = [
        TradeRecord(**t) if isinstance(t, dict) else TradeRecord(**t.__dict__)
        for t in (row.trades or [])
    ]

    metrics: BacktestMetrics | None = None
    if row.total_return_pct is not None:
        # Reconstruct full metrics from stored equity / trade data
        from services.backtest import _compute_metrics, BacktestConfig
        from datetime import date as date_type

        cfg = BacktestConfig(
            ticker=row.ticker,
            benchmark=row.benchmark,
            start_date=row.start_date,
            end_date=row.end_date,
            initial_capital=float(row.initial_capital),
            commission_pct=float(row.commission_pct),
            slippage_pct=float(row.slippage_pct),
            position_size_pct=float(row.position_size_pct),
            strategy_name=row.strategy_name,
            strategy_params=row.strategy_params or {},
        )
        import pandas as pd
        from services.backtest import EquitySnapshot, ClosedTrade

        eq_snapshots = [EquitySnapshot(**pt) if isinstance(pt, dict) else pt for pt in (row.equity_curve or [])]
        trade_objs = [ClosedTrade(**t) if isinstance(t, dict) else t for t in (row.trades or [])]
        m = _compute_metrics(eq_snapshots, trade_objs, cfg, pd.Series(dtype=float))

        metrics = BacktestMetrics(
            total_return_pct=m.total_return_pct,
            annual_return_pct=m.annual_return_pct,
            benchmark_return_pct=float(row.benchmark_return_pct or 0),
            alpha=m.alpha,
            beta=m.beta,
            volatility_pct=m.volatility_pct,
            sharpe_ratio=m.sharpe_ratio,
            sortino_ratio=m.sortino_ratio,
            calmar_ratio=m.calmar_ratio,
            max_drawdown_pct=m.max_drawdown_pct,
            max_drawdown_duration_days=m.max_drawdown_duration_days,
            total_trades=m.total_trades,
            winning_trades=m.winning_trades,
            losing_trades=m.losing_trades,
            win_rate_pct=m.win_rate_pct,
            avg_win_pct=m.avg_win_pct,
            avg_loss_pct=m.avg_loss_pct,
            profit_factor=m.profit_factor,
            avg_trade_duration_days=m.avg_trade_duration_days,
            best_trade_pct=m.best_trade_pct,
            worst_trade_pct=m.worst_trade_pct,
            time_in_market_pct=m.time_in_market_pct,
            final_equity=m.final_equity,
        )

    return BacktestResult(
        id=row.id,
        ticker=row.ticker,
        benchmark=row.benchmark,
        start_date=row.start_date,
        end_date=row.end_date,
        initial_capital=float(row.initial_capital),
        commission_pct=float(row.commission_pct),
        slippage_pct=float(row.slippage_pct),
        position_size_pct=float(row.position_size_pct),
        strategy_name=row.strategy_name,
        strategy_params=row.strategy_params or {},
        status=row.status,
        error_message=row.error_message,
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        monthly_returns=row.monthly_returns or {},
        created_at=row.created_at,
    )
