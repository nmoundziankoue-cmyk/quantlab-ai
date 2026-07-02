from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
import services.report_generator as svc
from services.report_generator import REPORT_SECTIONS

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate")
def generate_report(
    ticker: str,
    sections: Optional[List[str]] = Query(default=None),
    recommendation: str = "NEUTRAL",
    target_price: str = "N/A",
    sector: str = "N/A",
    company_name: Optional[str] = None,
):
    context = {
        "recommendation": recommendation,
        "target_price": target_price,
        "sector": sector,
        "company_name": company_name or ticker,
    }
    return svc.generate_report(ticker, context=context, sections=sections or None)


@router.get("/sections")
def list_sections():
    return {"sections": REPORT_SECTIONS}


@router.post("/section")
def generate_section(ticker: str, section: str, sector: str = "N/A"):
    context = {"sector": sector}
    return svc.generate_section(ticker, section, context=context)


@router.post("/export/html")
def export_html(body: Dict[str, str]):
    markdown = body.get("markdown", "")
    html = svc.export_html(markdown)
    return HTMLResponse(content=html)
