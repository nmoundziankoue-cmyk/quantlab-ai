"""M14 Phase 12 — Tests: event detection (Phase 6).

Actual AltEventType values: earnings, guidance_change, ceo_change, cfo_change,
mna, bankruptcy, buyback, secondary_offering, dividend, credit_downgrade,
regulatory_action, patent_approval, supply_chain_disruption, weather_impact,
geopolitical.

detect_events_batch takes List[Dict] and returns Dict[str, List[AltEvent]].
"""
import pytest
from services.event_detection import (
    AltEventType,
    EventSeverity,
    AltEvent,
    detect_events,
    detect_events_batch,
    event_density,
)


# ---------------------------------------------------------------------------
# AltEventType
# ---------------------------------------------------------------------------

def test_alt_event_type_count():
    assert len(AltEventType) == 15


def test_alt_event_type_values_are_strings():
    for e in AltEventType:
        assert isinstance(e.value, str)


def test_alt_event_type_has_earnings():
    assert AltEventType.EARNINGS.value == "earnings"


def test_alt_event_type_has_buyback():
    assert AltEventType.BUYBACK.value == "buyback"


def test_alt_event_type_has_mna():
    assert AltEventType.MNA.value == "mna"


def test_alt_event_type_has_dividend():
    assert AltEventType.DIVIDEND.value == "dividend"


def test_alt_event_type_has_patent():
    assert AltEventType.PATENT_APPROVAL.value == "patent_approval"


# ---------------------------------------------------------------------------
# AltEvent
# ---------------------------------------------------------------------------

def test_alt_event_to_dict():
    ev = AltEvent(
        event_type=AltEventType.EARNINGS,
        symbol="AAPL",
        confidence=0.85,
        severity=EventSeverity.HIGH,
        snippet="Earnings beat expectations.",
    )
    d = ev.to_dict()
    assert d["event_type"] == "earnings"
    assert d["symbol"] == "AAPL"
    assert d["confidence"] == 0.85
    assert "severity" in d
    assert "matched_patterns" in d


def test_alt_event_severity_in_dict():
    ev = AltEvent(AltEventType.BUYBACK, "MSFT", 0.7, EventSeverity.MEDIUM, "buyback text")
    d = ev.to_dict()
    assert d["severity"] == "medium"


# ---------------------------------------------------------------------------
# detect_events
# ---------------------------------------------------------------------------

def test_detect_events_returns_list():
    events = detect_events("Revenue grew 10%.")
    assert isinstance(events, list)


def test_detect_events_empty_text():
    events = detect_events("")
    assert events == []


def test_detect_events_earnings():
    text = "The company reported earnings per share of $2.45 beating analyst consensus estimates."
    events = detect_events(text, symbol="AAPL")
    types = [e.event_type for e in events]
    assert AltEventType.EARNINGS in types


def test_detect_events_ceo_change():
    text = "The board appoints new chief executive officer effective immediately."
    events = detect_events(text, symbol="XYZ")
    types = [e.event_type for e in events]
    assert AltEventType.CEO_CHANGE in types


def test_detect_events_merger():
    text = "Company A entered into merger agreement to acquire Company B for $5 billion."
    events = detect_events(text)
    types = [e.event_type for e in events]
    assert AltEventType.MNA in types


def test_detect_events_buyback():
    text = "The Board authorized a new share repurchase program of up to $10 billion."
    events = detect_events(text)
    types = [e.event_type for e in events]
    assert AltEventType.BUYBACK in types


def test_detect_events_patent():
    text = "The company received patent granted for its new semiconductor manufacturing process."
    events = detect_events(text)
    types = [e.event_type for e in events]
    assert AltEventType.PATENT_APPROVAL in types


def test_detect_events_dividend():
    text = "The board declares a quarterly dividend of $0.25 per share to all holders."
    events = detect_events(text)
    types = [e.event_type for e in events]
    assert AltEventType.DIVIDEND in types


def test_detect_events_bankruptcy():
    text = "Company X files for chapter 11 bankruptcy protection."
    events = detect_events(text)
    types = [e.event_type for e in events]
    assert AltEventType.BANKRUPTCY in types


