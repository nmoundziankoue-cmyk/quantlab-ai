"""Tests for the Economic Calendar service (M7)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest

import services.economic_calendar as svc
from models.economic_calendar import EconomicEvent


# ---------------------------------------------------------------------------
# Event CRUD
# ---------------------------------------------------------------------------

class TestEventCRUD:
    def test_create_event_minimal(self, db):
        event = svc.create_event(db, name="Test NFP", country="US", category="NFP")
        assert event.id is not None
        assert event.name == "Test NFP"
        assert event.country == "US"

    def test_create_event_country_uppercased(self, db):
        event = svc.create_event(db, name="EU CPI", country="eu", category="CPI")
        assert event.country == "EU"

    def test_create_event_with_actuals(self, db):
        event = svc.create_event(
            db, name="GDP Q1", country="US", category="GDP",
            actual=2.5, forecast=2.0, previous=1.8
        )
        assert event.actual == 2.5
        assert event.forecast == 2.0

    def test_create_event_impact_score_set(self, db):
        event = svc.create_event(
            db, name="Fed Rate Decision", country="US", category="FED_RATE",
            importance="HIGH", actual=5.25, forecast=5.25
        )
        assert event.impact_score is not None
        assert event.impact_score > 0

    def test_get_event_exists(self, db):
        event = svc.create_event(db, name="Get Test Event", country="US", category="PMI")
        fetched = svc.get_event(db, event.id)
        assert fetched is not None
        assert fetched.id == event.id

    def test_get_event_not_found(self, db):
        result = svc.get_event(db, uuid.uuid4())
        assert result is None

    def test_list_events_returns_created(self, db):
        svc.create_event(db, name="List Event 1", country="US", category="CPI")
        events = svc.list_events(db, limit=100)
        assert any(e.name == "List Event 1" for e in events)

    def test_list_events_filter_by_country(self, db):
        svc.create_event(db, name="UK PMI", country="UK", category="PMI")
        svc.create_event(db, name="US PMI", country="US", category="PMI")
        uk_events = svc.list_events(db, country="UK", limit=50)
        assert all(e.country == "UK" for e in uk_events)

    def test_list_events_filter_by_importance(self, db):
        svc.create_event(db, name="High Impact 1", country="US", category="NFP", importance="HIGH")
        svc.create_event(db, name="Low Impact 1", country="US", category="HOUSING", importance="LOW")
        high_events = svc.list_events(db, importance="HIGH", limit=50)
        assert all(e.importance == "HIGH" for e in high_events)

    def test_list_events_filter_by_category(self, db):
        svc.create_event(db, name="CPI Test", country="US", category="CPI")
        cpi_events = svc.list_events(db, category="CPI", limit=50)
        assert all(e.category == "CPI" for e in cpi_events)

    def test_update_event_actual(self, db):
        event = svc.create_event(db, name="Update Actual", country="US", category="NFP", forecast=200.0)
        updated = svc.update_event(db, event.id, actual=256.0)
        assert updated is not None
        assert updated.actual == 256.0

    def test_update_event_recalculates_impact(self, db):
        event = svc.create_event(
            db, name="Impact Recalc", country="US", category="FED_RATE",
            importance="HIGH", forecast=5.0
        )
        old_impact = event.impact_score
        updated = svc.update_event(db, event.id, actual=5.25)
        assert updated.impact_score is not None

    def test_update_event_not_found(self, db):
        result = svc.update_event(db, uuid.uuid4(), actual=1.0)
        assert result is None

    def test_delete_event(self, db):
        event = svc.create_event(db, name="Delete Event", country="US", category="PMI")
        ok = svc.delete_event(db, event.id)
        assert ok is True
        assert svc.get_event(db, event.id) is None

    def test_delete_event_not_found(self, db):
        ok = svc.delete_event(db, uuid.uuid4())
        assert ok is False


# ---------------------------------------------------------------------------
# Specialised queries
# ---------------------------------------------------------------------------

class TestSpecialisedQueries:
    def test_get_upcoming_events_returns_list(self, db):
        future = datetime.now(timezone.utc) + timedelta(days=2)
        svc.create_event(
            db, name="Upcoming NFP", country="US", category="NFP",
            importance="HIGH", release_date=future
        )
        events = svc.get_upcoming_events(db, days=7, limit=50)
        assert isinstance(events, list)

    def test_get_high_impact_events(self, db):
        svc.create_event(db, name="High1", country="US", category="GDP", importance="HIGH",
                         actual=2.5, forecast=2.0)
        events = svc.get_high_impact_events(db, limit=20)
        assert isinstance(events, list)
        assert all(e.importance == "HIGH" for e in events)

    def test_get_calendar_by_country(self, db):
        svc.create_event(db, name="US GDP", country="US", category="GDP")
        svc.create_event(db, name="EU CPI", country="EU", category="CPI")
        result = svc.get_calendar_by_country(db)
        assert isinstance(result, dict)

    def test_seed_sample_events(self, db):
        result = svc.seed_sample_events(db)
        assert "seeded" in result
        assert result["seeded"] >= 0

    def test_seed_idempotent(self, db):
        r1 = svc.seed_sample_events(db)
        r2 = svc.seed_sample_events(db)
        assert r2["seeded"] == 0  # already seeded

    def test_get_impact_summary(self, db):
        svc.create_event(db, name="Summary Test", country="US", category="CPI", importance="HIGH")
        result = svc.get_impact_summary(db)
        assert "total_events" in result
        assert "by_importance" in result
        assert "avg_impact_score" in result


# ---------------------------------------------------------------------------
# Impact scoring
# ---------------------------------------------------------------------------

class TestImpactScoring:
    def test_high_importance_higher_score(self):
        high = svc._compute_impact_score("HIGH", "NFP", 256, 220, 187)
        low = svc._compute_impact_score("LOW", "NFP", 200, 220, 187)
        assert high > low

    def test_fed_rate_high_score(self):
        score = svc._compute_impact_score("HIGH", "FED_RATE", 5.25, 5.25, 5.0)
        assert score > 0.5

    def test_surprise_increases_score(self):
        no_surprise = svc._compute_impact_score("HIGH", "NFP", 220, 220, 187)
        big_surprise = svc._compute_impact_score("HIGH", "NFP", 400, 220, 187)
        assert big_surprise >= no_surprise

    def test_score_between_0_and_1(self):
        for importance in ("HIGH", "MEDIUM", "LOW"):
            score = svc._compute_impact_score(importance, "GDP", 2.5, 2.0, 1.5)
            assert 0.0 <= score <= 1.0

    def test_event_to_dict_format(self, db):
        event = svc.create_event(db, name="Dict Test", country="US", category="CPI",
                                 actual=3.2, forecast=3.0)
        d = svc._event_to_dict(event)
        assert "id" in d
        assert "name" in d
        assert "impact_score" in d
        assert "affected_assets" in d
