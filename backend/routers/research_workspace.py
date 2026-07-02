from __future__ import annotations
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
import services.research_workspace as svc
from schemas.research_workspace import (
    ResearchProjectCreate, ResearchProjectUpdate, ResearchProjectResponse,
    ResearchFolderCreate, ResearchFolderUpdate, ResearchFolderResponse,
    ResearchNoteCreate, ResearchNoteUpdate, ResearchNoteResponse,
    BookmarkCreate, BookmarkResponse,
    SavedSearchCreate, SavedSearchResponse,
    ResearchSessionCreate, ResearchSessionResponse,
    ReportDraftCreate, ReportDraftUpdate, ReportDraftResponse,
    RecentActivityResponse, PinnedItemCreate, PinnedItemResponse,
    WorkspaceSearchResult,
)

router = APIRouter(prefix="/workspace", tags=["research-workspace"])


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@router.post("/projects", response_model=ResearchProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ResearchProjectCreate, db: Session = Depends(get_db)):
    project = svc.create_project(db, data)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=List[ResearchProjectResponse])
def list_projects(status_filter: Optional[str] = Query(None, alias="status"), page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    return svc.list_projects(db, status=status_filter, page=page, page_size=page_size)


@router.get("/projects/{project_id}", response_model=ResearchProjectResponse)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    p = svc.get_project(db, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.patch("/projects/{project_id}", response_model=ResearchProjectResponse)
def update_project(project_id: uuid.UUID, data: ResearchProjectUpdate, db: Session = Depends(get_db)):
    p = svc.update_project(db, project_id, data)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    db.commit()
    db.refresh(p)
    return p


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_project(db, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    db.commit()


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

@router.post("/folders", response_model=ResearchFolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(data: ResearchFolderCreate, db: Session = Depends(get_db)):
    folder = svc.create_folder(db, data)
    db.commit()
    db.refresh(folder)
    return folder


@router.get("/projects/{project_id}/folders", response_model=List[ResearchFolderResponse])
def list_folders(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return svc.list_folders(db, project_id)


@router.patch("/folders/{folder_id}", response_model=ResearchFolderResponse)
def update_folder(folder_id: uuid.UUID, data: ResearchFolderUpdate, db: Session = Depends(get_db)):
    f = svc.update_folder(db, folder_id, data)
    if not f:
        raise HTTPException(status_code=404, detail="Folder not found")
    db.commit()
    db.refresh(f)
    return f


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_folder(db, folder_id):
        raise HTTPException(status_code=404, detail="Folder not found")
    db.commit()


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@router.post("/notes", response_model=ResearchNoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(data: ResearchNoteCreate, db: Session = Depends(get_db)):
    note = svc.create_note(db, data)
    db.commit()
    db.refresh(note)
    return note


@router.get("/projects/{project_id}/notes", response_model=List[ResearchNoteResponse])
def list_notes(project_id: uuid.UUID, folder_id: Optional[uuid.UUID] = None, is_pinned: Optional[bool] = None, db: Session = Depends(get_db)):
    return svc.list_notes(db, project_id, folder_id=folder_id, is_pinned=is_pinned)


@router.patch("/notes/{note_id}", response_model=ResearchNoteResponse)
def update_note(note_id: uuid.UUID, data: ResearchNoteUpdate, db: Session = Depends(get_db)):
    n = svc.update_note(db, note_id, data)
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    db.commit()
    db.refresh(n)
    return n


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    db.commit()


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------

@router.post("/bookmarks", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
def create_bookmark(data: BookmarkCreate, db: Session = Depends(get_db)):
    bm = svc.create_bookmark(db, data)
    db.commit()
    db.refresh(bm)
    return bm


@router.get("/bookmarks", response_model=List[BookmarkResponse])
def list_bookmarks(project_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    return svc.list_bookmarks(db, project_id=project_id)


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_bookmark(db, bookmark_id):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.commit()


# ---------------------------------------------------------------------------
# Saved Searches
# ---------------------------------------------------------------------------

@router.post("/saved-searches", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
def create_saved_search(data: SavedSearchCreate, db: Session = Depends(get_db)):
    ss = svc.create_saved_search(db, data)
    db.commit()
    db.refresh(ss)
    return ss


@router.get("/saved-searches", response_model=List[SavedSearchResponse])
def list_saved_searches(db: Session = Depends(get_db)):
    return svc.list_saved_searches(db)


# ---------------------------------------------------------------------------
# Research Sessions
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=ResearchSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(data: ResearchSessionCreate, db: Session = Depends(get_db)):
    s = svc.create_session(db, data)
    db.commit()
    db.refresh(s)
    return s


@router.get("/sessions", response_model=List[ResearchSessionResponse])
def list_sessions(project_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    return svc.list_sessions(db, project_id=project_id)


@router.post("/sessions/{session_id}/end", response_model=ResearchSessionResponse)
def end_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    s = svc.end_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    db.commit()
    db.refresh(s)
    return s


# ---------------------------------------------------------------------------
# Report Drafts
# ---------------------------------------------------------------------------

@router.post("/report-drafts", response_model=ReportDraftResponse, status_code=status.HTTP_201_CREATED)
def create_report_draft(data: ReportDraftCreate, db: Session = Depends(get_db)):
    draft = svc.create_report_draft(db, data)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/report-drafts", response_model=List[ReportDraftResponse])
def list_report_drafts(project_id: Optional[uuid.UUID] = None, ticker: Optional[str] = None, db: Session = Depends(get_db)):
    return svc.list_report_drafts(db, project_id=project_id, ticker=ticker)


@router.get("/report-drafts/{draft_id}", response_model=ReportDraftResponse)
def get_report_draft(draft_id: uuid.UUID, db: Session = Depends(get_db)):
    d = svc.get_report_draft(db, draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    return d


@router.patch("/report-drafts/{draft_id}", response_model=ReportDraftResponse)
def update_report_draft(draft_id: uuid.UUID, data: ReportDraftUpdate, db: Session = Depends(get_db)):
    d = svc.update_report_draft(db, draft_id, data)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    db.commit()
    db.refresh(d)
    return d


@router.delete("/report-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report_draft(draft_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_report_draft(db, draft_id):
        raise HTTPException(status_code=404, detail="Draft not found")
    db.commit()


# ---------------------------------------------------------------------------
# Activity, Pinned Items, Search
# ---------------------------------------------------------------------------

@router.get("/activity", response_model=List[RecentActivityResponse])
def get_recent_activity(limit: int = 20, db: Session = Depends(get_db)):
    return svc.get_recent_activity(db, limit=limit)


@router.post("/pinned", response_model=PinnedItemResponse, status_code=status.HTTP_201_CREATED)
def create_pinned_item(data: PinnedItemCreate, db: Session = Depends(get_db)):
    item = svc.create_pinned_item(db, data)
    db.commit()
    db.refresh(item)
    return item


@router.get("/pinned", response_model=List[PinnedItemResponse])
def list_pinned_items(db: Session = Depends(get_db)):
    return svc.list_pinned_items(db)


@router.delete("/pinned/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pinned_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    if not svc.delete_pinned_item(db, item_id):
        raise HTTPException(status_code=404, detail="Pinned item not found")
    db.commit()


@router.get("/search", response_model=List[WorkspaceSearchResult])
def workspace_search(q: str, limit: int = 30, db: Session = Depends(get_db)):
    return svc.workspace_search(db, q, limit=limit)
