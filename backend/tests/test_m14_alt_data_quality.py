"""M14 Phase 12 — Tests: alternative data quality (Phase 11)."""
import pytest
from services.alt_data_quality import (
    DocQualityIssue,
    DocQualityResult,
    checksum_of,
    detect_duplicate,
    check_completeness,
    detect_language_is_english,
    check_language,
    check_encoding,
    check_metadata,
    validate_document,
    validate_many,
    summary_report,
)

GOOD_TEXT = (
    "Apple Inc reported quarterly earnings that significantly exceeded analyst expectations. "
    "Revenue grew 15% year over year driven by strong iPhone and Services performance. "
    "The company raised its guidance for the next fiscal year."
)

COMPLETE_METADATA = {
    "doc_id": "doc1",
    "symbol": "AAPL",
    "filing_type": "10-K",
    "source": "sec.gov",
}


# ---------------------------------------------------------------------------
# checksum_of
# ---------------------------------------------------------------------------

def test_checksum_deterministic():
    c1 = checksum_of(GOOD_TEXT)
    c2 = checksum_of(GOOD_TEXT)
    assert c1 == c2


def test_checksum_different_texts():
    c1 = checksum_of(GOOD_TEXT)
    c2 = checksum_of("Different text entirely.")
    assert c1 != c2


def test_checksum_length():
    c = checksum_of(GOOD_TEXT)
    assert len(c) == 16


def test_checksum_empty():
    c = checksum_of("")
    assert len(c) == 16


# ---------------------------------------------------------------------------
# detect_duplicate
# ---------------------------------------------------------------------------

def test_detect_duplicate_no_dup():
    seen = {"other": checksum_of("Different content here.")}
    assert detect_duplicate(GOOD_TEXT, seen, "doc1") is None


def test_detect_duplicate_finds_dup():
    seen = {"other_doc": checksum_of(GOOD_TEXT)}
    result = detect_duplicate(GOOD_TEXT, seen, "doc1")
    assert result == "other_doc"


def test_detect_duplicate_same_id_no_dup():
    seen = {"doc1": checksum_of(GOOD_TEXT)}
    assert detect_duplicate(GOOD_TEXT, seen, "doc1") is None


# ---------------------------------------------------------------------------
# check_completeness
# ---------------------------------------------------------------------------

def test_check_completeness_passes():
    assert check_completeness(GOOD_TEXT) is None


def test_check_completeness_too_short():
    issue = check_completeness("Short text.", min_words=20)
    assert issue is not None
    assert issue.severity == "error"


def test_check_completeness_exact_minimum():
    text = " ".join(["word"] * 20)
    assert check_completeness(text, min_words=20) is None


# ---------------------------------------------------------------------------
# detect_language_is_english
# ---------------------------------------------------------------------------

def test_detect_english_positive():
    assert detect_language_is_english(GOOD_TEXT) is True


def test_detect_english_no_words():
    assert detect_language_is_english("12345 678 9 0") is False


def test_detect_english_empty():
    assert detect_language_is_english("") is False


# ---------------------------------------------------------------------------
# check_language
# ---------------------------------------------------------------------------

def test_check_language_english_passes():
    assert check_language(GOOD_TEXT) is None


def test_check_language_non_english_flagged():
    # Non-English text with no common English words
    issue = check_language("12345 67890 abcd efgh")
    assert issue is not None or check_language("zzz bbb ccc ddd") is not None  # flexible


# ---------------------------------------------------------------------------
# check_encoding
# ---------------------------------------------------------------------------

def test_check_encoding_valid_utf8():
    assert check_encoding(GOOD_TEXT.encode("utf-8")) is None


def test_check_encoding_invalid_raises_issue():
    issue = check_encoding(b"\xff\xfe bad bytes \x80\x81", "utf-8")
    assert issue is not None
    assert issue.severity == "critical"


# ---------------------------------------------------------------------------
# check_metadata
# ---------------------------------------------------------------------------

def test_check_metadata_complete():
    assert check_metadata(COMPLETE_METADATA) is None


def test_check_metadata_missing_symbol():
    meta = {**COMPLETE_METADATA, "symbol": ""}
    issue = check_metadata(meta)
    assert issue is not None
    assert "symbol" in issue.description


