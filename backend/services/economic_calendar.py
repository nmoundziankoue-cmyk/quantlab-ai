"""Economic Calendar service — economic events, releases, impact scoring (M7)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.economic_calendar import EconomicEvent

# ---------------------------------------------------------------------------
# Importance weights for impact scoring
# ---------------------------------------------------------------------------

_IMPORTANCE_WEIGHT = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.2}
_CATEGORY_WEIGHT = {
    "GDP": 1.0,
    "CPI": 0.95,
    "NFP": 0.95,
    "FED_RATE": 1.0,
    "PMI": 0.7,
    "UNEMPLOYMENT": 0.85,
    "RETAIL_SALES": 0.7,
    "HOUSING": 0.6,
    "TRADE_BALANCE": 0.55,
    "CONSUMER_CONFIDENCE": 0.6,
    "INDUSTRIAL_PRODUCTION": 0.6,
    "EARNINGS": 0.5,
    "BONDS": 0.4,
    "OTHER": 0.3,
}

# Sample economic events for seeding
_SAMPLE_EVENTS = [
    {
        "name": "US Non-Farm Payrolls",
        "country": "US",
        "currency": "USD",
        "importance": "HIGH",
        "category": "NFP",
        "actual": 256.0,
        "forecast": 220.0,
        "previous": 187.0,
        "unit": "K",
        "description": "Monthly change in employed persons, excl. farming",
        "affected_assets": ["USD", "SPX", "BONDS"],
    },
    {
        "name": "US CPI YoY",
        "country": "US",
        "currency": "USD",
        "importance": "HIGH",
        "category": "CPI",
        "actual": 3.2,
        "forecast": 3.1,
        "previous": 3.4,
        "unit": "%",
        "description": "Consumer Price Index year-over-year",
        "affected_assets": ["USD", "GOLD", "BONDS", "SPX"],
    },
    {
        "name": "Fed Interest Rate Decision",
        "country": "US",
        "currency": "USD",
        "importance": "HIGH",
        "category": "FED_RATE",
        "actual": 5.25,
        "forecast": 5.25,
        "previous": 5.0,
        "unit": "%",
        "description": "Federal Open Market Committee interest rate decision",
        "affected_assets": ["USD", "SPX", "BONDS", "GOLD", "CRYPTO"],
    },
    {
        "name": "US GDP QoQ",
        "country": "US",
        "currency": "USD",
        "importance": "HIGH",
        "category": "GDP",
        "actual": 2.4,
        "forecast": 2.0,
        "previous": 2.1,
        "unit": "%",
        "description": "Gross Domestic Product quarter-over-quarter growth",
        "affected_assets": ["USD", "SPX"],
    },
    {
        "name": "US Unemployment Rate",
        "country": "US",
        "currency": "USD",
        "importance": "HIGH",
        "category": "UNEMPLOYMENT",
        "actual": 3.9,
        "forecast": 3.8,
        "previous": 3.7,
        "unit": "%",
        "description": "Percentage of total workforce that is unemployed",
        "affected_assets": ["USD", "SPX"],
    },
    {
        "name": "Eurozone CPI YoY",
        "country": "EU",
        "currency": "EUR",
        "importance": "HIGH",
        "category": "CPI",
        "actual": 2.6,
        "forecast": 2.5,
        "previous": 2.9,
        "unit": "%",
        "description": "Eurozone consumer price index year-over-year",
        "affected_assets": ["EUR", "DAX", "STOXX50"],
    },
    {
        "name": "ECB Interest Rate Decision",
        "country": "EU",
        "currency": "EUR",
        "importance": "HIGH",
        "category": "FED_RATE",
        "actual": 4.25,
        "forecast": 4.25,
        "previous": 4.5,
        "unit": "%",
        "description": "European Central Bank deposit facility rate",
        "affected_assets": ["EUR", "DAX", "STOXX50", "BONDS"],
    },
    {
        "name": "US ISM Manufacturing PMI",
        "country": "US",
        "currency": "USD",
        "importance": "MEDIUM",
        "category": "PMI",
        "actual": 49.5,
        "forecast": 48.5,
        "previous": 47.8,
        "unit": "Index",
        "description": "Institute for Supply Management Manufacturing PMI",
        "affected_assets": ["USD", "SPX", "INDUSTRIALS"],
    },
    {
        "name": "UK GDP QoQ",
        "country": "UK",
        "currency": "GBP",
        "importance": "HIGH",
        "category": "GDP",
        "actual": 0.6,
        "forecast": 0.4,
        "previous": 0.3,
        "unit": "%",
        "description": "UK Gross Domestic Product quarter-over-quarter",
        "affected_assets": ["GBP", "FTSE100"],
    },
    {
        "name": "China Caixin Manufacturing PMI",
        "country": "CN",
        "currency": "CNY",
        "importance": "HIGH",
        "category": "PMI",
        "actual": 51.2,
        "forecast": 50.5,
        "previous": 50.1,
        "unit": "Index",
        "description": "China Caixin Manufacturing Purchasing Managers Index",
        "affected_assets": ["CNY", "HSI", "COMMODITIES"],
    },
    {
        "name": "US Retail Sales MoM",
        "country": "US",
        "currency": "USD",
        "importance": "MEDIUM",
        "category": "RETAIL_SALES",
        "actual": 0.7,
        "forecast": 0.3,
        "previous": -0.1,
        "unit": "%",
        "description": "Monthly change in retail and food service sales",
        "affected_assets": ["USD", "SPX", "CONSUMER"],
    },
    {
        "name": "US Housing Starts",
        "country": "US",
        "currency": "USD",
        "importance": "MEDIUM",
        "category": "HOUSING",
        "actual": 1421.0,
        "forecast": 1390.0,
        "previous": 1355.0,
        "unit": "K",
        "description": "Monthly measure of housing starts",
        "affected_assets": ["USD", "HOMEBUILDERS"],
    },
]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_event(
    db: Session,
    name: str,
    country: str,
    category: str,
    importance: str = "MEDIUM",
    currency: Optional[str] = None,
    actual: Optional[float] = None,
    forecast: Optional[float] = None,
    previous: Optional[float] = None,
    unit: Optional[str] = None,
    release_date: Optional[datetime] = None,
    description: Optional[str] = None,
    affected_assets: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EconomicEvent:
    impact = _compute_impact_score(importance, category, actual, forecast, previous)
    event = EconomicEvent(
        name=name,
        country=country.upper(),
        currency=currency,
        importance=importance.upper(),
        category=category.upper(),
        actual=actual,
        forecast=forecast,
        previous=previous,
        unit=unit,
        release_date=release_date,
        description=description,
        impact_score=impact,
        affected_assets={"assets": affected_assets or []},
        metadata_=metadata,
    )
    db.add(event)
    db.flush()
    return event


def get_event(db: Session, event_id: uuid.UUID) -> Optional[EconomicEvent]:
    return db.get(EconomicEvent, event_id)


def list_events(
    db: Session,
    country: Optional[str] = None,
    importance: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
) -> List[EconomicEvent]:
    stmt = select(EconomicEvent).order_by(EconomicEvent.release_date.desc()).limit(limit)
    if country:
        stmt = stmt.where(EconomicEvent.country == country.upper())
    if importance:
        stmt = stmt.where(EconomicEvent.importance == importance.upper())
    if category:
        stmt = stmt.where(EconomicEvent.category == category.upper())
    if start_date:
        stmt = stmt.where(EconomicEvent.release_date >= start_date)
    if end_date:
        stmt = stmt.where(EconomicEvent.release_date <= end_date)
    return list(db.execute(stmt).scalars())


def get_upcoming_events(db: Session, days: int = 7, limit: int = 50) -> List[EconomicEvent]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    return list_events(db, start_date=now, end_date=end, limit=limit)


def get_high_impact_events(db: Session, limit: int = 20) -> List[EconomicEvent]:
    stmt = (
        select(EconomicEvent)
        .where(EconomicEvent.importance == "HIGH")
        .order_by(EconomicEvent.impact_score.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


def update_event(
    db: Session,
    event_id: uuid.UUID,
    **kwargs: Any,
) -> Optional[EconomicEvent]:
    event = db.get(EconomicEvent, event_id)
    if not event:
        return None
    for k, v in kwargs.items():
        if hasattr(event, k):
            setattr(event, k, v)
    if "actual" in kwargs or "forecast" in kwargs or "importance" in kwargs:
        event.impact_score = _compute_impact_score(
            event.importance,
            event.category,
            event.actual,
            event.forecast,
            event.previous,
        )
    db.flush()
    return event


def delete_event(db: Session, event_id: uuid.UUID) -> bool:
    event = db.get(EconomicEvent, event_id)
    if not event:
        return False
    db.delete(event)
    db.flush()
    return True


def get_calendar_by_country(db: Session) -> Dict[str, Any]:
    events = list_events(db, limit=500)
    by_country: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        key = event.country
        if key not in by_country:
            by_country[key] = []
        by_country[key].append(_event_to_dict(event))
    return by_country


def seed_sample_events(db: Session) -> Dict[str, Any]:
    """Seed the database with sample economic events (idempotent by name)."""
    from sqlalchemy import func as sqlfunc
    created = 0
    now = datetime.now(timezone.utc)
    for i, ev in enumerate(_SAMPLE_EVENTS):
        existing = db.execute(
            select(EconomicEvent).where(EconomicEvent.name == ev["name"])
        ).scalars().first()
        if not existing:
            release_date = now - timedelta(days=30 - i * 2)
            create_event(
                db=db,
                name=ev["name"],
                country=ev["country"],
                category=ev["category"],
                importance=ev["importance"],
                currency=ev.get("currency"),
                actual=ev.get("actual"),
                forecast=ev.get("forecast"),
                previous=ev.get("previous"),
                unit=ev.get("unit"),
                release_date=release_date,
                description=ev.get("description"),
                affected_assets=ev.get("affected_assets", []),
            )
            created += 1
    return {"seeded": created, "total_sample_events": len(_SAMPLE_EVENTS)}


def get_impact_summary(db: Session) -> Dict[str, Any]:
    events = list_events(db, limit=1000)
    by_importance: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    by_country: Dict[str, int] = {}
    total_impact = 0.0
    for ev in events:
        by_importance[ev.importance] = by_importance.get(ev.importance, 0) + 1
        by_country[ev.country] = by_country.get(ev.country, 0) + 1
        total_impact += ev.impact_score or 0.0

    return {
        "total_events": len(events),
        "by_importance": by_importance,
        "by_country": by_country,
        "avg_impact_score": round(total_impact / max(len(events), 1), 3),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _compute_impact_score(
    importance: str,
    category: str,
    actual: Optional[float],
    forecast: Optional[float],
    previous: Optional[float],
) -> float:
    base = _IMPORTANCE_WEIGHT.get(importance.upper(), 0.3)
    cat_weight = _CATEGORY_WEIGHT.get(category.upper(), 0.3)
    score = base * cat_weight

    # Surprise factor
    if actual is not None and forecast is not None and forecast != 0:
        surprise = abs(actual - forecast) / abs(forecast)
        score += min(0.3, surprise * 0.5)

    return round(min(1.0, score), 4)


def _event_to_dict(e: EconomicEvent) -> Dict[str, Any]:
    return {
        "id": str(e.id),
        "name": e.name,
        "country": e.country,
        "currency": e.currency,
        "importance": e.importance,
        "category": e.category,
        "actual": e.actual,
        "forecast": e.forecast,
        "previous": e.previous,
        "unit": e.unit,
        "release_date": e.release_date.isoformat() if e.release_date else None,
        "impact_score": e.impact_score,
        "affected_assets": (e.affected_assets or {}).get("assets", []),
    }
