"""M18 — Streaming Engine: event bus with 11 event types, priority queues, replay, filtering.

Pure Python, no external dependencies. Supports publish/subscribe, batching,
async consumers, persistence hooks, and operational metrics.

Architecture:
  StreamingEngine  — central event bus
  11 EventType enums → typed dataclasses
  SubscriptionHandle — returned on subscribe, used to cancel
  EventMetrics — operational counters per event type
"""
from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    """Enumeration of all first-class event types in the M18 streaming bus."""

    TICK = "TICK"
    QUOTE = "QUOTE"
    TRADE = "TRADE"
    ORDER_BOOK = "ORDER_BOOK"
    NEWS = "NEWS"
    ECONOMIC = "ECONOMIC"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    ALERT = "ALERT"
    PORTFOLIO = "PORTFOLIO"
    RISK = "RISK"
    EXECUTION = "EXECUTION"


# ---------------------------------------------------------------------------
# Event dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BaseEvent:
    """Common fields shared by every event.

    Args:
        event_id: Unique identifier for this event instance.
        event_type: Discriminator enum value.
        timestamp: UTC wall-clock time of event creation.
        sequence: Monotonically increasing sequence number assigned by the bus.
    """

    event_id: str
    event_type: EventType
    timestamp: datetime
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of this event."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
        }


@dataclass
class TickEvent(BaseEvent):
    """Best-price tick: last trade price and volume.

    Args:
        ticker: Instrument symbol.
        price: Last trade price.
        volume: Last trade volume (shares/contracts).
        venue: Originating exchange or data source.
    """

    ticker: str = ""
    price: float = 0.0
    volume: float = 0.0
    venue: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"ticker": self.ticker, "price": self.price,
                  "volume": self.volume, "venue": self.venue})
        return d


@dataclass
class QuoteEvent(BaseEvent):
    """NBBO / best bid-offer snapshot.

    Args:
        ticker: Instrument symbol.
        bid: Best bid price.
        ask: Best ask price.
        bid_size: Bid quantity.
        ask_size: Ask quantity.
        venue: Originating venue.
    """

    ticker: str = ""
    bid: float = 0.0
    ask: float = 0.0
    bid_size: float = 0.0
    ask_size: float = 0.0
    venue: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"ticker": self.ticker, "bid": self.bid, "ask": self.ask,
                  "bid_size": self.bid_size, "ask_size": self.ask_size,
                  "venue": self.venue})
        return d


@dataclass
class TradeEvent(BaseEvent):
    """Individual executed trade (time-and-sales).

    Args:
        trade_id: Exchange-assigned trade identifier.
        ticker: Instrument symbol.
        side: BUY or SELL (aggressor side).
        quantity: Number of shares/contracts traded.
        price: Execution price.
        venue: Originating exchange.
    """

    trade_id: str = ""
    ticker: str = ""
    side: str = "BUY"
    quantity: float = 0.0
    price: float = 0.0
    venue: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"trade_id": self.trade_id, "ticker": self.ticker,
                  "side": self.side, "quantity": self.quantity,
                  "price": self.price, "venue": self.venue})
        return d


@dataclass
class OrderBookEvent(BaseEvent):
    """Level II order book snapshot or delta.

    Args:
        ticker: Instrument symbol.
        bids: List of (price, size) bid levels, best first.
        asks: List of (price, size) ask levels, best first.
        is_snapshot: True if this is a full snapshot; False if incremental.
        venue: Originating venue.
    """

    ticker: str = ""
    bids: List[Tuple[float, float]] = field(default_factory=list)
    asks: List[Tuple[float, float]] = field(default_factory=list)
    is_snapshot: bool = True
    venue: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"ticker": self.ticker,
                  "bids": [[p, s] for p, s in self.bids],
                  "asks": [[p, s] for p, s in self.asks],
                  "is_snapshot": self.is_snapshot,
                  "venue": self.venue})
        return d


