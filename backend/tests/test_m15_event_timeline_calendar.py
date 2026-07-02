"""Tests for M15 EventTimeline and EventCalendar."""
import pytest
from services.event_engine import CorporateEventEngine, CorporateEventType, EventImportance, EventSeverity
from services.macro_event_engine import MacroEventEngine, MacroEventType
from services.event_timeline import EventTimeline, TimelineFilter, TimelineGrouping, TimelineGroup
from services.event_calendar import CalendarView, EventCalendar


def _corp_events():
    engine = CorporateEventEngine()
    for i, (ticker, etype) in enumerate([
        ("AAPL", CorporateEventType.EARNINGS),
        ("MSFT", CorporateEventType.DIVIDEND),
        ("GOOG", CorporateEventType.PRODUCT_LAUNCH),
    ]):
        engine.add_event(
            ticker=ticker, company=f"Co {i}", event_type=etype,
            description=f"Event {i}", sector="technology", industry="software",
            country="US", confidence=0.9, source="test",
            timestamp=1700000000.0 + i * 86400,
            importance=EventImportance.HIGH, severity=EventSeverity.MEDIUM,
            metadata={}, tags=[], event_id=f"corp-{i:03d}",
        )
    return engine.all_events()


def _macro_events():
    engine = MacroEventEngine()
    for i, etype in enumerate([MacroEventType.CPI, MacroEventType.GDP]):
        engine.add_event(
            event_type=etype, country="US", timestamp=1700000000.0 + i * 86400,
            importance=EventImportance.HIGH, description=f"Macro {i}",
            actual=3.2, forecast=3.1, previous=3.0, metadata={}, event_id=f"mac-{i:03d}",
        )
    return engine.all_events()


class TestEventTimeline:
    def setup_method(self):
        self.timeline = EventTimeline()
        self.corp = _corp_events()
        self.macro = _macro_events()

    def test_build_returns_list(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY)
        groups = self.timeline.build(self.corp, self.macro, f)
        assert isinstance(groups, list)

    def test_build_groups_are_timeline_group(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY)
        groups = self.timeline.build(self.corp, self.macro, f)
        assert all(isinstance(g, TimelineGroup) for g in groups)

    def test_build_day_grouping(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY)
        groups = self.timeline.build(self.corp, self.macro, f)
        assert len(groups) > 0

    def test_build_week_grouping(self):
        f = TimelineFilter(grouping=TimelineGrouping.WEEK)
        groups = self.timeline.build(self.corp, self.macro, f)
        assert isinstance(groups, list)

    def test_build_month_grouping(self):
        f = TimelineFilter(grouping=TimelineGrouping.MONTH)
        groups = self.timeline.build(self.corp, self.macro, f)
        assert isinstance(groups, list)

    def test_build_total_events_correct(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY)
        groups = self.timeline.build(self.corp, self.macro, f)
        total = sum(g.total_count for g in groups)
        assert total == 5

    def test_groups_have_label(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY)
        groups = self.timeline.build(self.corp, self.macro, f)
        for g in groups:
            assert g.label and len(g.label) > 0

    def test_groups_have_period_start(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY)
        groups = self.timeline.build(self.corp, self.macro, f)
        for g in groups:
            assert g.period_start >= 0

    def test_upcoming_returns_list(self):
        result = self.timeline.upcoming(self.corp, self.macro, since=1700000000.0 - 86400)
        assert isinstance(result, list)

    def test_upcoming_all_events(self):
        result = self.timeline.upcoming(self.corp, self.macro, since=0.0)
        assert len(result) == 5

    def test_heatmap_data_returns_list(self):
        result = self.timeline.heatmap_data(self.corp, self.macro, grouping=TimelineGrouping.DAY)
        assert isinstance(result, list)

    def test_heatmap_data_entries_have_count(self):
        result = self.timeline.heatmap_data(self.corp, self.macro, grouping=TimelineGrouping.DAY)
        for entry in result:
            assert "count" in entry

    def test_heatmap_data_entries_have_label(self):
        result = self.timeline.heatmap_data(self.corp, self.macro, grouping=TimelineGrouping.DAY)
        for entry in result:
            assert "label" in entry

    def test_timeline_grouping_enum_values(self):
        assert TimelineGrouping.DAY in TimelineGrouping
        assert TimelineGrouping.WEEK in TimelineGrouping
        assert TimelineGrouping.MONTH in TimelineGrouping

    def test_filter_by_ticker(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY, tickers=["AAPL"])
        groups = self.timeline.build(self.corp, self.macro, f)
        # Macro events without ticker may still pass if _matches_macro ignores tickers
        corp_total = sum(g.corporate_count for g in groups)
        assert corp_total == 1

    def test_filter_by_since(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY, since=1700086000.0)
        groups = self.timeline.build(self.corp, self.macro, f)
        total = sum(g.total_count for g in groups)
        assert total < 5

    def test_groups_sorted_ascending(self):
        f = TimelineFilter(grouping=TimelineGrouping.DAY)
        groups = self.timeline.build(self.corp, self.macro, f)
        starts = [g.period_start for g in groups]
        assert starts == sorted(starts)


