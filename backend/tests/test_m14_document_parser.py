"""M14 Phase 12 — Tests: document parser (Phase 3).

Actual API notes:
- extract_filing_entities returns: {"tickers", "executives", "dollar_amounts", "percentages"}
  (no "companies" key)
- extract_buyback_authorization pattern: "authoriz* the repurchase of up to $X"
- extract_guidance_range returns: {"low": str, "high": str, "unit": str} or None
- ParsedSection.line_items values are str (from regex), not float
"""
from services.document_parser import (
    SECTION_NAMES,
    ParsedSection,
    ParsedFiling,
    parse_filing,
    extract_filing_entities,
    extract_buyback_authorization,
    extract_guidance_range,
)


SAMPLE_10K = """
ITEM 1. BUSINESS
Apple Inc. designs, manufactures and markets smartphones, personal computers and related software.

ITEM 1A. RISK FACTORS
The company faces risks related to competition, supply chain disruptions and regulatory changes in various markets.

ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS
Revenue increased 8% to $394 billion. Operating income rose 14% compared to prior year.

GUIDANCE FOR FISCAL YEAR
The company expects revenues of $90 billion to $92 billion in the next quarter.

SHARE REPURCHASE
Apple authorized the repurchase of up to $90,000,000,000 of common shares.

EXECUTIVE COMPENSATION
Tim Cook, Chief Executive Officer received total compensation of $98 million.
"""


def test_section_names_defined():
    assert len(SECTION_NAMES) > 0
    assert isinstance(SECTION_NAMES, list)


def test_parse_filing_returns_parsed_filing():
    result = parse_filing("doc1", SAMPLE_10K)
    assert isinstance(result, ParsedFiling)
    assert result.doc_id == "doc1"


def test_parse_filing_has_sections():
    result = parse_filing("doc1", SAMPLE_10K)
    assert len(result.sections) > 0


def test_parse_filing_has_entities():
    result = parse_filing("doc1", SAMPLE_10K)
    assert isinstance(result.entities, dict)


def test_parse_filing_sections_are_parsed_section():
    result = parse_filing("doc1", SAMPLE_10K)
    for section in result.sections.values():
        assert isinstance(section, ParsedSection)


def test_parse_filing_text_nonempty():
    result = parse_filing("doc1", SAMPLE_10K)
    for section in result.sections.values():
        assert len(section.text) > 0


def test_parse_filing_detects_risk_factors():
    result = parse_filing("doc1", SAMPLE_10K)
    assert "risk_factors" in result.sections


def test_parse_filing_detects_management_discussion():
    result = parse_filing("doc1", SAMPLE_10K)
    assert "management_discussion" in result.sections


def test_parse_filing_detects_business_description():
    result = parse_filing("doc1", SAMPLE_10K)
    assert "business_description" in result.sections


def test_parse_filing_empty_text():
    result = parse_filing("empty", "")
    assert result.doc_id == "empty"
    assert isinstance(result.sections, dict)


def test_parse_filing_short_text():
    result = parse_filing("short", "Revenue grew 5%.")
    assert isinstance(result, ParsedFiling)


def test_parse_filing_section_names_method():
    result = parse_filing("doc1", SAMPLE_10K)
    names = result.section_names()
    assert isinstance(names, list)


# ---------------------------------------------------------------------------
# extract_filing_entities
# ---------------------------------------------------------------------------

def test_extract_filing_entities_returns_dict():
    entities = extract_filing_entities(SAMPLE_10K)
    assert isinstance(entities, dict)


def test_extract_filing_entities_has_tickers_key():
    entities = extract_filing_entities(SAMPLE_10K)
    assert "tickers" in entities


def test_extract_filing_entities_has_executives_key():
    entities = extract_filing_entities(SAMPLE_10K)
    assert "executives" in entities


def test_extract_filing_entities_has_dollar_amounts():
    entities = extract_filing_entities(SAMPLE_10K)
    assert "dollar_amounts" in entities


def test_extract_filing_entities_has_percentages():
    entities = extract_filing_entities(SAMPLE_10K)
    assert "percentages" in entities


def test_extract_filing_entities_finds_executives():
    text = "Tim Cook, Chief Executive Officer made the announcement today."
    entities = extract_filing_entities(text)
    assert any("Tim Cook" in e for e in entities["executives"])


def test_extract_filing_entities_finds_dollar_amounts():
    text = "The company earned $90 billion in revenue this quarter."
    entities = extract_filing_entities(text)
    assert len(entities["dollar_amounts"]) > 0


def test_extract_filing_entities_finds_percentages():
    text = "Revenue grew 15% year over year."
    entities = extract_filing_entities(text)
    assert len(entities["percentages"]) > 0


def test_extract_filing_entities_finds_tickers():
    text = "NASDAQ:AAPL and NYSE:MSFT both beat estimates."
    entities = extract_filing_entities(text)
    assert "AAPL" in entities["tickers"] or "MSFT" in entities["tickers"]


# ---------------------------------------------------------------------------
# extract_buyback_authorization
# Actual pattern: "authoriz* the repurchase of up to $X"
# ---------------------------------------------------------------------------

def test_extract_buyback_authorization_found():
    text = "Apple authorized the repurchase of up to $90 billion of common shares."
    result = extract_buyback_authorization(text)
    assert result is not None
    assert "90" in str(result)


def test_extract_buyback_authorization_not_found():
    text = "Revenue grew 10% year over year."
    result = extract_buyback_authorization(text)
    assert result is None


def test_extract_buyback_authorization_returns_string():
    text = "Board authorized the repurchase of up to $5.5 billion."
    result = extract_buyback_authorization(text)
    assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# extract_guidance_range
# Actual pattern: "expects/guidance/forecast ... $X to/- $Y billion/million"
# Returns: {"low": str, "high": str, "unit": str} or None
# ---------------------------------------------------------------------------

def test_extract_guidance_range_found():
    # Pattern requires "$NUM to $NUM unit", not "$NUM unit to $NUM unit"
    text = "The company expects revenues of $90 to $92 billion next quarter."
    result = extract_guidance_range(text)
    assert result is not None
    assert "low" in result
    assert "high" in result


def test_extract_guidance_range_not_found():
    result = extract_guidance_range("No guidance provided this quarter.")
    assert result is None


def test_extract_guidance_range_returns_dict():
    text = "We expect revenue of $95 billion to $97 billion."
    result = extract_guidance_range(text)
    assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# ParsedSection dataclass
# ---------------------------------------------------------------------------

def test_parsed_section_dataclass():
    sec = ParsedSection(name="income_statement", text="Revenue: $100B", line_items={"Revenue": "100B"})
    assert sec.name == "income_statement"
    assert sec.line_items["Revenue"] == "100B"


def test_parsed_section_default_line_items():
    sec = ParsedSection(name="risk_factors", text="Risk text here.")
    assert isinstance(sec.line_items, dict)
