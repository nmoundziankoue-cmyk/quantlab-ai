"""M9 Phase 6 — Knowledge Graph V2.

Entity embeddings, semantic similarity, relationship scoring, market memory,
company similarity, and concept clustering — all without pgvector.

Uses a lightweight in-memory cosine-similarity engine backed by stdlib only.
"""
from __future__ import annotations

import math
import statistics
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Minimal dense vector helpers (stdlib, no numpy)
# ---------------------------------------------------------------------------

def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    na, nb = _norm(a), _norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return _dot(a, b) / (na * nb)


def _hash_embed(text: str, dim: int = 64) -> List[float]:
    """Deterministic pseudo-embedding from text hash (no ML model required)."""
    seed = hash(text) & 0xFFFFFFFF
    vec: List[float] = []
    for i in range(dim):
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        vec.append((seed / 0x7FFFFFFF) - 1.0)
    n = _norm(vec) or 1.0
    return [x / n for x in vec]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    id: str
    entity_type: str   # company | sector | concept | event | person
    name: str
    description: str = ""
    embedding: List[float] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.embedding:
            self.embedding = _hash_embed(f"{self.entity_type}:{self.name}:{self.description}")


@dataclass
class Relationship:
    source_id: str
    target_id: str
    relation_type: str   # competitor | supplier | customer | peer | influences | correlates
    score: float = 1.0   # strength in [0, 1]
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    entity: Entity
    similarity: float


# ---------------------------------------------------------------------------
# Knowledge Graph store
# ---------------------------------------------------------------------------

