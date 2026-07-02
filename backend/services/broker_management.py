"""M17 — Broker Management Engine (pure Python, in-memory).

Institutional broker registry: commission schedules (flat, per-share,
tiered), supported exchanges / asset classes, routing rules, execution
quality history, and broker ranking.

No SQLAlchemy, no external libraries — stdlib + dataclasses only.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CommissionType(str, Enum):
    FLAT = "FLAT"
    PER_SHARE = "PER_SHARE"
    PERCENT = "PERCENT"
    TIERED = "TIERED"


class BrokerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    OPTIONS = "OPTIONS"
    FUTURES = "FUTURES"
    FIXED_INCOME = "FIXED_INCOME"
    FX = "FX"
    CRYPTO = "CRYPTO"
    ETF = "ETF"


class RoutingStrategy(str, Enum):
    BEST_EXECUTION = "BEST_EXECUTION"
    LOWEST_COST = "LOWEST_COST"
    FASTEST_FILL = "FASTEST_FILL"
    PREFERRED = "PREFERRED"
    DARKPOOL = "DARKPOOL"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CommissionTier:
    """A single tier in a tiered commission schedule.

    Args:
        min_quantity: Minimum quantity for this tier.
        max_quantity: Maximum quantity (None = unlimited).
        rate: Commission rate for this tier.
    """

    min_quantity: float
    max_quantity: Optional[float]
    rate: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "min_quantity": self.min_quantity,
            "max_quantity": self.max_quantity,
            "rate": self.rate,
        }


@dataclass
class CommissionSchedule:
    """Commission schedule for a broker and asset class.

    Args:
        schedule_id: Unique identifier.
        asset_class: Asset class this schedule applies to.
        commission_type: Pricing model.
        base_rate: Standard rate (per share, percentage, or flat).
        minimum_per_trade: Minimum commission per trade.
        maximum_pct_of_trade: Cap as percentage of trade value (0 = no cap).
        tiers: Tiered rates for TIERED type.
        currency: Currency of commission charges.
    """

    schedule_id: str
    asset_class: AssetClass
    commission_type: CommissionType
    base_rate: float
    minimum_per_trade: float = 0.0
    maximum_pct_of_trade: float = 0.0
    tiers: List[CommissionTier] = field(default_factory=list)
    currency: str = "USD"

    def compute(self, quantity: float, price: float) -> float:
        """Compute commission for a trade.

        Args:
            quantity: Number of shares / contracts.
            price: Execution price per share / contract.

        Returns:
            Commission in USD.
        """
        trade_value = quantity * price
        if self.commission_type == CommissionType.FLAT:
            raw = self.base_rate
        elif self.commission_type == CommissionType.PER_SHARE:
            raw = quantity * self.base_rate
        elif self.commission_type == CommissionType.PERCENT:
            raw = trade_value * self.base_rate
        elif self.commission_type == CommissionType.TIERED:
            raw = self._tiered(quantity)
        else:
            raw = 0.0

        commission = max(raw, self.minimum_per_trade)
        if self.maximum_pct_of_trade > 0:
            cap = trade_value * self.maximum_pct_of_trade
            commission = min(commission, cap)
        return commission

    def _tiered(self, quantity: float) -> float:
        if not self.tiers:
            return quantity * self.base_rate
        for tier in sorted(self.tiers, key=lambda t: t.min_quantity, reverse=True):
            if quantity >= tier.min_quantity:
                return quantity * tier.rate
        return quantity * self.base_rate

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "schedule_id": self.schedule_id,
            "asset_class": self.asset_class.value,
            "commission_type": self.commission_type.value,
            "base_rate": self.base_rate,
            "minimum_per_trade": self.minimum_per_trade,
            "maximum_pct_of_trade": self.maximum_pct_of_trade,
            "tiers": [t.to_dict() for t in self.tiers],
            "currency": self.currency,
        }


@dataclass
class RoutingRule:
    """A routing rule mapping criteria to a broker.

    Args:
        rule_id: Unique identifier.
        asset_class: Asset class this rule applies to.
        exchange: Exchange filter (None = any exchange).
        order_size_min: Minimum order value for this rule.
        order_size_max: Maximum order value for this rule (None = unlimited).
        routing_strategy: How to route within matching criteria.
        priority: Lower number = higher priority.
    """

    rule_id: str
    asset_class: AssetClass
    exchange: Optional[str]
    order_size_min: float
    order_size_max: Optional[float]
    routing_strategy: RoutingStrategy
    priority: int = 100

    def matches(
        self,
        asset_class: AssetClass,
        exchange: Optional[str],
        order_value: float,
    ) -> bool:
        """Check whether this rule applies to a given order.

        Args:
            asset_class: Asset class of the order.
            exchange: Target exchange.
            order_value: Value of the order in USD.

        Returns:
            True if the rule applies.
        """
        if self.asset_class != asset_class:
            return False
        if self.exchange and exchange and self.exchange != exchange:
            return False
        if order_value < self.order_size_min:
            return False
        if self.order_size_max is not None and order_value > self.order_size_max:
            return False
        return True

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "rule_id": self.rule_id,
            "asset_class": self.asset_class.value,
            "exchange": self.exchange,
            "order_size_min": self.order_size_min,
            "order_size_max": self.order_size_max,
            "routing_strategy": self.routing_strategy.value,
            "priority": self.priority,
        }


@dataclass
class ExecutionRecord:
    """A historical execution record for quality scoring.

    Args:
        record_id: Unique identifier.
        ticker: Instrument.
        quantity: Trade size.
        arrival_price: Market price at arrival.
        avg_fill_price: Realised fill price.
        fill_rate: Fraction of order filled.
        latency_ms: Execution latency in milliseconds.
        timestamp: UTC timestamp.
    """

    record_id: str
    ticker: str
    quantity: float
    arrival_price: float
    avg_fill_price: float
    fill_rate: float
    latency_ms: float
    timestamp: datetime

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "record_id": self.record_id,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "arrival_price": self.arrival_price,
            "avg_fill_price": round(self.avg_fill_price, 6),
            "fill_rate": round(self.fill_rate, 6),
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BrokerRecord:
    """Full broker registration record.

    Args:
        broker_id: Unique identifier.
        name: Human-readable broker name.
        status: ACTIVE / INACTIVE / SUSPENDED.
        supported_asset_classes: Asset classes this broker handles.
        supported_exchanges: Exchanges this broker can route to.
        commission_schedules: Commission schedules by asset class.
        routing_rules: Ordered routing rules.
        execution_history: Recent execution records.
        quality_score: Composite quality score (0–100).
        notes: Free-text notes.
        created_at: Registration datetime.
    """

    broker_id: str
    name: str
    status: BrokerStatus
    supported_asset_classes: List[AssetClass]
    supported_exchanges: List[str]
    commission_schedules: List[CommissionSchedule]
    routing_rules: List[RoutingRule]
    execution_history: List[ExecutionRecord]
    quality_score: float
    notes: str
    created_at: datetime

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "broker_id": self.broker_id,
            "name": self.name,
            "status": self.status.value,
            "supported_asset_classes": [a.value for a in self.supported_asset_classes],
            "supported_exchanges": list(self.supported_exchanges),
            "commission_schedules": [s.to_dict() for s in self.commission_schedules],
            "routing_rules": [r.to_dict() for r in self.routing_rules],
            "quality_score": round(self.quality_score, 2),
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "execution_record_count": len(self.execution_history),
        }


# ---------------------------------------------------------------------------
# Broker Management Engine
# ---------------------------------------------------------------------------

class BrokerManagementEngine:
    """Institutional broker registry and routing engine (pure Python).

    Manages broker registrations, commission schedules, routing rules,
    execution quality history, and broker ranking.
    """

    def __init__(self) -> None:
        self._brokers: Dict[str, BrokerRecord] = {}

    # ------------------------------------------------------------------
    # Broker registration
    # ------------------------------------------------------------------

    def register_broker(
        self,
        name: str,
        *,
        broker_id: Optional[str] = None,
        supported_asset_classes: Optional[List[AssetClass]] = None,
        supported_exchanges: Optional[List[str]] = None,
        notes: str = "",
    ) -> BrokerRecord:
        """Register a new broker.

        Args:
            name: Human-readable broker name.
            broker_id: Optional explicit ID; auto-generated if None.
            supported_asset_classes: Asset classes the broker handles.
            supported_exchanges: Exchange venues the broker can route to.
            notes: Free-text notes.

        Returns:
            Created BrokerRecord.

        Raises:
            ValueError: If name is empty.
        """
        if not name:
            raise ValueError("broker name cannot be empty")
        bid = broker_id or str(uuid.uuid4())
        broker = BrokerRecord(
            broker_id=bid,
            name=name,
            status=BrokerStatus.ACTIVE,
            supported_asset_classes=supported_asset_classes or [AssetClass.EQUITY],
            supported_exchanges=supported_exchanges or [],
            commission_schedules=[],
            routing_rules=[],
            execution_history=[],
            quality_score=50.0,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        self._brokers[bid] = broker
        return broker

    def deactivate_broker(self, broker_id: str) -> BrokerRecord:
        """Mark a broker as INACTIVE.

        Args:
            broker_id: Broker identifier.

        Returns:
            Updated BrokerRecord.

        Raises:
            KeyError: If broker not found.
        """
        broker = self._get_or_raise(broker_id)
        broker.status = BrokerStatus.INACTIVE
        return broker

    def suspend_broker(self, broker_id: str) -> BrokerRecord:
        """Mark a broker as SUSPENDED (cannot receive any orders).

        Args:
            broker_id: Broker identifier.

        Returns:
            Updated BrokerRecord.
        """
        broker = self._get_or_raise(broker_id)
        broker.status = BrokerStatus.SUSPENDED
        return broker

    # ------------------------------------------------------------------
    # Commission schedules
    # ------------------------------------------------------------------

    def add_commission_schedule(
        self,
        broker_id: str,
        asset_class: AssetClass,
        commission_type: CommissionType,
        base_rate: float,
        minimum_per_trade: float = 0.0,
        maximum_pct_of_trade: float = 0.0,
        tiers: Optional[List[Tuple[float, Optional[float], float]]] = None,
    ) -> CommissionSchedule:
        """Add a commission schedule to a broker.

        Args:
            broker_id: Broker identifier.
            asset_class: Asset class for this schedule.
            commission_type: Pricing model.
            base_rate: Base commission rate.
            minimum_per_trade: Minimum commission per trade.
            maximum_pct_of_trade: Maximum as a fraction of trade value.
            tiers: Optional list of (min_qty, max_qty, rate) tuples for TIERED type.

        Returns:
            Created CommissionSchedule.
        """
        broker = self._get_or_raise(broker_id)
        schedule = CommissionSchedule(
            schedule_id=str(uuid.uuid4()),
            asset_class=asset_class,
            commission_type=commission_type,
            base_rate=base_rate,
            minimum_per_trade=minimum_per_trade,
            maximum_pct_of_trade=maximum_pct_of_trade,
            tiers=[CommissionTier(mn, mx, r) for mn, mx, r in (tiers or [])],
        )
        broker.commission_schedules.append(schedule)
        return schedule

    def compute_commission(
        self,
        broker_id: str,
        asset_class: AssetClass,
        quantity: float,
        price: float,
    ) -> float:
        """Compute commission for a trade using the broker's schedule.

        Args:
            broker_id: Broker identifier.
            asset_class: Asset class of the trade.
            quantity: Trade quantity.
            price: Execution price.

        Returns:
            Commission in USD.

        Raises:
            KeyError: If broker not found.
            ValueError: If no matching commission schedule exists.
        """
        broker = self._get_or_raise(broker_id)
        for sched in broker.commission_schedules:
            if sched.asset_class == asset_class:
                return sched.compute(quantity, price)
        raise ValueError(f"No commission schedule for {asset_class.value} at broker {broker_id!r}")

    # ------------------------------------------------------------------
    # Routing rules
    # ------------------------------------------------------------------

    def add_routing_rule(
        self,
        broker_id: str,
        asset_class: AssetClass,
        routing_strategy: RoutingStrategy = RoutingStrategy.BEST_EXECUTION,
        exchange: Optional[str] = None,
        order_size_min: float = 0.0,
        order_size_max: Optional[float] = None,
        priority: int = 100,
    ) -> RoutingRule:
        """Add a routing rule to a broker.

        Args:
            broker_id: Broker identifier.
            asset_class: Asset class filter.
            routing_strategy: Execution strategy.
            exchange: Exchange filter (None = any).
            order_size_min: Minimum order value.
            order_size_max: Maximum order value.
            priority: Rule priority (lower = higher priority).

        Returns:
            Created RoutingRule.
        """
        broker = self._get_or_raise(broker_id)
        rule = RoutingRule(
            rule_id=str(uuid.uuid4()),
            asset_class=asset_class,
            exchange=exchange,
            order_size_min=order_size_min,
            order_size_max=order_size_max,
            routing_strategy=routing_strategy,
            priority=priority,
        )
        broker.routing_rules.append(rule)
        broker.routing_rules.sort(key=lambda r: r.priority)
        return rule

    def route_order(
        self,
        asset_class: AssetClass,
        exchange: Optional[str],
        order_value: float,
    ) -> Optional[BrokerRecord]:
        """Find the best active broker for an order using routing rules.

        Evaluates all ACTIVE brokers in quality-score order and returns the
        first broker whose routing rules match the order criteria.

        Args:
            asset_class: Asset class of the order.
            exchange: Target exchange (None = any).
            order_value: Order value in USD.

        Returns:
            Best matching BrokerRecord or None if no match found.
        """
        active_brokers = [b for b in self._brokers.values() if b.status == BrokerStatus.ACTIVE]
        active_brokers.sort(key=lambda b: b.quality_score, reverse=True)

        for broker in active_brokers:
            if asset_class not in broker.supported_asset_classes:
                continue
            if exchange and broker.supported_exchanges and exchange not in broker.supported_exchanges:
                continue
            for rule in broker.routing_rules:
                if rule.matches(asset_class, exchange, order_value):
                    return broker
        return None

    # ------------------------------------------------------------------
    # Execution quality
    # ------------------------------------------------------------------

    def record_execution(
        self,
        broker_id: str,
        ticker: str,
        quantity: float,
        arrival_price: float,
        avg_fill_price: float,
        fill_rate: float = 1.0,
        latency_ms: float = 50.0,
    ) -> ExecutionRecord:
        """Record an execution result for quality tracking.

        Args:
            broker_id: Executing broker.
            ticker: Instrument.
            quantity: Trade size.
            arrival_price: Market price at arrival.
            avg_fill_price: Realised fill price.
            fill_rate: Fraction of order filled.
            latency_ms: Execution latency.

        Returns:
            Created ExecutionRecord.
        """
        broker = self._get_or_raise(broker_id)
        rec = ExecutionRecord(
            record_id=str(uuid.uuid4()),
            ticker=ticker.upper(),
            quantity=quantity,
            arrival_price=arrival_price,
            avg_fill_price=avg_fill_price,
            fill_rate=fill_rate,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
        )
        broker.execution_history.append(rec)
        self._update_quality_score(broker)
        return rec

    def _update_quality_score(self, broker: BrokerRecord) -> None:
        """Recompute the broker's quality score from execution history."""
        history = broker.execution_history
        if not history:
            return
        avg_fill = sum(r.fill_rate for r in history) / len(history)
        avg_slip = []
        for r in history:
            if r.arrival_price > 0:
                slip = abs(r.avg_fill_price - r.arrival_price) / r.arrival_price * 10_000.0
                avg_slip.append(slip)
        mean_slip = sum(avg_slip) / len(avg_slip) if avg_slip else 0.0
        avg_lat = sum(r.latency_ms for r in history) / len(history)
        score = (avg_fill * 50.0) + max(0.0, 30.0 - mean_slip * 2.0) + max(0.0, 20.0 - avg_lat / 50.0)
        broker.quality_score = max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Broker ranking
    # ------------------------------------------------------------------

    def rank_brokers(
        self,
        asset_class: Optional[AssetClass] = None,
    ) -> List[Tuple[int, BrokerRecord]]:
        """Return brokers ranked by quality score.

        Args:
            asset_class: Optional filter by asset class.

        Returns:
            List of (rank, BrokerRecord) tuples sorted by quality score.
        """
        brokers = list(self._brokers.values())
        if asset_class:
            brokers = [b for b in brokers if asset_class in b.supported_asset_classes]
        brokers.sort(key=lambda b: b.quality_score, reverse=True)
        return [(i + 1, b) for i, b in enumerate(brokers)]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_broker(self, broker_id: str) -> Optional[BrokerRecord]:
        """Retrieve a broker by ID.

        Args:
            broker_id: Broker identifier.

        Returns:
            BrokerRecord or None.
        """
        return self._brokers.get(broker_id)

    def get_broker_by_name(self, name: str) -> Optional[BrokerRecord]:
        """Retrieve a broker by name (case-insensitive).

        Args:
            name: Broker name.

        Returns:
            BrokerRecord or None.
        """
        name_lower = name.lower()
        for b in self._brokers.values():
            if b.name.lower() == name_lower:
                return b
        return None

    def all_brokers(self, status: Optional[BrokerStatus] = None) -> List[BrokerRecord]:
        """Return all brokers, optionally filtered by status.

        Args:
            status: Status filter.

        Returns:
            List of BrokerRecord sorted by name.
        """
        result = list(self._brokers.values())
        if status:
            result = [b for b in result if b.status == status]
        return sorted(result, key=lambda b: b.name)

    def statistics(self) -> Dict:
        """Return aggregate statistics across the broker registry.

        Returns:
            Dict with counts and average quality score.
        """
        brokers = list(self._brokers.values())
        by_status: Dict[str, int] = {}
        for b in brokers:
            by_status[b.status.value] = by_status.get(b.status.value, 0) + 1
        avg_score = sum(b.quality_score for b in brokers) / len(brokers) if brokers else 0.0
        return {
            "total": len(brokers),
            "by_status": by_status,
            "avg_quality_score": round(avg_score, 2),
        }

    def _get_or_raise(self, broker_id: str) -> BrokerRecord:
        broker = self._brokers.get(broker_id)
        if broker is None:
            raise KeyError(f"Broker {broker_id!r} not found")
        return broker


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_broker_management: Optional[BrokerManagementEngine] = None


def get_broker_management_engine() -> BrokerManagementEngine:
    """Return the singleton BrokerManagementEngine instance.

    Returns:
        Shared BrokerManagementEngine instance.
    """
    global _default_broker_management
    if _default_broker_management is None:
        _default_broker_management = BrokerManagementEngine()
    return _default_broker_management
