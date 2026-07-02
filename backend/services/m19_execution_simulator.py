"""Realistic execution simulation with market impact, latency, and partial fills."""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderType(str, Enum):
    """Type of order submitted to the simulator."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Lifecycle state of a simulated order."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class SlippageModel(str, Enum):
    """Market impact / slippage model variant."""

    FIXED_BPS = "FIXED_BPS"
    VOLUME_WEIGHTED = "VOLUME_WEIGHTED"
    SQRT = "SQRT"


@dataclass
class SimOrder:
    """Order submitted to the execution simulator.

    Attributes:
        order_id: Unique identifier.
        ticker: Target instrument symbol.
        order_type: MARKET, LIMIT, STOP, or STOP_LIMIT.
        side: BUY or SELL.
        quantity: Requested fill quantity.
        limit_price: Limit price (LIMIT / STOP_LIMIT only).
        stop_price: Stop trigger price (STOP / STOP_LIMIT only).
        time_in_force: IOC, DAY, or GTC.
        metadata: Arbitrary strategy context.
    """

    order_id: str
    ticker: str
    order_type: OrderType
    side: str
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fill:
    """Record of a (possibly partial) order fill.

    Attributes:
        fill_id: Unique fill identifier.
        order_id: ID of the originating order.
        ticker: Instrument symbol.
        fill_price: Actual execution price including slippage.
        fill_qty: Quantity filled in this leg.
        remaining_qty: Quantity still outstanding.
        slippage: Absolute price slippage applied.
        commission: Commission for this fill.
        latency_us: Simulated latency in microseconds.
        status: Final order status.
        market_impact: Estimated price impact fraction.
    """

    fill_id: str
    order_id: str
    ticker: str
    fill_price: float
    fill_qty: float
    remaining_qty: float
    slippage: float
    commission: float
    latency_us: int
    status: OrderStatus
    market_impact: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fill to a plain dict."""
        return {
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "ticker": self.ticker,
            "fill_price": self.fill_price,
            "fill_qty": self.fill_qty,
            "remaining_qty": self.remaining_qty,
            "slippage": self.slippage,
            "commission": self.commission,
            "latency_us": self.latency_us,
            "status": self.status.value,
            "market_impact": self.market_impact,
        }


@dataclass
class SlippageReport:
    """Aggregate slippage statistics across multiple fills.

    Attributes:
        num_fills: Total number of fills included.
        total_slippage: Sum of absolute slippage across all fills.
        avg_slippage_bps: Mean slippage expressed in basis points.
        max_slippage_bps: Worst single-fill slippage in basis points.
        total_commission: Total commissions paid.
        total_market_impact: Sum of market impact fractions.
        fill_rate: Fraction of ordered quantity that was filled.
    """

    num_fills: int
    total_slippage: float
    avg_slippage_bps: float
    max_slippage_bps: float
    total_commission: float
    total_market_impact: float
    fill_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return self.__dict__.copy()


@dataclass
class FillModel:
    """Parameterisation of the fill probability model.

    Attributes:
        model_name: Descriptive label.
        fill_probability: Base probability of a full fill per bar.
        partial_fill_min: Minimum fraction filled when a partial occurs.
        partial_fill_max: Maximum fraction filled when a partial occurs.
        adverse_selection_bps: Additional adverse-selection cost in bps.
    """

    model_name: str
    fill_probability: float = 0.95
    partial_fill_min: float = 0.50
    partial_fill_max: float = 0.99
    adverse_selection_bps: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return self.__dict__.copy()