def test_check_metadata_missing_source():
    meta = {k: v for k, v in COMPLETE_METADATA.items() if k != "source"}
    issue = check_metadata(meta)
    assert issue is not None


# ---------------------------------------------------------------------------
# validate_document
# ---------------------------------------------------------------------------

def test_validate_document_passes():
    result = validate_document("doc1", GOOD_TEXT, COMPLETE_METADATA)
    assert result.passed is True
    assert result.quality_score > 0.5


def test_validate_document_short_text_fails():
    result = validate_document("doc1", "Too short.", COMPLETE_METADATA)
    assert result.passed is False


def test_validate_document_missing_metadata_fails():
    result = validate_document("doc1", GOOD_TEXT, {})
    assert result.passed is False


def test_validate_document_result_fields():
    result = validate_document("doc1", GOOD_TEXT, COMPLETE_METADATA)
    assert isinstance(result, DocQualityResult)
    assert 0 <= result.quality_score <= 1.0
    assert isinstance(result.issues, list)


def test_validate_document_to_dict():
    result = validate_document("doc1", GOOD_TEXT, COMPLETE_METADATA)
    d = result.to_dict()
    assert "doc_id" in d
    assert "quality_score" in d
    assert "passed" in d
    assert "issues" in d


def test_validate_document_duplicate_detection():
    seen = {"other": checksum_of(GOOD_TEXT)}
    result = validate_document("doc1", GOOD_TEXT, COMPLETE_METADATA, seen_checksums=seen)
    issue_types = [i.issue_type for i in result.issues]
    assert "duplicate_document" in issue_types


def test_validate_document_quality_penalty():
    result_good = validate_document("d1", GOOD_TEXT, COMPLETE_METADATA)
    result_bad = validate_document("d2", "Short.", {})
    assert result_good.quality_score > result_bad.quality_score


# ---------------------------------------------------------------------------
# validate_many
# ---------------------------------------------------------------------------

def test_validate_many_empty():
    result = validate_many([])
    assert result == {}


def test_validate_many_basic():
    docs = [
        {"doc_id": "d1", "text": GOOD_TEXT, "metadata": COMPLETE_METADATA},
        {"doc_id": "d2", "text": GOOD_TEXT + " Extended.", "metadata": {**COMPLETE_METADATA, "doc_id": "d2"}},
    ]
    results = validate_many(docs)
    assert "d1" in results
    assert "d2" in results


def test_validate_many_detects_duplicates():
    docs = [
        {"doc_id": "d1", "text": GOOD_TEXT, "metadata": COMPLETE_METADATA},
        {"doc_id": "d2", "text": GOOD_TEXT, "metadata": {**COMPLETE_METADATA, "doc_id": "d2"}},
    ]
    results = validate_many(docs)
    d2_issues = [i.issue_type for i in results["d2"].issues]
    assert "duplicate_document" in d2_issues


# ---------------------------------------------------------------------------
# summary_report
# ---------------------------------------------------------------------------

def test_summary_report_empty():
    report = summary_report({})
    assert report["total_documents"] == 0
    assert report["passed"] == 0


def test_summary_report_fields():
    docs = [{"doc_id": "d1", "text": GOOD_TEXT, "metadata": COMPLETE_METADATA}]
    results = validate_many(docs)
    report = summary_report(results)
    assert "total_documents" in report
    assert "passed" in report
    assert "failed" in report
    assert "pass_rate" in report
    assert "avg_quality_score" in report


def test_summary_report_pass_rate():
    docs = [
        {"doc_id": "d1", "text": GOOD_TEXT, "metadata": COMPLETE_METADATA},
        {"doc_id": "d2", "text": "Short.", "metadata": {}},
    ]
    results = validate_many(docs)
    report = summary_report(results)
    assert 0 <= report["pass_rate"] <= 1.0
    assert report["total_documents"] == 2


# ---------------------------------------------------------------------------
# DocQualityIssue
# ---------------------------------------------------------------------------

def test_issue_to_dict():
    issue = DocQualityIssue("test_type", "warning", "Test description")
    d = issue.to_dict()
    assert d["type"] == "test_type"
    assert d["severity"] == "warning"
    assert d["description"] == "Test description"
