"""M12 — Pydantic v2 schemas for the portfolio optimization API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class ConstraintsSchema(BaseModel):
    long_only: bool = True
    max_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    min_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    leverage_cap: float = Field(default=1.0, ge=0.0, le=10.0)
    gross_exposure_cap: float = Field(default=1.0, ge=0.0, le=10.0)
    net_exposure_min: float = Field(default=0.0, ge=-10.0, le=10.0)
    net_exposure_max: float = Field(default=1.0, ge=-10.0, le=10.0)


# ---------------------------------------------------------------------------
# Optimize — single method
# ---------------------------------------------------------------------------

class OptimizeRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    mu: List[float] = Field(..., description="Daily expected returns per asset")
    cov: List[List[float]] = Field(..., description="Daily covariance matrix (n×n)")
    method: str = Field(default="max_sharpe")
    risk_free_rate: float = Field(default=0.02, ge=0.0, le=0.20)
    constraints: ConstraintsSchema = Field(default_factory=ConstraintsSchema)
    target_return: Optional[float] = Field(default=None, ge=-1.0, le=5.0)
    target_volatility: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    gamma: float = Field(default=1.0, gt=0.0, le=100.0)
    kelly_fraction: float = Field(default=0.5, gt=0.0, le=2.0)
    views_P: Optional[List[List[float]]] = None
    views_q: Optional[List[float]] = None
    market_weights: Optional[List[float]] = None
    returns_matrix: Optional[List[List[float]]] = Field(
        default=None, description="T×n historical returns (required for CVaR)"
    )

    @model_validator(mode="after")
    def check_dimensions(self) -> "OptimizeRequest":
        n = len(self.tickers)
        if len(self.mu) != n:
            raise ValueError("mu must have same length as tickers")
        if len(self.cov) != n or any(len(row) != n for row in self.cov):
            raise ValueError("cov must be n × n")
        return self


class OptimizeResponse(BaseModel):
    method: str
    tickers: List[str]
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    concentration_score: float
    effective_n: float
    gross_exposure: float
    net_exposure: float
    leverage: float
    risk_contributions: Dict[str, float]
    warnings: List[str]
    converged: bool


# ---------------------------------------------------------------------------
# Compare — multiple methods
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    mu: List[float]
    cov: List[List[float]]
    methods: Optional[List[str]] = None
    risk_free_rate: float = Field(default=0.02, ge=0.0, le=0.20)
    constraints: ConstraintsSchema = Field(default_factory=ConstraintsSchema)
    gamma: float = Field(default=1.0, gt=0.0)
    kelly_fraction: float = Field(default=0.5, gt=0.0, le=2.0)
    returns_matrix: Optional[List[List[float]]] = None

    @model_validator(mode="after")
    def check_dimensions(self) -> "CompareRequest":
        n = len(self.tickers)
        if len(self.mu) != n or len(self.cov) != n:
            raise ValueError("mu and cov must match tickers length")
        return self


# ---------------------------------------------------------------------------
# Efficient frontier
# ---------------------------------------------------------------------------

class FrontierRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    mu: List[float]
    cov: List[List[float]]
    n_points: int = Field(default=50, ge=5, le=500)
    risk_free_rate: float = Field(default=0.02, ge=0.0, le=0.20)
    constraints: ConstraintsSchema = Field(default_factory=ConstraintsSchema)


class FrontierPoint(BaseModel):
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]
    feasible: bool


class FrontierResponse(BaseModel):
    points: List[FrontierPoint]
    max_sharpe_idx: int
    min_vol_idx: int
    equal_weight_point: FrontierPoint
    n_feasible: int
    n_infeasible: int
    warnings: List[str]


# ---------------------------------------------------------------------------
# Risk report
# ---------------------------------------------------------------------------

class RiskRequest(BaseModel):
    returns: List[float] = Field(..., min_length=10, description="Daily portfolio returns")
    nav: List[float] = Field(..., min_length=10, description="NAV series")
    benchmark_returns: Optional[List[float]] = None
    initial_capital: float = Field(default=100_000.0, gt=0)
    var_method: str = Field(default="historical")


class VaRSchema(BaseModel):
    var_90: float
    var_95: float
    var_975: float
    var_99: float
    cvar_90: float
    cvar_95: float
    cvar_975: float
    cvar_99: float
    method: str


class DrawdownSchema(BaseModel):
    max_drawdown_pct: float
    avg_drawdown_pct: float
    max_drawdown_duration_days: int
    avg_drawdown_duration_days: float
    current_drawdown_pct: float
    recovery_time_days: Optional[int]
    ulcer_index: float
    pain_index: float


class DistributionSchema(BaseModel):
    mean_daily: float
    std_daily: float
    skewness: float
    kurtosis: float
    is_fat_tailed: bool
    tail_ratio: float
    gain_to_pain: float
    best_day_pct: float
    worst_day_pct: float
    positive_days_pct: float


class RiskResponse(BaseModel):
    total_return_pct: float
    annual_return_pct: float
    annual_volatility_pct: float
    downside_volatility_pct: float
    semi_variance_daily: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    treynor_ratio: float
    information_ratio: float
    alpha: float
    beta: float
    r_squared: float
    tracking_error_pct: float
    benchmark_return_pct: float
    var: VaRSchema
    drawdown: DrawdownSchema
    distribution: DistributionSchema
    ulcer_index: float
    warnings: List[str]


# ---------------------------------------------------------------------------
# Risk attribution
# ---------------------------------------------------------------------------

class AttributionRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    mu: List[float]
    cov: List[List[float]]
    weights: Dict[str, float]


class AttributionResponse(BaseModel):
    tickers: List[str]
    weights: Dict[str, float]
    marginal_contributions: Dict[str, float]
    component_contributions: Dict[str, float]
    pct_contributions: Dict[str, float]
    portfolio_volatility: float
    diversification_benefit: float
    hhi: float
    effective_n: float


# ---------------------------------------------------------------------------
# Stress testing
# ---------------------------------------------------------------------------

class StressRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    weights: Dict[str, float]
    scenario_key: Optional[str] = None    # key from BUILTIN_STRESS_SCENARIOS; None = all
    custom_shocks: Optional[Dict[str, float]] = None   # ticker -> shock fraction
    market_shock: float = Field(default=0.0, ge=-1.0, le=1.0)


class StressResponse(BaseModel):
    scenario_name: str
    portfolio_impact_pct: float
    asset_impacts: Dict[str, float]
    worst_contributor: str
    best_contributor: str
    severity_score: float
    post_stress_weights: Dict[str, float]
    warnings: List[str]


class AllScenariosResponse(BaseModel):
    scenarios: List[StressResponse]


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

class MonteCarloRequest(BaseModel):
    weights: List[float] = Field(..., min_length=1, max_length=50)
    mu: List[float]
    cov: List[List[float]]
    n_simulations: int = Field(default=5000, ge=100, le=50_000)
    simulation_days: int = Field(default=252, ge=1, le=3_780)
    model: str = Field(default="gbm")
    seed: int = Field(default=42, ge=0)
    initial_value: float = Field(default=100_000.0, gt=0)
    target_return: Optional[float] = Field(default=None, ge=-1.0, le=10.0)
    returns_matrix: Optional[List[List[float]]] = None

    @model_validator(mode="after")
    def check_dimensions(self) -> "MonteCarloRequest":
        n = len(self.weights)
        if len(self.mu) != n or len(self.cov) != n:
            raise ValueError("weights, mu, cov must all have same length")
        return self


class MonteCarloResponse(BaseModel):
    model: str
    n_simulations: int
    simulation_days: int
    initial_value: float
    percentile_paths: Dict[str, List[float]]
    expected_terminal: float
    median_terminal: float
    std_terminal: float
    best_case: float
    worst_case: float
    probability_of_loss: float
    probability_of_target_return: Optional[float]
    var_95: float
    cvar_95: float
    ruin_probability: float
    median_max_drawdown_pct: float
    p95_max_drawdown_pct: float
    implied_annual_return: float
    warnings: List[str]


# ---------------------------------------------------------------------------
# Covariance diagnostics
# ---------------------------------------------------------------------------

class CovRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    returns_matrix: List[List[float]] = Field(..., description="T×n returns")
    method: str = Field(default="sample")


class CovResponse(BaseModel):
    n_assets: int
    n_observations: int
    method: str
    condition_number: float
    is_positive_definite: bool
    min_eigenvalue: float
    max_eigenvalue: float
    effective_rank: float
    highly_correlated_pairs: List[Any]
    shrinkage_intensity: float
    repaired: bool
    warnings: List[str]
    covariance_matrix: Optional[List[List[float]]] = None
    correlation_matrix: Optional[List[List[float]]] = None


# ---------------------------------------------------------------------------
# Methods list
# ---------------------------------------------------------------------------

class MethodInfo(BaseModel):
    key: str
    display_name: str
    requires_returns: bool
    requires_target: Optional[str]


class MethodsResponse(BaseModel):
    methods: List[MethodInfo]


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

class FullAnalysisRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, max_length=50)
    mu: List[float]
    cov: List[List[float]]
    method: str = Field(default="max_sharpe")
    risk_free_rate: float = Field(default=0.02, ge=0.0, le=0.20)
    constraints: ConstraintsSchema = Field(default_factory=ConstraintsSchema)
    n_frontier_points: int = Field(default=50, ge=5, le=200)
    returns_matrix: Optional[List[List[float]]] = None
    gamma: float = Field(default=1.0, gt=0.0)
    kelly_fraction: float = Field(default=0.5, gt=0.0, le=2.0)
    views_P: Optional[List[List[float]]] = None
    views_q: Optional[List[float]] = None
    market_weights: Optional[List[float]] = None
    run_stress: bool = True
    run_mc: bool = True
    mc_simulations: int = Field(default=2000, ge=100, le=20_000)

    @model_validator(mode="after")
    def check_dimensions(self) -> "FullAnalysisRequest":
        n = len(self.tickers)
        if len(self.mu) != n or len(self.cov) != n:
            raise ValueError("mu and cov must match tickers length")
        return self
