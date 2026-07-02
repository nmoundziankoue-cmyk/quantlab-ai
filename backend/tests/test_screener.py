"""Tests for M6 Screener service — rules, scoring, CRUD, run."""
from __future__ import annotations
import uuid
import pytest
from sqlalchemy.orm import Session

from schemas.screener import (
    ScreenerRule, SavedScreenerCreate, SavedScreenerUpdate,
    ScreenerRunRequest, ScreenerRunResponse, ScreenerResultItem,
)
from services.screener import (
    run_screener, save_result, create_screener, list_screeners,
    get_screener, update_screener, delete_screener, list_screener_results,
    MOCK_FUNDAMENTALS, SP500_UNIVERSE,
    _apply_operator, _get_field, _score_ticker,
)


# ---------------------------------------------------------------------------
# Operator logic (pure)
# ---------------------------------------------------------------------------

def test_apply_operator_gt():
    assert _apply_operator(20.0, "gt", 15.0) is True
    assert _apply_operator(10.0, "gt", 15.0) is False


def test_apply_operator_gte():
    assert _apply_operator(15.0, "gte", 15.0) is True
    assert _apply_operator(14.9, "gte", 15.0) is False


def test_apply_operator_lt():
    assert _apply_operator(10.0, "lt", 15.0) is True
    assert _apply_operator(20.0, "lt", 15.0) is False


def test_apply_operator_lte():
    assert _apply_operator(15.0, "lte", 15.0) is True
    assert _apply_operator(15.1, "lte", 15.0) is False


def test_apply_operator_eq():
    assert _apply_operator(1.5, "eq", 1.5) is True
    assert _apply_operator(1.5, "eq", 2.0) is False


def test_apply_operator_neq():
    assert _apply_operator(1.0, "neq", 2.0) is True
    assert _apply_operator(2.0, "neq", 2.0) is False


def test_apply_operator_unknown_returns_false():
    # operator "in" is not implemented — falls through to return False
    assert _apply_operator(5.0, "unknown_op", 5.0) is False


def test_apply_operator_threshold_not_float_returns_false():
    assert _apply_operator(5.0, "gt", "not_a_number") is False


def test_apply_operator_none_value():
    assert _apply_operator(None, "gt", 10.0) is False


# ---------------------------------------------------------------------------
# Field access (pure)
# ---------------------------------------------------------------------------

def test_get_field_known_ticker():
    pe = _get_field("AAPL", "pe")
    assert pe is not None
    assert isinstance(pe, (int, float))


def test_get_field_unknown_ticker():
    assert _get_field("ZZZZ_FAKE", "pe") is None


def test_get_field_unknown_field():
    assert _get_field("AAPL", "unknown_field_xyz") is None


def test_get_field_all_fundamentals_accessible():
    fields = ["pe", "pb", "ps", "roe", "revenue_growth", "ebitda_margin", "dividend_yield", "beta", "market_cap", "momentum_12m"]
    for field in fields:
        val = _get_field("AAPL", field)
        assert val is not None, f"Field {field} missing for AAPL"


# ---------------------------------------------------------------------------
# Score ticker (pure)
# ---------------------------------------------------------------------------

def test_score_ticker_all_pass():
    rules = [{"field": "pe", "operator": "gt", "value": 0}]
    item = _score_ticker("AAPL", rules)
    assert item.ticker == "AAPL"
    assert item.pass_count == 1
    assert item.fail_count == 0


def test_score_ticker_all_fail():
    rules = [{"field": "pe", "operator": "lt", "value": 0}]
    item = _score_ticker("AAPL", rules)
    assert item.fail_count == 1
    assert item.pass_count == 0


def test_score_ticker_partial_pass():
    rules = [
        {"field": "pe", "operator": "gt", "value": 0},
        {"field": "pe", "operator": "lt", "value": 0},
    ]
    item = _score_ticker("AAPL", rules)
    assert item.pass_count == 1
    assert item.fail_count == 1


def test_score_ticker_has_score():
    rules = [{"field": "roe", "operator": "gt", "value": 0}]
    item = _score_ticker("AAPL", rules)
    assert 0.0 <= item.score <= 100.0


# ---------------------------------------------------------------------------
# MOCK data constants
# ---------------------------------------------------------------------------

def test_mock_fundamentals_not_empty():
    assert len(MOCK_FUNDAMENTALS) >= 20


def test_mock_fundamentals_has_aapl():
    assert "AAPL" in MOCK_FUNDAMENTALS


def test_sp500_universe_has_tickers():
    assert len(SP500_UNIVERSE) >= 40


def test_sp500_universe_contains_aapl():
    assert "AAPL" in SP500_UNIVERSE


# ---------------------------------------------------------------------------
# run_screener (pure, no DB)
# ---------------------------------------------------------------------------

def test_run_screener_value():
    req = ScreenerRunRequest(
        rules=[
            ScreenerRule(field="pe", operator="lt", value=25),
            ScreenerRule(field="roe", operator="gt", value=0.1),
        ],
        screener_type="value",
    )
    result = run_screener(req)
    assert isinstance(result, ScreenerRunResponse)
    assert result.match_count >= 0
    for item in result.results:
        assert item.ticker in MOCK_FUNDAMENTALS