@dataclass
class NewsEvent(BaseEvent):
    """News article or headline.

    Args:
        headline: Short headline text.
        body: Full article body (may be truncated).
        source: News source name.
        tickers: List of related tickers.
        sentiment_score: Normalised sentiment in [-1.0, 1.0].
        risk_score: Risk relevance in [0.0, 1.0].
        url: Optional source URL.
    """

    headline: str = ""
    body: str = ""
    source: str = ""
    tickers: List[str] = field(default_factory=list)
    sentiment_score: float = 0.0
    risk_score: float = 0.0
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"headline": self.headline, "body": self.body,
                  "source": self.source, "tickers": self.tickers,
                  "sentiment_score": self.sentiment_score,
                  "risk_score": self.risk_score, "url": self.url})
        return d


@dataclass
class EconomicEvent(BaseEvent):
    """Macro-economic data release.

    Args:
        indicator: Indicator name (e.g. "CPI", "NFP").
        actual: Released actual value.
        expected: Consensus estimate before release.
        previous: Prior period reading.
        country: ISO country code (e.g. "US").
        surprise_bps: Actual minus expected in basis points.
    """

    indicator: str = ""
    actual: float = 0.0
    expected: float = 0.0
    previous: float = 0.0
    country: str = "US"
    surprise_bps: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"indicator": self.indicator, "actual": self.actual,
                  "expected": self.expected, "previous": self.previous,
                  "country": self.country, "surprise_bps": self.surprise_bps})
        return d


@dataclass
class CorporateActionEvent(BaseEvent):
    """Corporate action (split, dividend, spin-off, merger).

    Args:
        ticker: Subject instrument.
        action_type: SPLIT, DIVIDEND, SPINOFF, MERGER, RIGHTS.
        value: Numeric value (ratio for splits, $ for dividends).
        ex_date: Ex-date (ISO string).
        record_date: Record date (ISO string).
        pay_date: Payment date (ISO string, optional).
    """

    ticker: str = ""
    action_type: str = "DIVIDEND"
    value: float = 0.0
    ex_date: str = ""
    record_date: str = ""
    pay_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"ticker": self.ticker, "action_type": self.action_type,
                  "value": self.value, "ex_date": self.ex_date,
                  "record_date": self.record_date, "pay_date": self.pay_date})
        return d


@dataclass
class AlertEvent(BaseEvent):
    """System-generated alert notification.

    Args:
        alert_id: Unique alert identifier.
        alert_type: Category (RISK, PNL, VOLATILITY, etc.).
        severity: LOW, MEDIUM, HIGH, CRITICAL.
        message: Human-readable description.
        ticker: Related instrument (empty if portfolio-level).
        acknowledged: Whether the alert has been acknowledged.
    """

    alert_id: str = ""
    alert_type: str = "RISK"
    severity: str = "MEDIUM"
    message: str = ""
    ticker: str = ""
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"alert_id": self.alert_id, "alert_type": self.alert_type,
                  "severity": self.severity, "message": self.message,
                  "ticker": self.ticker, "acknowledged": self.acknowledged})
        return d


@dataclass
class PortfolioEvent(BaseEvent):
    """Portfolio state change or update.

    Args:
        portfolio_event_type: TRADE_FILLED, NAV_UPDATE, PNL_UPDATE, REBALANCE.
        ticker: Affected instrument (empty for portfolio-wide events).
        quantity: Quantity involved (signed: positive=long, negative=short).
        price: Reference price for this event.
        nav: Portfolio NAV after this event.
        pnl: PnL delta from this event.
    """

    portfolio_event_type: str = "NAV_UPDATE"
    ticker: str = ""
    quantity: float = 0.0
    price: float = 0.0
    nav: float = 0.0
    pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"portfolio_event_type": self.portfolio_event_type,
                  "ticker": self.ticker, "quantity": self.quantity,
                  "price": self.price, "nav": self.nav, "pnl": self.pnl})
        return d