class ExecutionSimulator:
    """Simulates realistic order execution including market impact, latency, and partial fills.

    Supports four order types (MARKET, LIMIT, STOP, STOP_LIMIT) and three
    slippage models (fixed bps, volume-weighted, square-root).

    Attributes:
        _fills: History of all fills produced.
        _orders: History of all orders submitted.
        _rng: Seeded random number generator for reproducibility.
    """

    def __init__(self, seed: int = 42) -> None:
        self._fills: List[Fill] = []
        self._orders: List[SimOrder] = []
        self._rng = random.Random(seed)

    def reset(self) -> None:
        """Clear all stored orders and fills."""
        self._fills.clear()
        self._orders.clear()

    def simulate(
        self,
        order: SimOrder,
        market_price: float,
        market_volume: float = 1_000_000.0,
        slippage_model: SlippageModel = SlippageModel.FIXED_BPS,
        fixed_slippage_bps: float = 5.0,
        commission_rate: float = 0.001,
        adv_fraction: float = 0.01,
        base_latency_us: int = 500,
        latency_std_us: int = 100,
    ) -> Fill:
        """Simulate the execution of a single order.

        LIMIT orders are filled only if the market price crosses the limit.
        STOP orders are triggered only when the stop price is breached.
        STOP_LIMIT require both the stop trigger and a favourable limit.

        Args:
            order: The order to simulate.
            market_price: Current mid-price of the instrument.
            market_volume: Average daily volume used for impact modelling.
            slippage_model: Which slippage model to apply.
            fixed_slippage_bps: Slippage in bps for FIXED_BPS model.
            commission_rate: Fractional commission per fill leg.
            adv_fraction: Maximum fraction of ADV per order (for SQRT model).
            base_latency_us: Mean simulated execution latency in microseconds.
            latency_std_us: Standard deviation of latency in microseconds.

        Returns:
            Fill record with execution details and status.
        """
        self._orders.append(order)

        latency = max(1, int(self._rng.gauss(base_latency_us, latency_std_us)))

        status = self._check_order_validity(order, market_price)
        if status != OrderStatus.PENDING:
            fill = Fill(
                fill_id=str(uuid.uuid4()),
                order_id=order.order_id,
                ticker=order.ticker,
                fill_price=market_price,
                fill_qty=0.0,
                remaining_qty=order.quantity,
                slippage=0.0,
                commission=0.0,
                latency_us=latency,
                status=status,
                market_impact=0.0,
            )
            self._fills.append(fill)
            return fill

        participation = min(1.0, order.quantity / max(market_volume, 1.0))
        impact = self._compute_market_impact(
            slippage_model, market_price, order.quantity, market_volume,
            fixed_slippage_bps, adv_fraction, participation,
        )
        is_buy = order.side.upper() == "BUY"
        slippage = impact * market_price
        if is_buy:
            fill_price = market_price + slippage
        else:
            fill_price = max(0.01, market_price - slippage)

        fill_qty, remaining, fill_status = self._compute_fill_qty(order, market_volume)
        commission = fill_qty * fill_price * commission_rate

        fill = Fill(
            fill_id=str(uuid.uuid4()),
            order_id=order.order_id,
            ticker=order.ticker,
            fill_price=round(fill_price, 6),
            fill_qty=round(fill_qty, 6),
            remaining_qty=round(remaining, 6),
            slippage=round(slippage, 6),
            commission=round(commission, 6),
            latency_us=latency,
            status=fill_status,
            market_impact=round(impact, 8),
        )
        self._fills.append(fill)
        return fill

    def _check_order_validity(self, order: SimOrder, market_price: float) -> OrderStatus:
        """Determine whether a limit/stop order can be triggered at current price.

        Args:
            order: The order to check.
            market_price: Current market price.

        Returns:
            PENDING if execution is possible, CANCELLED or REJECTED otherwise.
        """
        if order.order_type == OrderType.LIMIT:
            lp = order.limit_price or 0.0
            if order.side.upper() == "BUY" and market_price > lp:
                return OrderStatus.CANCELLED
            if order.side.upper() == "SELL" and market_price < lp:
                return OrderStatus.CANCELLED
        elif order.order_type == OrderType.STOP:
            sp = order.stop_price or 0.0
            if order.side.upper() == "BUY" and market_price < sp:
                return OrderStatus.CANCELLED
            if order.side.upper() == "SELL" and market_price > sp:
                return OrderStatus.CANCELLED
        elif order.order_type == OrderType.STOP_LIMIT:
            sp = order.stop_price or 0.0
            lp = order.limit_price or 0.0
            if order.side.upper() == "BUY" and market_price < sp:
                return OrderStatus.CANCELLED
            if order.side.upper() == "SELL" and market_price > sp:
                return OrderStatus.CANCELLED
            if order.side.upper() == "BUY" and market_price > lp:
                return OrderStatus.CANCELLED
            if order.side.upper() == "SELL" and market_price < lp:
                return OrderStatus.CANCELLED
        if order.quantity <= 0:
            return OrderStatus.REJECTED
        return OrderStatus.PENDING

    def _compute_market_impact(
        self,
        model: SlippageModel,
        price: float,
        qty: float,
        adv: float,
        fixed_bps: float,
        adv_fraction: float,
        participation: float,
    ) -> float:
        """Compute the price impact fraction for an order.

        Args:
            model: Which impact model to use.
            price: Current price of the instrument.
            qty: Order quantity.
            adv: Average daily volume.
            fixed_bps: Fixed slippage for FIXED_BPS model.
            adv_fraction: ADV-fraction cap for SQRT model.
            participation: Quantity / ADV ratio.

        Returns:
            Fractional price impact (e.g. 0.0005 = 5 bps).
        """
        if model == SlippageModel.FIXED_BPS:
            return fixed_bps / 10_000.0
        if model == SlippageModel.VOLUME_WEIGHTED:
            return (participation * 10.0) / 10_000.0
        sigma = 0.02
        pct = min(qty / max(adv, 1.0), adv_fraction)
        return sigma * math.sqrt(pct)

    def _compute_fill_qty(
        self, order: SimOrder, market_volume: float
    ) -> tuple[float, float, OrderStatus]:
        """Determine how much of the order is filled.

        Args:
            order: The order being simulated.
            market_volume: Available market liquidity.

        Returns:
            Tuple of (fill_qty, remaining_qty, OrderStatus).
        """
        max_fillable = market_volume * 0.10
        if order.quantity <= max_fillable:
            return order.quantity, 0.0, OrderStatus.FILLED
        fill_pct = self._rng.uniform(0.50, 0.99)
        fill_qty = order.quantity * fill_pct
        remaining = order.quantity - fill_qty
        return fill_qty, remaining, OrderStatus.PARTIAL

    def get_slippage_report(self) -> SlippageReport:
        """Aggregate slippage statistics across all fills in history.

        Returns:
            SlippageReport with totals and averages.
        """
        filled = [f for f in self._fills if f.fill_qty > 0]
        if not filled:
            return SlippageReport(
                num_fills=0,
                total_slippage=0.0,
                avg_slippage_bps=0.0,
                max_slippage_bps=0.0,
                total_commission=0.0,
                total_market_impact=0.0,
                fill_rate=0.0,
            )
        slippages_bps = [
            (f.slippage / f.fill_price * 10_000.0) if f.fill_price > 0 else 0.0
            for f in filled
        ]
        total_ordered = sum(
            (o.quantity for o in self._orders), 0.0
        )
        total_filled = sum(f.fill_qty for f in filled)
        return SlippageReport(
            num_fills=len(filled),
            total_slippage=round(sum(f.slippage * f.fill_qty for f in filled), 6),
            avg_slippage_bps=round(sum(slippages_bps) / len(slippages_bps), 4),
            max_slippage_bps=round(max(slippages_bps), 4),
            total_commission=round(sum(f.commission for f in filled), 6),
            total_market_impact=round(sum(f.market_impact for f in filled), 8),
            fill_rate=round(total_filled / total_ordered, 4) if total_ordered > 0 else 0.0,
        )

    def build_fill_model(
        self,
        model_name: str,
        fill_probability: float = 0.95,
        partial_fill_min: float = 0.50,
        partial_fill_max: float = 0.99,
        adverse_selection_bps: float = 1.0,
    ) -> FillModel:
        """Construct a named fill probability model.

        Args:
            model_name: Descriptive label for this model.
            fill_probability: Probability of a complete fill per bar.
            partial_fill_min: Minimum fill fraction when a partial occurs.
            partial_fill_max: Maximum fill fraction when a partial occurs.
            adverse_selection_bps: Extra cost from adverse selection in bps.

        Returns:
            FillModel dataclass.
        """
        return FillModel(
            model_name=model_name,
            fill_probability=fill_probability,
            partial_fill_min=partial_fill_min,
            partial_fill_max=partial_fill_max,
            adverse_selection_bps=adverse_selection_bps,
        )

    def simulate_batch(
        self,
        orders: List[SimOrder],
        prices: Dict[str, float],
        volumes: Optional[Dict[str, float]] = None,
        slippage_model: SlippageModel = SlippageModel.FIXED_BPS,
        fixed_slippage_bps: float = 5.0,
        commission_rate: float = 0.001,
    ) -> List[Fill]:
        """Simulate a batch of orders against current market snapshot.

        Args:
            orders: List of orders to execute.
            prices: Current mid-price per ticker.
            volumes: Average daily volume per ticker.
            slippage_model: Slippage model to apply to all orders.
            fixed_slippage_bps: Fixed slippage for FIXED_BPS model.
            commission_rate: Fractional commission per fill.

        Returns:
            List of Fill records in submission order.
        """
        _vols = volumes or {}
        fills: List[Fill] = []
        for order in orders:
            price = prices.get(order.ticker, 0.0)
            volume = _vols.get(order.ticker, 1_000_000.0)
            if price <= 0:
                continue
            fills.append(self.simulate(
                order,
                market_price=price,
                market_volume=volume,
                slippage_model=slippage_model,
                fixed_slippage_bps=fixed_slippage_bps,
                commission_rate=commission_rate,
            ))
        return fills

    def get_fill_history(self) -> List[Dict[str, Any]]:
        """Return serialised history of all fills.

        Returns:
            List of fill dicts.
        """
        return [f.to_dict() for f in self._fills]

    def get_order_history(self) -> List[Dict[str, Any]]:
        """Return serialised history of all submitted orders.

        Returns:
            List of order dicts.
        """
        return [
            {
                "order_id": o.order_id,
                "ticker": o.ticker,
                "order_type": o.order_type.value,
                "side": o.side,
                "quantity": o.quantity,
                "limit_price": o.limit_price,
                "stop_price": o.stop_price,
                "time_in_force": o.time_in_force,
            }
            for o in self._orders
        ]

    def compute_implementation_shortfall(
        self,
        order: SimOrder,
        decision_price: float,
        fill: Fill,
    ) -> Dict[str, float]:
        """Compute implementation shortfall relative to a decision-time price.

        Args:
            order: The original order.
            decision_price: Price at the time the decision was made.
            fill: The resulting fill record.

        Returns:
            Dict with shortfall_bps, delay_cost_bps, market_impact_bps.
        """
        if decision_price <= 0 or fill.fill_qty <= 0:
            return {"shortfall_bps": 0.0, "delay_cost_bps": 0.0, "market_impact_bps": 0.0}
        direction = 1.0 if order.side.upper() == "BUY" else -1.0
        shortfall = direction * (fill.fill_price - decision_price) / decision_price * 10_000.0
        impact_bps = fill.market_impact * 10_000.0
        delay_cost = max(0.0, shortfall - impact_bps)
        return {
            "shortfall_bps": round(shortfall, 4),
            "delay_cost_bps": round(delay_cost, 4),
            "market_impact_bps": round(impact_bps, 4),
        }
