"""M17 — Execution Engine (pure Python, in-memory).

Institutional EMS providing deterministic execution simulation,
slippage/spread/latency modelling, execution quality scoring,
VWAP/TWAP/Arrival benchmarks, implementation shortfall, and
market impact estimation (Almgren-Chriss-inspired square-root model).

No SQLAlchemy, no external libraries — stdlib + math only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SlippageModel(str, Enum):
    LINEAR = "LINEAR"
    SQRT = "SQRT"
    VOLUME_ADJ = "VOLUME_ADJ"
    FIXED_BPS = "FIXED_BPS"


class ExecutionBenchmark(str, Enum):
    ARRIVAL = "ARRIVAL"
    VWAP = "VWAP"
    TWAP = "TWAP"
    CLOSE = "CLOSE"
    OPEN = "OPEN"


class MarketImpactModel(str, Enum):
    LINEAR = "LINEAR"
    SQRT = "SQRT"
    ALMGREN_CHRISS = "ALMGREN_CHRISS"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SlippageEstimate:
    """Estimated execution slippage.

    Args:
        model: The slippage model used.
        order_quantity: Requested quantity.
        adv: Average daily volume (shares/contracts).
        volatility: Annualised volatility of the instrument.
        arrival_price: Mid price at order arrival.
        estimated_slippage_bps: Expected slippage in basis points.
        estimated_slippage_pct: Expected slippage as fraction.
        estimated_cost_usd: Dollar cost of slippage.
    """

    model: SlippageModel
    order_quantity: float
    adv: float
    volatility: float
    arrival_price: float
    estimated_slippage_bps: float
    estimated_slippage_pct: float
    estimated_cost_usd: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "model": self.model.value,
            "order_quantity": self.order_quantity,
            "adv": self.adv,
            "volatility": self.volatility,
            "arrival_price": self.arrival_price,
            "estimated_slippage_bps": round(self.estimated_slippage_bps, 4),
            "estimated_slippage_pct": round(self.estimated_slippage_pct, 6),
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }


@dataclass
class MarketImpactEstimate:
    """Market impact decomposed into permanent and temporary components.

    Args:
        model: The market impact model used.
        permanent_impact_bps: Permanent price impact in basis points.
        temporary_impact_bps: Temporary (intraday) price impact in basis points.
        total_impact_bps: Total impact in basis points.
        permanent_impact_usd: Dollar value of permanent impact.
        temporary_impact_usd: Dollar value of temporary impact.
        total_impact_usd: Total dollar impact.
        participation_rate: Order size as fraction of ADV.
    """

    model: MarketImpactModel
    permanent_impact_bps: float
    temporary_impact_bps: float
    total_impact_bps: float
    permanent_impact_usd: float
    temporary_impact_usd: float
    total_impact_usd: float
    participation_rate: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "model": self.model.value,
            "permanent_impact_bps": round(self.permanent_impact_bps, 4),
            "temporary_impact_bps": round(self.temporary_impact_bps, 4),
            "total_impact_bps": round(self.total_impact_bps, 4),
            "permanent_impact_usd": round(self.permanent_impact_usd, 4),
            "temporary_impact_usd": round(self.temporary_impact_usd, 4),
            "total_impact_usd": round(self.total_impact_usd, 4),
            "participation_rate": round(self.participation_rate, 6),
        }


@dataclass
class VWAPResult:
    """Computed VWAP from a price/volume series.

    Args:
        vwap: Volume-weighted average price.
        total_volume: Total volume in the period.
        n_bars: Number of price bars used.
        price_range: (min_price, max_price) over the period.
    """

    vwap: float
    total_volume: float
    n_bars: int
    price_range: Tuple[float, float]

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "vwap": round(self.vwap, 6),
            "total_volume": self.total_volume,
            "n_bars": self.n_bars,
            "price_min": self.price_range[0],
            "price_max": self.price_range[1],
        }


@dataclass
class TWAPResult:
    """Computed TWAP from a price series.

    Args:
        twap: Simple arithmetic average of prices.
        n_bars: Number of price observations used.
        price_range: (min_price, max_price) over the period.
    """

    twap: float
    n_bars: int
    price_range: Tuple[float, float]

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "twap": round(self.twap, 6),
            "n_bars": self.n_bars,
            "price_min": self.price_range[0],
            "price_max": self.price_range[1],
        }


@dataclass
class ImplementationShortfall:
    """Implementation shortfall decomposition.

    IS = Decision Price - Avg Fill Price (for BUY; inverted for SELL).

    Components:
        delay_cost: Cost of waiting between decision and arrival.
        market_impact: Cost of price moving due to order execution.
        spread_cost: Half-spread paid per transaction.
        opportunity_cost: Cost of unfilled portion (residual risk).
        total_is_bps: Total IS in basis points.
        total_is_usd: Total IS in dollars.
    """

    decision_price: float
    arrival_price: float
    avg_fill_price: float
    filled_quantity: float
    total_quantity: float
    delay_cost_bps: float
    market_impact_bps: float
    spread_cost_bps: float
    opportunity_cost_bps: float
    total_is_bps: float
    total_is_usd: float
    fill_rate: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "decision_price": self.decision_price,
            "arrival_price": self.arrival_price,
            "avg_fill_price": self.avg_fill_price,
            "filled_quantity": self.filled_quantity,
            "total_quantity": self.total_quantity,
            "delay_cost_bps": round(self.delay_cost_bps, 4),
            "market_impact_bps": round(self.market_impact_bps, 4),
            "spread_cost_bps": round(self.spread_cost_bps, 4),
            "opportunity_cost_bps": round(self.opportunity_cost_bps, 4),
            "total_is_bps": round(self.total_is_bps, 4),
            "total_is_usd": round(self.total_is_usd, 4),
            "fill_rate": round(self.fill_rate, 6),
        }


@dataclass
class ExecutionQuality:
    """Execution quality report for a completed trade.

    Args:
        ticker: Instrument.
        side: BUY or SELL.
        avg_fill_price: Realised average fill price.
        benchmark_price: Benchmark reference price.
        benchmark_type: Which benchmark was used.
        slippage_bps: Realised slippage vs benchmark in bps.
        slippage_usd: Dollar value of slippage.
        commission_usd: Total commission paid.
        total_cost_usd: slippage_usd + commission_usd.
        score: Quality score 0-100 (higher = better).
    """

    ticker: str
    side: str
    avg_fill_price: float
    benchmark_price: float
    benchmark_type: ExecutionBenchmark
    slippage_bps: float
    slippage_usd: float
    commission_usd: float
    total_cost_usd: float
    score: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "side": self.side,
            "avg_fill_price": self.avg_fill_price,
            "benchmark_price": self.benchmark_price,
            "benchmark_type": self.benchmark_type.value,
            "slippage_bps": round(self.slippage_bps, 4),
            "slippage_usd": round(self.slippage_usd, 4),
            "commission_usd": round(self.commission_usd, 4),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "score": round(self.score, 2),
        }


@dataclass
class SimulatedFill:
    """Result of deterministic execution simulation.

    Args:
        ticker: Instrument.
        side: BUY or SELL.
        requested_quantity: Quantity submitted.
        filled_quantity: Quantity actually simulated as filled.
        avg_fill_price: Volume-weighted fill price including spread/slippage.
        arrival_price: Mid price at time of order.
        spread_bps: Applied bid-ask spread in bps.
        slippage_bps: Applied market impact slippage in bps.
        commission_usd: Commission estimate.
        latency_ms: Simulated execution latency in milliseconds.
        is_fully_filled: Whether the entire quantity was filled.
    """

    ticker: str
    side: str
    requested_quantity: float
    filled_quantity: float
    avg_fill_price: float
    arrival_price: float
    spread_bps: float
    slippage_bps: float
    commission_usd: float
    latency_ms: float
    is_fully_filled: bool

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "side": self.side,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price": round(self.avg_fill_price, 6),
            "arrival_price": self.arrival_price,
            "spread_bps": round(self.spread_bps, 4),
            "slippage_bps": round(self.slippage_bps, 4),
            "commission_usd": round(self.commission_usd, 4),
            "latency_ms": round(self.latency_ms, 2),
            "is_fully_filled": self.is_fully_filled,
        }


# ---------------------------------------------------------------------------
# Execution Engine
# ---------------------------------------------------------------------------

class ExecutionEngine:
    """Institutional Execution Management System (pure Python, in-memory).

    Provides deterministic execution simulation, slippage and market impact
    modelling, VWAP/TWAP computation, implementation shortfall analysis, and
    execution quality scoring.
    """

    # Default commission: $0.005/share with $1 minimum
    DEFAULT_COMMISSION_PER_SHARE = 0.005
    DEFAULT_MIN_COMMISSION = 1.0

    def __init__(
        self,
        default_spread_bps: float = 5.0,
        default_slippage_model: SlippageModel = SlippageModel.SQRT,
        commission_per_share: float = DEFAULT_COMMISSION_PER_SHARE,
        min_commission: float = DEFAULT_MIN_COMMISSION,
        default_latency_ms: float = 50.0,
    ) -> None:
        """Initialise ExecutionEngine with default market microstructure assumptions.

        Args:
            default_spread_bps: Default bid-ask half-spread in basis points.
            default_slippage_model: Default slippage model.
            commission_per_share: Commission rate per share/contract.
            min_commission: Minimum commission per trade.
            default_latency_ms: Default simulated latency in milliseconds.
        """
        self.default_spread_bps = default_spread_bps
        self.default_slippage_model = default_slippage_model
        self.commission_per_share = commission_per_share
        self.min_commission = min_commission
        self.default_latency_ms = default_latency_ms

    # ------------------------------------------------------------------
    # VWAP / TWAP computation
    # ------------------------------------------------------------------

    def compute_vwap(self, prices: List[float], volumes: List[float]) -> VWAPResult:
        """Compute Volume-Weighted Average Price from price/volume series.

        Args:
            prices: List of prices for each time bar.
            volumes: List of volumes for each corresponding time bar.

        Returns:
            VWAPResult with computed VWAP, total volume, and price range.

        Raises:
            ValueError: If lists are empty, unequal length, or total volume is zero.
        """
        if not prices:
            raise ValueError("prices cannot be empty")
        if len(prices) != len(volumes):
            raise ValueError("prices and volumes must have the same length")
        total_vol = sum(volumes)
        if total_vol <= 0:
            raise ValueError("total volume must be positive")

        vwap = sum(p * v for p, v in zip(prices, volumes)) / total_vol
        return VWAPResult(
            vwap=vwap,
            total_volume=total_vol,
            n_bars=len(prices),
            price_range=(min(prices), max(prices)),
        )

    def compute_twap(self, prices: List[float]) -> TWAPResult:
        """Compute Time-Weighted Average Price from a price series.

        Args:
            prices: List of prices sampled at equal time intervals.

        Returns:
            TWAPResult with computed TWAP and price range.

        Raises:
            ValueError: If prices list is empty.
        """
        if not prices:
            raise ValueError("prices cannot be empty")
        twap = sum(prices) / len(prices)
        return TWAPResult(
            twap=twap,
            n_bars=len(prices),
            price_range=(min(prices), max(prices)),
        )

    # ------------------------------------------------------------------
    # Slippage estimation
    # ------------------------------------------------------------------

    def estimate_slippage(
        self,
        order_quantity: float,
        arrival_price: float,
        adv: float,
        volatility: float,
        model: Optional[SlippageModel] = None,
        fixed_bps: float = 10.0,
    ) -> SlippageEstimate:
        """Estimate market slippage for an order.

        Models:
            LINEAR: slippage_pct = (qty / adv) * volatility
            SQRT: slippage_pct = sqrt(qty / adv) * volatility  (Kyle-like)
            VOLUME_ADJ: slippage_pct = (qty / adv)^0.6 * volatility
            FIXED_BPS: slippage_pct = fixed_bps / 10000

        Args:
            order_quantity: Number of shares/contracts to be executed.
            arrival_price: Market mid price at order arrival.
            adv: Average daily volume for the instrument.
            volatility: Daily volatility (as decimal, e.g. 0.02 for 2%).
            model: SlippageModel to use; defaults to engine's default.
            fixed_bps: Fixed slippage in basis points (FIXED_BPS model only).

        Returns:
            SlippageEstimate with bps, pct, and USD estimates.

        Raises:
            ValueError: If adv or arrival_price is zero.
        """
        if adv <= 0:
            raise ValueError("adv must be positive")
        if arrival_price <= 0:
            raise ValueError("arrival_price must be positive")

        m = model or self.default_slippage_model
        pov = order_quantity / adv  # participation of volume

        if m == SlippageModel.LINEAR:
            slip_pct = pov * volatility
        elif m == SlippageModel.SQRT:
            slip_pct = math.sqrt(pov) * volatility
        elif m == SlippageModel.VOLUME_ADJ:
            slip_pct = (pov ** 0.6) * volatility
        else:  # FIXED_BPS
            slip_pct = fixed_bps / 10_000.0

        slip_bps = slip_pct * 10_000.0
        cost_usd = slip_pct * arrival_price * order_quantity

        return SlippageEstimate(
            model=m,
            order_quantity=order_quantity,
            adv=adv,
            volatility=volatility,
            arrival_price=arrival_price,
            estimated_slippage_bps=slip_bps,
            estimated_slippage_pct=slip_pct,
            estimated_cost_usd=cost_usd,
        )

    # ------------------------------------------------------------------
    # Market impact estimation
    # ------------------------------------------------------------------

    def estimate_market_impact(
        self,
        order_quantity: float,
        adv: float,
        price: float,
        volatility: float,
        model: MarketImpactModel = MarketImpactModel.SQRT,
        sigma_perm: float = 0.1,
        sigma_temp: float = 0.1,
    ) -> MarketImpactEstimate:
        """Estimate permanent and temporary market impact.

        For the SQRT / ALMGREN_CHRISS model:
            permanent_impact_bps = sigma_perm * sqrt(qty/adv) * vol * 10000
            temporary_impact_bps = sigma_temp * sqrt(qty/adv) * vol * 10000

        For LINEAR:
            permanent_impact_bps = sigma_perm * (qty/adv) * vol * 10000
            temporary_impact_bps = sigma_temp * (qty/adv) * vol * 10000

        Args:
            order_quantity: Order size in shares/contracts.
            adv: Average daily volume.
            price: Current price for USD conversion.
            volatility: Daily volatility (decimal fraction).
            model: Market impact model.
            sigma_perm: Permanent impact scaling factor.
            sigma_temp: Temporary impact scaling factor.

        Returns:
            MarketImpactEstimate with decomposed permanent / temporary impact.
        """
        if adv <= 0:
            raise ValueError("adv must be positive")
        if price <= 0:
            raise ValueError("price must be positive")

        pov = order_quantity / adv

        if model == MarketImpactModel.LINEAR:
            factor = pov
        else:
            factor = math.sqrt(pov)

        perm_pct = sigma_perm * factor * volatility
        temp_pct = sigma_temp * factor * volatility
        total_pct = perm_pct + temp_pct

        perm_usd = perm_pct * price * order_quantity
        temp_usd = temp_pct * price * order_quantity
        total_usd = perm_usd + temp_usd

        return MarketImpactEstimate(
            model=model,
            permanent_impact_bps=perm_pct * 10_000.0,
            temporary_impact_bps=temp_pct * 10_000.0,
            total_impact_bps=total_pct * 10_000.0,
            permanent_impact_usd=perm_usd,
            temporary_impact_usd=temp_usd,
            total_impact_usd=total_usd,
            participation_rate=pov,
        )

    # ------------------------------------------------------------------
    # Implementation shortfall
    # ------------------------------------------------------------------

    def implementation_shortfall(
        self,
        decision_price: float,
        arrival_price: float,
        avg_fill_price: float,
        total_quantity: float,
        filled_quantity: float,
        spread_bps: float,
        is_buy: bool = True,
    ) -> ImplementationShortfall:
        """Compute full implementation shortfall decomposition.

        IS = (paper_portfolio_return - real_portfolio_return).

        For a BUY:
            IS = (decision_price - avg_fill_price) * filled + (decision_price - close) * unfilled
        Components:
            delay_cost = arrival_price - decision_price (price moved before arrival)
            market_impact = avg_fill_price - arrival_price (price moved during execution)
            spread_cost = 0.5 * spread * filled
            opportunity_cost = (close_proxy - arrival_price) * (total - filled)

        Args:
            decision_price: Price when the trade decision was made.
            arrival_price: Market price when the order arrived at venue.
            avg_fill_price: Volume-weighted average fill price.
            total_quantity: Total quantity requested.
            filled_quantity: Quantity actually executed.
            spread_bps: Bid-ask spread in basis points.
            is_buy: True for BUY orders; inverts sign conventions for SELL.

        Returns:
            ImplementationShortfall with full decomposition.
        """
        sign = 1.0 if is_buy else -1.0

        delay_bps = sign * (arrival_price - decision_price) / decision_price * 10_000.0
        impact_bps = sign * (avg_fill_price - arrival_price) / arrival_price * 10_000.0
        spread_cost_bps = spread_bps * 0.5
        unfilled = total_quantity - filled_quantity
        opp_cost_bps = (unfilled / total_quantity) * abs(delay_bps) if total_quantity > 0 else 0.0

        total_bps = delay_bps + impact_bps + spread_cost_bps + opp_cost_bps
        total_usd = total_bps / 10_000.0 * decision_price * total_quantity
        fill_rate = filled_quantity / total_quantity if total_quantity > 0 else 0.0

        return ImplementationShortfall(
            decision_price=decision_price,
            arrival_price=arrival_price,
            avg_fill_price=avg_fill_price,
            filled_quantity=filled_quantity,
            total_quantity=total_quantity,
            delay_cost_bps=delay_bps,
            market_impact_bps=impact_bps,
            spread_cost_bps=spread_cost_bps,
            opportunity_cost_bps=opp_cost_bps,
            total_is_bps=total_bps,
            total_is_usd=total_usd,
            fill_rate=fill_rate,
        )

    # ------------------------------------------------------------------
    # Simulated fill
    # ------------------------------------------------------------------

    def simulate_fill(
        self,
        ticker: str,
        side: str,
        quantity: float,
        arrival_price: float,
        adv: float,
        volatility: float,
        *,
        spread_bps: Optional[float] = None,
        slippage_model: Optional[SlippageModel] = None,
        latency_ms: Optional[float] = None,
        fill_rate: float = 1.0,
    ) -> SimulatedFill:
        """Simulate order execution with realistic spread and slippage.

        Execution price = arrival_price ± (half_spread + slippage_offset),
        where the sign is adverse to the order side (BUY pays more, SELL gets less).

        Args:
            ticker: Instrument symbol.
            side: "BUY" or "SELL".
            quantity: Order size.
            arrival_price: Market price at time of arrival.
            adv: Average daily volume.
            volatility: Daily volatility.
            spread_bps: Bid-ask spread override; uses engine default if None.
            slippage_model: Slippage model override.
            latency_ms: Latency override in milliseconds.
            fill_rate: Fraction of quantity filled (0–1). Defaults to 1.0.

        Returns:
            SimulatedFill with all execution details.
        """
        if arrival_price <= 0:
            raise ValueError("arrival_price must be positive")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        fill_rate = max(0.0, min(1.0, fill_rate))

        sp_bps = spread_bps if spread_bps is not None else self.default_spread_bps
        lat_ms = latency_ms if latency_ms is not None else self.default_latency_ms

        slip_est = self.estimate_slippage(
            quantity, arrival_price, adv, volatility, model=slippage_model
        )
        slip_bps = slip_est.estimated_slippage_bps
        half_spread_bps = sp_bps * 0.5
        total_adverse_bps = half_spread_bps + slip_bps

        is_buy = side.upper() in ("BUY", "BUY_TO_COVER")
        adj_factor = 1.0 + (total_adverse_bps / 10_000.0) if is_buy else 1.0 - (total_adverse_bps / 10_000.0)
        fill_price = arrival_price * adj_factor

        filled_qty = quantity * fill_rate
        commission = max(self.min_commission, filled_qty * self.commission_per_share)

        return SimulatedFill(
            ticker=ticker,
            side=side.upper(),
            requested_quantity=quantity,
            filled_quantity=filled_qty,
            avg_fill_price=fill_price,
            arrival_price=arrival_price,
            spread_bps=sp_bps,
            slippage_bps=slip_bps,
            commission_usd=commission,
            latency_ms=lat_ms,
            is_fully_filled=(fill_rate >= 1.0),
        )

    # ------------------------------------------------------------------
    # Execution quality scoring
    # ------------------------------------------------------------------

    def execution_quality(
        self,
        ticker: str,
        side: str,
        avg_fill_price: float,
        benchmark_price: float,
        quantity: float,
        commission_usd: float,
        benchmark_type: ExecutionBenchmark = ExecutionBenchmark.ARRIVAL,
    ) -> ExecutionQuality:
        """Score the quality of an execution against a benchmark.

        Score = max(0, 100 - slippage_bps), capped to [0, 100].
        Zero slippage vs benchmark → score 100.
        Each basis point of adverse slippage reduces score by 1.

        Args:
            ticker: Instrument.
            side: BUY or SELL.
            avg_fill_price: Realised average fill price.
            benchmark_price: Reference price for the chosen benchmark.
            quantity: Filled quantity.
            commission_usd: Total commission paid.
            benchmark_type: Which benchmark to compare against.

        Returns:
            ExecutionQuality with slippage, cost, and score.
        """
        is_buy = side.upper() in ("BUY", "BUY_TO_COVER")
        sign = 1.0 if is_buy else -1.0
        slippage_pct = sign * (avg_fill_price - benchmark_price) / benchmark_price
        slippage_bps = slippage_pct * 10_000.0
        slippage_usd = slippage_pct * benchmark_price * quantity
        total_cost = abs(slippage_usd) + commission_usd
        score = max(0.0, min(100.0, 100.0 - slippage_bps))

        return ExecutionQuality(
            ticker=ticker,
            side=side.upper(),
            avg_fill_price=avg_fill_price,
            benchmark_price=benchmark_price,
            benchmark_type=benchmark_type,
            slippage_bps=slippage_bps,
            slippage_usd=slippage_usd,
            commission_usd=commission_usd,
            total_cost_usd=total_cost,
            score=score,
        )

    # ------------------------------------------------------------------
    # Participation rate
    # ------------------------------------------------------------------

    def participation_rate(self, order_quantity: float, period_volume: float) -> float:
        """Compute participation rate (order qty / period volume).

        Args:
            order_quantity: Total order quantity.
            period_volume: Volume traded in the market during the same period.

        Returns:
            Participation rate as a fraction (e.g. 0.05 = 5%).

        Raises:
            ValueError: If period_volume is zero.
        """
        if period_volume <= 0:
            raise ValueError("period_volume must be positive")
        return order_quantity / period_volume

    # ------------------------------------------------------------------
    # Arrival price benchmark comparison
    # ------------------------------------------------------------------

    def arrival_slippage(
        self,
        avg_fill_price: float,
        arrival_price: float,
        is_buy: bool = True,
    ) -> float:
        """Compute slippage in basis points against the arrival price.

        Args:
            avg_fill_price: Realised average fill price.
            arrival_price: Market price at order arrival.
            is_buy: True for BUY orders (adverse fill is above arrival).

        Returns:
            Slippage in basis points (positive = adverse, negative = favourable).
        """
        if arrival_price <= 0:
            raise ValueError("arrival_price must be positive")
        sign = 1.0 if is_buy else -1.0
        return sign * (avg_fill_price - arrival_price) / arrival_price * 10_000.0

    # ------------------------------------------------------------------
    # Commission calculation
    # ------------------------------------------------------------------

    def compute_commission(self, quantity: float, per_share_rate: Optional[float] = None) -> float:
        """Calculate commission for a given quantity.

        Args:
            quantity: Number of shares/contracts.
            per_share_rate: Per-share rate override; uses engine default if None.

        Returns:
            Commission in USD.
        """
        rate = per_share_rate if per_share_rate is not None else self.commission_per_share
        return max(self.min_commission, quantity * rate)

    # ------------------------------------------------------------------
    # Spread cost
    # ------------------------------------------------------------------

    def spread_cost(self, quantity: float, price: float, spread_bps: float) -> float:
        """Compute the dollar cost of crossing the bid-ask spread.

        For a single trade, cost = 0.5 * spread * quantity * price.

        Args:
            quantity: Order size in shares/contracts.
            price: Mid price.
            spread_bps: Full bid-ask spread in basis points.

        Returns:
            Spread cost in USD.
        """
        if price <= 0:
            raise ValueError("price must be positive")
        return 0.5 * (spread_bps / 10_000.0) * price * quantity


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_execution_engine: Optional[ExecutionEngine] = None


def get_execution_engine() -> ExecutionEngine:
    """Return the singleton ExecutionEngine instance.

    Returns:
        Shared ExecutionEngine instance.
    """
    global _default_execution_engine
    if _default_execution_engine is None:
        _default_execution_engine = ExecutionEngine()
    return _default_execution_engine
