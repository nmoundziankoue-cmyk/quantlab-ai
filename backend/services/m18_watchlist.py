"""M18 — Watchlist System: institutional multi-list instrument tracking.

Provides multi-list management, real-time price tracking, custom metadata,
screener integration, alert thresholds, list sharing/export, and portfolio
overlap analysis.

Pure Python, no external libraries.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WatchlistCategory(str, Enum):
    """Purpose category of a watchlist."""
    EQUITY_LONG = "EQUITY_LONG"
    EQUITY_SHORT = "EQUITY_SHORT"
    MACRO_HEDGES = "MACRO_HEDGES"
    EARNINGS_PLAYS = "EARNINGS_PLAYS"
    TECHNICAL_SETUPS = "TECHNICAL_SETUPS"
    FUNDAMENTAL_RESEARCH = "FUNDAMENTAL_RESEARCH"
    M_AND_A = "M_AND_A"
    SECTOR_ROTATION = "SECTOR_ROTATION"
    CUSTOM = "CUSTOM"


class AlertTrigger(str, Enum):
    """Condition that triggers a watchlist item alert."""
    PRICE_ABOVE = "PRICE_ABOVE"
    PRICE_BELOW = "PRICE_BELOW"
    VOLUME_SPIKE = "VOLUME_SPIKE"
    RSI_OVERBOUGHT = "RSI_OVERBOUGHT"
    RSI_OVERSOLD = "RSI_OVERSOLD"
    EARNINGS_DATE = "EARNINGS_DATE"
    CUSTOM = "CUSTOM"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WatchlistItem:
    """A single instrument tracked in a watchlist.

    Args:
        item_id: Unique identifier.
        ticker: Instrument symbol.
        added_at: When it was added.
        notes: Analyst notes.
        tags: Arbitrary tags.
        target_price: Price target.
        stop_loss: Stop-loss price.
        alert_thresholds: Dict of AlertTrigger → threshold value.
        last_price: Most recently updated price.
        last_updated: Timestamp of last price update.
        sector: GICS sector.
        conviction: Analyst conviction score 1-10.
    """

    item_id: str
    ticker: str
    added_at: datetime
    notes: str
    tags: List[str]
    target_price: float
    stop_loss: float
    alert_thresholds: Dict[str, float]
    last_price: float
    last_updated: Optional[datetime]
    sector: str
    conviction: int

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "item_id": self.item_id,
            "ticker": self.ticker,
            "added_at": self.added_at.isoformat(),
            "notes": self.notes,
            "tags": self.tags,
            "target_price": round(self.target_price, 4),
            "stop_loss": round(self.stop_loss, 4),
            "alert_thresholds": {k: round(v, 4) for k, v in self.alert_thresholds.items()},
            "last_price": round(self.last_price, 4),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "sector": self.sector,
            "conviction": self.conviction,
        }


@dataclass
class Watchlist:
    """A named collection of instruments.

    Args:
        list_id: Unique identifier.
        name: Human-readable name.
        description: Longer description.
        category: Watchlist category.
        owner: Owner identifier.
        is_shared: Whether the list is visible to all users.
        items: Dict of ticker → WatchlistItem.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        tags: List-level tags.
    """

    list_id: str
    name: str
    description: str
    category: WatchlistCategory
    owner: str
    is_shared: bool
    items: List[WatchlistItem]
    created_at: datetime
    updated_at: datetime
    tags: List[str]

    def to_dict(self, include_items: bool = True) -> Dict[str, Any]:
        """Return JSON-serialisable dict.

        Args:
            include_items: Whether to include full item details.
        """
        d: Dict[str, Any] = {
            "list_id": self.list_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "owner": self.owner,
            "is_shared": self.is_shared,
            "item_count": len(self.items),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
        }
        if include_items:
            d["items"] = [item.to_dict() for item in self.items]
        return d


@dataclass
class ScreenerResult:
    """A ticker that matched a screener criteria set.

    Args:
        ticker: Instrument symbol.
        matched_criteria: List of criteria descriptions that matched.
        score: Composite match score.
        metadata: Additional data attached.
    """

    ticker: str
    matched_criteria: List[str]
    score: float
    metadata: Dict[str, Any]

    @property
    def conviction(self) -> int:
        """Conviction score from metadata."""
        return int(self.metadata.get("conviction", 0))

    @property
    def sector(self) -> str:
        """Sector from metadata."""
        return str(self.metadata.get("sector", ""))

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "matched_criteria": self.matched_criteria,
            "score": round(self.score, 4),
            "conviction": self.conviction,
            "sector": self.sector,
            "metadata": self.metadata,
        }


@dataclass
class PortfolioOverlap:
    """Overlap analysis between a watchlist and an existing portfolio.

    Args:
        watchlist_name: Name of the watchlist.
        portfolio_tickers: Set of portfolio tickers.
        watchlist_tickers: Set of watchlist tickers.
        overlap_tickers: Tickers in both.
        overlap_pct: Fraction of watchlist already in portfolio.
        new_ideas: Watchlist tickers not yet in portfolio.
    """

    watchlist_name: str
    portfolio_tickers: List[str]
    watchlist_tickers: List[str]
    overlap_tickers: List[str]
    overlap_pct: float
    new_ideas: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "watchlist_name": self.watchlist_name,
            "portfolio_tickers": sorted(self.portfolio_tickers),
            "watchlist_tickers": sorted(self.watchlist_tickers),
            "overlap_tickers": sorted(self.overlap_tickers),
            "overlap_count": len(self.overlap_tickers),
            "overlap_pct": round(self.overlap_pct, 4),
            "new_ideas": sorted(self.new_ideas),
        }


@dataclass
class WatchlistAlert:
    """An alert fired when a watchlist item threshold is breached.

    Args:
        alert_id: Unique identifier.
        list_id: Source watchlist ID.
        ticker: Instrument symbol.
        trigger: Which trigger fired.
        current_value: Current value of the monitored field.
        threshold: Threshold that was breached.
        message: Human-readable message.
        timestamp: Alert time.
    """

    alert_id: str
    list_id: str
    ticker: str
    trigger: AlertTrigger
    current_value: float
    threshold: float
    message: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "alert_id": self.alert_id,
            "list_id": self.list_id,
            "ticker": self.ticker,
            "trigger": self.trigger.value,
            "current_value": round(self.current_value, 4),
            "threshold": round(self.threshold, 4),
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Watchlist System
# ---------------------------------------------------------------------------

class WatchlistSystem:
    """Institutional multi-list watchlist management system."""

    def __init__(self) -> None:
        self._lists: Dict[str, Watchlist] = {}
        self._alert_history: List[WatchlistAlert] = []

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def create_list(
        self,
        name: str,
        description: str = "",
        category: WatchlistCategory = WatchlistCategory.CUSTOM,
        owner: str = "default",
        is_shared: bool = False,
        tags: Optional[List[str]] = None,
    ) -> Watchlist:
        """Create a new watchlist.

        Args:
            name: List name.
            description: Description.
            category: Purpose category.
            owner: Owner identifier.
            is_shared: Whether visible to all.
            tags: Optional tags.

        Returns:
            Watchlist.

        Raises:
            ValueError: If name already exists for this owner.
        """
        for wl in self._lists.values():
            if wl.name == name and wl.owner == owner:
                raise ValueError(f"Watchlist '{name}' already exists for owner '{owner}'")
        now = datetime.now(timezone.utc)
        wl = Watchlist(
            list_id=str(uuid.uuid4()),
            name=name, description=description,
            category=category, owner=owner,
            is_shared=is_shared, items=[],
            created_at=now, updated_at=now,
            tags=tags or [],
        )
        self._lists[wl.list_id] = wl
        return wl

    def get_list(self, list_id: str) -> Optional[Watchlist]:
        """Retrieve a watchlist by ID.

        Args:
            list_id: Watchlist identifier.

        Returns:
            Watchlist or None.
        """
        return self._lists.get(list_id)

    def delete_list(self, list_id: str) -> bool:
        """Delete a watchlist.

        Args:
            list_id: Watchlist identifier.

        Returns:
            True if deleted.
        """
        if list_id in self._lists:
            del self._lists[list_id]
            return True
        return False

    def list_watchlists(
        self,
        owner: Optional[str] = None,
        category: Optional[WatchlistCategory] = None,
        include_shared: bool = True,
    ) -> List[Watchlist]:
        """List watchlists with optional filters.

        Args:
            owner: Filter by owner.
            category: Filter by category.
            include_shared: Include shared lists.

        Returns:
            List of Watchlist objects.
        """
        lists = list(self._lists.values())
        if owner:
            lists = [wl for wl in lists if wl.owner == owner or (include_shared and wl.is_shared)]
        if category:
            lists = [wl for wl in lists if wl.category == category]
        return sorted(lists, key=lambda wl: wl.updated_at, reverse=True)

    def update_list(
        self,
        list_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_shared: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Watchlist]:
        """Update watchlist metadata.

        Args:
            list_id: Watchlist identifier.
            name: New name.
            description: New description.
            is_shared: New shared status.
            tags: New tags.

        Returns:
            Updated Watchlist or None.
        """
        wl = self._lists.get(list_id)
        if not wl:
            return None
        if name is not None:
            wl.name = name
        if description is not None:
            wl.description = description
        if is_shared is not None:
            wl.is_shared = is_shared
        if tags is not None:
            wl.tags = tags
        wl.updated_at = datetime.now(timezone.utc)
        return wl

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    def add_item(
        self,
        list_id: str,
        ticker: str,
        notes: str = "",
        tags: Optional[List[str]] = None,
        target_price: float = 0.0,
        stop_loss: float = 0.0,
        sector: str = "UNKNOWN",
        conviction: int = 5,
        alert_thresholds: Optional[Dict[str, float]] = None,
        alerts: Optional[List[Any]] = None,
        alert_threshold: Optional[float] = None,
    ) -> WatchlistItem:
        """Add an instrument to a watchlist.

        Args:
            list_id: Watchlist identifier.
            ticker: Instrument symbol.
            notes: Analyst notes.
            tags: Tags.
            target_price: Price target.
            stop_loss: Stop-loss level.
            sector: GICS sector.
            conviction: 1-10 conviction score.
            alert_thresholds: Dict of trigger name → threshold.

        Returns:
            WatchlistItem.

        Raises:
            ValueError: If list not found or ticker already present.
        """
        wl = self._lists.get(list_id)
        if not wl:
            raise ValueError(f"Watchlist {list_id} not found")
        t = ticker.upper()
        if any(i.ticker == t for i in wl.items):
            raise ValueError(f"{t} already in watchlist {list_id}")
        resolved_thresholds = dict(alert_thresholds or {})
        if alerts and alert_threshold is not None:
            for trigger in alerts:
                key = trigger.value if hasattr(trigger, "value") else str(trigger)
                resolved_thresholds[key] = alert_threshold
        item = WatchlistItem(
            item_id=str(uuid.uuid4()),
            ticker=t,
            added_at=datetime.now(timezone.utc),
            notes=notes, tags=tags or [],
            target_price=target_price, stop_loss=stop_loss,
            alert_thresholds=resolved_thresholds,
            last_price=0.0, last_updated=None,
            sector=sector,
            conviction=max(1, min(10, conviction)),
        )
        wl.items.append(item)
        wl.updated_at = datetime.now(timezone.utc)
        return item

    def remove_item(self, list_id: str, ticker: str) -> bool:
        """Remove an item from a watchlist.

        Args:
            list_id: Watchlist identifier.
            ticker: Instrument symbol.

        Returns:
            True if removed.
        """
        wl = self._lists.get(list_id)
        if not wl:
            return False
        t = ticker.upper()
        before = len(wl.items)
        wl.items = [i for i in wl.items if i.ticker != t]
        if len(wl.items) < before:
            wl.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def update_item(
        self,
        list_id: str,
        ticker: str,
        notes: Optional[str] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        conviction: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[WatchlistItem]:
        """Update metadata on a watchlist item.

        Args:
            list_id: Watchlist identifier.
            ticker: Instrument symbol.
            notes: New notes.
            target_price: New price target.
            stop_loss: New stop-loss.
            conviction: New conviction score.
            tags: New tags.

        Returns:
            Updated WatchlistItem or None.
        """
        wl = self._lists.get(list_id)
        if not wl:
            return None
        t = ticker.upper()
        item = next((i for i in wl.items if i.ticker == t), None)
        if not item:
            return None
        if notes is not None:
            item.notes = notes
        if target_price is not None:
            item.target_price = target_price
        if stop_loss is not None:
            item.stop_loss = stop_loss
        if conviction is not None:
            item.conviction = max(1, min(10, conviction))
        if tags is not None:
            item.tags = tags
        wl.updated_at = datetime.now(timezone.utc)
        return item

    # ------------------------------------------------------------------
    # Price updates and alerts
    # ------------------------------------------------------------------

    def update_price(
        self,
        list_id: str,
        ticker: str,
        price: float,
        volume_ratio: float = 1.0,
        rsi: float = 50.0,
    ) -> List[WatchlistAlert]:
        """Update the price for a watchlist item and check alert thresholds.

        Args:
            list_id: Watchlist identifier.
            ticker: Instrument symbol.
            price: Current market price.
            volume_ratio: Current / avg volume ratio.
            rsi: Current RSI value.

        Returns:
            List of WatchlistAlert objects that were triggered.
        """
        wl = self._lists.get(list_id)
        if not wl:
            return []
        t = ticker.upper()
        item = next((i for i in wl.items if i.ticker == t), None)
        if not item:
            return []
        item.last_price = price
        item.last_updated = datetime.now(timezone.utc)
        fired: List[WatchlistAlert] = []
        field_map = {
            AlertTrigger.PRICE_ABOVE.value: ("price", price),
            AlertTrigger.PRICE_BELOW.value: ("price", price),
            AlertTrigger.VOLUME_SPIKE.value: ("volume_ratio", volume_ratio),
            AlertTrigger.RSI_OVERBOUGHT.value: ("rsi", rsi),
            AlertTrigger.RSI_OVERSOLD.value: ("rsi", rsi),
        }
        for trigger_name, threshold in item.alert_thresholds.items():
            field_info = field_map.get(trigger_name)
            if not field_info:
                continue
            field_label, current_val = field_info
            triggered = False
            if trigger_name == AlertTrigger.PRICE_ABOVE.value and current_val > threshold:
                triggered = True
            elif trigger_name == AlertTrigger.PRICE_BELOW.value and current_val < threshold:
                triggered = True
            elif trigger_name == AlertTrigger.VOLUME_SPIKE.value and current_val > threshold:
                triggered = True
            elif trigger_name == AlertTrigger.RSI_OVERBOUGHT.value and current_val > threshold:
                triggered = True
            elif trigger_name == AlertTrigger.RSI_OVERSOLD.value and current_val < threshold:
                triggered = True
            if triggered:
                try:
                    trig_enum = AlertTrigger(trigger_name)
                except ValueError:
                    trig_enum = AlertTrigger.CUSTOM
                alert = WatchlistAlert(
                    alert_id=str(uuid.uuid4()),
                    list_id=list_id, ticker=t,
                    trigger=trig_enum,
                    current_value=current_val,
                    threshold=threshold,
                    message=(f"{t}: {trigger_name} triggered "
                             f"(value={current_val:.4g}, threshold={threshold:.4g})"),
                    timestamp=datetime.now(timezone.utc),
                )
                fired.append(alert)
                self._alert_history.append(alert)
        return fired

    def get_alerts(
        self,
        list_id: Optional[str] = None,
        ticker: Optional[str] = None,
        limit: int = 50,
    ) -> List[WatchlistAlert]:
        """Retrieve watchlist alert history.

        Args:
            list_id: Filter by watchlist.
            ticker: Filter by ticker.
            limit: Maximum records.

        Returns:
            List of WatchlistAlert (newest first).
        """
        results = list(reversed(self._alert_history))
        if list_id:
            results = [a for a in results if a.list_id == list_id]
        if ticker:
            t = ticker.upper()
            results = [a for a in results if a.ticker == t]
        return results[:limit]

    # ------------------------------------------------------------------
    # Screener
    # ------------------------------------------------------------------

    def get_all_lists(self) -> List[Watchlist]:
        """Return all watchlists.

        Returns:
            List of all Watchlist objects.
        """
        return self.list_watchlists()

    def screen(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[ScreenerResult]:
        """Screen all watchlist items against criteria.

        Supported criteria keys: min_conviction, max_conviction, sector,
        min_target_price, max_target_price, tags (list intersection).

        Args:
            criteria: Screening criteria dict (or pass kwargs directly).

        Returns:
            List of ScreenerResult.
        """
        if criteria is None:
            criteria = kwargs
        results: List[ScreenerResult] = []
        seen: Set[str] = set()
        for wl in self._lists.values():
            for item in wl.items:
                if item.ticker in seen:
                    continue
                matched: List[str] = []
                score = 0.0
                min_conv = criteria.get("min_conviction")
                if min_conv is not None and item.conviction >= int(min_conv):
                    matched.append(f"conviction>={min_conv}")
                    score += 1.0
                max_conv = criteria.get("max_conviction")
                if max_conv is not None and item.conviction <= int(max_conv):
                    matched.append(f"conviction<={max_conv}")
                    score += 0.5
                sector = criteria.get("sector")
                if sector and item.sector.upper() == sector.upper():
                    matched.append(f"sector={sector}")
                    score += 1.5
                req_tags = criteria.get("tags", [])
                if req_tags:
                    item_tag_set = set(item.tags)
                    hit = item_tag_set & set(req_tags)
                    if hit:
                        matched.append(f"tags={hit}")
                        score += len(hit) * 0.5
                no_criteria = not any([
                    criteria.get("min_conviction") is not None,
                    criteria.get("max_conviction") is not None,
                    criteria.get("sector"),
                    criteria.get("tags"),
                ])
                if matched or no_criteria:
                    results.append(ScreenerResult(
                        ticker=item.ticker,
                        matched_criteria=matched,
                        score=score,
                        metadata={"sector": item.sector, "conviction": item.conviction},
                    ))
                    seen.add(item.ticker)
        results.sort(key=lambda r: -r.score)
        return results

    # ------------------------------------------------------------------
    # Portfolio overlap
    # ------------------------------------------------------------------

    def analyse_portfolio_overlap(
        self, list_id: str, portfolio_tickers: List[str]
    ) -> PortfolioOverlap:
        """Analyse overlap between a watchlist and a portfolio.

        Args:
            list_id: Watchlist identifier.
            portfolio_tickers: Current portfolio tickers.

        Returns:
            PortfolioOverlap.

        Raises:
            ValueError: If watchlist not found.
        """
        wl = self._lists.get(list_id)
        if not wl:
            raise ValueError(f"Watchlist {list_id} not found")
        port_set = {t.upper() for t in portfolio_tickers}
        watch_set = {i.ticker for i in wl.items}
        overlap = port_set & watch_set
        new_ideas = watch_set - port_set
        overlap_pct = len(overlap) / len(watch_set) if watch_set else 0.0
        return PortfolioOverlap(
            watchlist_name=wl.name,
            portfolio_tickers=sorted(port_set),
            watchlist_tickers=sorted(watch_set),
            overlap_tickers=sorted(overlap),
            overlap_pct=overlap_pct,
            new_ideas=sorted(new_ideas),
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_list(self, list_id: str) -> List[Dict[str, Any]]:
        """Export a watchlist as a flat list of dicts (CSV-ready).

        Args:
            list_id: Watchlist identifier.

        Returns:
            List of item dicts.

        Raises:
            ValueError: If list not found.
        """
        wl = self._lists.get(list_id)
        if not wl:
            raise ValueError(f"Watchlist {list_id} not found")
        return [
            {
                "ticker": item.ticker,
                "sector": item.sector,
                "conviction": item.conviction,
                "target_price": item.target_price,
                "stop_loss": item.stop_loss,
                "last_price": item.last_price,
                "notes": item.notes,
                "tags": ",".join(item.tags),
                "added_at": item.added_at.isoformat(),
            }
            for item in wl.items
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Return system-level statistics.

        Returns:
            Dict with counts and summary info.
        """
        total_items = sum(len(wl.items) for wl in self._lists.values())
        return {
            "total_lists": len(self._lists),
            "total_items": total_items,
            "shared_lists": sum(1 for wl in self._lists.values() if wl.is_shared),
            "total_alerts_fired": len(self._alert_history),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_system: Optional[WatchlistSystem] = None


def get_watchlist_system() -> WatchlistSystem:
    """Return the singleton WatchlistSystem.

    Returns:
        Shared WatchlistSystem instance.
    """
    global _default_system
    if _default_system is None:
        _default_system = WatchlistSystem()
    return _default_system
