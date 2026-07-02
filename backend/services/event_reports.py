"""M15 Phase 10 — Event Report Generator.

Generates structured institutional research reports (Daily, Weekly, Monthly,
Company, Sector, Macro, Portfolio, Catalyst). PDF-ready structured objects.
Pure Python, deterministic.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from services.event_engine import CorporateEvent, EventImportance
from services.macro_event_engine import MacroEvent
from services.market_catalyst import CatalystScore


# ---------------------------------------------------------------------------
# Report types
# ---------------------------------------------------------------------------

class ReportType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    COMPANY = "company"
    SECTOR = "sector"
    MACRO = "macro"
    PORTFOLIO = "portfolio"
    CATALYST = "catalyst"


# ---------------------------------------------------------------------------
# Report Section dataclass
# ---------------------------------------------------------------------------

@dataclass
class ReportSection:
    """A single section in a research report."""

    title: str
    content: str
    data: Optional[Dict[str, Any]] = None
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "data": self.data or {},
            "order": self.order,
        }


# ---------------------------------------------------------------------------
# EventReport dataclass
# ---------------------------------------------------------------------------

@dataclass
class EventReport:
    """Institutional research report — PDF-ready structured object."""

    report_id: str
    report_type: ReportType
    title: str
    subtitle: str
    generated_at: float
    period_start: Optional[float]
    period_end: Optional[float]
    sections: List[ReportSection] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "title": self.title,
            "subtitle": self.subtitle,
            "generated_at": self.generated_at,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "summary": self.summary,
            "sections": [s.to_dict() for s in sorted(self.sections, key=lambda x: x.order)],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# EventReportGenerator
# ---------------------------------------------------------------------------

def _ts_to_date(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _importance_filter(events: List[CorporateEvent], min_imp: EventImportance) -> List[CorporateEvent]:
    order = [EventImportance.LOW, EventImportance.MEDIUM, EventImportance.HIGH, EventImportance.CRITICAL]
    min_rank = order.index(min_imp)
    return [e for e in events if order.index(e.importance) >= min_rank]


class EventReportGenerator:
    """Generates structured research reports from event data."""

    def _make_id(self, report_type: ReportType) -> str:
        import uuid
        return f"RPT-{report_type.value.upper()}-{uuid.uuid4().hex[:8].upper()}"

    def _event_summary_lines(self, events: List[CorporateEvent], max_items: int = 10) -> str:
        lines = []
        for ev in events[:max_items]:
            date = _ts_to_date(ev.timestamp)
            lines.append(f"• [{date}] {ev.ticker} — {ev.event_type.value.replace('_', ' ').title()} ({ev.importance.value}): {ev.description[:80]}")
        return "\n".join(lines) if lines else "No events in this period."

    def _macro_summary_lines(self, events: List[MacroEvent], max_items: int = 5) -> str:
        lines = []
        for ev in events[:max_items]:
            date = _ts_to_date(ev.timestamp)
            surp = f" Surprise: {ev.surprise_pct:+.2f}%" if ev.surprise_pct is not None else ""
            lines.append(f"• [{date}] {ev.event_type.value.upper()} ({ev.country}){surp}: {ev.description[:80]}")
        return "\n".join(lines) if lines else "No macro events in this period."

    def generate_daily(
        self,
        corporate_events: List[CorporateEvent],
        macro_events: List[MacroEvent],
        date_ts: Optional[float] = None,
    ) -> EventReport:
        """Generate a daily event intelligence report."""
        now = time.time()
        date_ts = date_ts or now
        date_str = _ts_to_date(date_ts)
        report_id = self._make_id(ReportType.DAILY)

        high_corp = _importance_filter(corporate_events, EventImportance.HIGH)
        corp_summary = self._event_summary_lines(high_corp, 8)
        macro_summary = self._macro_summary_lines(macro_events, 5)

        by_type: Dict[str, int] = {}
        for ev in corporate_events:
            by_type[ev.event_type.value] = by_type.get(ev.event_type.value, 0) + 1

        summary = (
            f"Daily Intelligence Report — {date_str}. "
            f"{len(corporate_events)} corporate events and {len(macro_events)} macro events observed."
        )

        sections = [
            ReportSection(
                title="Executive Overview",
                content=summary,
                data={"corporate_count": len(corporate_events), "macro_count": len(macro_events)},
                order=1,
            ),
            ReportSection(
                title="High-Impact Corporate Events",
                content=corp_summary,
                data={"events": [e.to_dict() for e in high_corp[:8]]},
                order=2,
            ),
            ReportSection(
                title="Macro Releases",
                content=macro_summary,
                data={"events": [e.to_dict() for e in macro_events[:5]]},
                order=3,
            ),
            ReportSection(
                title="Event Distribution",
                content=f"Event breakdown by type: {', '.join(f'{k}: {v}' for k, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5])}",
                data={"by_type": by_type},
                order=4,
            ),
        ]

        return EventReport(
            report_id=report_id,
            report_type=ReportType.DAILY,
            title=f"Daily Event Intelligence — {date_str}",
            subtitle="Institutional Event Monitoring | ApexQuant",
            generated_at=now,
            period_start=date_ts,
            period_end=date_ts + 86400,
            sections=sections,
            summary=summary,
            metadata={"event_count": len(corporate_events), "macro_count": len(macro_events)},
        )

    def generate_company(
        self,
        ticker: str,
        corporate_events: List[CorporateEvent],
        catalysts: Optional[List[CatalystScore]] = None,
    ) -> EventReport:
        """Generate a company-specific event intelligence report."""
        now = time.time()
        ticker_events = [e for e in corporate_events if e.ticker.upper() == ticker.upper()]
        company = ticker_events[0].company if ticker_events else ticker
        report_id = self._make_id(ReportType.COMPANY)

        corp_summary = self._event_summary_lines(ticker_events, 15)
        cat_summary = ""
        if catalysts:
            ticker_cats = [c for c in catalysts if c.ticker.upper() == ticker.upper()]
            if ticker_cats:
                avg_score = sum(c.composite_score for c in ticker_cats) / len(ticker_cats)
                cat_summary = f"Average catalyst score: {avg_score:.3f}. Themes: {', '.join(set(c.theme.value for c in ticker_cats))}."

        summary = (
            f"Company Intelligence Report: {company} ({ticker.upper()}). "
            f"{len(ticker_events)} events analysed."
        )

        sections = [
            ReportSection(
                title="Company Overview",
                content=summary,
                data={"ticker": ticker.upper(), "event_count": len(ticker_events)},
                order=1,
            ),
            ReportSection(
                title="Event Timeline",
                content=corp_summary,
                data={"events": [e.to_dict() for e in ticker_events[:15]]},
                order=2,
            ),
            ReportSection(
                title="Catalyst Analysis",
                content=cat_summary or "No catalyst data available.",
                data={"catalysts": [c.to_dict() for c in (catalysts or [])]},
                order=3,
            ),
            ReportSection(
                title="Sector & Industry Context",
                content=(
                    f"Sector: {ticker_events[0].sector if ticker_events else 'N/A'}. "
                    f"Industry: {ticker_events[0].industry if ticker_events else 'N/A'}. "
                    f"Country: {ticker_events[0].country if ticker_events else 'N/A'}."
                ),
                order=4,
            ),
        ]

        return EventReport(
            report_id=report_id,
            report_type=ReportType.COMPANY,
            title=f"Company Intelligence: {company} ({ticker.upper()})",
            subtitle="Institutional Event Analysis | ApexQuant",
            generated_at=now,
            period_start=min((e.timestamp for e in ticker_events), default=now),
            period_end=max((e.timestamp for e in ticker_events), default=now),
            sections=sections,
            summary=summary,
            metadata={"ticker": ticker.upper(), "event_count": len(ticker_events)},
        )

    def generate_sector(
        self,
        sector: str,
        corporate_events: List[CorporateEvent],
    ) -> EventReport:
        """Generate a sector-level event intelligence report."""
        now = time.time()
        sector_events = [e for e in corporate_events if e.sector.lower() == sector.lower()]
        report_id = self._make_id(ReportType.SECTOR)

        tickers = list({e.ticker for e in sector_events})
        corp_summary = self._event_summary_lines(sector_events, 10)

        by_type: Dict[str, int] = {}
        for ev in sector_events:
            by_type[ev.event_type.value] = by_type.get(ev.event_type.value, 0) + 1

        summary = (
            f"Sector Intelligence Report: {sector.title()}. "
            f"{len(sector_events)} events across {len(tickers)} tickers."
        )

        sections = [
            ReportSection(title="Sector Overview", content=summary, data={"event_count": len(sector_events), "tickers": tickers}, order=1),
            ReportSection(title="Key Events", content=corp_summary, data={"events": [e.to_dict() for e in sector_events[:10]]}, order=2),
            ReportSection(title="Event Distribution", content=str(by_type), data={"by_type": by_type}, order=3),
        ]

        return EventReport(
            report_id=report_id,
            report_type=ReportType.SECTOR,
            title=f"Sector Intelligence: {sector.title()}",
            subtitle="Institutional Sector Analysis | ApexQuant",
            generated_at=now,
            period_start=min((e.timestamp for e in sector_events), default=now),
            period_end=max((e.timestamp for e in sector_events), default=now),
            sections=sections,
            summary=summary,
            metadata={"sector": sector, "event_count": len(sector_events)},
        )

    def generate_macro(
        self,
        macro_events: List[MacroEvent],
        period_label: str = "Current",
    ) -> EventReport:
        """Generate a macro intelligence report."""
        now = time.time()
        report_id = self._make_id(ReportType.MACRO)
        macro_summary = self._macro_summary_lines(macro_events, 10)
        high_impact = [e for e in macro_events if e.importance.value in ("critical", "high")]

        summary = (
            f"Macro Intelligence Report — {period_label}. "
            f"{len(macro_events)} macro events with {len(high_impact)} high-impact releases."
        )

        sections = [
            ReportSection(title="Macro Overview", content=summary, data={"count": len(macro_events)}, order=1),
            ReportSection(title="Key Macro Releases", content=macro_summary, data={"events": [e.to_dict() for e in macro_events[:10]]}, order=2),
            ReportSection(title="High-Impact Events", content=self._macro_summary_lines(high_impact), data={"events": [e.to_dict() for e in high_impact]}, order=3),
        ]

        return EventReport(
            report_id=report_id,
            report_type=ReportType.MACRO,
            title=f"Macro Intelligence — {period_label}",
            subtitle="Institutional Macro Analysis | ApexQuant",
            generated_at=now,
            period_start=min((e.timestamp for e in macro_events), default=now) if macro_events else now,
            period_end=max((e.timestamp for e in macro_events), default=now) if macro_events else now,
            sections=sections,
            summary=summary,
            metadata={"macro_count": len(macro_events)},
        )

    def generate_catalyst(
        self,
        catalysts: List[CatalystScore],
        corporate_events: Optional[List[CorporateEvent]] = None,
    ) -> EventReport:
        """Generate a catalyst-focused report."""
        now = time.time()
        report_id = self._make_id(ReportType.CATALYST)

        from services.market_catalyst import CatalystDirection
        bullish = [c for c in catalysts if c.direction == CatalystDirection.BULLISH]
        bearish = [c for c in catalysts if c.direction == CatalystDirection.BEARISH]
        neutral = [c for c in catalysts if c.direction == CatalystDirection.NEUTRAL]

        top_bull = sorted(bullish, key=lambda c: c.composite_score, reverse=True)[:5]
        top_bear = sorted(bearish, key=lambda c: c.composite_score, reverse=True)[:5]

        def _cat_lines(cats: List[CatalystScore]) -> str:
            return "\n".join(f"• {c.ticker} — {c.theme.value} score={c.composite_score:.3f}" for c in cats) or "None."

        summary = f"Catalyst Report: {len(catalysts)} catalysts — {len(bullish)} bullish, {len(bearish)} bearish, {len(neutral)} neutral."

        sections = [
            ReportSection(title="Catalyst Overview", content=summary, data={"total": len(catalysts), "bullish": len(bullish), "bearish": len(bearish)}, order=1),
            ReportSection(title="Top Bullish Catalysts", content=_cat_lines(top_bull), data={"catalysts": [c.to_dict() for c in top_bull]}, order=2),
            ReportSection(title="Top Bearish Catalysts", content=_cat_lines(top_bear), data={"catalysts": [c.to_dict() for c in top_bear]}, order=3),
        ]

        return EventReport(
            report_id=report_id,
            report_type=ReportType.CATALYST,
            title="Catalyst Intelligence Report",
            subtitle="Institutional Catalyst Analysis | ApexQuant",
            generated_at=now,
            period_start=now - 86400 * 30,
            period_end=now,
            sections=sections,
            summary=summary,
            metadata={"catalyst_count": len(catalysts)},
        )
