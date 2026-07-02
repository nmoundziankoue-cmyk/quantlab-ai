"""Tests for M6 Research Workspace service."""
from __future__ import annotations
import uuid
import pytest
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
    PinnedItemCreate,
)
import services.research_workspace as svc


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def test_create_project(db: Session):
    data = ResearchProjectCreate(name="AAPL Deep Dive", description="Q1 analysis", tags=["tech", "mega-cap"])
    project = svc.create_project(db, data)
    assert project.id is not None
    assert project.name == "AAPL Deep Dive"
    assert project.status == "ACTIVE"
    assert project.tags == ["tech", "mega-cap"]


def test_create_project_minimal(db: Session):
    data = ResearchProjectCreate(name="Minimal")
    project = svc.create_project(db, data)
    assert project.name == "Minimal"
    assert project.description is None


def test_list_projects_empty(db: Session):
    result = svc.list_projects(db)
    assert isinstance(result, list)


def test_list_projects_filter_status(db: Session):
    svc.create_project(db, ResearchProjectCreate(name="Active", status="ACTIVE"))
    svc.create_project(db, ResearchProjectCreate(name="Archived", status="ARCHIVED"))
    active = svc.list_projects(db, status="ACTIVE")
    archived = svc.list_projects(db, status="ARCHIVED")
    assert all(p.status == "ACTIVE" for p in active)
    assert all(p.status == "ARCHIVED" for p in archived)


def test_get_project(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Find Me"))
    found = svc.get_project(db, p.id)
    assert found is not None
    assert found.name == "Find Me"


def test_get_project_missing(db: Session):
    assert svc.get_project(db, uuid.uuid4()) is None


def test_update_project(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Old Name"))
    updated = svc.update_project(db, p.id, ResearchProjectUpdate(name="New Name", status="ARCHIVED"))
    assert updated.name == "New Name"
    assert updated.status == "ARCHIVED"


def test_update_project_missing(db: Session):
    result = svc.update_project(db, uuid.uuid4(), ResearchProjectUpdate(name="X"))
    assert result is None


def test_delete_project(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Delete Me"))
    assert svc.delete_project(db, p.id) is True
    assert svc.get_project(db, p.id) is None


def test_delete_project_missing(db: Session):
    assert svc.delete_project(db, uuid.uuid4()) is False


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

def test_create_folder(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    data = ResearchFolderCreate(project_id=p.id, name="Filings")
    folder = svc.create_folder(db, data)
    assert folder.id is not None
    assert folder.name == "Filings"
    assert folder.project_id == p.id


def test_create_nested_folder(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    parent = svc.create_folder(db, ResearchFolderCreate(project_id=p.id, name="Parent"))
    child = svc.create_folder(db, ResearchFolderCreate(project_id=p.id, name="Child", parent_folder_id=parent.id))
    assert child.parent_folder_id == parent.id


def test_list_folders(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    svc.create_folder(db, ResearchFolderCreate(project_id=p.id, name="A"))
    svc.create_folder(db, ResearchFolderCreate(project_id=p.id, name="B"))
    folders = svc.list_folders(db, p.id)
    assert len(folders) == 2


def test_update_folder(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    f = svc.create_folder(db, ResearchFolderCreate(project_id=p.id, name="Old"))
    updated = svc.update_folder(db, f.id, ResearchFolderUpdate(name="New"))
    assert updated.name == "New"


def test_delete_folder(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    f = svc.create_folder(db, ResearchFolderCreate(project_id=p.id, name="Del"))
    assert svc.delete_folder(db, f.id) is True
    assert svc.get_folder(db, f.id) is None


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def test_create_note(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    data = ResearchNoteCreate(project_id=p.id, title="My Note", content="Some content", tickers=["AAPL"])
    note = svc.create_note(db, data)
    assert note.id is not None
    assert note.title == "My Note"
    assert note.tickers == ["AAPL"]
    assert not note.is_pinned


def test_create_pinned_note(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    note = svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="Pinned", is_pinned=True))
    assert note.is_pinned is True


def test_list_notes_project(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="N1"))
    svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="N2"))
    notes = svc.list_notes(db, p.id)
    assert len(notes) == 2


def test_list_notes_filter_pinned(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="Pinned", is_pinned=True))
    svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="Normal"))
    pinned = svc.list_notes(db, p.id, is_pinned=True)
    assert all(n.is_pinned for n in pinned)


def test_update_note(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    n = svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="Old"))
    updated = svc.update_note(db, n.id, ResearchNoteUpdate(title="New", is_pinned=True))
    assert updated.title == "New"
    assert updated.is_pinned is True


def test_delete_note(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    n = svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="Del"))
    assert svc.delete_note(db, n.id) is True
    assert svc.get_note(db, n.id) is None


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------

def test_create_bookmark(db: Session):
    data = BookmarkCreate(title="AAPL 10-K", url="https://sec.gov/aapl", reference_type="SEC_FILING")
    bm = svc.create_bookmark(db, data)
    assert bm.title == "AAPL 10-K"
    assert bm.reference_type == "SEC_FILING"


def test_list_bookmarks(db: Session):
    svc.create_bookmark(db, BookmarkCreate(title="BM1"))
    svc.create_bookmark(db, BookmarkCreate(title="BM2"))
    result = svc.list_bookmarks(db)
    assert len(result) >= 2


