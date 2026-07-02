"""Knowledge Graph service — entity extraction, graph storage, traversal (M7)."""
from __future__ import annotations

import re
import uuid
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.knowledge_graph import KnowledgeEdge, KnowledgeEntity

# Known entity types
ENTITY_TYPES = {"TICKER", "SECTOR", "PERSON", "CONCEPT", "EVENT", "COUNTRY", "INDUSTRY", "PRODUCT"}

# Relationship types
RELATIONSHIP_TYPES = {
    "COMPETES_WITH", "SUPPLIES_TO", "CORRELATED_WITH", "BELONGS_TO",
    "MENTIONED_IN", "LEADS", "INFLUENCED_BY", "PART_OF",
}

# Regex patterns for entity extraction from text
_TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")
_COUNTRY_KEYWORDS = {"US", "USA", "EU", "UK", "CHINA", "JAPAN", "GERMANY", "FRANCE", "INDIA"}
_SECTOR_KEYWORDS = {
    "Technology", "Healthcare", "Financials", "Energy", "Industrials",
    "Materials", "Utilities", "Real Estate", "Consumer Staples", "Consumer Discretionary",
    "Communication Services",
}
_CONCEPT_KEYWORDS = {
    "inflation", "recession", "interest rate", "GDP", "Fed", "Federal Reserve",
    "earnings", "revenue", "profit margin", "debt", "equity", "volatility",
    "momentum", "value", "growth", "ESG", "AI", "machine learning", "cloud",
    "semiconductor", "supply chain", "M&A", "IPO", "buyback", "dividend",
}


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_entity(
    db: Session,
    name: str,
    entity_type: str,
    description: Optional[str] = None,
    aliases: Optional[List[str]] = None,
    properties: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    confidence_score: float = 1.0,
    source_doc_id: Optional[uuid.UUID] = None,
) -> KnowledgeEntity:
    entity = KnowledgeEntity(
        name=name,
        entity_type=entity_type.upper(),
        description=description,
        aliases=aliases,
        properties=properties,
        tags=tags,
        confidence_score=confidence_score,
        source_doc_id=source_doc_id,
    )
    db.add(entity)
    db.flush()
    return entity


def get_entity(db: Session, entity_id: uuid.UUID) -> Optional[KnowledgeEntity]:
    return db.get(KnowledgeEntity, entity_id)


def get_entity_by_name(db: Session, name: str) -> Optional[KnowledgeEntity]:
    stmt = select(KnowledgeEntity).where(KnowledgeEntity.name == name)
    return db.execute(stmt).scalars().first()


