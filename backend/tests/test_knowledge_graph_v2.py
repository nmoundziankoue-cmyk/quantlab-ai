"""Tests for M9 Phase 6 — Knowledge Graph V2."""
import pytest
from services.knowledge_graph_v2 import (
    KnowledgeGraphV2, cosine_similarity, _hash_embed, get_knowledge_graph,
)


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

class TestVectorHelpers:
    def test_cosine_identical(self):
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_cosine_opposite(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_cosine_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_hash_embed_deterministic(self):
        v1 = _hash_embed("AAPL", 32)
        v2 = _hash_embed("AAPL", 32)
        assert v1 == v2

    def test_hash_embed_different_texts(self):
        v1 = _hash_embed("AAPL")
        v2 = _hash_embed("MSFT")
        assert v1 != v2

    def test_hash_embed_unit_norm(self):
        import math
        v = _hash_embed("test", 64)
        norm = math.sqrt(sum(x * x for x in v))
        assert norm == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# Entity CRUD
# ---------------------------------------------------------------------------

class TestEntityCRUD:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_add_and_get(self):
        e = self.kg.add_entity("TEST", "company", "Test Corp", "A test company")
        assert e.id == "TEST"
        assert self.kg.get_entity("TEST") is e

    def test_get_nonexistent(self):
        assert self.kg.get_entity("NOBODY") is None

    def test_list_all(self):
        self.kg.add_entity("X1", "concept", "X1", "")
        entities = self.kg.list_entities()
        assert any(e.id == "X1" for e in entities)

    def test_list_by_type(self):
        self.kg.add_entity("S1", "sector", "Sector One", "")
        companies = self.kg.list_entities("company")
        sectors = self.kg.list_entities("sector")
        assert all(e.entity_type == "company" for e in companies)
        assert any(e.id == "S1" for e in sectors)

    def test_delete_entity(self):
        self.kg.add_entity("DEL", "company", "Delete Me", "")
        assert self.kg.delete_entity("DEL")
        assert self.kg.get_entity("DEL") is None

    def test_delete_nonexistent(self):
        assert not self.kg.delete_entity("GHOST")

    def test_delete_removes_relationships(self):
        self.kg.add_entity("A", "company", "A", "")
        self.kg.add_entity("B", "company", "B", "")
        self.kg.add_relationship("A", "B", "peer")
        self.kg.delete_entity("A")
        rels = self.kg.get_relationships("B")
        assert not any(r["source_id"] == "A" for r in rels)

    def test_limit(self):
        for i in range(10):
            self.kg.add_entity(f"C{i}", "company", f"Corp{i}", "")
        entities = self.kg.list_entities(limit=5)
        assert len(entities) <= 5


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

class TestRelationships:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)
        self.kg.add_entity("A", "company", "A Corp", "")
        self.kg.add_entity("B", "company", "B Corp", "")

    def test_add_relationship(self):
        r = self.kg.add_relationship("A", "B", "competitor", 0.9)
        assert r.source_id == "A"
        assert r.target_id == "B"
        assert r.score == 0.9

    def test_get_outbound(self):
        self.kg.add_relationship("A", "B", "peer")
        rels = self.kg.get_relationships("A", direction="out")
        assert len(rels) >= 1
        assert all(r["source_id"] == "A" for r in rels)

    def test_get_inbound(self):
        self.kg.add_relationship("A", "B", "peer")
        rels = self.kg.get_relationships("B", direction="in")
        assert any(r["source_id"] == "A" for r in rels)

    def test_filter_by_type(self):
        self.kg.add_relationship("A", "B", "competitor")
        self.kg.add_relationship("A", "B", "customer")
        comps = self.kg.get_relationships("A", relation_type="competitor")
        assert all(r["relation_type"] == "competitor" for r in comps)


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------

class TestSemanticSearch:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_search_returns_results(self):
        results = self.kg.semantic_search("technology company cloud", top_k=5)
        assert len(results) <= 5

    def test_search_sorted_by_similarity(self):
        results = self.kg.semantic_search("banking finance", top_k=10)
        sims = [r.similarity for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_min_similarity_filter(self):
        results = self.kg.semantic_search("anything", top_k=10, min_similarity=0.99)
        assert all(r.similarity >= 0.99 for r in results)

    def test_type_filter(self):
        results = self.kg.semantic_search("cloud", entity_type="company", top_k=10)
        assert all(r.entity.entity_type == "company" for r in results)

    def test_similar_companies(self):
        similar = self.kg.find_similar_companies("AAPL", top_k=3)
        assert len(similar) <= 3
        assert all(r.entity.id != "AAPL" for r in similar)

    def test_similar_nonexistent(self):
        assert self.kg.find_similar_companies("GHOST") == []


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

class TestClustering:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_cluster_returns_groups(self):
        clusters = self.kg.cluster_entities("company", n_clusters=3)
        assert len(clusters) > 0

    def test_all_entities_assigned(self):
        clusters = self.kg.cluster_entities("company", n_clusters=3)
        all_members = [m for c in clusters for m in c["members"]]
        companies = self.kg.list_entities("company")
        assert len(all_members) == len(companies)

    def test_fewer_entities_than_clusters(self):
        clusters = self.kg.cluster_entities("person", n_clusters=5)
        assert isinstance(clusters, list)


# ---------------------------------------------------------------------------
# Market memory
# ---------------------------------------------------------------------------

class TestMarketMemory:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_record_and_retrieve(self):
        self.kg.record_market_event("AAPL", "earnings_beat", 0.8)
        memory = self.kg.get_market_memory("AAPL")
        assert len(memory["events"]) > 0
        assert memory["events"][-1]["impact"] == 0.8

    def test_avg_impact_computed(self):
        self.kg.record_market_event("MSFT", "upgrade", 0.6)
        self.kg.record_market_event("MSFT", "downgrade", 0.2)
        m = self.kg.get_market_memory("MSFT")
        assert m["avg_impact"] == pytest.approx(0.4, abs=0.01)

    def test_nonexistent_entity(self):
        assert self.kg.get_market_memory("GHOST") == {}


# ---------------------------------------------------------------------------
# Stats and singleton
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats(self):
        kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(kg)
        s = kg.stats()
        assert "entity_count" in s
        assert "relationship_count" in s

    def test_singleton(self):
        g1 = get_knowledge_graph()
        g2 = get_knowledge_graph()
        assert g1 is g2
