"""Tests for M15 EventReportGenerator."""
import pytest
from services.event_engine import CorporateEventEngine, CorporateEventType, EventImportance, EventSeverity
from services.macro_event_engine import MacroEventEngine, MacroEventType
from services.event_reports import EventReport, EventReportGenerator, ReportType


def _corp_events():
    engine = CorporateEventEngine()
    for i, (ticker, etype, sector) in enumerate([
        ("AAPL", CorporateEventType.EARNINGS, "technology"),
        ("MSFT", CorporateEventType.PRODUCT_LAUNCH, "technology"),
        ("JNJ", CorporateEventType.FDA_APPROVAL, "healthcare"),
    ]):
        engine.add_event(
            ticker=ticker, company=f"Co {i}", event_type=etype,
            description=f"Event {i} description text for report", sector=sector,
            industry="general", country="US", confidence=0.9, source="test",
            timestamp=1700000000.0 + i * 3600, importance=EventImportance.HIGH,
            severity=EventSeverity.MEDIUM, metadata={}, tags=[], event_id=f"ev-{i:03d}",
        )
    return engine.all_events()


def _macro_events():
    engine = MacroEventEngine()
    for i, etype in enumerate([MacroEventType.CPI, MacroEventType.FOMC]):
        engine.add_event(
            event_type=etype, country="US", timestamp=1700000000.0 + i * 3600,
            importance=EventImportance.HIGH, description=f"Macro {i} description",
            actual=3.2, forecast=3.1, previous=3.0, metadata={}, event_id=f"mac-{i:03d}",
        )
    return engine.all_events()


class TestEventReportGenerator:
    def setup_method(self):
        self.gen = EventReportGenerator()
        self.corp = _corp_events()
        self.macro = _macro_events()

    def test_generate_daily_returns_event_report(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert isinstance(report, EventReport)

    def test_daily_report_has_id(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert report.report_id and len(report.report_id) > 0

    def test_daily_report_has_title(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert report.title and len(report.title) > 0

    def test_daily_report_type(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert report.report_type == ReportType.DAILY

    def test_daily_report_has_summary(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert report.summary and len(report.summary) > 0

    def test_daily_report_sections_is_list(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert isinstance(report.sections, list)

    def test_daily_report_has_sections(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert len(report.sections) > 0

    def test_daily_report_generated_at_is_float(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert isinstance(report.generated_at, float)
        assert report.generated_at > 0

    def test_generate_company_returns_report(self):
        report = self.gen.generate_company("AAPL", self.corp)
        assert isinstance(report, EventReport)

    def test_company_report_type(self):
        report = self.gen.generate_company("AAPL", self.corp)
        assert report.report_type == ReportType.COMPANY

    def test_company_report_title_has_ticker(self):
        report = self.gen.generate_company("AAPL", self.corp)
        assert "AAPL" in report.title

    def test_generate_sector_returns_report(self):
        report = self.gen.generate_sector("technology", self.corp)
        assert isinstance(report, EventReport)

    def test_sector_report_type(self):
        report = self.gen.generate_sector("technology", self.corp)
        assert report.report_type == ReportType.SECTOR

    def test_generate_macro_returns_report(self):
        report = self.gen.generate_macro(self.macro)
        assert isinstance(report, EventReport)

    def test_macro_report_type(self):
        report = self.gen.generate_macro(self.macro)
        assert report.report_type == ReportType.MACRO

    def test_generate_catalyst_returns_report(self):
        from services.market_catalyst import MarketCatalystEngine
        from services.event_engine import CorporateEvent, CorporateEventType, EventImportance, EventSeverity
        engine = MarketCatalystEngine()
        catalysts = engine.classify_batch(self.corp)
        report = self.gen.generate_catalyst(catalysts)
        assert isinstance(report, EventReport)

    def test_catalyst_report_type(self):
        from services.market_catalyst import MarketCatalystEngine
        engine = MarketCatalystEngine()
        catalysts = engine.classify_batch(self.corp)
        report = self.gen.generate_catalyst(catalysts)
        assert report.report_type == ReportType.CATALYST

    def test_report_type_enum_has_8_values(self):
        assert len(list(ReportType)) == 8

    def test_report_type_has_portfolio(self):
        assert ReportType.PORTFOLIO in ReportType

    def test_report_type_has_weekly(self):
        assert ReportType.WEEKLY in ReportType

    def test_sections_have_title_and_content(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        for section in report.sections:
            assert section.title and len(section.title) > 0
            assert section.content is not None

    def test_company_unknown_ticker_returns_report(self):
        report = self.gen.generate_company("UNKNOWN", self.corp)
        assert isinstance(report, EventReport)

    def test_sector_unknown_returns_report(self):
        report = self.gen.generate_sector("quantumcomputing", self.corp)
        assert isinstance(report, EventReport)

    def test_reports_have_subtitle(self):
        report = self.gen.generate_daily(self.corp, self.macro)
        assert report.subtitle is not None

    def test_daily_with_empty_data(self):
        report = self.gen.generate_daily([], [])
        assert isinstance(report, EventReport)

    def test_company_with_empty_data(self):
        report = self.gen.generate_company("AAPL", [])
        assert isinstance(report, EventReport)
