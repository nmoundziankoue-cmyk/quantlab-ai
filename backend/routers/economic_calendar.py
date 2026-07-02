"""Economic Calendar router (M7) — events, releases, impact scoring."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import services.economic_calendar as svc
from schemas.economic_calendar import (
    CreateEconomicEventRequest,
    EconomicEventSchema,
    UpdateEconomicEventRequest,
)

router = APIRouter(prefix="/economic-calendar", tags=["Economic Calendar"])


@router.post("/events", response_model=Dict[str, Any])
def create_event(req: CreateEconomicEventRequest, db: Session = Depends(get_db)):
    """Create a new economic event."""
    event = svc.create_event(
        db=db,
        name=req.name,
        country=req.country,
        category=req.category,
        importance=req.importance,
        currency=req.currency,
        actual=req.actual,
        forecast=req.forecast,
        previous=req.previous,
        unit=req.unit,
        release_date=req.release_date,
        description=req.description,
        affected_assets=req.affected_assets,
        metadata=req.metadata,
    )
    return svc._event_to_dict(event)


@router.get("/events", response_model=List[Dict[str, Any]])
def list_events(
    country: Optional[str] = None,
    importance: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List economic events with optional filters."""
    events = svc.list_events(
        db, country=country, importance=importance, category=category, limit=limit
    )
    return [svc._event_to_dict(e) for e in events]


@router.get("/events/upcoming", response_model=List[Dict[str, Any]])
def get_upcoming_events(days: int = 7, limit: int = 50, db: Session = Depends(get_db)):
    """Return upcoming events within the next N days."""
    events = svc.get_upcoming_events(db, days=days, limit=limit)
    return [svc._event_to_dict(e) for e in events]


@router.get("/events/high-impact", response_model=List[Dict[str, Any]])
def get_high_impact_events(limit: int = 20, db: Session = Depends(get_db)):
    """Return the highest-impact economic events."""
    events = svc.get_high_impact_events(db, limit=limit)
    return [svc._event_to_dict(e) for e in events]


@router.get("/events/{event_id}", response_model=Dict[str, Any])
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific economic event."""
    event = svc.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return svc._event_to_dict(event)


@router.put("/events/{event_id}", response_model=Dict[str, Any])
def update_event(
    event_id: uuid.UUID,
    req: UpdateEconomicEventRequest,
    db: Session = Depends(get_db),
):
    """Update an economic event (e.g., when actual data is released)."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    event = svc.update_event(db, event_id, **update_data)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return svc._event_to_dict(event)


@router.delete("/events/{event_id}", response_model=Dict[str, Any])
def delete_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete an economic event."""
    ok = svc.delete_event(db, event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": str(event_id)}


@router.get("/by-country", response_model=Dict[str, Any])
def get_calendar_by_country(db: Session = Depends(get_db)):
    """Return all events grouped by country."""
    return svc.get_calendar_by_country(db)


@router.post("/seed", response_model=Dict[str, Any])
def seed_sample_events(db: Session = Depends(get_db)):
    """Seed the database with sample historical economic events."""
    return svc.seed_sample_events(db)


@router.get("/impact-summary", response_model=Dict[str, Any])
def get_impact_summary(db: Session = Depends(get_db)):
    """Return aggregate impact summary across all events."""
    return svc.get_impact_summary(db)