@dataclass
class RiskEvent(BaseEvent):
    """Risk metric crossing a threshold.

    Args:
        risk_type: Metric category (VAR, LEVERAGE, DRAWDOWN, etc.).
        metric: Metric name (e.g. "portfolio_var_95").
        value: Current metric value.
        threshold: Limit that was breached.
        breached: True if value exceeds threshold.
        ticker: Related instrument (empty if portfolio-level).
    """

    risk_type: str = "VAR"
    metric: str = ""
    value: float = 0.0
    threshold: float = 0.0
    breached: bool = False
    ticker: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"risk_type": self.risk_type, "metric": self.metric,
                  "value": self.value, "threshold": self.threshold,
                  "breached": self.breached, "ticker": self.ticker})
        return d


@dataclass
class ExecutionEvent(BaseEvent):
    """Order execution lifecycle event.

    Args:
        order_id: OMS order identifier.
        ticker: Instrument.
        side: BUY or SELL.
        quantity: Order quantity.
        fill_price: Execution price (0.0 if not yet filled).
        filled_quantity: Cumulative filled quantity.
        status: NEW, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED.
        venue: Executing venue.
    """

    order_id: str = ""
    ticker: str = ""
    side: str = "BUY"
    quantity: float = 0.0
    fill_price: float = 0.0
    filled_quantity: float = 0.0
    status: str = "NEW"
    venue: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = super().to_dict()
        d.update({"order_id": self.order_id, "ticker": self.ticker,
                  "side": self.side, "quantity": self.quantity,
                  "fill_price": self.fill_price,
                  "filled_quantity": self.filled_quantity,
                  "status": self.status, "venue": self.venue})
        return d


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

@dataclass
class SubscriptionHandle:
    """Opaque handle returned by StreamingEngine.subscribe().

    Args:
        subscription_id: Unique identifier for this subscription.
        event_type: Event type this subscription listens to.
        priority: Lower number = called first.
        ticker_filter: If set, only deliver events for this ticker.
    """

    subscription_id: str
    event_type: EventType
    priority: int
    ticker_filter: Optional[str]
    _handler: Callable[[BaseEvent], None] = field(repr=False, default=lambda e: None)

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "subscription_id": self.subscription_id,
            "event_type": self.event_type.value,
            "priority": self.priority,
            "ticker_filter": self.ticker_filter,
        }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class EventMetrics:
    """Per-event-type operational metrics.

    Args:
        event_type: Metric category.
        published: Total events published.
        delivered: Total delivery invocations.
        filtered: Events dropped by ticker filter.
        batches: Batch publish calls.
        hook_calls: Persistence hook invocations.
    """

    event_type: EventType
    published: int = 0
    delivered: int = 0
    filtered: int = 0
    batches: int = 0
    hook_calls: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "event_type": self.event_type.value,
            "published": self.published,
            "delivered": self.delivered,
            "filtered": self.filtered,
            "batches": self.batches,
            "hook_calls": self.hook_calls,
        }


# ---------------------------------------------------------------------------
# Streaming Engine
# ---------------------------------------------------------------------------

_MAX_HISTORY: int = 10_000