def test_delete_bookmark(db: Session):
    bm = svc.create_bookmark(db, BookmarkCreate(title="Del"))
    assert svc.delete_bookmark(db, bm.id) is True
    assert svc.delete_bookmark(db, bm.id) is False


# ---------------------------------------------------------------------------
# Saved Searches
# ---------------------------------------------------------------------------

def test_create_saved_search(db: Session):
    data = SavedSearchCreate(name="AAPL news", query="AAPL earnings", search_type="HYBRID")
    ss = svc.create_saved_search(db, data)
    assert ss.name == "AAPL news"
    assert ss.search_type == "HYBRID"


def test_list_saved_searches(db: Session):
    svc.create_saved_search(db, SavedSearchCreate(name="S1", query="q1"))
    result = svc.list_saved_searches(db)
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def test_create_session(db: Session):
    data = ResearchSessionCreate(title="AAPL Session", tickers_researched=["AAPL"])
    s = svc.create_session(db, data)
    assert s.title == "AAPL Session"
    assert s.ended_at is None


def test_end_session(db: Session):
    s = svc.create_session(db, ResearchSessionCreate(title="Sess"))
    ended = svc.end_session(db, s.id)
    assert ended.ended_at is not None


def test_list_sessions(db: Session):
    svc.create_session(db, ResearchSessionCreate(title="S1"))
    result = svc.list_sessions(db)
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# Report Drafts
# ---------------------------------------------------------------------------

def test_create_report_draft(db: Session):
    data = ReportDraftCreate(title="AAPL Report", ticker="AAPL", status="DRAFT")
    draft = svc.create_report_draft(db, data)
    assert draft.title == "AAPL Report"
    assert draft.ticker == "AAPL"
    assert draft.version == 1


def test_update_report_draft_to_final(db: Session):
    draft = svc.create_report_draft(db, ReportDraftCreate(title="Draft"))
    updated = svc.update_report_draft(db, draft.id, ReportDraftUpdate(status="FINAL"))
    assert updated.status == "FINAL"
    assert updated.version == 2


def test_list_report_drafts(db: Session):
    svc.create_report_draft(db, ReportDraftCreate(title="D1", ticker="MSFT"))
    svc.create_report_draft(db, ReportDraftCreate(title="D2", ticker="AAPL"))
    result = svc.list_report_drafts(db)
    assert len(result) >= 2


def test_list_report_drafts_filter_ticker(db: Session):
    svc.create_report_draft(db, ReportDraftCreate(title="D1", ticker="MSFT"))
    svc.create_report_draft(db, ReportDraftCreate(title="D2", ticker="AAPL"))
    result = svc.list_report_drafts(db, ticker="MSFT")
    assert all(d.ticker == "MSFT" for d in result)


def test_delete_report_draft(db: Session):
    draft = svc.create_report_draft(db, ReportDraftCreate(title="Del"))
    assert svc.delete_report_draft(db, draft.id) is True
    assert svc.get_report_draft(db, draft.id) is None


# ---------------------------------------------------------------------------
# Activity & Pinned Items
# ---------------------------------------------------------------------------

def test_recent_activity_created_on_project(db: Session):
    svc.create_project(db, ResearchProjectCreate(name="ActProj"))
    activity = svc.get_recent_activity(db, limit=5)
    assert len(activity) >= 1


def test_create_pinned_item(db: Session):
    data = PinnedItemCreate(entity_type="ticker", entity_id="AAPL", label="Apple Inc.")
    item = svc.create_pinned_item(db, data)
    assert item.entity_id == "AAPL"
    assert item.label == "Apple Inc."


def test_list_pinned_items(db: Session):
    svc.create_pinned_item(db, PinnedItemCreate(entity_type="ticker", entity_id="MSFT", label="MSFT"))
    result = svc.list_pinned_items(db)
    assert len(result) >= 1


def test_delete_pinned_item(db: Session):
    item = svc.create_pinned_item(db, PinnedItemCreate(entity_type="note", entity_id="x", label="X"))
    assert svc.delete_pinned_item(db, item.id) is True
    assert svc.delete_pinned_item(db, item.id) is False


# ---------------------------------------------------------------------------
# Global Workspace Search
# ---------------------------------------------------------------------------

def test_workspace_search_finds_project(db: Session):
    svc.create_project(db, ResearchProjectCreate(name="Semiconductor Deep Dive"))
    results = svc.workspace_search(db, "Semiconductor")
    assert any(r.entity_type == "project" for r in results)


def test_workspace_search_finds_note(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Tech"))
    svc.create_note(db, ResearchNoteCreate(project_id=p.id, title="NVDA earnings beat", content="Q4 results exceeded expectations"))
    results = svc.workspace_search(db, "NVDA earnings")
    assert any(r.entity_type == "note" for r in results)


def test_workspace_search_no_results(db: Session):
    results = svc.workspace_search(db, "xyzzy_no_match_9999")
    assert isinstance(results, list)


def test_workspace_search_limit(db: Session):
    p = svc.create_project(db, ResearchProjectCreate(name="Proj"))
    for i in range(5):
        svc.create_note(db, ResearchNoteCreate(project_id=p.id, title=f"Search note {i}"))
    results = svc.workspace_search(db, "Search note", limit=3)
    assert len(results) <= 3
