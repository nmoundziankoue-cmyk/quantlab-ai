"""M14 Phase 11 — Alternative-data quality checks.

Document-level quality validation: duplicate/checksum detection,
completeness, language detection, encoding validation, and metadata
validation, rolled into a single 0-1 quality score (same penalty-weighted
pattern as M13's `data_validation.py`, applied to text documents instead of
OHLCV bars).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_REQUIRED_METADATA_FIELDS = ("doc_id", "symbol", "filing_type", "source")

_COMMON_ENGLISH_WORDS = {
    "the", "and", "of", "to", "in", "a", "is", "that", "for", "on", "with",
    "as", "are", "this", "by", "be", "was", "or", "from", "at", "an",
}

_PENALTIES = {"critical": 0.40, "error": 0.20, "warning": 0.05, "info": 0.01}


@dataclass
class DocQualityIssue:
    issue_type: str
    severity: str
    description: str

    def to_dict(self) -> Dict[str, str]:
        return {"type": self.issue_type, "severity": self.severity, "description": self.description}


@dataclass
class DocQualityResult:
    doc_id: str
    quality_score: float
    passed: bool
    issues: List[DocQualityIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "quality_score": round(self.quality_score, 4),
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
        }


def checksum_of(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def detect_duplicate(text: str, seen_checksums: Dict[str, str], doc_id: str) -> Optional[str]:
    """Returns the doc_id of the duplicate if ``text``'s checksum was seen under a different id."""
    chk = checksum_of(text)
    for other_id, other_chk in seen_checksums.items():
        if other_chk == chk and other_id != doc_id:
            return other_id
    return None


def check_completeness(text: str, min_words: int = 20) -> Optional[DocQualityIssue]:
    word_count = len(text.split())
    if word_count < min_words:
        return DocQualityIssue("incomplete_document", "error", f"Only {word_count} words (minimum {min_words})")
    return None


def detect_language_is_english(text: str, threshold: float = 0.02) -> bool:
    tokens = re.findall(r"[A-Za-z']+", text.lower())
    if not tokens:
        return False
    common_hits = sum(1 for t in tokens if t in _COMMON_ENGLISH_WORDS)
    return (common_hits / len(tokens)) >= threshold


def check_language(text: str) -> Optional[DocQualityIssue]:
    if not detect_language_is_english(text):
        return DocQualityIssue("language_detection", "warning", "Document does not appear to be English-language")
    return None


def check_encoding(raw: bytes, encoding: str = "utf-8") -> Optional[DocQualityIssue]:
    try:
        raw.decode(encoding)
    except UnicodeDecodeError as exc:
        return DocQualityIssue("encoding_error", "critical", f"Failed to decode as {encoding}: {exc}")
    return None


def check_metadata(metadata: Dict[str, Any]) -> Optional[DocQualityIssue]:
    missing = [f for f in _REQUIRED_METADATA_FIELDS if not metadata.get(f)]
    if missing:
        return DocQualityIssue("missing_metadata", "error", f"Missing required fields: {', '.join(missing)}")
    return None


def validate_document(
    doc_id: str,
    text: str,
    metadata: Dict[str, Any],
    seen_checksums: Optional[Dict[str, str]] = None,
) -> DocQualityResult:
    issues: List[DocQualityIssue] = []

    if seen_checksums is not None:
        dup = detect_duplicate(text, seen_checksums, doc_id)
        if dup:
            issues.append(DocQualityIssue("duplicate_document", "warning", f"Duplicate of {dup}"))

    for check in (check_completeness(text), check_language(text), check_metadata(metadata)):
        if check:
            issues.append(check)

    encoding_issue = check_encoding(text.encode("utf-8", errors="ignore"))
    if encoding_issue:
        issues.append(encoding_issue)

    score = 1.0
    for issue in issues:
        score -= _PENALTIES.get(issue.severity, 0.0)
    score = max(0.0, min(1.0, score))

    has_blocking = any(i.severity in ("critical", "error") for i in issues)
    return DocQualityResult(doc_id=doc_id, quality_score=score, passed=not has_blocking, issues=issues)


def validate_many(documents: List[Dict[str, Any]]) -> Dict[str, DocQualityResult]:
    """documents: list of {"doc_id", "text", "metadata"}."""
    seen: Dict[str, str] = {}
    results: Dict[str, DocQualityResult] = {}
    for doc in documents:
        doc_id = doc["doc_id"]
        result = validate_document(doc_id, doc["text"], doc.get("metadata", {}), seen_checksums=seen)
        seen[doc_id] = checksum_of(doc["text"])
        results[doc_id] = result
    return results


def summary_report(results: Dict[str, DocQualityResult]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results.values() if r.passed)
    avg_score = sum(r.quality_score for r in results.values()) / total if total else 0.0
    return {
        "total_documents": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "avg_quality_score": round(avg_score, 4),
    }
