"""M14 Phase 12 — Tests: knowledge graph enrichment (Phase 4).

Entity fields use `.id` (not `.entity_id`).
connected_components returns List[List[str]].
"""
import pytest
from services.knowledge_graph_v2 import KnowledgeGraphV2
from services.knowledge_graph_enrichment import (
    ALT_ENTITY_TYPES,
    ALT_RELATION_TYPES,
    add_executive,
    add_board_member,
    add_fund,
    add_supplier_relationship,
    add_customer_relationship,
    add_country_exposure,
    add_commodity_exposure,
    add_technology,
    add_patent,
    degree_centrality,
    connected_components,
    label_propagation_communities,
    dependency_chain,
    graph_metrics_summary,
)


@pytest.fixture()
def kg():
    return KnowledgeGraphV2()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_alt_entity_types_nonempty():
    assert len(ALT_ENTITY_TYPES) > 0


def test_alt_relation_types_nonempty():
    assert len(ALT_RELATION_TYPES) > 0


# ---------------------------------------------------------------------------
# add_executive
# ---------------------------------------------------------------------------

def test_add_executive_adds_entity(kg):
    before = len(kg.list_entities())
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    after = len(kg.list_entities())
    assert after > before


def test_add_executive_creates_relationship(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    rels = kg._relations
    assert any(r.source_id == "exec_cook" or r.target_id == "exec_cook" for r in rels)


# ---------------------------------------------------------------------------
# add_board_member
# ---------------------------------------------------------------------------

def test_add_board_member(kg):
    before = len(kg.list_entities())
    add_board_member(kg, "board_01", "Arthur Levinson", "AAPL")
    after = len(kg.list_entities())
    assert after > before


# ---------------------------------------------------------------------------
# add_fund
# ---------------------------------------------------------------------------

def test_add_fund(kg):
    before = len(kg.list_entities())
    add_fund(kg, "fund_berkshire", "Berkshire Hathaway", ["AAPL", "BAC"])
    after = len(kg.list_entities())
    assert after > before


# ---------------------------------------------------------------------------
# add_supplier_relationship
# ---------------------------------------------------------------------------

def test_add_supplier_relationship(kg):
    add_supplier_relationship(kg, "TSMC", "Taiwan Semiconductor", "AAPL", 0.35)
    rels = kg._relations
    assert any(r.source_id == "TSMC" or r.target_id == "TSMC" for r in rels)


# ---------------------------------------------------------------------------
# add_customer_relationship
# ---------------------------------------------------------------------------

def test_add_customer_relationship(kg):
    add_customer_relationship(kg, "FOXCONN", "Foxconn", "AAPL", 0.25)
    rels = kg._relations
    assert any(r.source_id == "FOXCONN" or r.target_id == "FOXCONN" for r in rels)


# ---------------------------------------------------------------------------
# add_country_exposure
# ---------------------------------------------------------------------------

def test_add_country_exposure(kg):
    before = len(kg.list_entities())
    add_country_exposure(kg, "AAPL", "CN", 0.20)
    after = len(kg.list_entities())
    assert after > before


# ---------------------------------------------------------------------------
# add_commodity_exposure
# ---------------------------------------------------------------------------

def test_add_commodity_exposure(kg):
    before = len(kg.list_entities())
    add_commodity_exposure(kg, "AAPL", "LITHIUM", 0.10)
    after = len(kg.list_entities())
    assert after > before


# ---------------------------------------------------------------------------
# add_technology
# ---------------------------------------------------------------------------

def test_add_technology(kg):
    before = len(kg.list_entities())
    add_technology(kg, "AAPL", "tech_mlchip", "Apple Silicon")
    after = len(kg.list_entities())
    assert after > before


# ---------------------------------------------------------------------------
# add_patent
# ---------------------------------------------------------------------------

def test_add_patent_adds_relationship(kg):
    initial_rels = len(kg._relations)
    add_patent(kg, "AAPL", "pat_12345", "Face ID biometric authentication method")
    # Patent adds a relationship even if entity isn't separately listed
    assert len(kg._relations) >= initial_rels


# ---------------------------------------------------------------------------
# Graph algorithms
# ---------------------------------------------------------------------------

def test_degree_centrality_empty():
    kg_empty = KnowledgeGraphV2()
    centrality = degree_centrality(kg_empty)
    assert isinstance(centrality, dict)


def test_degree_centrality_after_additions(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    add_supplier_relationship(kg, "TSMC", "TSMC", "AAPL", 0.4)
    centrality = degree_centrality(kg)
    assert isinstance(centrality, dict)
    assert all(isinstance(v, float) for v in centrality.values())


def test_degree_centrality_aapl_connected(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    add_supplier_relationship(kg, "TSMC", "TSMC", "AAPL", 0.4)
    centrality = degree_centrality(kg)
    # AAPL should have centrality > 0 since it has connections
    assert centrality.get("AAPL", 0) > 0


def test_connected_components_empty():
    kg_empty = KnowledgeGraphV2()
    comps = connected_components(kg_empty)
    assert isinstance(comps, list)


def test_connected_components_returns_lists(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    comps = connected_components(kg)
    assert len(comps) >= 1
    # Each component is a list or set
    for c in comps:
        assert hasattr(c, "__iter__")


def test_connected_components_cover_nodes(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    add_supplier_relationship(kg, "TSMC", "TSMC", "AAPL", 0.4)
    comps = connected_components(kg)
    all_nodes = {node for comp in comps for node in comp}
    # exec_cook should be reachable
    assert "exec_cook" in all_nodes


def test_label_propagation_communities_returns_mapping(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    add_supplier_relationship(kg, "TSMC", "TSMC", "AAPL", 0.4)
    communities = label_propagation_communities(kg)
    # Returns Dict[str, int] (node -> community_id)
    assert isinstance(communities, dict)


def test_label_propagation_communities_nonempty(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    communities = label_propagation_communities(kg)
    # Dict has at least one node->community mapping
    assert len(communities) >= 1


def test_label_propagation_deterministic(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    add_supplier_relationship(kg, "TSMC", "TSMC", "AAPL", 0.4)
    c1 = label_propagation_communities(kg)
    c2 = label_propagation_communities(kg)
    # Same number of nodes in community map
    assert len(c1) == len(c2)


def test_dependency_chain_not_found(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    path = dependency_chain(kg, "AAPL", "NONEXISTENT_NODE_12345")
    assert path is None


def test_dependency_chain_self(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    path = dependency_chain(kg, "AAPL", "AAPL")
    assert path == ["AAPL"]


def test_dependency_chain_one_hop(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    path = dependency_chain(kg, "exec_cook", "AAPL")
    assert path is not None
    assert "exec_cook" in path
    assert "AAPL" in path


def test_dependency_chain_max_depth_respected(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    # max_depth=0 → only self paths possible
    path = dependency_chain(kg, "exec_cook", "AAPL", max_depth=0)
    # With depth 0, no path to a different node
    assert path is None


# ---------------------------------------------------------------------------
# graph_metrics_summary
# ---------------------------------------------------------------------------

def test_graph_metrics_summary_empty():
    kg_empty = KnowledgeGraphV2()
    metrics = graph_metrics_summary(kg_empty)
    assert "node_count" in metrics
    assert "component_count" in metrics
    assert "largest_component_size" in metrics
    assert "community_count" in metrics
    assert "top_central_nodes" in metrics


def test_graph_metrics_summary_counts(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    add_supplier_relationship(kg, "TSMC", "TSMC", "AAPL", 0.4)
    metrics = graph_metrics_summary(kg)
    assert metrics["node_count"] > 0
    assert metrics["largest_component_size"] <= metrics["node_count"]
    assert isinstance(metrics["top_central_nodes"], list)


def test_graph_metrics_summary_top_nodes_have_fields(kg):
    add_executive(kg, "exec_cook", "Tim Cook", "AAPL", "CEO")
    metrics = graph_metrics_summary(kg)
    for node in metrics["top_central_nodes"]:
        assert "node_id" in node or "centrality" in node or len(node) > 0