class KnowledgeGraphV2:
    """In-memory knowledge graph with cosine-similarity semantic search."""

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._relations: List[Relationship] = []
        self._type_index: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()
        self._seed_defaults()

    # ------------------------------------------------------------------
    # Entity CRUD
    # ------------------------------------------------------------------

    def add_entity(
        self,
        id: str,
        entity_type: str,
        name: str,
        description: str = "",
        embedding: Optional[List[float]] = None,
        metadata: Optional[dict] = None,
    ) -> Entity:
        e = Entity(id=id, entity_type=entity_type, name=name, description=description,
                   embedding=embedding or [], metadata=metadata or {})
        with self._lock:
            self._entities[id] = e
            if id not in self._type_index[entity_type]:
                self._type_index[entity_type].append(id)
        return e

    def get_entity(self, id: str) -> Optional[Entity]:
        return self._entities.get(id)

    def list_entities(self, entity_type: Optional[str] = None, limit: int = 100) -> List[Entity]:
        if entity_type:
            ids = self._type_index.get(entity_type, [])[:limit]
            return [self._entities[i] for i in ids if i in self._entities]
        return list(self._entities.values())[:limit]

    def delete_entity(self, id: str) -> bool:
        with self._lock:
            if id not in self._entities:
                return False
            etype = self._entities[id].entity_type
            self._entities.pop(id)
            self._type_index[etype] = [i for i in self._type_index[etype] if i != id]
            self._relations = [r for r in self._relations if r.source_id != id and r.target_id != id]
        return True

    # ------------------------------------------------------------------
    # Relationship CRUD
    # ------------------------------------------------------------------

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        score: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> Relationship:
        r = Relationship(source_id=source_id, target_id=target_id, relation_type=relation_type,
                         score=score, metadata=metadata or {})
        with self._lock:
            self._relations.append(r)
        return r

    def get_relationships(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "both",
    ) -> List[dict]:
        results = []
        for r in self._relations:
            if direction in ("out", "both") and r.source_id == entity_id:
                if not relation_type or r.relation_type == relation_type:
                    results.append({**r.__dict__, "direction": "out"})
            if direction in ("in", "both") and r.target_id == entity_id:
                if not relation_type or r.relation_type == relation_type:
                    results.append({**r.__dict__, "direction": "in"})
        return results

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        min_similarity: float = 0.0,
    ) -> List[SearchResult]:
        q_emb = _hash_embed(query)
        candidates = (
            [self._entities[i] for i in self._type_index.get(entity_type, []) if i in self._entities]
            if entity_type
            else list(self._entities.values())
        )
        scored = [
            SearchResult(entity=e, similarity=cosine_similarity(q_emb, e.embedding))
            for e in candidates
        ]
        scored = [s for s in scored if s.similarity >= min_similarity]
        scored.sort(key=lambda s: s.similarity, reverse=True)
        return scored[:top_k]

    def find_similar_companies(self, ticker: str, top_k: int = 5) -> List[SearchResult]:
        entity = self._entities.get(ticker)
        if not entity:
            return []
        candidates = [e for e in self._entities.values() if e.id != ticker and e.entity_type == "company"]
        scored = [SearchResult(entity=e, similarity=cosine_similarity(entity.embedding, e.embedding))
                  for e in candidates]
        scored.sort(key=lambda s: s.similarity, reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Concept clustering (simple centroid-based k-means, stdlib only)
    # ------------------------------------------------------------------

    def cluster_entities(self, entity_type: str = "concept", n_clusters: int = 5, iterations: int = 10) -> List[dict]:
        entities = [e for e in self._entities.values() if e.entity_type == entity_type]
        if len(entities) < n_clusters:
            return [{"cluster": i, "members": [e.id for e in entities[i:i+1]]} for i in range(len(entities))]

        dim = len(entities[0].embedding) if entities[0].embedding else 64
        centroids = [entities[i].embedding[:] for i in range(n_clusters)]

        for _ in range(iterations):
            assignments: List[List[int]] = [[] for _ in range(n_clusters)]
            for idx, e in enumerate(entities):
                best = max(range(n_clusters), key=lambda k: cosine_similarity(e.embedding, centroids[k]))
                assignments[best].append(idx)

            for k in range(n_clusters):
                if not assignments[k]:
                    continue
                new_centroid = [0.0] * dim
                for idx in assignments[k]:
                    for d in range(dim):
                        new_centroid[d] += entities[idx].embedding[d]
                n = len(assignments[k])
                new_centroid = [x / n for x in new_centroid]
                centroids[k] = new_centroid

        final_assignments: List[List[str]] = [[] for _ in range(n_clusters)]
        for e in entities:
            best = max(range(n_clusters), key=lambda k: cosine_similarity(e.embedding, centroids[k]))
            final_assignments[best].append(e.id)

        return [{"cluster": k, "members": final_assignments[k]} for k in range(n_clusters) if final_assignments[k]]

    # ------------------------------------------------------------------
    # Market memory (simple recency-weighted scoring)
    # ------------------------------------------------------------------

    def record_market_event(self, entity_id: str, event_type: str, impact: float) -> None:
        e = self._entities.get(entity_id)
        if not e:
            return
        events = e.metadata.get("events", [])
        events.append({"type": event_type, "impact": impact})
        events = events[-50:]  # keep last 50
        e.metadata["events"] = events
        e.metadata["avg_impact"] = statistics.mean(ev["impact"] for ev in events)

    def get_market_memory(self, entity_id: str) -> dict:
        e = self._entities.get(entity_id)
        if not e:
            return {}
        return {
            "id": entity_id,
            "name": e.name,
            "events": e.metadata.get("events", []),
            "avg_impact": e.metadata.get("avg_impact", 0.0),
        }

    # ------------------------------------------------------------------
    # Graph statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        return {
            "entity_count": len(self._entities),
            "relationship_count": len(self._relations),
            "entity_types": {k: len(v) for k, v in self._type_index.items()},
        }

    # ------------------------------------------------------------------
    # Seed with common company and sector entities
    # ------------------------------------------------------------------

    def _seed_defaults(self) -> None:
        companies = [
            ("AAPL", "Apple Inc.", "Consumer technology: iPhone, Mac, services"),
            ("MSFT", "Microsoft Corp.", "Enterprise software, cloud Azure, Office 365"),
            ("GOOGL", "Alphabet Inc.", "Search advertising, cloud GCP, AI research"),
            ("AMZN", "Amazon.com Inc.", "E-commerce, AWS cloud, logistics"),
            ("NVDA", "NVIDIA Corp.", "GPUs, AI accelerators, data center"),
            ("META", "Meta Platforms Inc.", "Social media, VR/AR, advertising"),
            ("TSLA", "Tesla Inc.", "Electric vehicles, energy storage, AI"),
            ("JPM", "JPMorgan Chase", "Investment banking, retail banking, asset management"),
            ("V", "Visa Inc.", "Payment network, consumer spending"),
            ("XOM", "ExxonMobil", "Integrated oil & gas, refining, chemicals"),
        ]
        sectors = [
            ("tech", "Technology", "Information technology sector"),
            ("finance", "Financials", "Banking, insurance, asset management"),
            ("energy", "Energy", "Oil, gas, renewables"),
            ("healthcare", "Healthcare", "Pharma, biotech, medical devices"),
            ("consumer", "Consumer Discretionary", "Retail, autos, entertainment"),
        ]
        for ticker, name, desc in companies:
            self.add_entity(ticker, "company", name, desc)
        for id_, name, desc in sectors:
            self.add_entity(id_, "sector", name, desc)
        self.add_relationship("AAPL", "MSFT", "competitor", 0.8)
        self.add_relationship("GOOGL", "MSFT", "competitor", 0.9)
        self.add_relationship("NVDA", "AMD", "competitor", 0.95)
        self.add_relationship("AAPL", "tech", "peer", 1.0)
        self.add_relationship("MSFT", "tech", "peer", 1.0)
        self.add_relationship("JPM", "finance", "peer", 1.0)
        self.add_relationship("XOM", "energy", "peer", 1.0)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_kg: Optional[KnowledgeGraphV2] = None


def get_knowledge_graph() -> KnowledgeGraphV2:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraphV2()
    return _kg
