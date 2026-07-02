"""Pydantic v2 schemas for the M19 Quant Research Engine API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class PriceBarSchema(BaseModel):
    """OHLCV bar for a single session."""

    date: str = Field(..., description="ISO date string YYYY-MM-DD")
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: float = Field(default=0.0, ge=0)


class SignalSchema(BaseModel):
    """Trading signal for a single ticker on a single date."""

    date: str
    ticker: str
    signal_type: str = Field(..., description="LONG | SHORT | FLAT")
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Backtest schemas
# ---------------------------------------------------------------------------

class BacktestRunRequest(BaseModel):
    """Request body for POST /backtest/run."""

    strategy_name: str = Field(..., min_length=1)
    signals: List[SignalSchema] = Field(..., min_length=1)
    price_data: Dict[str, List[PriceBarSchema]] = Field(
        ..., description="Ticker → list of OHLCV bars"
    )
    initial_capital: float = Field(default=100_000.0, gt=0)
    commission_rate: float = Field(default=0.001, ge=0.0, le=0.05)
    slippage_bps: float = Field(default=5.0, ge=0.0)
    position_size_pct: float = Field(default=0.10, gt=0.0, le=1.0)
    allow_short: bool = False
    start_date: str = ""
    end_date: str = ""


class BacktestCompareRequest(BaseModel):
    """Request body for POST /backtest/compare."""

    backtest_ids: List[str] = Field(..., min_length=2)


class BacktestMetricsResponse(BaseModel):
    """Performance metrics for a completed backtest."""

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


class BacktestSummaryResponse(BaseModel):
    """Summary row for GET /backtest/list."""

    backtest_id: str
    strategy_name: str
    start_date: str
    end_date: str
    total_return: float
    sharpe_ratio: float
    num_trades: int


class TradeResponse(BaseModel):
    """Single trade record from a backtest."""

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


class EquityPointResponse(BaseModel):
    """Single point on the equity curve."""

    date: str
    equity: float
    cash: float
    positions_value: float
    drawdown: float
    drawdown_pct: float


class BacktestResultResponse(BaseModel):
    """Full backtest result with trades and equity curve."""

    backtest_id: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    metrics: BacktestMetricsResponse
    config: Dict[str, Any]


class MonthlyReturnsResponse(BaseModel):
    """Monthly return series from a backtest."""

    backtest_id: str
    monthly_returns: Dict[str, float]


# ---------------------------------------------------------------------------
# Execution simulation schemas
# ---------------------------------------------------------------------------

class SimOrderSchema(BaseModel):
    """Order to submit to the execution simulator."""

    ticker: str
    order_type: str = Field(default="MARKET", description="MARKET | LIMIT | STOP | STOP_LIMIT")
    side: str = Field(..., description="BUY | SELL")
    quantity: float = Field(..., gt=0)
    limit_price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    time_in_force: str = Field(default="DAY")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionSimulateRequest(BaseModel):
    """Request body for POST /execution/simulate."""

    order: SimOrderSchema
    market_price: float = Field(..., gt=0)
    market_volume: float = Field(default=1_000_000.0, gt=0)
    slippage_model: str = Field(default="FIXED_BPS", description="FIXED_BPS | VOLUME_WEIGHTED | SQRT")
    fixed_slippage_bps: float = Field(default=5.0, ge=0)
    commission_rate: float = Field(default=0.001, ge=0)
    adv_fraction: float = Field(default=0.01, gt=0, le=1.0)


class ExecutionBatchRequest(BaseModel):
    """Request body for POST /execution/batch."""

    orders: List[SimOrderSchema] = Field(..., min_length=1)
    prices: Dict[str, float]
    volumes: Dict[str, float] = Field(default_factory=dict)
    slippage_model: str = "FIXED_BPS"
    fixed_slippage_bps: float = 5.0
    commission_rate: float = 0.001


class FillModelRequest(BaseModel):
    """Request body for POST /execution/fill-model."""

    model_name: str
    fill_probability: float = Field(default=0.95, ge=0.0, le=1.0)
    partial_fill_min: float = Field(default=0.50, ge=0.0, le=1.0)
    partial_fill_max: float = Field(default=0.99, ge=0.0, le=1.0)
    adverse_selection_bps: float = Field(default=1.0, ge=0.0)


class ImplementationShortfallRequest(BaseModel):
    """Request body for POST /execution/implementation-shortfall."""

    order: SimOrderSchema
    decision_price: float = Field(..., gt=0)
    fill_price: float = Field(..., gt=0)
    fill_qty: float = Field(..., gt=0)
    market_impact: float = Field(default=0.0, ge=0)


class FillResponse(BaseModel):
    """Fill record from a simulation."""

    fill_id: str
    order_id: str
    ticker: str
    fill_price: float
    fill_qty: float
    remaining_qty: float
    slippage: float
    commission: float
    latency_us: int
    status: str
    market_impact: float


class SlippageReportResponse(BaseModel):
    """Aggregate slippage statistics."""

    num_fills: int
    total_slippage: float
    avg_slippage_bps: float
    max_slippage_bps: float
    total_commission: float
    total_market_impact: float
    fill_rate: float


# ---------------------------------------------------------------------------
# Walk-forward schemas
# ---------------------------------------------------------------------------

class SimpleSignalConfig(BaseModel):
    """Simple momentum signal config used by the WF signal generator."""

    lookback_bars: int = Field(default=20, ge=1)
    tickers: List[str] = Field(default_factory=list)


class WalkForwardRunRequest(BaseModel):
    """Request body for POST /walk-forward/run."""

    strategy_name: str
    price_data: Dict[str, List[PriceBarSchema]]
    signal_config: SimpleSignalConfig = Field(default_factory=SimpleSignalConfig)
    in_sample_bars: int = Field(default=252, ge=10)
    out_sample_bars: int = Field(default=63, ge=5)
    window_mode: str = Field(default="ROLLING", description="ROLLING | EXPANDING")
    initial_capital: float = Field(default=100_000.0, gt=0)
    commission_rate: float = Field(default=0.001, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    position_size_pct: float = Field(default=0.10, gt=0, le=1.0)


class WFWindowResponse(BaseModel):
    """Single walk-forward window result."""

    window_index: int
    in_sample_start: str
    in_sample_end: str
    out_sample_start: str
    out_sample_end: str
    in_sample_sharpe: float
    out_sample_sharpe: float
    in_sample_return: float
    out_sample_return: float
    efficiency: float
    backtest_id: str


class StabilityMetricsResponse(BaseModel):
    """Aggregate walk-forward stability statistics."""

    num_windows: int
    avg_oos_sharpe: float
    std_oos_sharpe: float
    avg_efficiency: float
    pct_windows_positive: float
    stability_score: float
    avg_oos_return: float
    degradation: float


class WalkForwardSummaryResponse(BaseModel):
    """Summary for GET /walk-forward/list."""

    run_id: str
    strategy_name: str
    num_windows: int
    stability_score: float
    avg_oos_sharpe: float


# ---------------------------------------------------------------------------
# Monte Carlo schemas
# ---------------------------------------------------------------------------

class MCBootstrapRequest(BaseModel):
    """Request body for POST /monte-carlo/bootstrap."""

    daily_returns: List[float] = Field(..., min_length=10)
    num_paths: int = Field(default=1000, ge=10, le=50_000)
    num_steps: int = Field(default=252, ge=5)
    initial_equity: float = Field(default=100_000.0, gt=0)
    block_size: int = Field(default=1, ge=1)


class MCGBMRequest(BaseModel):
    """Request body for POST /monte-carlo/gbm."""

    mean_daily_return: float = Field(default=0.0003)
    daily_volatility: float = Field(default=0.01, gt=0)
    num_paths: int = Field(default=1000, ge=10, le=50_000)
    num_steps: int = Field(default=252, ge=5)
    initial_equity: float = Field(default=100_000.0, gt=0)


class MCSensitivityRequest(BaseModel):
    """Request body for POST /monte-carlo/sensitivity."""

    daily_returns: List[float] = Field(..., min_length=10)
    drift_shocks: List[float] = Field(default_factory=lambda: [-0.001, 0.0, 0.001])
    vol_shocks: List[float] = Field(default_factory=lambda: [0.8, 1.0, 1.2])
    num_paths: int = Field(default=500, ge=10, le=10_000)
    num_steps: int = Field(default=252, ge=5)
    initial_equity: float = Field(default=100_000.0, gt=0)


class ConfidenceIntervalResponse(BaseModel):
    """Confidence interval for a simulated metric."""

    metric: str
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean: float
    std: float


class MCResultResponse(BaseModel):
    """Monte Carlo simulation summary."""

    simulation_id: str
    num_paths: int
    num_steps: int
    initial_equity: float
    var_95: float
    var_99: float
    expected_shortfall_95: float
    max_drawdown_p50: float
    max_drawdown_p95: float
    probability_of_ruin: float
    probability_of_profit: float
    method: str


class MCPathResponse(BaseModel):
    """Simulated equity path (subset of steps for charting)."""

    path_id: int
    final_equity: float
    total_return: float
    max_drawdown: float


# ---------------------------------------------------------------------------
# Factor model schemas
# ---------------------------------------------------------------------------

class FactorReturnSchema(BaseModel):
    """Single factor return observation."""

    date: str
    factor: str = Field(..., description="MARKET | SIZE | VALUE | MOMENTUM | QUALITY | LOW_VOL")
    return_value: float


class AddFactorReturnsRequest(BaseModel):
    """Request body for POST /factors/returns."""

    factor_returns: List[FactorReturnSchema] = Field(..., min_length=1)


class RegressRequest(BaseModel):
    """Request body for POST /factors/regress."""

    ticker: str
    security_returns: Dict[str, float] = Field(
        ..., description="Date → daily return fraction"
    )
    factors: List[str] = Field(
        default_factory=lambda: ["MARKET", "SIZE", "VALUE", "MOMENTUM"]
    )
    include_alpha: bool = True


class AttributionRequest(BaseModel):
    """Request body for POST /factors/attribution."""

    ticker: str
    total_return: float
    period_factor_returns: Dict[str, float] = Field(
        ..., description="Factor name → cumulative period return"
    )


class PortfolioBetaRequest(BaseModel):
    """Request body for POST /factors/portfolio-beta."""

    weights: Dict[str, float]
    factor: str = Field(default="MARKET")


class FactorCorrelationRequest(BaseModel):
    """Request body for POST /factors/correlations."""

    factors: List[str] = Field(
        default_factory=lambda: ["MARKET", "SIZE", "VALUE", "MOMENTUM"]
    )


class FactorExposureResponse(BaseModel):
    """Factor regression results for a security."""

    ticker: str
    alpha: float
    betas: Dict[str, float]
    t_stats: Dict[str, float]
    p_values: Dict[str, float]
    r_squared: float
    adj_r_squared: float
    tracking_error: float
    information_ratio: float


class FactorAttributionResponse(BaseModel):
    """Return attribution decomposition."""

    ticker: str
    total_return: float
    factor_contributions: Dict[str, float]
    alpha_contribution: float
    residual: float


class FactorCorrelationResponse(BaseModel):
    """Pairwise factor correlation."""

    factor_a: str
    factor_b: str
    correlation: float
    num_observations: int


# ---------------------------------------------------------------------------
# Optimization schemas
# ---------------------------------------------------------------------------

class WeightConstraintSchema(BaseModel):
    """Per-asset weight bound."""

    ticker: Optional[str] = None
    min_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    max_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    sector: Optional[str] = None


class MeanVarianceRequest(BaseModel):
    """Request body for POST /optimize/mean-variance."""

    tickers: List[str] = Field(..., min_length=2)
    expected_returns: Dict[str, float]
    covariance_matrix: Dict[str, Dict[str, float]]
    risk_aversion: float = Field(default=2.0, gt=0)
    constraints: List[WeightConstraintSchema] = Field(default_factory=list)
    risk_free_rate: float = Field(default=0.04, ge=0)


class MinVarianceRequest(BaseModel):
    """Request body for POST /optimize/min-variance."""

    tickers: List[str] = Field(..., min_length=2)
    covariance_matrix: Dict[str, Dict[str, float]]
    constraints: List[WeightConstraintSchema] = Field(default_factory=list)
    risk_free_rate: float = Field(default=0.04, ge=0)


class MaxSharpeRequest(BaseModel):
    """Request body for POST /optimize/max-sharpe."""

    tickers: List[str] = Field(..., min_length=2)
    expected_returns: Dict[str, float]
    covariance_matrix: Dict[str, Dict[str, float]]
    constraints: List[WeightConstraintSchema] = Field(default_factory=list)
    risk_free_rate: float = Field(default=0.04, ge=0)


class RiskParityRequest(BaseModel):
    """Request body for POST /optimize/risk-parity."""

    tickers: List[str] = Field(..., min_length=2)
    covariance_matrix: Dict[str, Dict[str, float]]
    target_risk_contributions: Optional[Dict[str, float]] = None
    risk_free_rate: float = Field(default=0.04, ge=0)


class FrontierRequest(BaseModel):
    """Request body for POST /optimize/frontier."""

    tickers: List[str] = Field(..., min_length=2)
    expected_returns: Dict[str, float]
    covariance_matrix: Dict[str, Dict[str, float]]
    n_points: int = Field(default=20, ge=3, le=200)
    risk_free_rate: float = Field(default=0.04, ge=0)
    constraints: List[WeightConstraintSchema] = Field(default_factory=list)


class FactorConstrainedRequest(BaseModel):
    """Request body for POST /optimize/factor-constrained."""

    tickers: List[str] = Field(..., min_length=2)
    expected_returns: Dict[str, float]
    covariance_matrix: Dict[str, Dict[str, float]]
    factor_constraints: Dict[str, List[float]] = Field(
        ..., description="Factor name → [min_beta, max_beta]"
    )
    risk_aversion: float = Field(default=2.0, gt=0)
    risk_free_rate: float = Field(default=0.04, ge=0)


class OptimizationResultResponse(BaseModel):
    """Portfolio optimisation result."""

    result_id: str
    optimization_type: str
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    max_weight: float
    min_weight: float
    num_assets: int
    risk_contributions: Dict[str, float]
    iterations: int


class FrontierPointResponse(BaseModel):
    """Single efficient frontier point."""

    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class FrontierResponse(BaseModel):
    """Full efficient frontier result."""

    n_points: int
    points: List[FrontierPointResponse]
    min_variance_point: Optional[FrontierPointResponse] = None
    max_sharpe_point: Optional[FrontierPointResponse] = None
