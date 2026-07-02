"""Analytics REST router — M4 Portfolio & Risk Analytics.

All endpoints are scoped under ``/analytics/{portfolio_id}``.
Each endpoint:
  1. Validates the portfolio exists
  2. Derives holdings from the transaction ledger
  3. Downloads price history via existing market_data service
  4. Computes analytics via the appropriate M4 service
  5. Returns a typed Pydantic response

Error mapping:
  Portfolio not found               → 404
  No holdings / insufficient data   → 422
  External data failure             → 503
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from typing import Annotated, Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio import PortfolioNotFoundError, get_portfolio
from services.transaction import compute_portfolio_summary
from services.performance import compute_performance
from services.market_data import get_price_history

from services.risk_analytics import (
    compute_full_risk_metrics,
    fetch_portfolio_data,
)
from services.optimization import (
    AVAILABLE_METHODS,
    run_optimization,
    efficient_frontier,
)
from services.stress_testing import (
    BUILTIN_SCENARIOS,
    run_all_builtin_scenarios,
    run_builtin_scenario,
    run_custom_scenario,
)
from services.monte_carlo import run_monte_carlo
from services.factor_analytics import compute_factor_exposures, FACTOR_PROXIES
from services.correlation_analytics import (
    compute_all_correlation_analytics,
    compute_rolling_correlation,
    compute_correlation_matrix,
    compute_mst,
)

from schemas.analytics import (
    RiskAnalyticsRequest,
    OptimizationRequest,
    EfficientFrontierResponse,
    CustomStressRequest,
    MonteCarloRequest,
    RollingCorrelationRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_portfolio(db: Session, portfolio_id: uuid.UUID) -> Any:
    """Return portfolio or raise 404."""
    try:
        return get_portfolio(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


def _get_holdings_map(db: Session, portfolio_id: uuid.UUID) -> Dict[str, float]:
    """Return {ticker: market_value} for current open positions."""
    try:
        summary = compute_portfolio_summary(db, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    holdings = {h.ticker: h.market_value for h in summary.holdings if h.market_value > 0}
    if not holdings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Portfolio has no open positions with non-zero market value.",
        )
    return holdings


def _get_returns(
    holdings: Dict[str, float],
    lookback_days: int,
    benchmark: str,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Download price history and compute returns. Raises 503 on failure."""
    try:
        returns_df, port_rets, bench_rets = fetch_portfolio_data(
            holdings, lookback_days, benchmark
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.warning("Price data fetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data unavailable: {exc}",
        )
    if len(port_rets) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient price history — need at least 5 trading days.",
        )
    return returns_df, port_rets, bench_rets


def _portfolio_nav(db: Session, portfolio_id: uuid.UUID) -> pd.Series:
    """Build the portfolio NAV series from the performance service."""
    try:
        perf = compute_performance(db, portfolio_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not build portfolio NAV: {exc}",
        )
    nav_values = [p.nav for p in perf.nav_series]
    nav_dates = pd.to_datetime([p.date for p in perf.nav_series])
    if not nav_values:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No NAV history available. Add transactions first.",
        )
    return pd.Series(nav_values, index=nav_dates, dtype=float)


# ---------------------------------------------------------------------------
# Risk Metrics
# ---------------------------------------------------------------------------

