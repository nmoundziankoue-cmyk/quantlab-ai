"""Institutional screener engine — rules-based filtering and scoring."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.screener import SavedScreener, ScreenerResult
from schemas.screener import (
    SavedScreenerCreate, SavedScreenerUpdate, ScreenerRunRequest,
    ScreenerRunResponse, ScreenerResultItem,
)

# ---------------------------------------------------------------------------
# Built-in screening universes (deterministic, no external data)
# ---------------------------------------------------------------------------

SP500_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH", "JPM",
    "V", "XOM", "MA", "JNJ", "AVGO", "PG", "HD", "MRK", "CVX", "ABBV",
    "ORCL", "COST", "CRM", "BAC", "NFLX", "KO", "LLY", "PEP", "MCD", "AMD",
    "TMO", "CSCO", "ABT", "WFC", "ADBE", "DHR", "TXN", "ACN", "INTC", "QCOM",
    "NKE", "DIS", "PM", "INTU", "RTX", "BMY", "AMT", "MS", "CAT", "HON",
]

MOCK_FUNDAMENTALS: Dict[str, Dict[str, float]] = {
    "AAPL":  {"pe": 29.5, "pb": 48.0, "ps": 8.1, "roe": 147.0, "revenue_growth": 0.08, "ebitda_margin": 0.33, "dividend_yield": 0.005, "beta": 1.25, "market_cap": 3e12, "momentum_12m": 0.28},
    "MSFT":  {"pe": 35.2, "pb": 14.0, "ps": 14.2, "roe": 39.0, "revenue_growth": 0.16, "ebitda_margin": 0.52, "dividend_yield": 0.007, "beta": 0.90, "market_cap": 3.1e12, "momentum_12m": 0.32},
    "GOOGL": {"pe": 22.1, "pb": 6.8, "ps": 6.8, "roe": 28.0, "revenue_growth": 0.14, "ebitda_margin": 0.35, "dividend_yield": 0.0, "beta": 1.05, "market_cap": 2e12, "momentum_12m": 0.22},
    "AMZN":  {"pe": 44.0, "pb": 9.5, "ps": 3.5, "roe": 21.0, "revenue_growth": 0.12, "ebitda_margin": 0.18, "dividend_yield": 0.0, "beta": 1.30, "market_cap": 1.9e12, "momentum_12m": 0.40},
    "NVDA":  {"pe": 65.0, "pb": 38.0, "ps": 22.0, "roe": 68.0, "revenue_growth": 1.22, "ebitda_margin": 0.62, "dividend_yield": 0.001, "beta": 1.70, "market_cap": 2.5e12, "momentum_12m": 1.80},
    "META":  {"pe": 25.0, "pb": 8.5, "ps": 8.5, "roe": 35.0, "revenue_growth": 0.22, "ebitda_margin": 0.45, "dividend_yield": 0.002, "beta": 1.20, "market_cap": 1.3e12, "momentum_12m": 0.55},
    "TSLA":  {"pe": 58.0, "pb": 11.0, "ps": 7.5, "roe": 18.0, "revenue_growth": 0.02, "ebitda_margin": 0.10, "dividend_yield": 0.0, "beta": 2.00, "market_cap": 6.5e11, "momentum_12m": -0.30},
    "JPM":   {"pe": 13.0, "pb": 2.2, "ps": 3.5, "roe": 16.0, "revenue_growth": 0.08, "ebitda_margin": 0.35, "dividend_yield": 0.025, "beta": 1.15, "market_cap": 6e11, "momentum_12m": 0.18},
    "V":     {"pe": 31.0, "pb": 14.5, "ps": 16.0, "roe": 45.0, "revenue_growth": 0.10, "ebitda_margin": 0.70, "dividend_yield": 0.008, "beta": 0.95, "market_cap": 5e11, "momentum_12m": 0.22},
    "XOM":   {"pe": 14.0, "pb": 2.0, "ps": 1.5, "roe": 14.0, "revenue_growth": -0.05, "ebitda_margin": 0.20, "dividend_yield": 0.035, "beta": 1.05, "market_cap": 4e11, "momentum_12m": 0.05},
    "JNJ":   {"pe": 22.0, "pb": 5.5, "ps": 4.5, "roe": 25.0, "revenue_growth": 0.05, "ebitda_margin": 0.28, "dividend_yield": 0.030, "beta": 0.55, "market_cap": 3.5e11, "momentum_12m": 0.02},
    "PG":    {"pe": 26.0, "pb": 8.0, "ps": 4.5, "roe": 32.0, "revenue_growth": 0.03, "ebitda_margin": 0.25, "dividend_yield": 0.025, "beta": 0.50, "market_cap": 3.6e11, "momentum_12m": 0.08},
    "KO":    {"pe": 24.0, "pb": 10.5, "ps": 5.8, "roe": 42.0, "revenue_growth": 0.04, "ebitda_margin": 0.29, "dividend_yield": 0.030, "beta": 0.55, "market_cap": 2.6e11, "momentum_12m": 0.06},
    "NFLX":  {"pe": 40.0, "pb": 12.0, "ps": 6.0, "roe": 30.0, "revenue_growth": 0.15, "ebitda_margin": 0.25, "dividend_yield": 0.0, "beta": 1.35, "market_cap": 2.5e11, "momentum_12m": 0.65},
    "AMD":   {"pe": 48.0, "pb": 3.5, "ps": 9.5, "roe": 8.0, "revenue_growth": 0.22, "ebitda_margin": 0.22, "dividend_yield": 0.0, "beta": 1.85, "market_cap": 2.8e11, "momentum_12m": 0.45},
    "INTC":  {"pe": 30.0, "pb": 1.8, "ps": 2.5, "roe": 5.0, "revenue_growth": -0.02, "ebitda_margin": 0.18, "dividend_yield": 0.018, "beta": 1.00, "market_cap": 1.6e11, "momentum_12m": -0.15},
    "DIS":   {"pe": 35.0, "pb": 2.8, "ps": 2.8, "roe": 8.0, "revenue_growth": 0.05, "ebitda_margin": 0.12, "dividend_yield": 0.0, "beta": 1.10, "market_cap": 1.7e11, "momentum_12m": -0.10},
    "NKE":   {"pe": 28.0, "pb": 12.0, "ps": 3.5, "roe": 42.0, "revenue_growth": -0.01, "ebitda_margin": 0.16, "dividend_yield": 0.018, "beta": 1.05, "market_cap": 1.2e11, "momentum_12m": -0.20},
    "COST":  {"pe": 50.0, "pb": 16.0, "ps": 1.5, "roe": 30.0, "revenue_growth": 0.08, "ebitda_margin": 0.06, "dividend_yield": 0.006, "beta": 0.80, "market_cap": 3.8e11, "momentum_12m": 0.32},
    "ABBV":  {"pe": 18.0, "pb": 8.0, "ps": 5.5, "roe": 50.0, "revenue_growth": 0.04, "ebitda_margin": 0.38, "dividend_yield": 0.038, "beta": 0.55, "market_cap": 3.2e11, "momentum_12m": 0.12},
}


SCREENER_TYPES = ["fundamental", "momentum", "value", "growth", "dividend", "low_volatility", "quality"]


def _get_universe(universe: Optional[List[str]] = None) -> List[str]:
    if universe:
        return [t.upper() for t in universe]
    return SP500_UNIVERSE


def _get_field(ticker: str, field: str) -> Optional[float]:
    data = MOCK_FUNDAMENTALS.get(ticker, {})
    return data.get(field)


def _apply_operator(value: Optional[float], operator: str, threshold: Any) -> bool:
    if value is None:
        return False
    try:
        t = float(threshold)
    except (TypeError, ValueError):
        return False
    if operator == "gt":
        return value > t
    elif operator == "gte":
        return value >= t
    elif operator == "lt":
        return value < t
    elif operator == "lte":
        return value <= t
    elif operator == "eq":
        return abs(value - t) < 1e-9
    elif operator == "neq":
        return abs(value - t) >= 1e-9
    return False


def _score_ticker(ticker: str, rules: List[Dict[str, Any]], weights: Optional[Dict[str, float]] = None) -> ScreenerResultItem:
    pass_count = 0
    fail_count = 0
    field_values: Dict[str, Any] = {}
    raw_score = 0.0

    fundamentals = MOCK_FUNDAMENTALS.get(ticker, {})
    for field, val in fundamentals.items():
        field_values[field] = val

    for rule in rules:
        field = rule.get("field", "")
        operator = rule.get("operator", "gt")
        threshold = rule.get("value", 0)
        value = fundamentals.get(field)
        passed = _apply_operator(value, operator, threshold)
        if passed:
            pass_count += 1
        else:
            fail_count += 1

    total_rules = pass_count + fail_count
    score = (pass_count / total_rules * 100) if total_rules > 0 else 0.0

    if weights:
        weighted = 0.0
        total_w = 0.0
        for field, w in weights.items():
            val = fundamentals.get(field)
            if val is not None:
                weighted += val * w
                total_w += w
        if total_w > 0:
            score = min(max((weighted / total_w) * 10, 0), 100)

    return ScreenerResultItem(
        ticker=ticker,
        rank=0,
        score=round(score, 2),
        field_values=field_values,
        pass_count=pass_count,
        fail_count=fail_count,
    )


def run_screener(req: ScreenerRunRequest) -> ScreenerRunResponse:
    universe = _get_universe(req.universe)
    rules = [r.model_dump() for r in (req.rules or [])]
    weights = None
    results: List[ScreenerResultItem] = []

    for ticker in universe:
        item = _score_ticker(ticker, rules, weights)
        if not rules or item.pass_count > 0:
            results.append(item)

    sort_by = req.sort_by or "score"
    reverse = req.sort_dir.upper() != "ASC"
    results.sort(key=lambda x: getattr(x, sort_by, x.score) if hasattr(x, sort_by) else x.field_values.get(sort_by, 0), reverse=reverse)
    for i, item in enumerate(results):
        item.rank = i + 1

    results = results[: req.limit]
    return ScreenerRunResponse(
        screener_id=req.screener_id,
        screener_type=req.screener_type,
        run_at=datetime.now(timezone.utc),
        total_universe=len(universe),
        match_count=len(results),
        results=results,
    )


def save_result(db: Session, screener_id: Optional[uuid.UUID], result: ScreenerRunResponse) -> ScreenerResult:
    tickers = [r.ticker for r in result.results]
    sr = ScreenerResult(
        screener_id=screener_id,
        run_at=result.run_at,
        tickers_matched=tickers,
        results=[r.model_dump() for r in result.results],
        total_universe=result.total_universe,
        match_count=result.match_count,
    )
    db.add(sr)
    db.flush()
    return sr


# CRUD for saved screeners
def create_screener(db: Session, data: SavedScreenerCreate) -> SavedScreener:
    s = SavedScreener(
        name=data.name,
        description=data.description,
        screener_type=data.screener_type,
        rules=[r.model_dump() for r in (data.rules or [])],
        sort_by=data.sort_by,
        sort_dir=data.sort_dir,
        scoring_weights=data.scoring_weights,
    )
    db.add(s)
    db.flush()
    return s


def list_screeners(db: Session) -> List[SavedScreener]:
    return db.query(SavedScreener).order_by(SavedScreener.updated_at.desc()).all()


def get_screener(db: Session, screener_id: uuid.UUID) -> Optional[SavedScreener]:
    return db.query(SavedScreener).filter(SavedScreener.id == screener_id).first()


def update_screener(db: Session, screener_id: uuid.UUID, data: SavedScreenerUpdate) -> Optional[SavedScreener]:
    s = get_screener(db, screener_id)
    if not s:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "rules" and value is not None:
            value = [r.model_dump() if hasattr(r, 'model_dump') else r for r in value]
        setattr(s, field, value)
    db.flush()
    return s


def delete_screener(db: Session, screener_id: uuid.UUID) -> bool:
    s = get_screener(db, screener_id)
    if not s:
        return False
    db.delete(s)
    db.flush()
    return True


def list_screener_results(db: Session, screener_id: uuid.UUID) -> List[ScreenerResult]:
    return db.query(ScreenerResult).filter(ScreenerResult.screener_id == screener_id).order_by(ScreenerResult.run_at.desc()).limit(10).all()
