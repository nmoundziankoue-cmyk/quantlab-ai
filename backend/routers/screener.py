from __future__ import annotations
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import services.screener as svc
from schemas.screener import (
    SavedScreenerCreate, SavedScreenerUpdate, SavedScreenerResponse,
    ScreenerRunRequest, ScreenerRunResponse, ScreenerResultResponse,
)
from services.screener import SCREENER_TYPES

router = APIRouter(prefix="/screeners", tags=["screeners"])


@router.get("/types")
def list_types():
    return {"types": SCREENER_TYPES}


@router.post("", response_model=SavedScreenerResponse, status_code=status.HTTP_201_CREATED)
def create_screener(data: SavedScreenerCreate, db: Session = Depends(get_db)):
    s = svc.create_screener(db, data)
    db.commit()
    db.refresh(s)
    return s


@router.get("", response_model=List[SavedScreenerResponse])
def list_screeners(db: Session = Depends(get_db)):
    return svc.list_screeners(db)


@router.get("/{screener_id}", response_model=SavedScreenerResponse)
def get_screener(screener_id: uuid.UUID, db: Session = Depends(get_db)):
    s = svc.get_screener(db, screener_id)
    if not s:
        raise HTTPException(status_code=404, detail="Screener not found")
    return s


@router.patch("/{screener_id}", response_model=SavedScreenerResponse)
def update_screener(screener_id: uuid.UUID, data: SavedScreenerUpdate, db: Session = Depends(get_db)):
    s = svc.update_screener(db, screener_id, data)
    if not s:
        raise HTTPException(status_code=404, detail="Screener not found")
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{screener_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_screener(screener_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_screener(db, screener_id):
        raise HTTPException(status_code=404, detail="Screener not found")
    db.commit()


@router.post("/run", response_model=ScreenerRunResponse)
def run_screener(req: ScreenerRunRequest, save: bool = False, db: Session = Depends(get_db)):
    result = svc.run_screener(req)
    if save:
        svc.save_result(db, req.screener_id, result)
        db.commit()
    return result


@router.get("/{screener_id}/results", response_model=List[ScreenerResultResponse])
def list_results(screener_id: uuid.UUID, db: Session = Depends(get_db)):
    return svc.list_screener_results(db, screener_id)