class StreamingEngine:
    """Central event bus for the M18 real-time operating system.

    All M18 services publish and consume events through this engine.
    Supports priority ordering, per-ticker filtering, ring-buffer replay,
    batch publishing, persistence hooks, and operational metrics.
    """

    def __init__(self, max_history: int = _MAX_HISTORY) -> None:
        self._max_history = max_history
        self._sequence: int = 0
        self._subscriptions: Dict[EventType, List[SubscriptionHandle]] = {
            et: [] for et in EventType
        }
        self._history: Dict[EventType, Deque[BaseEvent]] = {
            et: deque(maxlen=max_history) for et in EventType
        }
        self._metrics: Dict[EventType, EventMetrics] = {
            et: EventMetrics(event_type=et) for et in EventType
        }
        self._persistence_hooks: List[Callable[[BaseEvent], None]] = []

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish(self, event: BaseEvent) -> None:
        """Publish a single event to all matching subscribers.

        Assigns a monotonic sequence number, appends to history, calls
        persistence hooks, then delivers to subscribers ordered by priority.

        Args:
            event: Any subclass of BaseEvent.
        """
        self._sequence += 1
        event.sequence = self._sequence
        et = event.event_type
        self._history[et].append(event)
        m = self._metrics[et]
        m.published += 1
        for hook in self._persistence_hooks:
            hook(event)
            m.hook_calls += 1
        for sub in self._subscriptions[et]:
            ticker = getattr(event, "ticker", None) or getattr(event, "alert_id", None)
            if sub.ticker_filter and ticker and sub.ticker_filter != ticker:
                m.filtered += 1
                continue
            sub._handler(event)
            m.delivered += 1

    def batch_publish(self, events: List[BaseEvent]) -> int:
        """Publish multiple events atomically (sequenced consecutively).

        Args:
            events: List of BaseEvent instances to publish.

        Returns:
            Number of events published.
        """
        for event in events:
            self.publish(event)
            if events:
                self._metrics[events[0].event_type].batches = max(
                    1, self._metrics[events[0].event_type].batches
                )
        if events:
            self._metrics[events[0].event_type].batches += 1
        return len(events)

    # ------------------------------------------------------------------
    # Subscribe / Unsubscribe
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[BaseEvent], None],
        *,
        priority: int = 100,
        ticker_filter: Optional[str] = None,
    ) -> SubscriptionHandle:
        """Register a handler for a specific event type.

        Args:
            event_type: Which event type to listen to.
            handler: Callable that receives each matching event.
            priority: Lower number = called earlier. Default 100.
            ticker_filter: If provided, only deliver events where ticker matches.

        Returns:
            SubscriptionHandle that can be passed to unsubscribe().
        """
        handle = SubscriptionHandle(
            subscription_id=str(uuid.uuid4()),
            event_type=event_type,
            priority=priority,
            ticker_filter=ticker_filter,
            _handler=handler,
        )
        self._subscriptions[event_type].append(handle)
        self._subscriptions[event_type].sort(key=lambda h: h.priority)
        return handle

    def unsubscribe(self, subscription_id: str) -> bool:
        """Cancel a subscription by its ID.

        Args:
            subscription_id: ID from the SubscriptionHandle returned by subscribe().

        Returns:
            True if the subscription was found and removed; False otherwise.
        """
        for et in EventType:
            subs = self._subscriptions[et]
            for i, s in enumerate(subs):
                if s.subscription_id == subscription_id:
                    subs.pop(i)
                    return True
        return False

    def get_subscription_count(self, event_type: Optional[EventType] = None) -> int:
        """Return total number of active subscriptions.

        Args:
            event_type: If provided, count only for that type.

        Returns:
            Subscription count.
        """
        if event_type is not None:
            return len(self._subscriptions[event_type])
        return sum(len(v) for v in self._subscriptions.values())

    # ------------------------------------------------------------------
    # Replay / History
    # ------------------------------------------------------------------

    def get_history(
        self,
        event_type: EventType,
        max_events: int = 100,
        ticker: Optional[str] = None,
    ) -> List[BaseEvent]:
        """Return recent events of a given type from the ring buffer.

        Args:
            event_type: Which history to query.
            max_events: Maximum events to return (most-recent first).
            ticker: If provided, filter to events with matching ticker.

        Returns:
            List of BaseEvent ordered most-recent first.
        """
        history = list(self._history[event_type])
        if ticker:
            history = [e for e in history if getattr(e, "ticker", None) == ticker]
        return list(reversed(history))[:max_events]

    def replay_since(
        self,
        event_type: EventType,
        since_sequence: int,
        max_events: int = 1000,
    ) -> List[BaseEvent]:
        """Replay events with sequence number greater than since_sequence.

        Args:
            event_type: Which event type to replay.
            since_sequence: Replay events with sequence > this value.
            max_events: Maximum events to return.

        Returns:
            List of events in chronological order.
        """
        history = [e for e in self._history[event_type] if e.sequence > since_sequence]
        return history[:max_events]

    def clear_history(self, event_type: Optional[EventType] = None) -> None:
        """Clear the replay buffer.

        Args:
            event_type: If provided, clear only that type; else clear all.
        """
        if event_type is not None:
            self._history[event_type].clear()
        else:
            for et in EventType:
                self._history[et].clear()

    # ------------------------------------------------------------------
    # Filtering helpers
    # ------------------------------------------------------------------

    def get_filtered(
        self,
        event_type: EventType,
        ticker: Optional[str] = None,
        min_sequence: int = 0,
        max_results: int = 500,
    ) -> List[BaseEvent]:
        """Query history with combined filters.

        Args:
            event_type: Which event type to query.
            ticker: Ticker filter (None = all tickers).
            min_sequence: Only return events with sequence >= this value.
            max_results: Maximum events to return.

        Returns:
            Matching events in chronological order.
        """
        results = []
        for event in self._history[event_type]:
            if event.sequence < min_sequence:
                continue
            if ticker and getattr(event, "ticker", None) != ticker:
                continue
            results.append(event)
            if len(results) >= max_results:
                break
        return results

    # ------------------------------------------------------------------
    # Persistence hooks
    # ------------------------------------------------------------------

    def register_persistence_hook(
        self, hook: Callable[[BaseEvent], None]
    ) -> None:
        """Register a hook called synchronously on every published event.

        Args:
            hook: Callable that receives the event before subscribers.
        """
        self._persistence_hooks.append(hook)

    def remove_persistence_hook(self, hook: Callable[[BaseEvent], None]) -> bool:
        """Remove a previously registered persistence hook.

        Args:
            hook: The same callable reference passed to register_persistence_hook.

        Returns:
            True if found and removed; False otherwise.
        """
        try:
            self._persistence_hooks.remove(hook)
            return True
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(
        self, event_type: Optional[EventType] = None
    ) -> List[EventMetrics]:
        """Return operational metrics.

        Args:
            event_type: If provided, return only that type.

        Returns:
            List of EventMetrics (one per type, or one if filtered).
        """
        if event_type is not None:
            return [self._metrics[event_type]]
        return list(self._metrics.values())

    def get_total_published(self) -> int:
        """Return total events published across all types.

        Returns:
            Sum of published counters.
        """
        return sum(m.published for m in self._metrics.values())

    def reset_metrics(self) -> None:
        """Reset all operational counters to zero."""
        for et in EventType:
            self._metrics[et] = EventMetrics(event_type=et)

    def get_sequence(self) -> int:
        """Return the current sequence counter.

        Returns:
            Last sequence number assigned.
        """
        return self._sequence


