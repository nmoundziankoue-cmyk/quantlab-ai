"""M9 Phase 6 — Knowledge Graph V2 API."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from services.knowledge_graph_v2 import get_knowledge_graph

router = APIRouter(prefix="/knowledge/v2", tags=["knowledge_graph_v2"])


class EntityCreate(BaseModel):
    id: str
    entity_type: str
    name: str
    description: str = ""
    metadata: dict = {}


class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    score: float = 1.0
    metadata: dict = {}


@router.get("/stats")
def stats():
    return get_knowledge_graph().stats()


@router.post("/entities")
def create_entity(body: EntityCreate):
    e = get_knowledge_graph().add_entity(body.id, body.entity_type, body.name, body.description, metadata=body.metadata)
    return {"id": e.id, "name": e.name, "entity_type": e.entity_type}


@router.get("/entities")
def list_entities(entity_type: Optional[str] = None, limit: int = Query(100, le=500)):
    entities = get_knowledge_graph().list_entities(entity_type, limit)
    return {"entities": [{"id": e.id, "name": e.name, "type": e.entity_type, "description": e.description} for e in entities]}


@router.get("/entities/{entity_id}")
def get_entity(entity_id: str):
    e = get_knowledge_graph().get_entity(entity_id)
    if not e:
        raise HTTPException(404, f"Entity '{entity_id}' not found")
    return {"id": e.id, "name": e.name, "type": e.entity_type, "description": e.description, "metadata": e.metadata}


@router.delete("/entities/{entity_id}")
def delete_entity(entity_id: str):
    ok = get_knowledge_graph().delete_entity(entity_id)
    if not ok:
        raise HTTPException(404, f"Entity '{entity_id}' not found")
    return {"deleted": entity_id}


@router.post("/relationships")
def create_relationship(body: RelationshipCreate):
    r = get_knowledge_graph().add_relationship(body.source_id, body.target_id, body.relation_type, body.score, body.metadata)
    return r.__dict__


@router.get("/entities/{entity_id}/relationships")
def get_relationships(entity_id: str, relation_type: Optional[str] = None, direction: str = "both"):
    return {"relationships": get_knowledge_graph().get_relationships(entity_id, relation_type, direction)}


@router.get("/search")
def semantic_search(
    q: str = Query(..., description="Search query"),
    entity_type: Optional[str] = None,
    top_k: int = Query(10, le=50),
    min_similarity: float = 0.0,
):
    results = get_knowledge_graph().semantic_search(q, top_k, entity_type, min_similarity)
    return {
        "query": q,
        "results": [{"id": r.entity.id, "name": r.entity.name, "type": r.entity.entity_type, "similarity": round(r.similarity, 4)} for r in results],
    }


@router.get("/similar/{ticker}")
def similar_companies(ticker: str, top_k: int = Query(5, le=20)):
    results = get_knowledge_graph().find_similar_companies(ticker, top_k)
    return {
        "ticker": ticker,
        "similar": [{"id": r.entity.id, "name": r.entity.name, "similarity": round(r.similarity, 4)} for r in results],
    }


@router.get("/clusters")
def clusters(entity_type: str = "company", n: int = Query(5, le=20)):
    return {"clusters": get_knowledge_graph().cluster_entities(entity_type, n)}
