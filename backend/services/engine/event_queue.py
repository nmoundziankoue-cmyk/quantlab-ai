"""M11 Phase 1 — Priority event queue.

Events are ordered by (priority, insertion_order) so that within a single
bar, MARKET events are always processed before SIGNAL events, which are
processed before ORDER events, etc.

The queue is deliberately not thread-safe: the event-driven backtester is
single-threaded (deterministic replay), so locking would be wasteful.
"""

from __future__ import annotations

from typing import Any, Iterator

from services.engine.events import (
    PRIORITY_FILL,
    PRIORITY_MARKET,
    PRIORITY_ORDER,
    PRIORITY_PORTFOLIO,
    PRIORITY_SIGNAL,
    FillEvent,
    MarketEvent,
    OrderEvent,
    PortfolioEvent,
    SignalEvent,
)

_AnyEvent = MarketEvent | SignalEvent | OrderEvent | FillEvent | PortfolioEvent


class EventQueue:
    """Ordered queue of backtesting events.

    Events are dequeued in (priority, insertion_order) order:
        MARKET < SIGNAL < ORDER < FILL < PORTFOLIO

    Usage::

        q = EventQueue()
        q.push(MarketEvent(ticker="AAPL", timestamp="2024-01-02", ...))
        q.push(SignalEvent(ticker="AAPL", timestamp="2024-01-02", signal="BUY"))

        while not q.is_empty():
            event = q.pop()
            ...
    """

    def __init__(self) -> None:
        self._items: list[tuple[int, int, _AnyEvent]] = []
        self._counter: int = 0

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def push(self, event: _AnyEvent) -> None:
        """Enqueue *event*.  Priority is read from ``event.priority``."""
        self._items.append((event.priority, self._counter, event))
        self._counter += 1
        self._items.sort(key=lambda x: (x[0], x[1]))

    def pop(self) -> _AnyEvent:
        """Remove and return the highest-priority event (lowest priority number).

        Raises ``IndexError`` if the queue is empty.
        """
        if not self._items:
            raise IndexError("pop from an empty EventQueue")
        _, _, event = self._items.pop(0)
        return event

    def peek(self) -> _AnyEvent:
        """Return (without removing) the next event to be dequeued.

        Raises ``IndexError`` if the queue is empty.
        """
        if not self._items:
            raise IndexError("peek at an empty EventQueue")
        return self._items[0][2]

    def is_empty(self) -> bool:
        """Return True iff the queue contains no events."""
        return len(self._items) == 0

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[_AnyEvent]:
        """Drain the queue in priority order (destructive iteration)."""
        while not self.is_empty():
            yield self.pop()

    # ------------------------------------------------------------------
    # Convenience: typed pushers (cleaner call sites in backtester)
    # ------------------------------------------------------------------

    def push_market(self, **kwargs: Any) -> None:
        self.push(MarketEvent(**kwargs))

    def push_signal(self, **kwargs: Any) -> None:
        self.push(SignalEvent(**kwargs))

    def push_order(self, **kwargs: Any) -> None:
        self.push(OrderEvent(**kwargs))

    def push_fill(self, **kwargs: Any) -> None:
        self.push(FillEvent(**kwargs))

    def push_portfolio(self, **kwargs: Any) -> None:
        self.push(PortfolioEvent(**kwargs))

    # ------------------------------------------------------------------
    # Bulk helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Remove all events."""
        self._items.clear()

    def drain_by_type(self, event_type: str) -> list[_AnyEvent]:
        """Remove and return all events of the given ``event_type``."""
        kept: list[tuple[int, int, _AnyEvent]] = []
        drained: list[_AnyEvent] = []
        for item in self._items:
            if item[2].event_type == event_type:
                drained.append(item[2])
            else:
                kept.append(item)
        self._items = kept
        return drained
