"""Tests for the Knowledge Graph service (M7)."""
from __future__ import annotations

import uuid
import pytest

import services.knowledge_graph as svc
from models.knowledge_graph import KnowledgeEdge, KnowledgeEntity


# ---------------------------------------------------------------------------
# Entity CRUD
# ---------------------------------------------------------------------------

class TestEntityCRUD:
    def test_create_entity_minimal(self, db):
        entity = svc.create_entity(db, name="AAPL", entity_type="TICKER")
        assert entity.id is not None
        assert entity.name == "AAPL"
        assert entity.entity_type == "TICKER"

    def test_create_entity_with_description(self, db):
        entity = svc.create_entity(db, name="Technology", entity_type="SECTOR", description="Tech sector")
        assert entity.description == "Tech sector"

    def test_create_entity_type_uppercased(self, db):
        entity = svc.create_entity(db, name="MSFT", entity_type="ticker")
        assert entity.entity_type == "TICKER"

    def test_get_entity_exists(self, db):
        entity = svc.create_entity(db, name="NVDA", entity_type="TICKER")
        fetched = svc.get_entity(db, entity.id)
        assert fetched is not None
        assert fetched.id == entity.id

    def test_get_entity_not_found(self, db):
        result = svc.get_entity(db, uuid.uuid4())
        assert result is None

    def test_get_entity_by_name(self, db):
        svc.create_entity(db, name="TSLA_UNIQUE", entity_type="TICKER")
        entity = svc.get_entity_by_name(db, "TSLA_UNIQUE")
        assert entity is not None
        assert entity.name == "TSLA_UNIQUE"

    def test_list_entities_empty(self, db):
        result = svc.list_entities(db, limit=100)
        assert isinstance(result, list)

    def test_list_entities_filter_by_type(self, db):
        svc.create_entity(db, name="AMZN_T", entity_type="TICKER")
        svc.create_entity(db, name="US_C", entity_type="COUNTRY")
        tickers = svc.list_entities(db, entity_type="TICKER", limit=100)
        assert all(e.entity_type == "TICKER" for e in tickers)

    def test_list_entities_search(self, db):
        svc.create_entity(db, name="SearchTarget123", entity_type="CONCEPT")
        results = svc.list_entities(db, search="SearchTarget123", limit=10)
        assert any(e.name == "SearchTarget123" for e in results)

    def test_update_entity(self, db):
        entity = svc.create_entity(db, name="UpdateMe", entity_type="CONCEPT")
        updated = svc.update_entity(db, entity.id, description="Updated description")
        assert updated is not None
        assert updated.description == "Updated description"

    def test_update_entity_not_found(self, db):
        result = svc.update_entity(db, uuid.uuid4(), name="X")
        assert result is None

    def test_delete_entity(self, db):
        entity = svc.create_entity(db, name="DeleteMe_KG", entity_type="TICKER")
        ok = svc.delete_entity(db, entity.id)
        assert ok is True
        assert svc.get_entity(db, entity.id) is None

    def test_delete_entity_not_found(self, db):
        ok = svc.delete_entity(db, uuid.uuid4())
        assert ok is False


# ---------------------------------------------------------------------------
# Edge CRUD
# ---------------------------------------------------------------------------

