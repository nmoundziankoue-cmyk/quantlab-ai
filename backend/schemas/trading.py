"""Pydantic v2 request / response schemas for M5 Trading & Execution Engine."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.trading import (
    AlertTypeEnum,
    AuditEventEnum,
    BrokerStatusEnum,
    BrokerTypeEnum,
    CommissionTypeEnum,
    ExecAlgoEnum,
    LinkTypeEnum,
    OrderSideEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    TimeInForceEnum,
    TrailTypeEnum,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POS_DEC = Field(gt=Decimal("0"))
_NON_NEG_DEC = Field(ge=Decimal("0"), default=Decimal("0"))


# ---------------------------------------------------------------------------
# Order Schemas
# ---------------------------------------------------------------------------


class OrderCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    asset_class: str = Field(default="EQUITY", max_length=20)
    order_type: OrderTypeEnum
    side: OrderSideEnum
    time_in_force: TimeInForceEnum = TimeInForceEnum.DAY
    quantity: Decimal = Field(gt=Decimal("0"))
    limit_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    stop_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    trail_amount: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    trail_type: Optional[TrailTypeEnum] = None
    exec_algo: ExecAlgoEnum = ExecAlgoEnum.NONE
    exec_algo_params: Dict[str, Any] = Field(default_factory=dict)
    strategy_tag: Optional[str] = Field(default=None, max_length=100)
    tags: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None

    # For OCO/OTO/Bracket: link to related order (set after primary is created)
    link_type: LinkTypeEnum = LinkTypeEnum.NONE
    parent_order_id: Optional[uuid.UUID] = None
    basket_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate_prices(self) -> "OrderCreate":
        ot = self.order_type
        if ot in (OrderTypeEnum.LIMIT, OrderTypeEnum.STOP_LIMIT, OrderTypeEnum.BRACKET):
            if self.limit_price is None:
                raise ValueError(f"{ot} orders require limit_price")
        if ot in (OrderTypeEnum.STOP, OrderTypeEnum.STOP_LIMIT, OrderTypeEnum.BRACKET):
            if self.stop_price is None:
                raise ValueError(f"{ot} orders require stop_price")
        if ot == OrderTypeEnum.TRAILING_STOP:
            if self.trail_amount is None:
                raise ValueError("TRAILING_STOP orders require trail_amount")
            if self.trail_type is None:
                raise ValueError("TRAILING_STOP orders require trail_type")
        return self


class OrderModify(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    quantity: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    limit_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    stop_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    trail_amount: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    time_in_force: Optional[TimeInForceEnum] = None
    notes: Optional[str] = None


class OrderPreviewRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    order_type: OrderTypeEnum
    side: OrderSideEnum
    quantity: Decimal = Field(gt=Decimal("0"))
    limit_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    stop_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))


class OrderPreviewResponse(BaseModel):
    ticker: str
    side: str
    quantity: Decimal
    order_type: str
    estimated_price: Optional[Decimal]
    estimated_value: Optional[Decimal]
    estimated_commission: Decimal
    estimated_slippage: Decimal
    estimated_total_cost: Optional[Decimal]
    market_price: Decimal
    buying_power_required: Optional[Decimal]
    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    portfolio_id: Optional[uuid.UUID]
    paper_account_id: Optional[uuid.UUID]
    broker_connection_id: Optional[uuid.UUID]
    basket_id: Optional[uuid.UUID]
    parent_order_id: Optional[uuid.UUID]
    linked_order_id: Optional[uuid.UUID]
    link_type: str
    ticker: str
    asset_class: str
    order_type: str
    side: str
    time_in_force: str
    quantity: Decimal
    filled_quantity: Decimal
    limit_price: Optional[Decimal]
    stop_price: Optional[Decimal]
    trail_amount: Optional[Decimal]
    trail_type: Optional[str]
    average_fill_price: Optional[Decimal]
    exec_algo: str
    exec_algo_params: Dict[str, Any]
    status: str
    rejection_reason: Optional[str]
    commission: Decimal
    estimated_commission: Decimal
    total_slippage: Decimal
    strategy_tag: Optional[str]
    tags: Dict[str, Any]
    notes: Optional[str]
    broker_order_id: Optional[str]
    submitted_at: Optional[datetime]
    filled_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Audit Log Schemas
# ---------------------------------------------------------------------------


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    order_id: uuid.UUID
    event_type: str
    from_status: Optional[str]
    to_status: Optional[str]
    payload: Dict[str, Any]
    message: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Execution Schemas
# ---------------------------------------------------------------------------


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    ticker: str
    side: str
    quantity: Decimal
    fill_price: Decimal
    market_price_at_fill: Optional[Decimal]
    slippage: Decimal
    commission: Decimal
    venue: str
    broker: str
    latency_ms: Optional[int]
    execution_time: datetime
    created_at: datetime


class ExecutionListResponse(BaseModel):
    executions: List[ExecutionResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Paper Account Schemas
# ---------------------------------------------------------------------------


class PaperAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    initial_cash: Decimal = Field(gt=Decimal("0"))
    commission_type: CommissionTypeEnum = CommissionTypeEnum.FLAT
    commission_rate: Decimal = Field(default=Decimal("1.00"), ge=Decimal("0"))
    min_commission: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    slippage_bps: int = Field(default=10, ge=0, le=500)


class PaperAccountUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    commission_type: Optional[CommissionTypeEnum] = None
    commission_rate: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    min_commission: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    slippage_bps: Optional[int] = Field(default=None, ge=0, le=500)


class PaperPositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    ticker: str
    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    last_price: Optional[Decimal]
    updated_at: datetime


class PaperTradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    order_id: Optional[uuid.UUID]
    execution_id: Optional[uuid.UUID]
    ticker: str
    side: str
    quantity: Decimal
    fill_price: Decimal
    market_price_at_fill: Decimal
    commission: Decimal
    slippage_cost: Decimal
    realized_pnl: Decimal
    strategy_tag: Optional[str]
    trade_time: datetime


class PaperAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    currency: str
    initial_cash: Decimal
    cash_balance: Decimal
    buying_power: Decimal
    total_market_value: Decimal
    total_equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    commission_type: str
    commission_rate: Decimal
    min_commission: Decimal
    slippage_bps: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaperAccountSummary(PaperAccountResponse):
    positions: List[PaperPositionResponse] = Field(default_factory=list)
    open_orders_count: int = 0
    total_trades: int = 0
    total_commission_paid: Decimal = Decimal("0")
    total_slippage_cost: Decimal = Decimal("0")
    return_pct: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Basket / Bulk Order Schemas
# ---------------------------------------------------------------------------


class BasketOrderItem(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ticker: str = Field(min_length=1, max_length=20)
    side: OrderSideEnum
    quantity: Decimal = Field(gt=Decimal("0"))
    order_type: OrderTypeEnum = OrderTypeEnum.MARKET
    limit_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    strategy_tag: Optional[str] = None


class BasketOrderCreate(BaseModel):
    items: List[BasketOrderItem] = Field(min_length=1)
    time_in_force: TimeInForceEnum = TimeInForceEnum.DAY
    notes: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)


class BasketOrderResponse(BaseModel):
    basket_id: uuid.UUID
    orders: List[OrderResponse]
    total_items: int
    submitted_at: datetime


# ---------------------------------------------------------------------------
# Execution Algorithm Schemas
# ---------------------------------------------------------------------------


class AlgoScheduleItem(BaseModel):
    slice_index: int
    quantity: Decimal
    delay_minutes: float
    target_price: Optional[Decimal] = None
    label: str


class AlgoScheduleResponse(BaseModel):
    algo: str
    ticker: str
    total_quantity: Decimal
    total_slices: int
    estimated_duration_minutes: float
    schedule: List[AlgoScheduleItem]
    params: Dict[str, Any]


class TWAPRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=Decimal("0"))
    duration_minutes: int = Field(default=60, ge=5, le=390)
    n_slices: int = Field(default=12, ge=2, le=100)
    current_price: Decimal = Field(gt=Decimal("0"))


class VWAPRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=Decimal("0"))
    duration_minutes: int = Field(default=60, ge=5, le=390)
    volume_profile: List[float] = Field(min_length=2)
    current_price: Decimal = Field(gt=Decimal("0"))


class POVRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=Decimal("0"))
    participation_rate: float = Field(default=0.10, gt=0.0, le=0.50)
    avg_volume_per_minute: float = Field(gt=0.0)
    current_price: Decimal = Field(gt=Decimal("0"))


class IcebergRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    total_quantity: Decimal = Field(gt=Decimal("0"))
    display_quantity: Decimal = Field(gt=Decimal("0"))
    limit_price: Decimal = Field(gt=Decimal("0"))
    refill_delay_minutes: float = Field(default=1.0, gt=0.0)


# ---------------------------------------------------------------------------
# Broker Connection Schemas
# ---------------------------------------------------------------------------


class BrokerConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    broker: BrokerTypeEnum
    is_paper: bool = False
    credentials: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)


class BrokerConnectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    credentials: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class BrokerConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    name: str
    broker: str
    is_paper: bool
    is_active: bool
    status: str
    last_heartbeat: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Alert Schemas
# ---------------------------------------------------------------------------


class AlertCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(min_length=1, max_length=100)
    alert_type: AlertTypeEnum
    portfolio_id: Optional[uuid.UUID] = None
    paper_account_id: Optional[uuid.UUID] = None
    ticker: Optional[str] = Field(default=None, max_length=20)
    trigger_condition: Dict[str, Any]
    message_template: str = Field(min_length=1)

    @field_validator("trigger_condition")
    @classmethod
    def validate_trigger(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if "metric" not in v and "value" not in v:
            raise ValueError("trigger_condition must contain at least 'metric' or 'value'")
        return v


class AlertUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    trigger_condition: Optional[Dict[str, Any]] = None
    message_template: Optional[str] = None
    is_active: Optional[bool] = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    name: str
    alert_type: str
    portfolio_id: Optional[uuid.UUID]
    paper_account_id: Optional[uuid.UUID]
    ticker: Optional[str]
    trigger_condition: Dict[str, Any]
    message_template: str
    is_active: bool
    is_triggered: bool
    trigger_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Execution Analytics Schemas
# ---------------------------------------------------------------------------


class ExecutionAnalyticsSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    total_trades: int
    total_volume: Decimal
    fill_ratio: float  # filled_qty / ordered_qty overall
    avg_slippage_bps: float
    avg_commission_per_trade: Decimal
    total_commission: Decimal
    total_slippage_cost: Decimal
    avg_latency_ms: Optional[float]
    win_rate: float
    avg_holding_period_days: Optional[float]
    turnover: Decimal
    # Per-ticker breakdown
    by_ticker: List[Dict[str, Any]] = Field(default_factory=list)
    # Slippage histogram buckets (bps)
    slippage_distribution: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionQualityReport(BaseModel):
    order_id: uuid.UUID
    ticker: str
    side: str
    ordered_qty: Decimal
    filled_qty: Decimal
    avg_fill_price: Decimal
    arrival_price: Optional[Decimal]
    implementation_shortfall_bps: Optional[float]
    vwap_benchmark: Optional[Decimal]
    vwap_slippage_bps: Optional[float]
    fill_ratio: float
    total_commission: Decimal
    execution_time_ms: Optional[int]
    quality_score: float  # 0-100


# ---------------------------------------------------------------------------
# Streaming / WebSocket Schemas
# ---------------------------------------------------------------------------


class StreamSubscribeRequest(BaseModel):
    channels: List[str] = Field(
        description="Channels to subscribe to: 'orders', 'executions', 'positions', 'prices:{TICKER}'"
    )


class StreamEvent(BaseModel):
    event_type: str
    channel: str
    payload: Dict[str, Any]
    timestamp: str


# ---------------------------------------------------------------------------
# Trade Blotter Schemas
# ---------------------------------------------------------------------------


class BlotterRow(BaseModel):
    execution_id: uuid.UUID
    order_id: uuid.UUID
    trade_date: str
    execution_time: datetime
    ticker: str
    side: str
    quantity: Decimal
    fill_price: Decimal
    gross_value: Decimal
    commission: Decimal
    slippage: Decimal
    net_value: Decimal
    venue: str
    broker: str
    strategy_tag: Optional[str]
    notes: Optional[str]
    order_type: str
    latency_ms: Optional[int]
    market_price_at_fill: Optional[Decimal]
    execution_quality_bps: Optional[float]


class BlotterResponse(BaseModel):
    rows: List[BlotterRow]
    total: int
    page: int
    page_size: int
    summary: Dict[str, Any]