# ---------------------------------------------------------------------------
# Convenience factory functions
# ---------------------------------------------------------------------------

def make_tick(
    ticker: str,
    price: float,
    volume: float,
    venue: str = "",
    *,
    timestamp: Optional[datetime] = None,
) -> TickEvent:
    """Create a TickEvent with auto-generated event_id and current timestamp.

    Args:
        ticker: Instrument symbol.
        price: Last trade price.
        volume: Trade volume.
        venue: Originating venue.
        timestamp: Override timestamp (default: now UTC).

    Returns:
        TickEvent instance.
    """
    return TickEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TICK,
        timestamp=timestamp or datetime.now(timezone.utc),
        ticker=ticker,
        price=price,
        volume=volume,
        venue=venue,
    )


def make_quote(
    ticker: str,
    bid: float,
    ask: float,
    bid_size: float = 0.0,
    ask_size: float = 0.0,
    venue: str = "",
    *,
    timestamp: Optional[datetime] = None,
) -> QuoteEvent:
    """Create a QuoteEvent with auto-generated event_id.

    Args:
        ticker: Instrument symbol.
        bid: Best bid price.
        ask: Best ask price.
        bid_size: Bid quantity.
        ask_size: Ask quantity.
        venue: Originating venue.
        timestamp: Override timestamp.

    Returns:
        QuoteEvent instance.
    """
    return QuoteEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.QUOTE,
        timestamp=timestamp or datetime.now(timezone.utc),
        ticker=ticker,
        bid=bid,
        ask=ask,
        bid_size=bid_size,
        ask_size=ask_size,
        venue=venue,
    )