@router.get("/risk/ticker/{ticker}")
def ticker_risk_metrics(ticker: str, lookback_days: int = 252) -> Dict[str, Any]:
    """Single-ticker risk metrics — VaR, CVaR, Sharpe, volatility, max drawdown.

    Used by the M9 Risk Center page. Fetches price history via yfinance
    and computes risk metrics without requiring a portfolio ID.
    """
    import re
    import math as _math
    if not re.match(r'^[A-Z]{1,5}$', ticker.upper()):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")
    ticker = ticker.upper()

    try:
        import yfinance as yf
        hist = yf.download(ticker, period=f"{min(lookback_days, 252 * 2)}d",
                           interval="1d", progress=False, auto_adjust=True)
        if hist is None or hist.empty or len(hist) < 10:
            raise HTTPException(status_code=422, detail=f"Insufficient price history for {ticker}")
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.droplevel(1)
        closes = hist["Close"].dropna().astype(float)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Market data unavailable: {exc}")

    returns = closes.pct_change().dropna()
    n = len(returns)
    if n < 5:
        raise HTTPException(status_code=422, detail="Insufficient return history")

    # VaR (Historical)
    sorted_returns = returns.sort_values()
    var_idx = max(0, int(_math.floor(0.05 * n)) - 1)
    var_95 = float(-sorted_returns.iloc[var_idx])

    # CVaR (expected shortfall)
    tail = sorted_returns.iloc[:max(1, int(0.05 * n))]
    cvar_95 = float(-tail.mean())

    # Annualised volatility
    vol = float(returns.std() * _math.sqrt(252))

    # Max drawdown
    nav = (1 + returns).cumprod()
    peak = nav.cummax()
    drawdown = (nav - peak) / peak
    max_dd = float(drawdown.min())

    # Sharpe (assume 4.5% risk-free)
    annual_ret = float(returns.mean() * 252)
    sharpe = (annual_ret - 0.045) / vol if vol > 0 else 0.0

    # Beta vs SPY
    try:
        spy = yf.download("SPY", period=f"{min(lookback_days, 252 * 2)}d",
                          interval="1d", progress=False, auto_adjust=True)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.droplevel(1)
        spy_rets = spy["Close"].dropna().pct_change().dropna()
        common = returns.index.intersection(spy_rets.index)
        if len(common) >= 20:
            cov = float(returns.loc[common].cov(spy_rets.loc[common]))
            var_spy = float(spy_rets.loc[common].var())
            beta = cov / var_spy if var_spy > 0 else 1.0
        else:
            beta = 1.0
    except Exception:
        beta = 1.0

    return {
        "ticker": ticker,
        "lookback_days": n,
        "var_95": round(var_95 * 100, 3),
        "cvar_95": round(cvar_95 * 100, 3),
        "beta": round(beta, 3),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(abs(max_dd) * 100, 2),
        "volatility": round(vol, 3),
        "annual_return_pct": round(annual_ret * 100, 2),
        "n_observations": n,
    }


@router.post("/{portfolio_id}/risk")
def get_risk_metrics(
    portfolio_id: uuid.UUID,
    req: RiskAnalyticsRequest,
    db: DbSession,
) -> Dict[str, Any]:
    """Full risk analytics suite for a portfolio.

    Computes VaR (Historical/Parametric/MC), CVaR, volatility metrics,
    Sharpe/Sortino/Calmar/Treynor/Information ratios, drawdown,
    beta/alpha/R², concentration metrics, and risk contributions.
    """
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    returns_df, port_rets, bench_rets = _get_returns(holdings, req.lookback_days, req.benchmark)

    # Build NAV series for drawdown and Calmar
    nav = _portfolio_nav(db, portfolio_id)

    # Weights and covariance for concentration metrics
    total_value = sum(holdings.values())
    tickers = returns_df.columns.tolist()
    weights = np.array([holdings.get(t, 0.0) for t in tickers])
    weights /= weights.sum()
    cov_matrix = returns_df.cov().values

    metrics = compute_full_risk_metrics(
        portfolio_returns=port_rets,
        benchmark_returns=bench_rets,
        nav=nav,
        weights=weights,
        cov_matrix=cov_matrix,
        tickers=tickers,
    )

    return {
        "portfolio_id": str(portfolio_id),
        "lookback_days": req.lookback_days,
        "benchmark": req.benchmark,
        **metrics,
    }


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------

