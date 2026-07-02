"""M17 Pydantic v2 request / response schemas for the Institutional Trading &
Portfolio Management platform."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.order_management import OrderType, OrderSide, TimeInForce, TrailType, PegType
from services.execution_engine import SlippageModel, MarketImpactModel, ExecutionBenchmark
from services.risk_limits import LimitType, LimitSeverity
from services.tca import TCABenchmark
from services.broker_management import (
    AssetClass, CommissionType, BrokerStatus, RoutingStrategy,
)
from services.performance_attribution import AttributionModel


# ---------------------------------------------------------------------------
# OMS — Order Management
# ---------------------------------------------------------------------------

class OrderSubmitRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    order_type: OrderType
    side: OrderSide
    quantity: float = Field(gt=0)
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    trail_amount: Optional[float] = Field(default=None, gt=0)
    trail_type: Optional[TrailType] = None
    peg_type: Optional[PegType] = None
    iceberg_visible_qty: Optional[float] = Field(default=None, gt=0)
    expires_at: Optional[datetime] = None
    broker_id: Optional[str] = None
    strategy_tag: Optional[str] = None
    notes: Optional[str] = None
    client_order_id: Optional[str] = None
    order_params: Dict[str, Any] = Field(default_factory=dict)


class OrderAmendRequest(BaseModel):
    quantity: Optional[float] = Field(default=None, gt=0)
    limit_price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    trail_amount: Optional[float] = Field(default=None, gt=0)
    expires_at: Optional[datetime] = None


class BracketOrderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    side: OrderSide
    quantity: float = Field(gt=0)
    entry_price: Optional[float] = Field(default=None, gt=0)
    take_profit_price: float = Field(gt=0)
    stop_loss_price: float = Field(gt=0)
    entry_order_type: OrderType = OrderType.LIMIT
    broker_id: Optional[str] = None
    strategy_tag: Optional[str] = None


class OCOOrderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    side: OrderSide
    quantity: float = Field(gt=0)
    limit_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    broker_id: Optional[str] = None
    strategy_tag: Optional[str] = None


class TWAPRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    side: OrderSide
    total_quantity: float = Field(gt=0)
    n_slices: int = Field(ge=1)
    limit_price: Optional[float] = Field(default=None, gt=0)
    broker_id: Optional[str] = None
    strategy_tag: Optional[str] = None


class VWAPRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    side: OrderSide
    total_quantity: float = Field(gt=0)
    volume_profile: List[float] = Field(min_length=1)
    limit_price: Optional[float] = Field(default=None, gt=0)
    broker_id: Optional[str] = None
    strategy_tag: Optional[str] = None


class TrailingStopUpdateRequest(BaseModel):
    current_price: float = Field(gt=0)


class FillRequest(BaseModel):
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    venue: str = "PAPER"
    commission: float = Field(default=0.0, ge=0)
    fees: float = Field(default=0.0, ge=0)


class OrderQueryRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: Optional[str] = None
    status: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    strategy_tag: Optional[str] = None


# ---------------------------------------------------------------------------
# Execution Engine
# ---------------------------------------------------------------------------

class SlippageRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    order_quantity: float = Field(gt=0)
    arrival_price: float = Field(gt=0)
    adv: float = Field(gt=0)
    volatility: float = Field(gt=0)
    model: SlippageModel = SlippageModel.SQRT
    fixed_bps: float = Field(default=10.0, ge=0)


class MarketImpactRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    order_quantity: float = Field(gt=0)
    adv: float = Field(gt=0)
    price: float = Field(gt=0)
    volatility: float = Field(gt=0)
    model: MarketImpactModel = MarketImpactModel.SQRT
    sigma_perm: float = Field(default=0.1, gt=0)
    sigma_temp: float = Field(default=0.1, gt=0)


class ISRequest(BaseModel):
    decision_price: float = Field(gt=0)
    arrival_price: float = Field(gt=0)
    avg_fill_price: float = Field(gt=0)
    total_quantity: float = Field(gt=0)
    filled_quantity: float = Field(gt=0)
    spread_bps: float = Field(default=5.0, ge=0)
    is_buy: bool = True


class VWAPComputeRequest(BaseModel):
    prices: List[float] = Field(min_length=1)
    volumes: List[float] = Field(min_length=1)


class TWAPComputeRequest(BaseModel):
    prices: List[float] = Field(min_length=1)


class SimFillRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1)
    side: str
    quantity: float = Field(gt=0)
    arrival_price: float = Field(gt=0)
    adv: float = Field(gt=0)
    volatility: float = Field(gt=0)
    spread_bps: Optional[float] = Field(default=None, ge=0)
    slippage_model: Optional[SlippageModel] = None
    fill_rate: float = Field(default=1.0, ge=0, le=1)


class ExecQualityRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str
    side: str
    avg_fill_price: float = Field(gt=0)
    benchmark_price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    commission_usd: float = Field(default=0.0, ge=0)
    benchmark_type: ExecutionBenchmark = ExecutionBenchmark.ARRIVAL


# ---------------------------------------------------------------------------
# Portfolio Accounting
# ---------------------------------------------------------------------------

class DepositRequest(BaseModel):
    amount: float = Field(gt=0)
    description: str = "Deposit"


class WithdrawRequest(BaseModel):
    amount: float = Field(gt=0)
    description: str = "Withdrawal"


class BookTradeRequest(BaseModel):
    ticker: str = Field(min_length=1)
    side: str
    quantity: float = Field(gt=0)
    avg_price: float = Field(gt=0)
    commission: float = Field(default=0.0, ge=0)
    fees: float = Field(default=0.0, ge=0)
    reference_id: Optional[str] = None


class SplitRequest(BaseModel):
    ticker: str = Field(min_length=1)
    ratio: float = Field(gt=0)


class DividendRequest(BaseModel):
    ticker: str = Field(min_length=1)
    per_share_amount: float = Field(gt=0)


class MarkToMarketRequest(BaseModel):
    prices: Dict[str, float]


class NAVRequest(BaseModel):
    prices: Dict[str, float]


# ---------------------------------------------------------------------------
# Position Engine
# ---------------------------------------------------------------------------

class OpenPositionRequest(BaseModel):
    ticker: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class ClosePositionRequest(BaseModel):
    ticker: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    lot_id: Optional[str] = None


class ExposureRequest(BaseModel):
    prices: Dict[str, float]
    nav: float = Field(gt=0)


class PositionRequest(BaseModel):
    ticker: str
    market_price: float = Field(gt=0)


# ---------------------------------------------------------------------------
# Risk Limits
# ---------------------------------------------------------------------------

class AddLimitRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    limit_type: LimitType
    hard_limit: float = Field(gt=0)
    soft_limit: Optional[float] = Field(default=None, gt=0)
    description: str = ""
    asset_filter: Dict[str, Any] = Field(default_factory=dict)


class PreTradeCheckRequest(BaseModel):
    ticker: str = Field(min_length=1)
    side: str
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    sector: Optional[str] = None
    country: Optional[str] = None
    asset_beta: float = 1.0
    nav: float = Field(gt=0)
    cash: float = Field(default=0.0, ge=0)
    current_positions: Dict[str, float] = Field(default_factory=dict)
    current_market_values: Dict[str, float] = Field(default_factory=dict)
    sector_weights: Dict[str, float] = Field(default_factory=dict)
    country_weights: Dict[str, float] = Field(default_factory=dict)
    gross_leverage: float = Field(default=0.0, ge=0)
    net_leverage: float = 0.0
    portfolio_beta: float = 0.0
    portfolio_var_pct: float = Field(default=0.0, ge=0)
    current_drawdown: float = 0.0
    daily_turnover: float = Field(default=0.0, ge=0)
    top_position_weight: float = Field(default=0.0, ge=0)


# ---------------------------------------------------------------------------
# Trade Analytics
# ---------------------------------------------------------------------------

class TradeRecordRequest(BaseModel):
    trade_id: str
    ticker: str
    side: str
    quantity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)
    entry_datetime: datetime
    exit_datetime: datetime
    commission: float = Field(default=0.0, ge=0)
    pnl: float = 0.0
    sector: Optional[str] = None
    strategy_tag: Optional[str] = None


class PortfolioPerformanceRequest(BaseModel):
    returns: List[float] = Field(min_length=1)
    benchmark_returns: Optional[List[float]] = None
    risk_free: float = Field(default=0.0, ge=0)
    periods_per_year: int = Field(default=252, ge=1)


class KellyRequest(BaseModel):
    win_rate: float = Field(ge=0, le=1)
    avg_win: float = Field(gt=0)
    avg_loss: float = Field(gt=0)


# ---------------------------------------------------------------------------
# TCA
# ---------------------------------------------------------------------------

class TCATradeRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    trade_id: str
    ticker: str
    side: str
    quantity: float = Field(gt=0)
    decision_price: float = Field(gt=0)
    arrival_price: float = Field(gt=0)
    avg_fill_price: float = Field(gt=0)
    commission_usd: float = Field(default=0.0, ge=0)
    spread_bps: float = Field(default=5.0, ge=0)
    benchmark_price: float = Field(gt=0)
    benchmark_type: TCABenchmark = TCABenchmark.ARRIVAL
    fill_rate: float = Field(default=1.0, ge=0, le=1)


class RecordTCATradeRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    trade_id: str
    ticker: str
    side: str
    quantity: float = Field(gt=0)
    arrival_price: float = Field(gt=0)
    avg_fill_price: float = Field(gt=0)
    decision_price: Optional[float] = Field(default=None, gt=0)
    commission_usd: float = Field(default=0.0, ge=0)
    spread_bps: float = Field(default=5.0, ge=0)
    broker_id: Optional[str] = None
    broker_name: Optional[str] = None
    fill_rate: float = Field(default=1.0, ge=0, le=1)


# ---------------------------------------------------------------------------
# Broker Management
# ---------------------------------------------------------------------------

class BrokerRegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    supported_asset_classes: List[str] = Field(default_factory=lambda: ["EQUITY"])
    supported_exchanges: List[str] = Field(default_factory=list)
    notes: str = ""


class CommissionScheduleRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    broker_id: str
    asset_class: AssetClass = AssetClass.EQUITY
    commission_type: CommissionType = CommissionType.PER_SHARE
    base_rate: float = Field(gt=0)
    minimum_per_trade: float = Field(default=0.0, ge=0)
    maximum_pct_of_trade: float = Field(default=0.0, ge=0)


class RoutingRuleRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    broker_id: str
    asset_class: AssetClass = AssetClass.EQUITY
    routing_strategy: RoutingStrategy = RoutingStrategy.BEST_EXECUTION
    exchange: Optional[str] = None
    order_size_min: float = Field(default=0.0, ge=0)
    order_size_max: Optional[float] = None
    priority: int = Field(default=100, ge=1)


class RouteOrderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    asset_class: AssetClass = AssetClass.EQUITY
    exchange: Optional[str] = None
    order_value: float = Field(gt=0)


class CommissionComputeRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    broker_id: str
    asset_class: AssetClass = AssetClass.EQUITY
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class BrokerExecutionRequest(BaseModel):
    broker_id: str
    ticker: str
    quantity: float = Field(gt=0)
    arrival_price: float = Field(gt=0)
    avg_fill_price: float = Field(gt=0)
    fill_rate: float = Field(default=1.0, ge=0, le=1)
    latency_ms: float = Field(default=50.0, ge=0)


# ---------------------------------------------------------------------------
# Paper Trading Simulator
# ---------------------------------------------------------------------------

class SimMarketOrderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1)
    side: OrderSide
    quantity: float = Field(gt=0)
    strategy_tag: Optional[str] = None


class SimLimitOrderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1)
    side: OrderSide
    quantity: float = Field(gt=0)
    limit_price: float = Field(gt=0)
    strategy_tag: Optional[str] = None


class PriceUpdateRequest(BaseModel):
    prices: Dict[str, float]


class SimResetRequest(BaseModel):
    initial_cash: Optional[float] = Field(default=None, gt=0)


# ---------------------------------------------------------------------------
# Performance Attribution
# ---------------------------------------------------------------------------

class HoldingRequest(BaseModel):
    category: str
    portfolio_weight: float = Field(ge=0, le=1)
    benchmark_weight: float = Field(ge=0, le=1)
    portfolio_return: float
    benchmark_return: float


class BrinsonRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    holdings: List[HoldingRequest] = Field(min_length=1)
    benchmark_total_return: float
    model: AttributionModel = AttributionModel.BRINSON


class FactorExposureRequest(BaseModel):
    factor_name: str
    portfolio_exposure: float
    benchmark_exposure: float
    factor_return: float


class FactorAttributionRequest(BaseModel):
    factors: List[FactorExposureRequest] = Field(min_length=1)


class CurrencyHoldingRequest(BaseModel):
    currency: str
    portfolio_weight: float = Field(ge=0, le=1)
    benchmark_weight: float = Field(ge=0, le=1)
    currency_return: float


class FullAttributionRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sector_holdings: List[HoldingRequest] = Field(min_length=1)
    benchmark_total_return: float
    country_holdings: Optional[List[HoldingRequest]] = None
    currency_holdings: Optional[List[CurrencyHoldingRequest]] = None
    factor_exposures: Optional[List[FactorExposureRequest]] = None
    active_return_series: Optional[List[float]] = None
    periods_per_year: int = Field(default=252, ge=1)
    model: AttributionModel = AttributionModel.BRINSON


class IRRequest(BaseModel):
    active_returns: List[float] = Field(min_length=2)
    periods_per_year: int = Field(default=252, ge=1)