def make_trade_event(
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    venue: str = "",
    *,
    trade_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> TradeEvent:
    """Create a TradeEvent with auto-generated IDs.

    Args:
        ticker: Instrument symbol.
        side: BUY or SELL.
        quantity: Trade size.
        price: Execution price.
        venue: Originating venue.
        trade_id: Override trade ID.
        timestamp: Override timestamp.

    Returns:
        TradeEvent instance.
    """
    return TradeEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TRADE,
        timestamp=timestamp or datetime.now(timezone.utc),
        trade_id=trade_id or str(uuid.uuid4()),
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        venue=venue,
    )


def make_order_book_event(
    ticker: str,
    bids: List[Tuple[float, float]],
    asks: List[Tuple[float, float]],
    is_snapshot: bool = True,
    venue: str = "",
    *,
    timestamp: Optional[datetime] = None,
) -> OrderBookEvent:
    """Create an OrderBookEvent.

    Args:
        ticker: Instrument symbol.
        bids: List of (price, size) bid levels.
        asks: List of (price, size) ask levels.
        is_snapshot: Full snapshot vs. incremental update.
        venue: Originating venue.
        timestamp: Override timestamp.

    Returns:
        OrderBookEvent instance.
    """
    return OrderBookEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.ORDER_BOOK,
        timestamp=timestamp or datetime.now(timezone.utc),
        ticker=ticker,
        bids=bids,
        asks=asks,
        is_snapshot=is_snapshot,
        venue=venue,
    )


def make_news_event(
    headline: str,
    source: str = "",
    body: str = "",
    tickers: Optional[List[str]] = None,
    sentiment_score: float = 0.0,
    risk_score: float = 0.0,
    *,
    timestamp: Optional[datetime] = None,
) -> NewsEvent:
    """Create a NewsEvent.

    Args:
        headline: Article headline.
        body: Full article body.
        source: News source.
        tickers: Related tickers.
        sentiment_score: [-1, 1] sentiment.
        risk_score: [0, 1] risk relevance.
        timestamp: Override timestamp.

    Returns:
        NewsEvent instance.
    """
    return NewsEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.NEWS,
        timestamp=timestamp or datetime.now(timezone.utc),
        headline=headline,
        body=body,
        source=source,
        tickers=tickers or [],
        sentiment_score=sentiment_score,
        risk_score=risk_score,
    )


def make_risk_event(
    risk_type: str,
    metric: str,
    value: float,
    threshold: float,
    breached: bool,
    ticker: str = "",
    *,
    timestamp: Optional[datetime] = None,
) -> RiskEvent:
    """Create a RiskEvent.

    Args:
        risk_type: Category (VAR, LEVERAGE, DRAWDOWN, etc.).
        metric: Specific metric name.
        value: Current value.
        threshold: Limit for breach determination.
        breached: Whether value exceeds threshold.
        ticker: Optional related ticker.
        timestamp: Override timestamp.

    Returns:
        RiskEvent instance.
    """
    return RiskEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.RISK,
        timestamp=timestamp or datetime.now(timezone.utc),
        risk_type=risk_type,
        metric=metric,
        value=value,
        threshold=threshold,
        breached=breached,
        ticker=ticker,
    )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[StreamingEngine] = None


def get_streaming_engine() -> StreamingEngine:
    """Return the singleton StreamingEngine instance.

    Returns:
        Shared StreamingEngine.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = StreamingEngine()
    return _default_engine