class TestEdgeCRUD:
    def test_create_edge(self, db):
        src = svc.create_entity(db, name="AAPL_Edge", entity_type="TICKER")
        tgt = svc.create_entity(db, name="Technology_Edge", entity_type="SECTOR")
        edge = svc.create_edge(db, src.id, tgt.id, "BELONGS_TO")
        assert edge.id is not None
        assert edge.relationship_type == "BELONGS_TO"

    def test_edge_type_uppercased(self, db):
        src = svc.create_entity(db, name="SrcUpper", entity_type="TICKER")
        tgt = svc.create_entity(db, name="TgtUpper", entity_type="SECTOR")
        edge = svc.create_edge(db, src.id, tgt.id, "belongs_to")
        assert edge.relationship_type == "BELONGS_TO"

    def test_create_edge_with_weight(self, db):
        src = svc.create_entity(db, name="SrcW", entity_type="TICKER")
        tgt = svc.create_entity(db, name="TgtW", entity_type="TICKER")
        edge = svc.create_edge(db, src.id, tgt.id, "CORRELATED_WITH", weight=0.85)
        assert edge.weight == 0.85

    def test_get_edge_exists(self, db):
        src = svc.create_entity(db, name="SrcGet", entity_type="TICKER")
        tgt = svc.create_entity(db, name="TgtGet", entity_type="SECTOR")
        edge = svc.create_edge(db, src.id, tgt.id, "BELONGS_TO")
        fetched = svc.get_edge(db, edge.id)
        assert fetched is not None

    def test_get_edge_not_found(self, db):
        result = svc.get_edge(db, uuid.uuid4())
        assert result is None

    def test_list_edges_by_entity(self, db):
        src = svc.create_entity(db, name="SrcList", entity_type="TICKER")
        tgt1 = svc.create_entity(db, name="TgtList1", entity_type="SECTOR")
        tgt2 = svc.create_entity(db, name="TgtList2", entity_type="SECTOR")
        svc.create_edge(db, src.id, tgt1.id, "BELONGS_TO")
        svc.create_edge(db, src.id, tgt2.id, "CORRELATED_WITH")
        edges = svc.list_edges(db, entity_id=src.id, limit=10)
        assert len(edges) >= 2

    def test_delete_edge(self, db):
        src = svc.create_entity(db, name="SrcDel", entity_type="TICKER")
        tgt = svc.create_entity(db, name="TgtDel", entity_type="SECTOR")
        edge = svc.create_edge(db, src.id, tgt.id, "BELONGS_TO")
        ok = svc.delete_edge(db, edge.id)
        assert ok is True

    def test_delete_edge_not_found(self, db):
        ok = svc.delete_edge(db, uuid.uuid4())
        assert ok is False


# ---------------------------------------------------------------------------
# Graph traversal
# ---------------------------------------------------------------------------

class TestGraphTraversal:
    def test_get_neighbors_not_found(self, db):
        result = svc.get_neighbors(db, uuid.uuid4())
        assert "error" in result

    def test_get_neighbors_depth_1(self, db):
        src = svc.create_entity(db, name="SrcNeighbor", entity_type="TICKER")
        tgt = svc.create_entity(db, name="TgtNeighbor", entity_type="SECTOR")
        svc.create_edge(db, src.id, tgt.id, "BELONGS_TO")
        result = svc.get_neighbors(db, src.id, depth=1)
        assert "nodes" in result
        assert "edges" in result
        node_ids = {n["id"] for n in result["nodes"]}
        assert str(tgt.id) in node_ids

    def test_get_neighbors_includes_root(self, db):
        entity = svc.create_entity(db, name="RootNode", entity_type="CONCEPT")
        result = svc.get_neighbors(db, entity.id)
        node_ids = {n["id"] for n in result["nodes"]}
        assert str(entity.id) in node_ids

    def test_get_full_graph_returns_nodes_edges(self, db):
        result = svc.get_full_graph(db)
        assert "nodes" in result
        assert "edges" in result

    def test_get_full_graph_filter_by_type(self, db):
        svc.create_entity(db, name="FullGraphTicker1", entity_type="TICKER")
        result = svc.get_full_graph(db, entity_type="TICKER")
        assert all(n["entity_type"] == "TICKER" for n in result["nodes"])


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

class TestEntityExtraction:
    def test_extract_known_ticker(self):
        entities = svc.extract_entities_from_text("AAPL reported strong earnings this quarter.")
        names = [e["name"] for e in entities]
        assert "AAPL" in names

    def test_extract_sector(self):
        entities = svc.extract_entities_from_text("The Technology sector outperformed.")
        names = [e["name"] for e in entities]
        assert "Technology" in names

    def test_extract_country(self):
        entities = svc.extract_entities_from_text("The US economy grew 2.5%.")
        names = [e["name"] for e in entities]
        assert "US" in names

    def test_extract_concept(self):
        entities = svc.extract_entities_from_text("Inflation concerns are weighing on markets.")
        names = [e["name"] for e in entities]
        assert "inflation" in names

    def test_extract_returns_entity_types(self):
        entities = svc.extract_entities_from_text("AAPL is in the Technology sector.")
        for e in entities:
            assert "entity_type" in e
            assert "confidence_score" in e

    def test_bulk_extract_and_store_creates_entities(self, db):
        result = svc.bulk_extract_and_store(
            db, "MSFT is a Technology company in the US market."
        )
        assert "extracted_count" in result
        assert result["extracted_count"] >= 0

    def test_bulk_extract_idempotent(self, db):
        text = "AAPL AAPL AAPL"
        r1 = svc.bulk_extract_and_store(db, text)
        r2 = svc.bulk_extract_and_store(db, text)
        # Second call should find existing entities
        assert r2["existing"] >= r1["created"]
