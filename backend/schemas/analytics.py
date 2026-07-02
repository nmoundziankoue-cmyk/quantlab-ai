"""Pydantic v2 schemas for M4 Portfolio & Risk Analytics endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Risk Analytics
# ---------------------------------------------------------------------------

class RiskAnalyticsRequest(BaseModel):
    lookback_days: int = 252
    benchmark: str = "SPY"
    confidence: float = 0.95

    @field_validator("lookback_days")
    @classmethod
    def validate_lookback(cls, v: int) -> int:
        if v < 30 or v > 1260:
            raise ValueError("lookback_days must be between 30 and 1260")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v <= 0.5 or v >= 1.0:
            raise ValueError("confidence must be between 0.5 and 1.0 exclusive")
        return v


class RiskContribution(BaseModel):
    weight: float
    component_risk: float
    pct_risk: float


class RiskMetricsResponse(BaseModel):
    portfolio_id: str
    lookback_days: int
    benchmark: str
    var_historical_95: Optional[float]
    var_historical_99: Optional[float]
    var_parametric_95: Optional[float]
    var_parametric_99: Optional[float]
    var_monte_carlo_95: Optional[float]
    cvar_95: Optional[float]
    cvar_99: Optional[float]
    volatility_annual: Optional[float]
    downside_deviation: Optional[float]
    semi_variance: Optional[float]
    ulcer_index: Optional[float]
    max_drawdown_pct: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    treynor_ratio: Optional[float]
    information_ratio: Optional[float]
    beta: Optional[float]
    alpha_annual: Optional[float]
    r_squared: Optional[float]
    tracking_error: Optional[float]
    hhi: Optional[float]
    diversification_ratio: Optional[float]
    risk_contributions: Optional[Dict[str, RiskContribution]]


# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------

class OptimizationRequest(BaseModel):
    method: str = "max_sharpe"
    lookback_days: int = 252

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        from services.optimization import AVAILABLE_METHODS
        if v not in AVAILABLE_METHODS:
            raise ValueError(f"method must be one of {AVAILABLE_METHODS}")
        return v


class OptimizationResponse(BaseModel):
    portfolio_id: str
    method: str
    tickers: List[str]
    weights: Dict[str, float]
    expected_return: Optional[float]
    expected_volatility: Optional[float]
    sharpe_ratio: Optional[float]
    converged: Optional[bool] = None


class EfficientFrontierPoint(BaseModel):
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class EfficientFrontierResponse(BaseModel):
    portfolio_id: str
    tickers: List[str]
    points: List[EfficientFrontierPoint]


# ---------------------------------------------------------------------------
# Stress Testing
# ---------------------------------------------------------------------------

class CustomStressRequest(BaseModel):
    scenario_name: str
    shocks: Dict[str, float]

    @field_validator("shocks")
    @classmethod
    def validate_shocks(cls, v: Dict[str, float]) -> Dict[str, float]:
        for ticker, shock in v.items():
            if shock < -1.0 or shock > 1.0:
                raise ValueError(f"Shock for {ticker} must be between -1.0 and 1.0")
        return v


class AssetImpact(BaseModel):
    ticker: str
    market_value: float
    return_pct: Optional[float]
    pnl: float
    weight_pct: float


class StressTestResponse(BaseModel):
    scenario_key: str
    scenario_name: str
    description: str
    period_start: Optional[str]
    period_end: Optional[str]
    total_portfolio_value: float
    total_pnl: float
    portfolio_return_pct: float
    asset_impacts: List[AssetImpact]


class StressTestSummaryItem(BaseModel):
    scenario_key: str
    scenario_name: str
    portfolio_return_pct: Optional[float]
    total_pnl: Optional[float]


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

class MonteCarloRequest(BaseModel):
    simulation_days: int = 252
    n_simulations: int = 10_000
    model: str = "gbm"
    lookback_days: int = 252

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if v not in ("gbm", "student_t", "bootstrap"):
            raise ValueError("model must be 'gbm', 'student_t', or 'bootstrap'")
        return v

    @field_validator("n_simulations")
    @classmethod
    def validate_n_sims(cls, v: int) -> int:
        if v < 1000 or v > 100_000:
            raise ValueError("n_simulations must be between 1,000 and 100,000")
        return v

    @field_validator("simulation_days")
    @classmethod
    def validate_sim_days(cls, v: int) -> int:
        if v < 21 or v > 2520:
            raise ValueError("simulation_days must be between 21 (1mo) and 2520 (10yr)")
        return v


class MonteCarloResponse(BaseModel):
    portfolio_id: str
    model: str
    n_simulations: int
    simulation_days: int
    initial_value: float
    percentile_paths: Dict[str, List[float]]
    final_value_stats: Dict[str, float]
    prob_loss: float
    expected_final_value: float
    implied_annual_return: float


# ---------------------------------------------------------------------------
# Factor Analytics
# ---------------------------------------------------------------------------

class FactorExposure(BaseModel):
    factor: str
    etf_proxy: str
    beta: Optional[float]
    t_stat: Optional[float]
    p_value: Optional[float]
    significant: bool


class FactorAnalyticsResponse(BaseModel):
    portfolio_id: str
    exposures: List[FactorExposure]
    alpha_daily: Optional[float]
    alpha_annual: Optional[float]
    alpha_t_stat: Optional[float]
    alpha_p_value: Optional[float]
    r_squared: Optional[float]
    adj_r_squared: Optional[float]
    n_obs: int


# ---------------------------------------------------------------------------
# Correlation Analytics
# ---------------------------------------------------------------------------

class CorrelationMatrixResponse(BaseModel):
    portfolio_id: str
    tickers: List[str]
    method: str
    matrix: List[List[float]]
    summary: Dict[str, Any]


class RollingCorrelationRequest(BaseModel):
    ticker_a: str
    ticker_b: str
    window: int = 60
    lookback_days: int = 504

    @field_validator("window")
    @classmethod
    def validate_window(cls, v: int) -> int:
        if v < 10 or v > 252:
            raise ValueError("window must be between 10 and 252")
        return v


class RollingCorrelationResponse(BaseModel):
    portfolio_id: str
    ticker_a: str
    ticker_b: str
    window: int
    dates: List[str]
    values: List[float]


class MSTNode(BaseModel):
    id: str
    degree: int


class MSTEdge(BaseModel):
    source: str
    target: str
    distance: float
    correlation: float


class MSTResponse(BaseModel):
    portfolio_id: str
    nodes: List[MSTNode]
    edges: List[MSTEdge]
    n_nodes: int
    n_edges: int
