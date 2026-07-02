"""Watchlist CRUD service."""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import Session

from models.watchlist import Watchlist, WatchlistItem
from schemas.market import WatchlistCreate, WatchlistItemCreate, WatchlistRead, WatchlistUpdate


class WatchlistNotFoundError(Exception):
    """Raised when a watchlist with the given ID does not exist."""


class WatchlistItemNotFoundError(Exception):
    """Raised when a watchlist item with the given ID does not exist."""


class DuplicateTickerError(Exception):
    """Raised when a ticker already exists in the watchlist."""


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------

def list_watchlists(db: Session) -> Sequence[Watchlist]:
    """Return all watchlists ordered newest first."""
    return db.query(Watchlist).order_by(Watchlist.created_at.desc()).all()


def get_watchlist(db: Session, watchlist_id: uuid.UUID) -> Watchlist:
    """Fetch a watchlist by primary key.

    Raises:
        WatchlistNotFoundError: If not found.
    """
    wl: Optional[Watchlist] = (
        db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    )
    if wl is None:
        raise WatchlistNotFoundError(watchlist_id)
    return wl


def create_watchlist(db: Session, payload: WatchlistCreate) -> Watchlist:
    """Create and persist a new watchlist."""
    wl = Watchlist(name=payload.name)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return wl


def update_watchlist(
    db: Session, watchlist_id: uuid.UUID, payload: WatchlistUpdate
) -> Watchlist:
    """Partially update a watchlist.

    Raises:
        WatchlistNotFoundError: If not found.
    """
    wl = get_watchlist(db, watchlist_id)
    updates = payload.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(wl, k, v)
    db.commit()
    db.refresh(wl)
    return wl


def delete_watchlist(db: Session, watchlist_id: uuid.UUID) -> None:
    """Delete a watchlist and all its items (cascade).

    Raises:
        WatchlistNotFoundError: If not found.
    """
    wl = get_watchlist(db, watchlist_id)
    db.delete(wl)
    db.commit()


# ---------------------------------------------------------------------------
# Watchlist item CRUD
# ---------------------------------------------------------------------------

def add_item(
    db: Session, watchlist_id: uuid.UUID, payload: WatchlistItemCreate
) -> WatchlistItem:
    """Add a ticker to a watchlist.

    Raises:
        WatchlistNotFoundError:  If the watchlist does not exist.
        DuplicateTickerError:    If the ticker is already in this watchlist.
    """
    get_watchlist(db, watchlist_id)  # existence check

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        ticker=payload.ticker,
        notes=payload.notes,
    )
    db.add(item)
    try:
        db.commit()
    except sa_exc.IntegrityError:
        db.rollback()
        raise DuplicateTickerError(payload.ticker)
    db.refresh(item)
    return item


def delete_item(
    db: Session, watchlist_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    """Remove an item from a watchlist.

    Raises:
        WatchlistItemNotFoundError: If no matching item exists.
    """
    item: Optional[WatchlistItem] = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.id == item_id,
            WatchlistItem.watchlist_id == watchlist_id,
        )
        .first()
    )
    if item is None:
        raise WatchlistItemNotFoundError(item_id)
    db.delete(item)
    db.commit()
