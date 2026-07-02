from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from models.research_workspace import (
    ResearchProject, ResearchFolder, ResearchNote,
    Bookmark, SavedSearch, ResearchSession, ReportDraft,
    RecentActivity, PinnedItem,
)
from schemas.research_workspace import (
    ResearchProjectCreate, ResearchProjectUpdate,
    ResearchFolderCreate, ResearchFolderUpdate,
    ResearchNoteCreate, ResearchNoteUpdate,
    BookmarkCreate, SavedSearchCreate,
    ResearchSessionCreate, ReportDraftCreate, ReportDraftUpdate,
    PinnedItemCreate, WorkspaceSearchResult,
)


def _log_activity(db: Session, activity_type: str, entity_type: str, entity_id: str, description: str) -> None:
    activity = RecentActivity(
        activity_type=activity_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(activity)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def create_project(db: Session, data: ResearchProjectCreate) -> ResearchProject:
    project = ResearchProject(
        name=data.name,
        description=data.description,
        owner_id=data.owner_id,
        status=data.status,
        tags=data.tags,
        metadata_=data.metadata_,
        tickers=data.tickers,
    )
    db.add(project)
    db.flush()
    _log_activity(db, "CREATE", "project", str(project.id), f"Created project: {project.name}")
    return project


def list_projects(db: Session, status: Optional[str] = None, page: int = 1, page_size: int = 50) -> List[ResearchProject]:
    q = db.query(ResearchProject)
    if status:
        q = q.filter(ResearchProject.status == status)
    return q.order_by(ResearchProject.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()


def get_project(db: Session, project_id: uuid.UUID) -> Optional[ResearchProject]:
    return db.query(ResearchProject).filter(ResearchProject.id == project_id).first()


def update_project(db: Session, project_id: uuid.UUID, data: ResearchProjectUpdate) -> Optional[ResearchProject]:
    project = get_project(db, project_id)
    if not project:
        return None
    for field, value in data.model_dump(exclude_unset=True, by_alias=False).items():
        if field == "metadata_":
            setattr(project, "metadata_", value)
        else:
            setattr(project, field, value)
    db.flush()
    return project


def delete_project(db: Session, project_id: uuid.UUID) -> bool:
    project = get_project(db, project_id)
    if not project:
        return False
    db.delete(project)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

def create_folder(db: Session, data: ResearchFolderCreate) -> ResearchFolder:
    folder = ResearchFolder(
        project_id=data.project_id,
        parent_folder_id=data.parent_folder_id,
        name=data.name,
    )
    db.add(folder)
    db.flush()
    return folder


def list_folders(db: Session, project_id: uuid.UUID) -> List[ResearchFolder]:
    return db.query(ResearchFolder).filter(ResearchFolder.project_id == project_id).order_by(ResearchFolder.name).all()


def get_folder(db: Session, folder_id: uuid.UUID) -> Optional[ResearchFolder]:
    return db.query(ResearchFolder).filter(ResearchFolder.id == folder_id).first()


def update_folder(db: Session, folder_id: uuid.UUID, data: ResearchFolderUpdate) -> Optional[ResearchFolder]:
    folder = get_folder(db, folder_id)
    if not folder:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(folder, field, value)
    db.flush()
    return folder


def delete_folder(db: Session, folder_id: uuid.UUID) -> bool:
    folder = get_folder(db, folder_id)
    if not folder:
        return False
    db.delete(folder)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def create_note(db: Session, data: ResearchNoteCreate) -> ResearchNote:
    note = ResearchNote(
        project_id=data.project_id,
        folder_id=data.folder_id,
        title=data.title,
        content=data.content,
        tags=data.tags,
        tickers=data.tickers,
        is_pinned=data.is_pinned,
    )
    db.add(note)
    db.flush()
    _log_activity(db, "CREATE", "note", str(note.id), f"Created note: {note.title}")
    return note


def list_notes(db: Session, project_id: uuid.UUID, folder_id: Optional[uuid.UUID] = None, is_pinned: Optional[bool] = None) -> List[ResearchNote]:
    q = db.query(ResearchNote).filter(ResearchNote.project_id == project_id)
    if folder_id:
        q = q.filter(ResearchNote.folder_id == folder_id)
    if is_pinned is not None:
        q = q.filter(ResearchNote.is_pinned == is_pinned)
    return q.order_by(ResearchNote.updated_at.desc()).all()


def get_note(db: Session, note_id: uuid.UUID) -> Optional[ResearchNote]:
    return db.query(ResearchNote).filter(ResearchNote.id == note_id).first()


def update_note(db: Session, note_id: uuid.UUID, data: ResearchNoteUpdate) -> Optional[ResearchNote]:
    note = get_note(db, note_id)
    if not note:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    db.flush()
    return note


def delete_note(db: Session, note_id: uuid.UUID) -> bool:
    note = get_note(db, note_id)
    if not note:
        return False
    db.delete(note)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------

def create_bookmark(db: Session, data: BookmarkCreate) -> Bookmark:
    bm = Bookmark(
        project_id=data.project_id,
        title=data.title,
        url=data.url,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        tags=data.tags,
        notes=data.notes,
    )
    db.add(bm)
    db.flush()
    return bm


def list_bookmarks(db: Session, project_id: Optional[uuid.UUID] = None) -> List[Bookmark]:
    q = db.query(Bookmark)
    if project_id:
        q = q.filter(Bookmark.project_id == project_id)
    return q.order_by(Bookmark.created_at.desc()).all()


def delete_bookmark(db: Session, bookmark_id: uuid.UUID) -> bool:
    bm = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bm:
        return False
    db.delete(bm)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Saved Searches
# ---------------------------------------------------------------------------

def create_saved_search(db: Session, data: SavedSearchCreate) -> SavedSearch:
    ss = SavedSearch(
        name=data.name,
        query=data.query,
        filters=data.filters,
        search_type=data.search_type,
    )
    db.add(ss)
    db.flush()
    return ss


def list_saved_searches(db: Session) -> List[SavedSearch]:
    return db.query(SavedSearch).order_by(SavedSearch.updated_at.desc()).all()


# ---------------------------------------------------------------------------
# Research Sessions
# ---------------------------------------------------------------------------

def create_session(db: Session, data: ResearchSessionCreate) -> ResearchSession:
    session = ResearchSession(
        project_id=data.project_id,
        title=data.title,
        tickers_researched=data.tickers_researched,
        session_data={},
    )
    db.add(session)
    db.flush()
    return session


def list_sessions(db: Session, project_id: Optional[uuid.UUID] = None) -> List[ResearchSession]:
    q = db.query(ResearchSession)
    if project_id:
        q = q.filter(ResearchSession.project_id == project_id)
    return q.order_by(ResearchSession.started_at.desc()).limit(50).all()


def end_session(db: Session, session_id: uuid.UUID) -> Optional[ResearchSession]:
    s = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not s:
        return None
    s.ended_at = datetime.now(timezone.utc)
    db.flush()
    return s


# ---------------------------------------------------------------------------
# Report Drafts
# ---------------------------------------------------------------------------

def create_report_draft(db: Session, data: ReportDraftCreate) -> ReportDraft:
    draft = ReportDraft(
        project_id=data.project_id,
        ticker=data.ticker,
        title=data.title,
        content=data.content,
        sections=data.sections,
        status=data.status,
    )
    db.add(draft)
    db.flush()
    _log_activity(db, "CREATE", "report_draft", str(draft.id), f"Created draft: {draft.title}")
    return draft


def list_report_drafts(db: Session, project_id: Optional[uuid.UUID] = None, ticker: Optional[str] = None) -> List[ReportDraft]:
    q = db.query(ReportDraft)
    if project_id:
        q = q.filter(ReportDraft.project_id == project_id)
    if ticker:
        q = q.filter(func.upper(ReportDraft.ticker) == ticker.upper())
    return q.order_by(ReportDraft.updated_at.desc()).all()


def get_report_draft(db: Session, draft_id: uuid.UUID) -> Optional[ReportDraft]:
    return db.query(ReportDraft).filter(ReportDraft.id == draft_id).first()


def update_report_draft(db: Session, draft_id: uuid.UUID, data: ReportDraftUpdate) -> Optional[ReportDraft]:
    draft = get_report_draft(db, draft_id)
    if not draft:
        return None
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] == "FINAL" and draft.status != "FINAL":
        draft.version += 1
    for field, value in updates.items():
        setattr(draft, field, value)
    db.flush()
    return draft


def delete_report_draft(db: Session, draft_id: uuid.UUID) -> bool:
    draft = get_report_draft(db, draft_id)
    if not draft:
        return False
    db.delete(draft)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Recent Activity + Pinned Items
# ---------------------------------------------------------------------------

def get_recent_activity(db: Session, limit: int = 20) -> List[RecentActivity]:
    return db.query(RecentActivity).order_by(RecentActivity.created_at.desc()).limit(limit).all()


def create_pinned_item(db: Session, data: PinnedItemCreate) -> PinnedItem:
    item = PinnedItem(
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        label=data.label,
        sort_order=data.sort_order,
    )
    db.add(item)
    db.flush()
    return item


def list_pinned_items(db: Session) -> List[PinnedItem]:
    return db.query(PinnedItem).order_by(PinnedItem.sort_order, PinnedItem.created_at.desc()).all()


def delete_pinned_item(db: Session, item_id: uuid.UUID) -> bool:
    item = db.query(PinnedItem).filter(PinnedItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Global Workspace Search
# ---------------------------------------------------------------------------

def workspace_search(db: Session, query: str, limit: int = 30) -> List[WorkspaceSearchResult]:
    results: List[WorkspaceSearchResult] = []
    q_lower = query.lower()

    # Search projects
    projects = db.query(ResearchProject).filter(
        or_(
            func.lower(ResearchProject.name).contains(q_lower),
            func.lower(ResearchProject.description).contains(q_lower),
        )
    ).limit(10).all()
    for p in projects:
        results.append(WorkspaceSearchResult(
            entity_type="project", entity_id=str(p.id),
            title=p.name, snippet=p.description, score=1.0,
        ))

    # Search notes
    notes = db.query(ResearchNote).filter(
        or_(
            func.lower(ResearchNote.title).contains(q_lower),
            func.lower(ResearchNote.content).contains(q_lower),
        )
    ).limit(10).all()
    for n in notes:
        snippet = n.content[:200] if n.content else None
        results.append(WorkspaceSearchResult(
            entity_type="note", entity_id=str(n.id),
            title=n.title, snippet=snippet, score=0.9,
        ))

    # Search report drafts
    drafts = db.query(ReportDraft).filter(
        or_(
            func.lower(ReportDraft.title).contains(q_lower),
            func.lower(ReportDraft.ticker).contains(q_lower),
        )
    ).limit(10).all()
    for d in drafts:
        results.append(WorkspaceSearchResult(
            entity_type="report_draft", entity_id=str(d.id),
            title=d.title, snippet=d.ticker, score=0.8,
        ))

    return results[:limit]