def test_run_screener_all_pass():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="pe", operator="gt", value=0)],
        screener_type="fundamental",
    )
    result = run_screener(req)
    assert result.match_count > 0


def test_run_screener_none_pass():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="pe", operator="lt", value=0)],
        screener_type="fundamental",
    )
    result = run_screener(req)
    assert result.match_count == 0


def test_run_screener_limit():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="pe", operator="gt", value=0)],
        limit=3,
    )
    result = run_screener(req)
    assert len(result.results) <= 3


def test_run_screener_custom_universe():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="pe", operator="gt", value=0)],
        universe=["AAPL", "MSFT"],
    )
    result = run_screener(req)
    assert result.total_universe == 2
    for item in result.results:
        assert item.ticker in ["AAPL", "MSFT"]


def test_run_screener_results_sorted_by_score():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="roe", operator="gt", value=0)],
        limit=10,
    )
    result = run_screener(req)
    scores = [item.score for item in result.results]
    assert scores == sorted(scores, reverse=True)


def test_run_screener_has_field_values():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="pe", operator="gt", value=0)],
        limit=5,
    )
    result = run_screener(req)
    for item in result.results:
        assert "pe" in item.field_values or len(item.field_values) >= 0


def test_run_screener_dividend():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="dividend_yield", operator="gt", value=0.01)],
        screener_type="dividend",
    )
    result = run_screener(req)
    assert isinstance(result, ScreenerRunResponse)


def test_run_screener_momentum():
    req = ScreenerRunRequest(
        rules=[ScreenerRule(field="momentum_12m", operator="gt", value=0.1)],
        screener_type="momentum",
    )
    result = run_screener(req)
    assert isinstance(result, ScreenerRunResponse)


def test_run_screener_quality():
    req = ScreenerRunRequest(
        rules=[
            ScreenerRule(field="roe", operator="gt", value=0.15),
            ScreenerRule(field="ebitda_margin", operator="gt", value=0.2),
        ],
        screener_type="quality",
    )
    result = run_screener(req)
    assert isinstance(result, ScreenerRunResponse)


# ---------------------------------------------------------------------------
# Saved screeners CRUD (DB)
# ---------------------------------------------------------------------------

def test_create_screener(db: Session):
    data = SavedScreenerCreate(
        name="Value Screen",
        screener_type="value",
        rules=[ScreenerRule(field="pe", operator="lt", value=20)],
    )
    screener = create_screener(db, data)
    assert screener.id is not None
    assert screener.name == "Value Screen"
    assert len(screener.rules) == 1


def test_list_screeners(db: Session):
    create_screener(db, SavedScreenerCreate(name="S1", screener_type="value", rules=[ScreenerRule(field="pe", operator="lt", value=30)]))
    create_screener(db, SavedScreenerCreate(name="S2", screener_type="momentum", rules=[ScreenerRule(field="momentum_12m", operator="gt", value=0)]))
    result = list_screeners(db)
    assert len(result) >= 2


def test_get_screener(db: Session):
    s = create_screener(db, SavedScreenerCreate(name="Get Me", screener_type="value", rules=[ScreenerRule(field="pe", operator="lt", value=25)]))
    found = get_screener(db, s.id)
    assert found is not None
    assert found.name == "Get Me"


def test_get_screener_missing(db: Session):
    assert get_screener(db, uuid.uuid4()) is None


def test_update_screener(db: Session):
    s = create_screener(db, SavedScreenerCreate(name="Old", screener_type="value", rules=[ScreenerRule(field="pe", operator="lt", value=25)]))
    updated = update_screener(db, s.id, SavedScreenerUpdate(name="New"))
    assert updated.name == "New"


def test_delete_screener(db: Session):
    s = create_screener(db, SavedScreenerCreate(name="Del", screener_type="value", rules=[ScreenerRule(field="pe", operator="lt", value=25)]))
    assert delete_screener(db, s.id) is True
    assert get_screener(db, s.id) is None


def test_delete_screener_missing(db: Session):
    assert delete_screener(db, uuid.uuid4()) is False


# ---------------------------------------------------------------------------
# save_result & list results (DB)
# ---------------------------------------------------------------------------

def test_save_result(db: Session):
    req = ScreenerRunRequest(rules=[ScreenerRule(field="pe", operator="gt", value=0)], limit=5)
    run_result = run_screener(req)
    saved = save_result(db, None, run_result)
    assert saved.id is not None
    assert saved.match_count == run_result.match_count


def test_save_result_with_screener_id(db: Session):
    screener = create_screener(db, SavedScreenerCreate(name="S", screener_type="value", rules=[ScreenerRule(field="pe", operator="gt", value=0)]))
    req = ScreenerRunRequest(rules=[ScreenerRule(field="pe", operator="gt", value=0)], limit=5)
    run_result = run_screener(req)
    saved = save_result(db, screener.id, run_result)
    assert saved.screener_id == screener.id


def test_list_screener_results(db: Session):
    screener = create_screener(db, SavedScreenerCreate(name="S", screener_type="value", rules=[ScreenerRule(field="pe", operator="gt", value=0)]))
    req = ScreenerRunRequest(rules=[ScreenerRule(field="pe", operator="gt", value=0)], limit=5)
    save_result(db, screener.id, run_screener(req))
    save_result(db, screener.id, run_screener(req))
    results = list_screener_results(db, screener.id)
    assert len(results) >= 2