@router.post("/{portfolio_id}/optimize")
def optimize_portfolio(
    portfolio_id: uuid.UUID,
    req: OptimizationRequest,
    db: DbSession,
) -> Dict[str, Any]:
    """Run a portfolio optimization and return optimal weights.

    Methods: equal_weight, min_variance, max_sharpe, risk_parity,
             max_diversification, hrp.
    """
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    returns_df, _, _ = _get_returns(holdings, req.lookback_days, "SPY")

    try:
        result = run_optimization(req.method, list(holdings.keys()), returns_df)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return {
        "portfolio_id": str(portfolio_id),
        **result,
        "tickers": list(result["weights"].keys()),
    }


@router.get("/{portfolio_id}/optimize/methods")
def list_optimization_methods(portfolio_id: uuid.UUID, db: DbSession) -> Dict[str, Any]:
    """List available optimization methods."""
    _resolve_portfolio(db, portfolio_id)
    return {"available_methods": AVAILABLE_METHODS}


@router.post("/{portfolio_id}/efficient-frontier")
def get_efficient_frontier(
    portfolio_id: uuid.UUID,
    req: OptimizationRequest,
    db: DbSession,
    n_points: int = Query(40, ge=10, le=100),
) -> Dict[str, Any]:
    """Compute the mean-variance efficient frontier for the portfolio holdings."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    returns_df, _, _ = _get_returns(holdings, req.lookback_days, "SPY")

    tickers = [t for t in holdings if t in returns_df.columns]
    if len(tickers) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Need at least 2 assets with return data.",
        )

    rets = returns_df[tickers].dropna(how="all").ffill()
    mu = rets.mean().values
    cov = rets.cov().values

    points = efficient_frontier(tickers, mu, cov, n_points=n_points)
    return {
        "portfolio_id": str(portfolio_id),
        "tickers": tickers,
        "points": points,
    }


# ---------------------------------------------------------------------------
# Stress Testing
# ---------------------------------------------------------------------------

@router.get("/{portfolio_id}/stress/scenarios")
def list_stress_scenarios(portfolio_id: uuid.UUID, db: DbSession) -> Dict[str, Any]:
    """List all available built-in stress scenarios."""
    _resolve_portfolio(db, portfolio_id)
    return {
        "scenarios": [
            {
                "key": k,
                "name": v["name"],
                "description": v["description"],
                "period_start": v["start"],
                "period_end": v["end"],
            }
            for k, v in BUILTIN_SCENARIOS.items()
        ]
    }


@router.get("/{portfolio_id}/stress/all")
def run_all_stress_tests(portfolio_id: uuid.UUID, db: DbSession) -> Dict[str, Any]:
    """Run all built-in stress scenarios and return a summary."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)

    results = run_all_builtin_scenarios(holdings)
    return {
        "portfolio_id": str(portfolio_id),
        "total_portfolio_value": round(sum(holdings.values()), 2),
        "scenarios": results,
    }


@router.get("/{portfolio_id}/stress/{scenario_key}")
def run_stress_scenario(
    portfolio_id: uuid.UUID,
    scenario_key: str,
    db: DbSession,
) -> Dict[str, Any]:
    """Run a single built-in stress scenario."""
    _resolve_portfolio(db, portfolio_id)
    if scenario_key not in BUILTIN_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_key!r} not found. Use /stress/scenarios to list available ones.",
        )
    holdings = _get_holdings_map(db, portfolio_id)

    try:
        result = run_builtin_scenario(scenario_key, holdings)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stress test failed: {exc}",
        )
    return {"portfolio_id": str(portfolio_id), **result}