class TestEventCalendar:
    def setup_method(self):
        self.cal = EventCalendar()
        self.corp = _corp_events()
        self.macro = _macro_events()

    def test_agenda_view_returns_list(self):
        result = self.cal.agenda_view(self.corp, self.macro)
        assert isinstance(result, list)

    def test_agenda_view_has_all_events(self):
        result = self.cal.agenda_view(self.corp, self.macro)
        assert len(result) == 5

    def test_day_view_returns_dict(self):
        result = self.cal.day_view(self.corp, self.macro, 1700000000.0)
        assert isinstance(result, dict)

    def test_day_view_has_entries(self):
        result = self.cal.day_view(self.corp, self.macro, 1700000000.0)
        assert "entries" in result

    def test_week_view_returns_list(self):
        result = self.cal.week_view(self.corp, self.macro, 1700000000.0)
        assert isinstance(result, list)

    def test_week_view_has_7_days(self):
        result = self.cal.week_view(self.corp, self.macro, 1700000000.0)
        assert len(result) == 7

    def test_month_view_returns_list(self):
        result = self.cal.month_view(self.corp, self.macro, 1700000000.0)
        assert isinstance(result, list)

    def test_heatmap_returns_list(self):
        result = self.cal.heatmap(self.corp, self.macro, TimelineGrouping.DAY)
        assert isinstance(result, list)

    def test_heatmap_entries_have_count(self):
        result = self.cal.heatmap(self.corp, self.macro, TimelineGrouping.DAY)
        for entry in result:
            assert "count" in entry

    def test_upcoming_returns_list(self):
        result = self.cal.upcoming(self.corp, self.macro, since=0.0)
        assert isinstance(result, list)

    def test_upcoming_all_events(self):
        result = self.cal.upcoming(self.corp, self.macro, since=0.0)
        assert len(result) == 5

    def test_past_returns_list(self):
        result = self.cal.past(self.corp, self.macro, until=9999999999.0)
        assert isinstance(result, list)

    def test_statistics_returns_dict(self):
        stats = self.cal.statistics(self.corp, self.macro)
        assert isinstance(stats, dict)

    def test_statistics_has_total(self):
        stats = self.cal.statistics(self.corp, self.macro)
        assert "total_entries" in stats

    def test_statistics_total_correct(self):
        stats = self.cal.statistics(self.corp, self.macro)
        assert stats["total_entries"] == 5

    def test_agenda_entries_have_timestamp(self):
        entries = self.cal.agenda_view(self.corp, self.macro)
        for e in entries:
            assert e["timestamp"] > 0

    def test_agenda_entries_have_kind(self):
        entries = self.cal.agenda_view(self.corp, self.macro)
        for e in entries:
            assert e["kind"] in ("corporate", "macro")

    def test_day_view_empty_for_far_future(self):
        result = self.cal.day_view(self.corp, self.macro, 9999999999.0)
        assert result["total_count"] == 0

    def test_calendar_view_enum_has_views(self):
        assert CalendarView.AGENDA in CalendarView
        assert CalendarView.HEATMAP in CalendarView
        assert CalendarView.UPCOMING in CalendarView

    def test_statistics_corporate_count(self):
        stats = self.cal.statistics(self.corp, self.macro)
        assert stats["corporate_count"] == 3

    def test_statistics_macro_count(self):
        stats = self.cal.statistics(self.corp, self.macro)
        assert stats["macro_count"] == 2
