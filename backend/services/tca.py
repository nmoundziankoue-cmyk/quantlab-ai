"""M17 — Transaction Cost Analysis (TCA) Engine (pure Python, in-memory).

Institutional TCA covering spread cost, commission, slippage decomposition,
delay cost, opportunity cost, implementation shortfall, and benchmark
comparisons (VWAP, TWAP, Arrival, Close).  Generates broker scorecards.

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

class TCABenchmark(str, Enum):
    ARRIVAL = "ARRIVAL"
    VWAP = "VWAP"
    TWAP = "TWAP"
    CLOSE = "CLOSE"
    OPEN = "OPEN"
    PREVIOUS_CLOSE = "PREVIOUS_CLOSE"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TradeCostBreakdown:
    """Full cost breakdown for a single trade.

    Args:
        trade_id: Reference trade identifier.
        ticker: Instrument symbol.
        side: BUY or SELL.
        quantity: Trade size in shares/contracts.
        decision_price: Price at trade decision time.
        arrival_price: Market price at order arrival.
        avg_fill_price: Realised volume-weighted average fill price.
        benchmark_price: Chosen benchmark price.
        benchmark_type: Which benchmark was used.
        spread_cost_bps: Half-spread cost in basis points.
        commission_bps: Commission cost in basis points.
        slippage_bps: Slippage vs arrival in basis points.
        delay_cost_bps: Cost from delay between decision and arrival.
        opportunity_cost_bps: Cost from unfilled portion.
        market_impact_bps: Residual market impact beyond spread/delay.
        total_cost_bps: Sum of all cost components.
        spread_cost_usd: Spread cost in USD.
        commission_usd: Commission in USD.
        slippage_usd: Slippage cost in USD.
        total_cost_usd: Total transaction cost in USD.
        is_vs_benchmark_bps: IS relative to chosen benchmark.
    """

    trade_id: str
    ticker: str
    side: str
    quantity: float
    decision_price: float
    arrival_price: float
    avg_fill_price: float
    benchmark_price: float
    benchmark_type: TCABenchmark
    spread_cost_bps: float
    commission_bps: float
    slippage_bps: float
    delay_cost_bps: float
    opportunity_cost_bps: float
    market_impact_bps: float
    total_cost_bps: float
    spread_cost_usd: float
    commission_usd: float
    slippage_usd: float
    total_cost_usd: float
    is_vs_benchmark_bps: float

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "decision_price": self.decision_price,
            "arrival_price": self.arrival_price,
            "avg_fill_price": self.avg_fill_price,
            "benchmark_price": self.benchmark_price,
            "benchmark_type": self.benchmark_type.value,
            "spread_cost_bps": round(self.spread_cost_bps, 4),
            "commission_bps": round(self.commission_bps, 4),
            "slippage_bps": round(self.slippage_bps, 4),
            "delay_cost_bps": round(self.delay_cost_bps, 4),
            "opportunity_cost_bps": round(self.opportunity_cost_bps, 4),
            "market_impact_bps": round(self.market_impact_bps, 4),
            "total_cost_bps": round(self.total_cost_bps, 4),
            "spread_cost_usd": round(self.spread_cost_usd, 4),
            "commission_usd": round(self.commission_usd, 4),
            "slippage_usd": round(self.slippage_usd, 4),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "is_vs_benchmark_bps": round(self.is_vs_benchmark_bps, 4),
        }


@dataclass
class BrokerScorecard:
    """Execution quality summary for a single broker.

    Args:
        broker_id: Broker identifier.
        broker_name: Human-readable name.
        trade_count: Number of trades via this broker.
        avg_slippage_bps: Average slippage in basis points.
        avg_commission_bps: Average commission in basis points.
        avg_total_cost_bps: Average total transaction cost in basis points.
        avg_spread_cost_bps: Average spread cost in basis points.
        fill_rate: Average fill rate (0–1).
        quality_score: Composite quality score 0–100.
        rank: Rank among all brokers (1 = best).
    """

    broker_id: str
    broker_name: str
    trade_count: int
    avg_slippage_bps: float
    avg_commission_bps: float
    avg_total_cost_bps: float
    avg_spread_cost_bps: float
    fill_rate: float
    quality_score: float
    rank: int

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "broker_id": self.broker_id,
            "broker_name": self.broker_name,
            "trade_count": self.trade_count,
            "avg_slippage_bps": round(self.avg_slippage_bps, 4),
            "avg_commission_bps": round(self.avg_commission_bps, 4),
            "avg_total_cost_bps": round(self.avg_total_cost_bps, 4),
            "avg_spread_cost_bps": round(self.avg_spread_cost_bps, 4),
            "fill_rate": round(self.fill_rate, 6),
            "quality_score": round(self.quality_score, 2),
            "rank": self.rank,
        }


@dataclass
class TCAReport:
    """Aggregated TCA report across multiple trades.

    Args:
        trade_count: Number of trades analysed.
        total_traded_value: Sum of |qty × arrival_price| across trades.
        avg_spread_cost_bps: Average spread cost.
        avg_commission_bps: Average commission.
        avg_slippage_bps: Average market slippage.
        avg_delay_cost_bps: Average decision-to-arrival cost.
        avg_total_cost_bps: Average all-in transaction cost.
        total_cost_usd: Total dollar transaction costs.
        broker_scorecards: Scorecards for each broker in the dataset.
    """

    trade_count: int
    total_traded_value: float
    avg_spread_cost_bps: float
    avg_commission_bps: float
    avg_slippage_bps: float
    avg_delay_cost_bps: float
    avg_total_cost_bps: float
    total_cost_usd: float
    broker_scorecards: List[BrokerScorecard]

    def to_dict(self) -> Dict:
        """Return JSON-serialisable dict."""
        return {
            "trade_count": self.trade_count,
            "total_traded_value": round(self.total_traded_value, 2),
            "avg_spread_cost_bps": round(self.avg_spread_cost_bps, 4),
            "avg_commission_bps": round(self.avg_commission_bps, 4),
            "avg_slippage_bps": round(self.avg_slippage_bps, 4),
            "avg_delay_cost_bps": round(self.avg_delay_cost_bps, 4),
            "avg_total_cost_bps": round(self.avg_total_cost_bps, 4),
            "total_cost_usd": round(self.total_cost_usd, 2),
            "broker_scorecards": [b.to_dict() for b in self.broker_scorecards],
        }


@dataclass
class _TradeCostRecord:
    """Internal storage record for TCA analysis."""
    trade_id: str
    ticker: str
    side: str
    quantity: float
    arrival_price: float
    avg_fill_price: float
    decision_price: float
    commission_usd: float
    spread_bps: float
    broker_id: Optional[str]
    broker_name: Optional[str]
    fill_rate: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# TCA Engine
# ---------------------------------------------------------------------------

class TCAEngine:
    """Transaction Cost Analysis engine (pure Python, in-memory).

    Records trade execution data and provides full cost breakdown:
    spread, commission, slippage, delay, opportunity cost, and IS.
    Generates broker scorecards and aggregate TCA reports.
    """

    def __init__(self) -> None:
        self._records: List[_TradeCostRecord] = []

    # ------------------------------------------------------------------
    # Trade recording
    # ------------------------------------------------------------------

    def record_trade(
        self,
        trade_id: str,
        ticker: str,
        side: str,
        quantity: float,
        arrival_price: float,
        avg_fill_price: float,
        *,
        decision_price: Optional[float] = None,
        commission_usd: float = 0.0,
        spread_bps: float = 5.0,
        broker_id: Optional[str] = None,
        broker_name: Optional[str] = None,
        fill_rate: float = 1.0,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a completed trade for TCA analysis.

        Args:
            trade_id: Unique trade identifier.
            ticker: Instrument symbol.
            side: "BUY" or "SELL".
            quantity: Executed quantity.
            arrival_price: Market price at order arrival (mid).
            avg_fill_price: Volume-weighted average fill price.
            decision_price: Price at decision time (defaults to arrival_price).
            commission_usd: Commission charged.
            spread_bps: Bid-ask spread in basis points.
            broker_id: Executing broker ID.
            broker_name: Executing broker name.
            fill_rate: Fraction of order filled.
            timestamp: Execution timestamp.
        """
        self._records.append(_TradeCostRecord(
            trade_id=trade_id,
            ticker=ticker.upper(),
            side=side.upper(),
            quantity=quantity,
            arrival_price=arrival_price,
            avg_fill_price=avg_fill_price,
            decision_price=decision_price if decision_price is not None else arrival_price,
            commission_usd=commission_usd,
            spread_bps=spread_bps,
            broker_id=broker_id,
            broker_name=broker_name,
            fill_rate=max(0.0, min(1.0, fill_rate)),
            timestamp=timestamp or datetime.now(timezone.utc),
        ))

    # ------------------------------------------------------------------
    # Cost breakdown
    # ------------------------------------------------------------------

    def analyse_trade(
        self,
        trade_id: str,
        ticker: str,
        side: str,
        quantity: float,
        decision_price: float,
        arrival_price: float,
        avg_fill_price: float,
        commission_usd: float,
        spread_bps: float,
        benchmark_price: float,
        benchmark_type: TCABenchmark = TCABenchmark.ARRIVAL,
        fill_rate: float = 1.0,
    ) -> TradeCostBreakdown:
        """Compute a full cost breakdown for a single trade.

        Args:
            trade_id: Trade identifier.
            ticker: Instrument symbol.
            side: BUY or SELL.
            quantity: Trade size.
            decision_price: Price at portfolio manager's decision.
            arrival_price: Price at order arrival.
            avg_fill_price: Realised average fill price.
            commission_usd: Commission paid.
            spread_bps: Bid-ask spread in basis points.
            benchmark_price: Reference benchmark price.
            benchmark_type: Type of benchmark.
            fill_rate: Fraction filled (for opportunity cost).

        Returns:
            TradeCostBreakdown with full cost decomposition.
        """
        is_buy = side.upper() in ("BUY", "BUY_TO_COVER")
        sign = 1.0 if is_buy else -1.0
        base_value = decision_price * quantity

        # Spread cost: half-spread per trade
        spread_cost_bps = spread_bps * 0.5
        spread_cost_usd = (spread_cost_bps / 10_000.0) * arrival_price * quantity * fill_rate

        # Commission in basis points relative to trade value
        commission_bps = (commission_usd / base_value * 10_000.0) if base_value > 0 else 0.0

        # Delay cost: decision → arrival price move (adverse for buy = price rose)
        delay_cost_bps = sign * (arrival_price - decision_price) / decision_price * 10_000.0

        # Market slippage: arrival → fill price
        slippage_bps = sign * (avg_fill_price - arrival_price) / arrival_price * 10_000.0
        slippage_usd = (slippage_bps / 10_000.0) * arrival_price * quantity * fill_rate

        # Opportunity cost on unfilled portion
        unfilled_frac = 1.0 - fill_rate
        opp_cost_bps = unfilled_frac * abs(delay_cost_bps)

        # Market impact residual (slippage minus spread)
        market_impact_bps = max(0.0, slippage_bps - spread_cost_bps)

        # Total
        total_bps = spread_cost_bps + commission_bps + slippage_bps + delay_cost_bps + opp_cost_bps
        total_usd = spread_cost_usd + commission_usd + slippage_usd

        # IS vs benchmark
        is_bps = sign * (avg_fill_price - benchmark_price) / benchmark_price * 10_000.0

        return TradeCostBreakdown(
            trade_id=trade_id,
            ticker=ticker.upper(),
            side=side.upper(),
            quantity=quantity,
            decision_price=decision_price,
            arrival_price=arrival_price,
            avg_fill_price=avg_fill_price,
            benchmark_price=benchmark_price,
            benchmark_type=benchmark_type,
            spread_cost_bps=spread_cost_bps,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            delay_cost_bps=delay_cost_bps,
            opportunity_cost_bps=opp_cost_bps,
            market_impact_bps=market_impact_bps,
            total_cost_bps=total_bps,
            spread_cost_usd=spread_cost_usd,
            commission_usd=commission_usd,
            slippage_usd=slippage_usd,
            total_cost_usd=total_usd,
            is_vs_benchmark_bps=is_bps,
        )

    # ------------------------------------------------------------------
    # Aggregate analysis
    # ------------------------------------------------------------------

    def generate_report(
        self,
        records: Optional[List[_TradeCostRecord]] = None,
    ) -> TCAReport:
        """Generate aggregate TCA report from stored records.

        Args:
            records: Explicit record list; if None uses all stored records.

        Returns:
            TCAReport with averages and broker scorecards.

        Raises:
            ValueError: If no records available.
        """
        recs = records if records is not None else self._records
        if not recs:
            raise ValueError("No trade records available for TCA report")

        n = len(recs)

        def _slippage(r: _TradeCostRecord) -> float:
            is_buy = r.side in ("BUY", "BUY_TO_COVER")
            sign = 1.0 if is_buy else -1.0
            if r.arrival_price <= 0:
                return 0.0
            return sign * (r.avg_fill_price - r.arrival_price) / r.arrival_price * 10_000.0

        def _delay(r: _TradeCostRecord) -> float:
            is_buy = r.side in ("BUY", "BUY_TO_COVER")
            sign = 1.0 if is_buy else -1.0
            if r.decision_price <= 0:
                return 0.0
            return sign * (r.arrival_price - r.decision_price) / r.decision_price * 10_000.0

        def _comm_bps(r: _TradeCostRecord) -> float:
            base = r.decision_price * r.quantity
            return (r.commission_usd / base * 10_000.0) if base > 0 else 0.0

        avg_spread = sum(r.spread_bps * 0.5 for r in recs) / n
        avg_comm = sum(_comm_bps(r) for r in recs) / n
        avg_slip = sum(_slippage(r) for r in recs) / n
        avg_delay = sum(_delay(r) for r in recs) / n
        avg_total = avg_spread + avg_comm + avg_slip + avg_delay
        total_traded = sum(r.quantity * r.arrival_price for r in recs)
        total_cost_usd = sum(
            (r.spread_bps * 0.5 / 10_000.0) * r.arrival_price * r.quantity * r.fill_rate
            + r.commission_usd
            for r in recs
        )

        scorecards = self._build_scorecards(recs)

        return TCAReport(
            trade_count=n,
            total_traded_value=total_traded,
            avg_spread_cost_bps=avg_spread,
            avg_commission_bps=avg_comm,
            avg_slippage_bps=avg_slip,
            avg_delay_cost_bps=avg_delay,
            avg_total_cost_bps=avg_total,
            total_cost_usd=total_cost_usd,
            broker_scorecards=scorecards,
        )

    def _build_scorecards(self, recs: List[_TradeCostRecord]) -> List[BrokerScorecard]:
        """Build per-broker quality scorecards."""
        by_broker: Dict[str, List[_TradeCostRecord]] = {}
        for r in recs:
            bid = r.broker_id or "UNKNOWN"
            by_broker.setdefault(bid, []).append(r)

        def _slippage(r: _TradeCostRecord) -> float:
            is_buy = r.side in ("BUY", "BUY_TO_COVER")
            sign = 1.0 if is_buy else -1.0
            if r.arrival_price <= 0:
                return 0.0
            return sign * (r.avg_fill_price - r.arrival_price) / r.arrival_price * 10_000.0

        scorecards = []
        for broker_id, br in by_broker.items():
            n = len(br)
            avg_slip = sum(_slippage(r) for r in br) / n
            avg_comm = sum(
                (r.commission_usd / (r.decision_price * r.quantity) * 10_000.0)
                if r.decision_price * r.quantity > 0 else 0.0
                for r in br
            ) / n
            avg_spread = sum(r.spread_bps * 0.5 for r in br) / n
            avg_total = avg_slip + avg_comm + avg_spread
            avg_fill = sum(r.fill_rate for r in br) / n
            name = br[0].broker_name or broker_id

            score = max(0.0, min(100.0, 100.0 - avg_slip - avg_comm + avg_fill * 10.0))
            scorecards.append(BrokerScorecard(
                broker_id=broker_id,
                broker_name=name,
                trade_count=n,
                avg_slippage_bps=avg_slip,
                avg_commission_bps=avg_comm,
                avg_total_cost_bps=avg_total,
                avg_spread_cost_bps=avg_spread,
                fill_rate=avg_fill,
                quality_score=score,
                rank=0,
            ))

        scorecards.sort(key=lambda s: s.quality_score, reverse=True)
        for i, s in enumerate(scorecards):
            s.rank = i + 1
        return scorecards

    # ------------------------------------------------------------------
    # Benchmark helpers
    # ------------------------------------------------------------------

    def spread_cost(
        self,
        quantity: float,
        price: float,
        spread_bps: float,
        fill_rate: float = 1.0,
    ) -> float:
        """Compute dollar spread cost.

        Args:
            quantity: Order size.
            price: Mid price.
            spread_bps: Full bid-ask spread in basis points.
            fill_rate: Fraction filled.

        Returns:
            Spread cost in USD.
        """
        if price <= 0:
            raise ValueError("price must be positive")
        return 0.5 * (spread_bps / 10_000.0) * price * quantity * fill_rate

    def slippage_vs_arrival(
        self,
        avg_fill: float,
        arrival: float,
        quantity: float,
        is_buy: bool = True,
    ) -> Tuple[float, float]:
        """Compute slippage vs arrival price.

        Args:
            avg_fill: Average fill price.
            arrival: Arrival price.
            quantity: Quantity filled.
            is_buy: True for BUY orders.

        Returns:
            (slippage_bps, slippage_usd).
        """
        if arrival <= 0:
            raise ValueError("arrival price must be positive")
        sign = 1.0 if is_buy else -1.0
        bps = sign * (avg_fill - arrival) / arrival * 10_000.0
        usd = (bps / 10_000.0) * arrival * quantity
        return bps, usd

    def get_records(self) -> List[_TradeCostRecord]:
        """Return all stored TCA records.

        Returns:
            List of _TradeCostRecord.
        """
        return list(self._records)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_tca_engine: Optional[TCAEngine] = None


def get_tca_engine() -> TCAEngine:
    """Return the singleton TCAEngine instance.

    Returns:
        Shared TCAEngine instance.
    """
    global _default_tca_engine
    if _default_tca_engine is None:
        _default_tca_engine = TCAEngine()
    return _default_tca_engine
