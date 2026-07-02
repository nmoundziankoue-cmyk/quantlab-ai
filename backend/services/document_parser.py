"""M14 Phase 3 — Financial document parser engine.

Rule-based section extraction and structured-entity parsing for SEC-style
filing text.  Deterministic, regex/heuristic driven — no ML dependency, no
network calls. Designed to operate on whatever raw text the M14 ingestion
pipeline (document_store.py) hands it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Section catalog
# ---------------------------------------------------------------------------

SECTION_NAMES = [
    "income_statement",
    "balance_sheet",
    "cash_flow_statement",
    "risk_factors",
    "management_discussion",
    "business_description",
    "executive_compensation",
    "share_buybacks",
    "guidance",
]

# Heading patterns that mark the start of each section (case-insensitive).
_SECTION_HEADERS: Dict[str, List[str]] = {
    "income_statement": [r"consolidated\s+statements?\s+of\s+(income|operations)", r"^income\s+statement"],
    "balance_sheet": [r"consolidated\s+balance\s+sheets?", r"^balance\s+sheet"],
    "cash_flow_statement": [r"consolidated\s+statements?\s+of\s+cash\s+flows?", r"^cash\s+flow"],
    "risk_factors": [r"^item\s+1a\.?\s+risk\s+factors", r"^risk\s+factors"],
    "management_discussion": [r"management.?s\s+discussion\s+and\s+analysis", r"^md&a"],
    "business_description": [r"^item\s+1\.?\s+business", r"^business\s+overview"],
    "executive_compensation": [r"executive\s+compensation", r"summary\s+compensation\s+table"],
    "share_buybacks": [r"share\s+repurchase", r"stock\s+buyback"],
    "guidance": [r"^outlook", r"forward.?looking\s+guidance", r"guidance\s+for"],
}

_NUMERIC_RE = re.compile(r"\$?\(?-?[\d,]+(?:\.\d+)?\)?%?")
_LINE_ITEM_RE = re.compile(r"^(?P<label>[A-Za-z][A-Za-z\s,&'\-/]{2,60}?)\s{1,}\$?\(?-?[\d,]")


@dataclass
class ParsedSection:
    name: str
    text: str
    line_items: Dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedFiling:
    doc_id: str
    sections: Dict[str, ParsedSection] = field(default_factory=dict)
    entities: Dict[str, List[str]] = field(default_factory=dict)

    def section_names(self) -> List[str]:
        return list(self.sections.keys())

    def to_dict(self) -> Dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "sections": {
                name: {"text_preview": sec.text[:240], "line_items": sec.line_items}
                for name, sec in self.sections.items()
            },
            "entities": self.entities,
        }


def _find_section_spans(text: str) -> Dict[str, int]:
    """Locate the start offset of each recognised section header."""
    lines = text.split("\n")
    offsets: Dict[str, int] = {}
    cursor = 0
    compiled = {
        name: [re.compile(p, re.IGNORECASE) for p in patterns]
        for name, patterns in _SECTION_HEADERS.items()
    }
    for line in lines:
        stripped = line.strip()
        for name, patterns in compiled.items():
            if name in offsets:
                continue
            for pat in patterns:
                if pat.search(stripped):
                    offsets[name] = cursor
                    break
        cursor += len(line) + 1
    return offsets


def _extract_line_items(section_text: str) -> Dict[str, str]:
    """Extract "Label .... 1,234" style numeric line items from a section."""
    items: Dict[str, str] = {}
    for line in section_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = _LINE_ITEM_RE.match(line)
        if match:
            label = match.group("label").strip()
            numbers = _NUMERIC_RE.findall(line)
            if numbers:
                items[label] = numbers[-1]
    return items


def parse_filing(doc_id: str, text: str) -> ParsedFiling:
    """Parse raw filing text into recognised sections with extracted line items."""
    offsets = _find_section_spans(text)
    ordered = sorted(offsets.items(), key=lambda kv: kv[1])

    sections: Dict[str, ParsedSection] = {}
    for i, (name, start) in enumerate(ordered):
        end = ordered[i + 1][1] if i + 1 < len(ordered) else len(text)
        body = text[start:end]
        sections[name] = ParsedSection(
            name=name,
            text=body,
            line_items=_extract_line_items(body) if name in {
                "income_statement", "balance_sheet", "cash_flow_statement"
            } else {},
        )

    entities = extract_filing_entities(text)
    return ParsedFiling(doc_id=doc_id, sections=sections, entities=entities)


# ---------------------------------------------------------------------------
# Entity extraction (structured, rule-based)
# ---------------------------------------------------------------------------

_TICKER_RE = re.compile(r"\b(?:NASDAQ|NYSE):\s*([A-Z]{1,5})\b")
_EXEC_TITLE_RE = re.compile(
    r"\b([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){1,2}),?\s+"
    r"(Chief Executive Officer|Chief Financial Officer|Chief Operating Officer|"
    r"President|Chairman|Chairwoman|Chief Technology Officer)\b"
)
_DOLLAR_AMOUNT_RE = re.compile(r"\$\s?[\d,]+(?:\.\d+)?\s?(?:million|billion|thousand)?", re.IGNORECASE)
_PERCENT_RE = re.compile(r"-?\d+(?:\.\d+)?\s?%")


def extract_filing_entities(text: str) -> Dict[str, List[str]]:
    tickers = sorted(set(_TICKER_RE.findall(text)))
    execs = sorted({f"{name.strip()} ({title})" for name, title in _EXEC_TITLE_RE.findall(text)})
    amounts = list(dict.fromkeys(_DOLLAR_AMOUNT_RE.findall(text)))[:25]
    percents = list(dict.fromkeys(_PERCENT_RE.findall(text)))[:25]
    return {
        "tickers": tickers,
        "executives": execs,
        "dollar_amounts": amounts,
        "percentages": percents,
    }


def extract_buyback_authorization(text: str) -> Optional[str]:
    match = re.search(
        r"authoriz\w+\s+(?:the\s+)?repurchase\s+of\s+(?:up\s+to\s+)?(\$[\d,.]+\s?(?:million|billion)?)",
        text, re.IGNORECASE,
    )
    return match.group(1) if match else None


def extract_guidance_range(text: str) -> Optional[Dict[str, str]]:
    match = re.search(
        r"(?:expects?|guidance|forecast)[^.\n]{0,80}?\$?([\d,.]+)\s*(?:to|-)\s*\$?([\d,.]+)\s*(billion|million)?",
        text, re.IGNORECASE,
    )
    if not match:
        return None
    low, high, unit = match.groups()
    return {"low": low, "high": high, "unit": unit or ""}
