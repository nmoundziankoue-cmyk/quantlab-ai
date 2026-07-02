from __future__ import annotations
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
import services.news_intelligence as svc

router = APIRouter(prefix="/news", tags=["news-intelligence"])


@router.get("/feed")
def news_feed(page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    return svc.news_feed(db, page=page, page_size=page_size)


@router.get("/breaking")
def breaking_news(limit: int = 20, db: Session = Depends(get_db)):
    return svc.breaking_news(db, limit=limit)


@router.get("/ticker/{ticker}")
def ticker_news(ticker: str, limit: int = 50, db: Session = Depends(get_db)):
    return svc.ticker_news(db, ticker.upper(), limit=limit)


@router.get("/sector/{sector}")
def sector_news(sector: str, limit: int = 50, db: Session = Depends(get_db)):
    return svc.sector_news(db, sector, limit=limit)


@router.get("/summary/daily")
def daily_summary(db: Session = Depends(get_db)):
    return svc.daily_summary(db)


@router.get("/clusters")
def news_clusters(db: Session = Depends(get_db)):
    return svc.news_clusters(db)


@router.get("/impact")
def news_impact(limit: int = 20, db: Session = Depends(get_db)):
    return svc.news_impact(db, limit=limit)