@router.post("/{portfolio_id}/stress/custom")
def run_custom_stress_test(
    portfolio_id: uuid.UUID,
    req: CustomStressRequest,
    db: DbSession,
) -> Dict[str, Any]:
    """Run a user-defined stress scenario with explicit per-ticker shocks."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    result = run_custom_scenario(req.scenario_name, req.shocks, holdings)
    return {"portfolio_id": str(portfolio_id), **result}


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

@router.post("/{portfolio_id}/monte-carlo")
def run_monte_carlo_simulation(
    portfolio_id: uuid.UUID,
    req: MonteCarloRequest,
    db: DbSession,
) -> Dict[str, Any]:
    """Run a Monte Carlo projection of the portfolio.

    Returns percentile fan-chart data and terminal value statistics.
    """
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    _, port_rets, _ = _get_returns(holdings, req.lookback_days, "SPY")

    total_value = sum(holdings.values())

    try:
        result = run_monte_carlo(
            portfolio_returns=port_rets,
            initial_value=total_value,
            simulation_days=req.simulation_days,
            n_simulations=req.n_simulations,
            model=req.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return {"portfolio_id": str(portfolio_id), **result}


# ---------------------------------------------------------------------------
# Factor Analytics
# ---------------------------------------------------------------------------

@router.get("/{portfolio_id}/factors")
def get_factor_exposures(
    portfolio_id: uuid.UUID,
    db: DbSession,
    lookback_days: int = Query(252, ge=60, le=1260),
) -> Dict[str, Any]:
    """Estimate portfolio factor exposures via OLS regression on ETF proxies."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    _, port_rets, _ = _get_returns(holdings, lookback_days, "SPY")

    try:
        result = compute_factor_exposures(port_rets, lookback_days)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Factor analytics failed: {exc}",
        )

    return {"portfolio_id": str(portfolio_id), **result}


# ---------------------------------------------------------------------------
# Correlation Analytics
# ---------------------------------------------------------------------------

@router.get("/{portfolio_id}/correlation")
def get_correlation_matrix(
    portfolio_id: uuid.UUID,
    db: DbSession,
    lookback_days: int = Query(252, ge=30, le=1260),
    method: str = Query("pearson", pattern="^(pearson|spearman|kendall)$"),
) -> Dict[str, Any]:
    """Return pairwise correlation matrix for portfolio assets."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    returns_df, _, _ = _get_returns(holdings, lookback_days, "SPY")

    result = compute_correlation_matrix(returns_df, method=method)
    return {"portfolio_id": str(portfolio_id), **result}


@router.post("/{portfolio_id}/correlation/rolling")
def get_rolling_correlation(
    portfolio_id: uuid.UUID,
    req: RollingCorrelationRequest,
    db: DbSession,
) -> Dict[str, Any]:
    """Rolling pairwise correlation between two portfolio assets."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)

    if req.ticker_a not in holdings or req.ticker_b not in holdings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both tickers must be in the current portfolio holdings.",
        )

    returns_df, _, _ = _get_returns(holdings, req.lookback_days, "SPY")

    try:
        result = compute_rolling_correlation(returns_df, req.ticker_a, req.ticker_b, req.window)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return {"portfolio_id": str(portfolio_id), **result}


@router.get("/{portfolio_id}/correlation/mst")
def get_mst(
    portfolio_id: uuid.UUID,
    db: DbSession,
    lookback_days: int = Query(252, ge=30, le=1260),
) -> Dict[str, Any]:
    """Return the Minimum Spanning Tree of the asset correlation network."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    returns_df, _, _ = _get_returns(holdings, lookback_days, "SPY")

    result = compute_mst(returns_df)
    return {"portfolio_id": str(portfolio_id), **result}


@router.get("/{portfolio_id}/correlation/clusters")
def get_clusters(
    portfolio_id: uuid.UUID,
    db: DbSession,
    lookback_days: int = Query(252, ge=30, le=1260),
    n_clusters: int = Query(3, ge=2, le=10),
) -> Dict[str, Any]:
    """Return hierarchical clustering of portfolio assets by correlation."""
    _resolve_portfolio(db, portfolio_id)
    holdings = _get_holdings_map(db, portfolio_id)
    returns_df, _, _ = _get_returns(holdings, lookback_days, "SPY")

    from services.correlation_analytics import compute_hierarchical_clusters
    result = compute_hierarchical_clusters(returns_df, n_clusters=n_clusters)
    return {"portfolio_id": str(portfolio_id), **result}