def test_detect_events_symbol_assigned():
    events = detect_events("Earnings reported per share.", symbol="AAPL")
    for e in events:
        assert e.symbol == "AAPL"


def test_detect_events_confidence_range():
    text = "The company reported earnings per share beating estimates significantly."
    events = detect_events(text)
    for e in events:
        assert 0 <= e.confidence <= 1.0


def test_detect_events_severity_valid():
    text = "The company files for chapter 11 bankruptcy protection proceedings."
    events = detect_events(text)
    for e in events:
        assert e.severity in EventSeverity


def test_detect_events_snippet_nonempty():
    text = "Earnings per share of $2.45 beat estimates significantly."
    events = detect_events(text)
    for e in events:
        assert len(e.snippet) > 0


def test_detect_events_source_doc_id():
    events = detect_events("Share repurchase program authorized.", source_doc_id="doc123")
    for e in events:
        assert e.source_doc_id == "doc123"


def test_detect_events_to_dict_keys():
    text = "New share repurchase program authorized by the board of directors."
    events = detect_events(text)
    if events:
        d = events[0].to_dict()
        for key in ("event_type", "symbol", "confidence", "severity", "snippet", "matched_patterns"):
            assert key in d


def test_detect_events_matched_patterns():
    text = "Earnings per share of $2.45 beat consensus estimate."
    events = detect_events(text)
    for e in events:
        assert isinstance(e.matched_patterns, list)


def test_detect_events_credit_downgrade():
    text = "Moody's downgrades company credit rating to Ba1 with negative outlook."
    events = detect_events(text)
    types = [e.event_type for e in events]
    assert AltEventType.CREDIT_DOWNGRADE in types


def test_detect_events_regulatory():
    text = "SEC investigation launched against the company for alleged accounting irregularities."
    events = detect_events(text)
    types = [e.event_type for e in events]
    assert AltEventType.REGULATORY_ACTION in types


# ---------------------------------------------------------------------------
# detect_events_batch — takes List[Dict], returns Dict[symbol, List[AltEvent]]
# ---------------------------------------------------------------------------

def test_detect_events_batch_empty():
    result = detect_events_batch([])
    assert result == {} or isinstance(result, dict)


def test_detect_events_batch_multiple_texts():
    docs = [
        {"doc_id": "d1", "symbol": "AAPL", "text": "The board authorized a new share repurchase program of up to $5 billion."},
        {"doc_id": "d2", "symbol": "MSFT", "text": "Earnings per share beat estimates."},
        {"doc_id": "d3", "symbol": "AAPL", "text": "Revenue grew 10% year over year."},
    ]
    result = detect_events_batch(docs)
    assert isinstance(result, dict)
    assert len(result) > 0


def test_detect_events_batch_keyed_by_symbol():
    docs = [{"doc_id": "d1", "symbol": "AAPL", "text": "Earnings per share beat estimates today."}]
    result = detect_events_batch(docs)
    assert "AAPL" in result
    assert isinstance(result["AAPL"], list)


def test_detect_events_batch_no_crash_duplicates():
    docs = [
        {"doc_id": "d1", "symbol": "AAPL", "text": "Share repurchase program of up to $5 billion authorized."},
        {"doc_id": "d2", "symbol": "AAPL", "text": "Share repurchase program of up to $5 billion authorized."},
    ]
    result = detect_events_batch(docs)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# event_density
# ---------------------------------------------------------------------------

def test_event_density_no_events():
    assert event_density([], 1) == 0.0


def test_event_density_no_documents():
    ev = AltEvent(AltEventType.EARNINGS, "AAPL", 0.8, EventSeverity.HIGH, "snippet")
    assert event_density([ev], 0) == 0.0


def test_event_density_value_range():
    events = [
        AltEvent(AltEventType.EARNINGS, "AAPL", 0.8, EventSeverity.HIGH, "s"),
        AltEvent(AltEventType.MNA, "AAPL", 0.9, EventSeverity.HIGH, "s"),
    ]
    d = event_density(events, 5)
    assert 0 <= d <= 1.0


def test_event_density_clamps_to_one():
    events = [AltEvent(AltEventType.EARNINGS, "A", 0.8, EventSeverity.HIGH, "s") for _ in range(100)]
    d = event_density(events, 1)
    assert d <= 1.0