def list_entities(
    db: Session,
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> List[KnowledgeEntity]:
    stmt = select(KnowledgeEntity).order_by(KnowledgeEntity.name).limit(limit)
    if entity_type:
        stmt = stmt.where(KnowledgeEntity.entity_type == entity_type.upper())
    if search:
        stmt = stmt.where(KnowledgeEntity.name.ilike(f"%{search}%"))
    return list(db.execute(stmt).scalars())


def update_entity(
    db: Session,
    entity_id: uuid.UUID,
    **kwargs: Any,
) -> Optional[KnowledgeEntity]:
    entity = db.get(KnowledgeEntity, entity_id)
    if not entity:
        return None
    for k, v in kwargs.items():
        if hasattr(entity, k):
            setattr(entity, k, v)
    db.flush()
    return entity


def delete_entity(db: Session, entity_id: uuid.UUID) -> bool:
    entity = db.get(KnowledgeEntity, entity_id)
    if not entity:
        return False
    db.delete(entity)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Edge CRUD
# ---------------------------------------------------------------------------

def create_edge(
    db: Session,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    relationship_type: str,
    weight: float = 1.0,
    evidence: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> KnowledgeEdge:
    edge = KnowledgeEdge(
        source_id=source_id,
        target_id=target_id,
        relationship_type=relationship_type.upper(),
        weight=weight,
        evidence=evidence,
        properties=properties,
    )
    db.add(edge)
    db.flush()
    return edge


def get_edge(db: Session, edge_id: uuid.UUID) -> Optional[KnowledgeEdge]:
    return db.get(KnowledgeEdge, edge_id)


def list_edges(
    db: Session,
    entity_id: Optional[uuid.UUID] = None,
    relationship_type: Optional[str] = None,
    limit: int = 200,
) -> List[KnowledgeEdge]:
    stmt = select(KnowledgeEdge).limit(limit)
    if entity_id:
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(KnowledgeEdge.source_id == entity_id, KnowledgeEdge.target_id == entity_id)
        )
    if relationship_type:
        stmt = stmt.where(KnowledgeEdge.relationship_type == relationship_type.upper())
    return list(db.execute(stmt).scalars())


def delete_edge(db: Session, edge_id: uuid.UUID) -> bool:
    edge = db.get(KnowledgeEdge, edge_id)
    if not edge:
        return False
    db.delete(edge)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Graph traversal
# ---------------------------------------------------------------------------

def get_neighbors(
    db: Session,
    entity_id: uuid.UUID,
    depth: int = 1,
    relationship_type: Optional[str] = None,
) -> Dict[str, Any]:
    """BFS traversal up to `depth` hops from the given entity."""
    root = db.get(KnowledgeEntity, entity_id)
    if not root:
        return {"error": "Entity not found"}

    visited: Set[uuid.UUID] = {entity_id}
    frontier: Set[uuid.UUID] = {entity_id}
    nodes: List[Dict[str, Any]] = [_entity_to_dict(root)]
    edges_out: List[Dict[str, Any]] = []

    for _ in range(depth):
        next_frontier: Set[uuid.UUID] = set()
        for fid in frontier:
            all_edges = list_edges(db, entity_id=fid, relationship_type=relationship_type, limit=50)
            for edge in all_edges:
                edges_out.append(_edge_to_dict(edge))
                for nid in (edge.source_id, edge.target_id):
                    if nid not in visited:
                        visited.add(nid)
                        next_frontier.add(nid)
                        entity = db.get(KnowledgeEntity, nid)
                        if entity:
                            nodes.append(_entity_to_dict(entity))
        frontier = next_frontier
        if not frontier:
            break

    return {
        "root_entity_id": str(entity_id),
        "depth": depth,
        "nodes": nodes,
        "edges": edges_out,
        "node_count": len(nodes),
        "edge_count": len(edges_out),
    }


def get_full_graph(
    db: Session,
    entity_type: Optional[str] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    """Return the full knowledge graph (or a filtered subgraph)."""
    entities = list_entities(db, entity_type=entity_type, limit=limit)
    entity_ids = {e.id for e in entities}
    edges = list_edges(db, limit=500)
    # Filter edges to only include those where both endpoints are in the entity set
    visible_edges = [
        e for e in edges
        if e.source_id in entity_ids and e.target_id in entity_ids
    ]
    return {
        "nodes": [_entity_to_dict(e) for e in entities],
        "edges": [_edge_to_dict(e) for e in visible_edges],
        "node_count": len(entities),
        "edge_count": len(visible_edges),
    }


# ---------------------------------------------------------------------------
# Entity extraction from text
# ---------------------------------------------------------------------------

KNOWN_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK", "UNH", "JNJ",
    "JPM", "V", "MA", "PG", "XOM", "CVX", "LLY", "HD", "MRK", "ABBV", "PEP",
    "KO", "AVGO", "COST", "TMO", "MCD", "ADBE", "CRM", "NFLX", "AMD", "INTC",
    "QCOM", "ORCL", "IBM", "CSCO", "TXN", "NEE", "DIS", "GE", "HON", "CAT",
    "RTX", "BA", "GS", "MS", "BAC", "WFC", "C", "BLK",
}


def extract_entities_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract entities from free text. Returns a list of entity dicts."""
    entities: List[Dict[str, Any]] = []
    seen_names: Set[str] = set()

    # Tickers: known list only (avoid false positives)
    for ticker in KNOWN_TICKERS:
        if re.search(rf"\b{ticker}\b", text):
            if ticker not in seen_names:
                seen_names.add(ticker)
                entities.append({
                    "name": ticker,
                    "entity_type": "TICKER",
                    "confidence_score": 0.95,
                })

    # Sectors
    for sector in _SECTOR_KEYWORDS:
        if sector.lower() in text.lower():
            if sector not in seen_names:
                seen_names.add(sector)
                entities.append({
                    "name": sector,
                    "entity_type": "SECTOR",
                    "confidence_score": 0.85,
                })

    # Countries
    for country in _COUNTRY_KEYWORDS:
        if re.search(rf"\b{country}\b", text, re.IGNORECASE):
            if country not in seen_names:
                seen_names.add(country)
                entities.append({
                    "name": country,
                    "entity_type": "COUNTRY",
                    "confidence_score": 0.90,
                })

    # Concepts
    for concept in _CONCEPT_KEYWORDS:
        if concept.lower() in text.lower():
            if concept not in seen_names:
                seen_names.add(concept)
                entities.append({
                    "name": concept,
                    "entity_type": "CONCEPT",
                    "confidence_score": 0.75,
                })

    return entities


def bulk_extract_and_store(
    db: Session,
    text: str,
    source_doc_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Extract entities from text and persist new ones to the knowledge graph."""
    extracted = extract_entities_from_text(text)
    created = 0
    existing = 0
    entity_ids: List[str] = []

    for e in extracted:
        existing_entity = get_entity_by_name(db, e["name"])
        if existing_entity:
            existing += 1
            entity_ids.append(str(existing_entity.id))
        else:
            new_entity = create_entity(
                db=db,
                name=e["name"],
                entity_type=e["entity_type"],
                confidence_score=e["confidence_score"],
                source_doc_id=source_doc_id,
            )
            created += 1
            entity_ids.append(str(new_entity.id))

    return {
        "extracted_count": len(extracted),
        "created": created,
        "existing": existing,
        "entity_ids": entity_ids,
    }


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _entity_to_dict(e: KnowledgeEntity) -> Dict[str, Any]:
    return {
        "id": str(e.id),
        "name": e.name,
        "entity_type": e.entity_type,
        "description": e.description,
        "confidence_score": e.confidence_score,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _edge_to_dict(e: KnowledgeEdge) -> Dict[str, Any]:
    return {
        "id": str(e.id),
        "source_id": str(e.source_id),
        "target_id": str(e.target_id),
        "relationship_type": e.relationship_type,
        "weight": e.weight,
        "evidence": e.evidence,
    }
