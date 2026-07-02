"""Knowledge Graph router (M7) — entities, edges, traversal, extraction."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import services.knowledge_graph as svc
from schemas.knowledge_graph import (
    CreateEdgeRequest,
    CreateEntityRequest,
    ExtractEntitiesRequest,
    GraphNeighborhoodRequest,
)

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])


@router.post("/entities", response_model=Dict[str, Any])
def create_entity(req: CreateEntityRequest, db: Session = Depends(get_db)):
    """Create a new knowledge entity."""
    entity = svc.create_entity(
        db=db,
        name=req.name,
        entity_type=req.entity_type,
        description=req.description,
        aliases=req.aliases,
        properties=req.properties,
        tags=req.tags,
        confidence_score=req.confidence_score,
        source_doc_id=req.source_doc_id,
    )
    return svc._entity_to_dict(entity)


@router.get("/entities", response_model=List[Dict[str, Any]])
def list_entities(
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List entities, optionally filtered by type or name search."""
    entities = svc.list_entities(db, entity_type=entity_type, search=search, limit=limit)
    return [svc._entity_to_dict(e) for e in entities]


@router.get("/entities/{entity_id}", response_model=Dict[str, Any])
def get_entity(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific entity by ID."""
    entity = svc.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return svc._entity_to_dict(entity)


@router.put("/entities/{entity_id}", response_model=Dict[str, Any])
def update_entity(
    entity_id: uuid.UUID,
    body: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Update an existing entity."""
    entity = svc.update_entity(db, entity_id, **body)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return svc._entity_to_dict(entity)


@router.delete("/entities/{entity_id}", response_model=Dict[str, Any])
def delete_entity(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete an entity and all its edges."""
    ok = svc.delete_entity(db, entity_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"deleted": str(entity_id)}


@router.post("/edges", response_model=Dict[str, Any])
def create_edge(req: CreateEdgeRequest, db: Session = Depends(get_db)):
    """Create a directed edge between two entities."""
    edge = svc.create_edge(
        db=db,
        source_id=req.source_id,
        target_id=req.target_id,
        relationship_type=req.relationship_type,
        weight=req.weight,
        evidence=req.evidence,
        properties=req.properties,
    )
    return svc._edge_to_dict(edge)


@router.get("/edges", response_model=List[Dict[str, Any]])
def list_edges(
    entity_id: Optional[uuid.UUID] = None,
    relationship_type: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """List edges, optionally filtered by entity or relationship type."""
    edges = svc.list_edges(db, entity_id=entity_id, relationship_type=relationship_type, limit=limit)
    return [svc._edge_to_dict(e) for e in edges]


@router.delete("/edges/{edge_id}", response_model=Dict[str, Any])
def delete_edge(edge_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete an edge."""
    ok = svc.delete_edge(db, edge_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Edge not found")
    return {"deleted": str(edge_id)}


@router.get("/entities/{entity_id}/neighbors", response_model=Dict[str, Any])
def get_neighbors(
    entity_id: uuid.UUID,
    depth: int = 1,
    relationship_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """BFS traversal from an entity up to a given depth."""
    result = svc.get_neighbors(db, entity_id, depth=depth, relationship_type=relationship_type)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/graph", response_model=Dict[str, Any])
def get_full_graph(
    entity_type: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """Return the full knowledge graph as nodes + edges."""
    return svc.get_full_graph(db, entity_type=entity_type, limit=limit)


@router.post("/extract", response_model=Dict[str, Any])
def extract_entities(req: ExtractEntitiesRequest, db: Session = Depends(get_db)):
    """Extract entities from text and optionally persist them."""
    if req.persist:
        return svc.bulk_extract_and_store(db, req.text, source_doc_id=req.source_doc_id)
    entities = svc.extract_entities_from_text(req.text)
    return {"extracted_count": len(entities), "entities": entities}
