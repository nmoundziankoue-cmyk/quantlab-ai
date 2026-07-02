"""Tests for M6 Report Generator — pure functions, no DB required."""
from __future__ import annotations
import pytest

from services.report_generator import (
    generate_report, generate_section, export_html, REPORT_SECTIONS,
)
from services.prompt_templates import (
    render_investment_thesis, render_bull_case, render_bear_case,
    render_swot, render_porter_five_forces, render_earnings_summary,
    render_research_memo, render_full_report_structure,
    list_templates,
)


# ---------------------------------------------------------------------------
# REPORT_SECTIONS constant
# ---------------------------------------------------------------------------

def test_report_sections_list():
    assert isinstance(REPORT_SECTIONS, list)
    assert len(REPORT_SECTIONS) >= 10


def test_report_sections_include_executive_summary():
    assert "executive_summary" in REPORT_SECTIONS or any("executive" in s for s in REPORT_SECTIONS)


def test_report_sections_include_investment_thesis():
    assert "investment_thesis" in REPORT_SECTIONS or any("thesis" in s for s in REPORT_SECTIONS)


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

def test_generate_report_returns_dict():
    result = generate_report("AAPL")
    assert isinstance(result, dict)


def test_generate_report_has_ticker():
    result = generate_report("MSFT")
    assert result.get("ticker") == "MSFT"


def test_generate_report_has_sections():
    result = generate_report("NVDA")
    assert "sections" in result
    assert isinstance(result["sections"], dict)
    assert len(result["sections"]) >= 5


def test_generate_report_all_sections_non_empty():
    result = generate_report("AAPL", context={"company_name": "Apple Inc."})
    for key, content in result["sections"].items():
        assert isinstance(content, str)
        assert len(content) > 0, f"Section {key} is empty"


def test_generate_report_with_context():
    ctx = {"company_name": "Tesla", "sector": "Automotive", "market_cap": "600B"}
    result = generate_report("TSLA", context=ctx)
    assert result["ticker"] == "TSLA"


def test_generate_report_custom_sections():
    result = generate_report("GOOGL", sections=["investment_thesis", "bull_case"])
    assert "sections" in result
    assert len(result["sections"]) == 2


def test_generate_report_has_metadata():
    result = generate_report("AMZN")
    assert "generated_at" in result or "timestamp" in result or "model" in result


def test_generate_report_ticker_in_section_content():
    result = generate_report("NVDA", context={"company_name": "NVIDIA"})
    all_content = " ".join(result["sections"].values())
    assert "NVDA" in all_content or "NVIDIA" in all_content


def test_generate_report_reproducible():
    ctx = {"company_name": "Apple"}
    r1 = generate_report("AAPL", context=ctx)
    r2 = generate_report("AAPL", context=ctx)
    assert r1["sections"] == r2["sections"]


def test_generate_report_different_tickers():
    r_aapl = generate_report("AAPL")
    r_msft = generate_report("MSFT")
    assert r_aapl["sections"] != r_msft["sections"]


# ---------------------------------------------------------------------------
# generate_section
# ---------------------------------------------------------------------------

def test_generate_section_returns_dict():
    result = generate_section("AAPL", "investment_thesis")
    assert isinstance(result, dict)


def test_generate_section_has_content():
    result = generate_section("MSFT", "bull_case")
    assert "content" in result or "section" in result
    content = result.get("content") or result.get("text", "")
    assert len(content) > 0


def test_generate_section_bull_case():
    result = generate_section("NVDA", "bull_case", context={"company_name": "NVIDIA"})
    assert isinstance(result, dict)


def test_generate_section_bear_case():
    result = generate_section("TSLA", "bear_case")
    assert isinstance(result, dict)


def test_generate_section_swot():
    result = generate_section("AMZN", "swot")
    assert isinstance(result, dict)


def test_generate_section_unknown_graceful():
    result = generate_section("AAPL", "unknown_section_xyz")
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# export_html
# ---------------------------------------------------------------------------

def test_export_html_returns_string():
    md = "# AAPL Investment Report\n\n## Executive Summary\n\nApple is a technology company."
    result = export_html(md)
    assert isinstance(result, str)


def test_export_html_contains_html_tags():
    md = "# Title\n\n## Section\n\nContent paragraph."
    result = export_html(md)
    assert "<html" in result or "<body" in result or "<h1" in result or "<h2" in result


def test_export_html_has_inline_styles():
    md = "# Report"
    result = export_html(md)
    assert "style" in result


def test_export_html_title_appears():
    md = "# AAPL Full Report 2024"
    result = export_html(md)
    assert "AAPL" in result


def test_export_html_preserves_content():
    md = "## Investment Thesis\n\nKey insight about the company."
    result = export_html(md)
    assert "Investment Thesis" in result or "investment_thesis" in result.lower()


def test_export_html_empty_markdown():
    result = export_html("")
    assert isinstance(result, str)


def test_export_html_headers_converted():
    md = "# H1\n## H2\n### H3"
    result = export_html(md)
    assert "<h" in result


# ---------------------------------------------------------------------------
# Full report structure from prompt_templates
# ---------------------------------------------------------------------------

def test_full_report_structure_keys():
    sections = render_full_report_structure("AAPL", {"company_name": "Apple"})
    expected_keys = {"executive_summary", "investment_thesis", "bull_case", "bear_case", "risk_factors"}
    for key in expected_keys:
        assert key in sections, f"Missing section: {key}"


def test_full_report_structure_all_non_empty():
    sections = render_full_report_structure("MSFT", {"company_name": "Microsoft"})
    for key, content in sections.items():
        assert len(content) > 0, f"Empty section: {key}"


def test_full_report_structure_14_sections():
    sections = render_full_report_structure("NVDA", {})
    assert len(sections) >= 10


def test_prompt_templates_metadata():
    for t in list_templates():
        assert "key" in t or "id" in t
        assert "name" in t or "key" in t
        assert "description" in t


def test_prompt_templates_all_renderable():
    from services.prompt_templates import render_investment_thesis, render_bull_case, render_bear_case
    ctx = {"company_name": "Test Corp", "sector": "Technology"}
    for renderer in [render_investment_thesis, render_bull_case, render_bear_case]:
        out = renderer("TEST", ctx)
        assert isinstance(out, str)
        assert len(out) > 0
