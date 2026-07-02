"""Watchlist REST router (Milestone 2).

Endpoints:
  GET    /watchlists                          — list all watchlists
  POST   /watchlists                          — create watchlist
  GET    /watchlists/{id}                     — get watchlist (with live quotes)
  PUT    /watchlists/{id}                     — rename watchlist
  DELETE /watchlists/{id}                     — delete watchlist
  POST   /watchlists/{id}/items               — add ticker to watchlist
  DELETE /watchlists/{id}/items/{item_id}     — remove ticker from watchlist
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.market import (
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemRead,
    WatchlistRead,
    WatchlistUpdate,
)
from services.quotes import get_quote
from services.watchlist import (
    DuplicateTickerError,
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
    add_item,
    create_watchlist,
    delete_item,
    delete_watchlist,
    get_watchlist,
    list_watchlists,
    update_watchlist,
)

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

DbSession = Annotated[Session, Depends(get_db)]


def _enrich_watchlist(wl, include_quotes: bool = True) -> dict:
    """Convert a Watchlist ORM object to a dict with optional live quotes."""
    items = []
    for it in wl.items:
        quote = None
        if include_quotes:
            try:
                quote = get_quote(it.ticker).model_dump()
            except Exception:
                pass
        items.append(
            {
                "id": it.id,
                "ticker": it.ticker,
                "notes": it.notes,
                "created_at": it.created_at,
                "quote": quote,
            }
        )
    return {
        "id": wl.id,
        "name": wl.name,
        "created_at": wl.created_at,
        "updated_at": wl.updated_at,
        "items": items,
    }


@router.get("", response_model=list[WatchlistRead], summary="List watchlists")
def route_list_watchlists(db: DbSession):
    """Return all watchlists with live quotes for each item."""
    wls = list_watchlists(db)
    return [_enrich_watchlist(wl) for wl in wls]


@router.post(
    "",
    response_model=WatchlistRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create watchlist",
)
def route_create_watchlist(payload: WatchlistCreate, db: DbSession):
    """Create a new empty watchlist."""
    wl = create_watchlist(db, payload)
    return _enrich_watchlist(wl, include_quotes=False)


@router.get("/{watchlist_id}", response_model=WatchlistRead, summary="Get watchlist")
def route_get_watchlist(watchlist_id: uuid.UUID, db: DbSession):
    """Return a watchlist with live quotes for all items."""
    try:
        wl = get_watchlist(db, watchlist_id)
    except WatchlistNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return _enrich_watchlist(wl)


@router.put("/{watchlist_id}", response_model=WatchlistRead, summary="Rename watchlist")
def route_update_watchlist(
    watchlist_id: uuid.UUID, payload: WatchlistUpdate, db: DbSession
):
    try:
        wl = update_watchlist(db, watchlist_id, payload)
    except WatchlistNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return _enrich_watchlist(wl)


@router.delete(
    "/{watchlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete watchlist",
)
def route_delete_watchlist(watchlist_id: uuid.UUID, db: DbSession):
    try:
        delete_watchlist(db, watchlist_id)
    except WatchlistNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")


@router.post(
    "/{watchlist_id}/items",
    response_model=WatchlistItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add ticker to watchlist",
)
def route_add_item(
    watchlist_id: uuid.UUID, payload: WatchlistItemCreate, db: DbSession
):
    try:
        item = add_item(db, watchlist_id, payload)
    except WatchlistNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    except DuplicateTickerError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{payload.ticker} is already in this watchlist",
        )

    quote = None
    try:
        quote = get_quote(item.ticker).model_dump()
    except Exception:
        pass

    return {
        "id": item.id,
        "ticker": item.ticker,
        "notes": item.notes,
        "created_at": item.created_at,
        "quote": quote,
    }


@router.delete(
    "/{watchlist_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove ticker from watchlist",
)
def route_delete_item(watchlist_id: uuid.UUID, item_id: uuid.UUID, db: DbSession):
    try:
        delete_item(db, watchlist_id, item_id)
    except WatchlistItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found"
        )
