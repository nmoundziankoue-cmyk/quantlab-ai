"""ORM models for M5 Institutional Trading & Execution Engine.

Entities:
  Order          — the canonical order record with full lifecycle state
  OrderAuditLog  — immutable audit trail; one row per state transition
  Execution      — individual fills (a single order may have many partials)
  PaperAccount   — virtual broker account for paper trading
  PaperPosition  — current open positions inside a paper account
  PaperTrade     — historical fill records for a paper account
  BrokerConnection — stored broker authentication/configuration
  Alert          — event-driven alert definitions and trigger records

All PKs are UUIDs.  Every table has created_at; mutable tables have
updated_at.  JSONB is used for flexible payloads (tags, credentials,
trigger conditions) to avoid schema churn.

Enum naming follows <ClassName>Enum convention to avoid collision with
existing ``TransactionType`` and ``Signal`` enums elsewhere in the project.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class OrderTypeEnum(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    BRACKET = "BRACKET"
    OCO = "OCO"        # One Cancels Other (pair of limit/stop orders)
    OTO = "OTO"        # One Triggers Other (trigger → submit secondary)


class OrderSideEnum(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"


class TimeInForceEnum(str, enum.Enum):
    DAY = "DAY"
    GTC = "GTC"   # Good Till Cancelled
    IOC = "IOC"   # Immediate Or Cancel
    FOK = "FOK"   # Fill Or Kill


class OrderStatusEnum(str, enum.Enum):
    PENDING = "PENDING"          # created, not yet submitted
    SUBMITTED = "SUBMITTED"      # sent to broker / paper engine
    ACCEPTED = "ACCEPTED"        # broker acknowledged
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TrailTypeEnum(str, enum.Enum):
    AMOUNT = "AMOUNT"
    PERCENT = "PERCENT"


class LinkTypeEnum(str, enum.Enum):
    NONE = "NONE"
    BRACKET_PARENT = "BRACKET_PARENT"
    BRACKET_PROFIT = "BRACKET_PROFIT"
    BRACKET_STOP = "BRACKET_STOP"
    OCO_PRIMARY = "OCO_PRIMARY"
    OCO_SECONDARY = "OCO_SECONDARY"
    OTO_TRIGGER = "OTO_TRIGGER"
    OTO_SECONDARY = "OTO_SECONDARY"


class ExecAlgoEnum(str, enum.Enum):
    NONE = "NONE"
    TWAP = "TWAP"
    VWAP = "VWAP"
    POV = "POV"          # Percentage of Volume
    ICEBERG = "ICEBERG"
    ARRIVAL = "ARRIVAL"  # Arrival Price / Implementation Shortfall
    ADAPTIVE = "ADAPTIVE"


class BrokerTypeEnum(str, enum.Enum):
    PAPER = "PAPER"
    ALPACA = "ALPACA"
    IBKR = "IBKR"
    BINANCE = "BINANCE"
    KRAKEN = "KRAKEN"
    OANDA = "OANDA"
    POLYGON = "POLYGON"


class BrokerStatusEnum(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    ERROR = "ERROR"


class AuditEventEnum(str, enum.Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    MODIFIED = "MODIFIED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SIMULATION = "SIMULATION"


class AlertTypeEnum(str, enum.Enum):
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    MARGIN_WARNING = "MARGIN_WARNING"
    RISK_LIMIT = "RISK_LIMIT"
    PORTFOLIO_LIMIT = "PORTFOLIO_LIMIT"
    DRAWDOWN_ALERT = "DRAWDOWN_ALERT"
    PNL_ALERT = "PNL_ALERT"
    POSITION_LIMIT = "POSITION_LIMIT"
    PRICE_ALERT = "PRICE_ALERT"


class CommissionTypeEnum(str, enum.Enum):
    FLAT = "FLAT"           # fixed $ per trade
    PER_SHARE = "PER_SHARE"  # $ per share
    PERCENT = "PERCENT"      # % of trade value


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


class Order(Base):
    """Canonical order record spanning the full lifecycle from creation to fill.

    Both real-broker and paper-trading orders use this table.  Exactly one of
    ``portfolio_id``, ``paper_account_id`` must be non-NULL for any given order
    (enforced at the service layer, not the DB layer to allow bulk loading).
    """

    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_portfolio_status", "portfolio_id", "status"),
        Index("ix_orders_paper_account_status", "paper_account_id", "status"),
        Index("ix_orders_ticker_created", "ticker", "created_at"),
        Index("ix_orders_basket", "basket_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner context — one of these is set
    portfolio_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    paper_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    broker_connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("broker_connections.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Basket / multi-leg grouping
    basket_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    parent_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,  # not a FK to avoid circular constraints
    )
    link_type: Mapped[LinkTypeEnum] = mapped_column(
        SAEnum(LinkTypeEnum, name="link_type_enum", create_constraint=True),
        nullable=False,
        default=LinkTypeEnum.NONE,
    )

    # Instrument
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False, default="EQUITY")

    # Order specification
    order_type: Mapped[OrderTypeEnum] = mapped_column(
        SAEnum(OrderTypeEnum, name="order_type_enum", create_constraint=True),
        nullable=False,
    )
    side: Mapped[OrderSideEnum] = mapped_column(
        SAEnum(OrderSideEnum, name="order_side_enum", create_constraint=True),
        nullable=False,
    )
    time_in_force: Mapped[TimeInForceEnum] = mapped_column(
        SAEnum(TimeInForceEnum, name="time_in_force_enum", create_constraint=True),
        nullable=False,
        default=TimeInForceEnum.DAY,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=Decimal("0"))

    # Price fields
    limit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    stop_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    trail_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    trail_type: Mapped[Optional[TrailTypeEnum]] = mapped_column(
        SAEnum(TrailTypeEnum, name="trail_type_enum", create_constraint=True),
        nullable=True,
    )
    average_fill_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)

    # Execution algorithm
    exec_algo: Mapped[ExecAlgoEnum] = mapped_column(
        SAEnum(ExecAlgoEnum, name="exec_algo_enum", create_constraint=True),
        nullable=False,
        default=ExecAlgoEnum.NONE,
    )
    exec_algo_params: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # State
    status: Mapped[OrderStatusEnum] = mapped_column(
        SAEnum(OrderStatusEnum, name="order_status_enum", create_constraint=True),
        nullable=False,
        default=OrderStatusEnum.PENDING,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cost tracking
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    estimated_commission: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    total_slippage: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))

    # Metadata
    strategy_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)

    # Timestamps
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    executions: Mapped[List["Execution"]] = relationship("Execution", back_populates="order", cascade="all, delete-orphan")
    audit_log: Mapped[List["OrderAuditLog"]] = relationship("OrderAuditLog", back_populates="order", cascade="all, delete-orphan")
    child_orders: Mapped[List["Order"]] = relationship("Order", foreign_keys=[parent_order_id])

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} ticker={self.ticker} {self.side.value} "
            f"{self.quantity} @ {self.order_type.value} status={self.status.value}>"
        )


# ---------------------------------------------------------------------------
# OrderAuditLog
# ---------------------------------------------------------------------------


class OrderAuditLog(Base):
    """Immutable audit trail — one row per state transition of an Order.

    Never updated after creation; only inserted.
    """

    __tablename__ = "order_audit_log"
    __table_args__ = (Index("ix_audit_log_order_created", "order_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[AuditEventEnum] = mapped_column(
        SAEnum(AuditEventEnum, name="audit_event_enum", create_constraint=True),
        nullable=False,
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="audit_log")


# ---------------------------------------------------------------------------
# Execution (Fill)
# ---------------------------------------------------------------------------


class Execution(Base):
    """A single fill event for an order.  An order may have many partial fills.

    Stores the definitive record of what was traded: price, quantity, cost.
    """

    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_order_time", "order_id", "execution_time"),
        Index("ix_executions_ticker_time", "ticker", "execution_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)  # BUY / SELL
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    fill_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    market_price_at_fill: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    slippage: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))

    venue: Mapped[str] = mapped_column(String(50), nullable=False, default="PAPER")
    broker: Mapped[str] = mapped_column(String(50), nullable=False, default="PAPER")
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    execution_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="executions")

    @property
    def gross_value(self) -> Decimal:
        return self.quantity * self.fill_price

    @property
    def net_value(self) -> Decimal:
        return self.gross_value - self.commission


# ---------------------------------------------------------------------------
# Paper Account
# ---------------------------------------------------------------------------


class PaperAccount(Base):
    """Virtual broker account for paper (simulated) trading.

    Cash and equity are tracked in real time as orders fill.
    """

    __tablename__ = "paper_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Cash tracking
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    buying_power: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Aggregate portfolio values (updated on each fill)
    total_market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_equity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)  # cash + mkt_value
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    # Commission and cost config
    commission_type: Mapped[CommissionTypeEnum] = mapped_column(
        SAEnum(CommissionTypeEnum, name="commission_type_enum", create_constraint=True),
        nullable=False,
        default=CommissionTypeEnum.FLAT,
    )
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("1.00"))
    min_commission: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    slippage_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=10)  # basis points

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    positions: Mapped[List["PaperPosition"]] = relationship("PaperPosition", back_populates="account", cascade="all, delete-orphan")
    trades: Mapped[List["PaperTrade"]] = relationship("PaperTrade", back_populates="account", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Paper Position
# ---------------------------------------------------------------------------


class PaperPosition(Base):
    """Current open position inside a paper account (AVCO cost basis)."""

    __tablename__ = "paper_positions"
    __table_args__ = (Index("ix_paper_positions_account_ticker", "account_id", "ticker", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    # market_value and unrealized_pnl are derived; stored as a cache
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    account: Mapped["PaperAccount"] = relationship("PaperAccount", back_populates="positions")


# ---------------------------------------------------------------------------
# Paper Trade
# ---------------------------------------------------------------------------


class PaperTrade(Base):
    """Historical fill record for paper trading.  Immutable after creation."""

    __tablename__ = "paper_trades"
    __table_args__ = (Index("ix_paper_trades_account_time", "account_id", "trade_time"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )

    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    fill_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    market_price_at_fill: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    slippage_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    strategy_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    trade_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account: Mapped["PaperAccount"] = relationship("PaperAccount", back_populates="trades")


# ---------------------------------------------------------------------------
# Broker Connection
# ---------------------------------------------------------------------------


class BrokerConnection(Base):
    """Stored broker authentication configuration.

    Credentials are stored as JSONB.  In production, the credentials blob
    would be encrypted at rest (e.g. via pgcrypto or application-level AES).
    This model represents the interface contract; actual encryption is an
    infrastructure concern.
    """

    __tablename__ = "broker_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    broker: Mapped[BrokerTypeEnum] = mapped_column(
        SAEnum(BrokerTypeEnum, name="broker_type_enum", create_constraint=True),
        nullable=False,
    )
    is_paper: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[BrokerStatusEnum] = mapped_column(
        SAEnum(BrokerStatusEnum, name="broker_status_enum", create_constraint=True),
        nullable=False,
        default=BrokerStatusEnum.DISCONNECTED,
    )
    credentials: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------


class Alert(Base):
    """Event-driven alert definition.

    ``trigger_condition`` is a flexible JSONB blob describing when this
    alert fires.  Examples:
      {"metric": "drawdown_pct", "threshold": 10.0, "operator": "gt"}
      {"metric": "pnl_usd", "threshold": -5000.0, "operator": "lt"}
      {"metric": "order_status", "value": "REJECTED"}
    """

    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_portfolio", "portfolio_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    alert_type: Mapped[AlertTypeEnum] = mapped_column(
        SAEnum(AlertTypeEnum, name="alert_type_enum", create_constraint=True),
        nullable=False,
    )
    portfolio_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=True,
    )
    paper_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        nullable=True,
    )
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    trigger_condition: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trigger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
