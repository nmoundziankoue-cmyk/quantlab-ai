"""Market data REST router (Milestone 2 / M10).

Endpoints:
  GET  /market/quote/{ticker}          — full real-time quote (SWR-cached)
  POST /market/quotes                  — batch quotes (body: list of tickers)
  GET  /market/ohlcv/{ticker}          — historical OHLCV bars
  GET  /market/news/{ticker}           — news feed + sentiment
  GET  /market/sentiment/{ticker}      — condensed sentiment snapshot
  GET  /market/calendar                — economic calendar
  GET  /market/circuit-breakers        — per-provider circuit breaker states
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from schemas.market import (
    BatchQuoteRead,
    BatchQuoteRequest,
    CalendarRead,
    NewsRead,
    OHLCVRead,
    QuoteRead,
    SentimentRead,
)
from services.quotes import (
    get_batch_quotes,
    get_economic_calendar,
    get_news,
    get_ohlcv,
    get_quote,
    get_sentiment,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote/{ticker}", response_model=QuoteRead, summary="Real-time quote")
def route_quote(ticker: str) -> QuoteRead:
    """Return a full real-time quote for a single ticker."""
    try:
        return get_quote(ticker.upper())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/quotes", response_model=BatchQuoteRead, summary="Batch quotes")
def route_batch_quotes(body: BatchQuoteRequest) -> BatchQuoteRead:
    """Return quotes for up to 50 tickers in one call.

    Tickers that fail are recorded in the ``errors`` map; successful ones
    appear in ``quotes``.
    """
    return get_batch_quotes(body.tickers)


@router.get("/ohlcv/{ticker}", response_model=OHLCVRead, summary="Historical OHLCV")
def route_ohlcv(
    ticker: str,
    interval: Annotated[str, Query(description="Bar size: 1m 5m 15m 1h 1d 1wk 1mo")] = "1d",
    period: Annotated[str, Query(description="Look-back: 1d 5d 1mo 3mo 6mo 1y 2y 5y ytd max")] = "6mo",
) -> OHLCVRead:
    """Return OHLCV bars for a ticker at the requested interval and period."""
    try:
        return get_ohlcv(ticker.upper(), interval=interval, period=period)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/news/{ticker}", response_model=NewsRead, summary="News feed + sentiment")
def route_news(
    ticker: str,
    max_articles: Annotated[int, Query(ge=1, le=50)] = 15,
) -> NewsRead:
    """Return recent news articles for *ticker* with per-article sentiment scores."""
    return get_news(ticker.upper(), max_articles=max_articles)


@router.get(
    "/sentiment/{ticker}", response_model=SentimentRead, summary="Sentiment snapshot"
)
def route_sentiment(ticker: str) -> SentimentRead:
    """Return an aggregated sentiment snapshot (score, label, signal) for *ticker*."""
    return get_sentiment(ticker.upper())


@router.get("/calendar", response_model=CalendarRead, summary="Economic calendar")
def route_calendar(
    days_ahead: Annotated[int, Query(ge=1, le=365, description="Days from today")] = 30,
) -> CalendarRead:
    """Return scheduled macroeconomic events for the next *days_ahead* days."""
    return get_economic_calendar(days_ahead=days_ahead)


@router.get("/circuit-breakers", summary="Provider circuit breaker states")
def route_circuit_breakers() -> dict:
    """Return the circuit breaker state for every market data provider.

    States: ``closed`` (normal), ``open`` (tripped, skipping requests),
    ``half_open`` (cooling down, probing recovery).
    """
    from services.market_data_provider import get_router
    return {"providers": get_router().circuit_breaker_states()}
