"""M14 Phase 4 — Knowledge graph enrichment.

Extends the existing M9 `KnowledgeGraphV2` (services/knowledge_graph_v2.py)
with alternative-data entity types (executives, boards, funds, suppliers,
customers, countries, currencies, commodities, technologies, patents) and
graph-theoretic metrics (degree centrality, connected components, community
detection, dependency chains).  Composition over modification — the stable
M9 module is never edited.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set

from services.knowledge_graph_v2 import KnowledgeGraphV2, get_knowledge_graph

# Entity types introduced by M14 (in addition to M9's "company"/"sector"/"concept")
ALT_ENTITY_TYPES = [
    "executive", "board", "fund", "industry", "supplier", "customer",
    "country", "currency", "commodity", "technology", "patent",
]

# Relationship types introduced by M14
ALT_RELATION_TYPES = [
    "employs", "board_member_of", "holds_position_in", "supplies_to",
    "customer_of", "located_in", "denominated_in", "exposed_to_commodity",
    "uses_technology", "owns_patent",
]


def add_executive(kg: KnowledgeGraphV2, exec_id: str, name: str, company_id: str, title: str = "") -> None:
    kg.add_entity(exec_id, "executive", name, description=title, metadata={"company": company_id, "title": title})
    kg.add_relationship(exec_id, company_id, "holds_position_in", score=1.0, metadata={"title": title})


def add_board_member(kg: KnowledgeGraphV2, member_id: str, name: str, company_id: str) -> None:
    kg.add_entity(member_id, "board", name)
    kg.add_relationship(member_id, company_id, "board_member_of", score=1.0)


def add_fund(kg: KnowledgeGraphV2, fund_id: str, name: str, holdings: Optional[List[str]] = None) -> None:
    kg.add_entity(fund_id, "fund", name, metadata={"holdings": holdings or []})
    for ticker in (holdings or []):
        kg.add_relationship(fund_id, ticker, "customer_of", score=0.5, metadata={"relation": "holds"})


def add_supplier_relationship(kg: KnowledgeGraphV2, supplier_id: str, supplier_name: str, customer_company_id: str, concentration: float = 0.0) -> None:
    if kg.get_entity(supplier_id) is None:
        kg.add_entity(supplier_id, "supplier", supplier_name)
    kg.add_relationship(supplier_id, customer_company_id, "supplies_to", score=concentration)


def add_customer_relationship(kg: KnowledgeGraphV2, customer_id: str, customer_name: str, supplier_company_id: str, concentration: float = 0.0) -> None:
    if kg.get_entity(customer_id) is None:
        kg.add_entity(customer_id, "customer", customer_name)
    kg.add_relationship(customer_id, supplier_company_id, "customer_of", score=concentration)


def add_country_exposure(kg: KnowledgeGraphV2, company_id: str, country_id: str, country_name: str) -> None:
    if kg.get_entity(country_id) is None:
        kg.add_entity(country_id, "country", country_name)
    kg.add_relationship(company_id, country_id, "located_in", score=1.0)


def add_commodity_exposure(kg: KnowledgeGraphV2, company_id: str, commodity_id: str, commodity_name: str, exposure: float = 0.5) -> None:
    if kg.get_entity(commodity_id) is None:
        kg.add_entity(commodity_id, "commodity", commodity_name)
    kg.add_relationship(company_id, commodity_id, "exposed_to_commodity", score=exposure)


def add_technology(kg: KnowledgeGraphV2, company_id: str, tech_id: str, tech_name: str) -> None:
    if kg.get_entity(tech_id) is None:
        kg.add_entity(tech_id, "technology", tech_name)
    kg.add_relationship(company_id, tech_id, "uses_technology", score=1.0)


def add_patent(kg: KnowledgeGraphV2, patent_id: str, title: str, company_id: str) -> None:
    kg.add_entity(patent_id, "patent", title, metadata={"assignee": company_id})
    kg.add_relationship(company_id, patent_id, "owns_patent", score=1.0)


# ---------------------------------------------------------------------------
# Graph metrics
# ---------------------------------------------------------------------------

def _build_adjacency(kg: KnowledgeGraphV2) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = defaultdict(set)
    for e in kg.list_entities(limit=100000):
        adj[e.id]  # ensure node present even if isolated
    for r in kg._relations:  # internal access — read-only traversal, no mutation
        adj[r.source_id].add(r.target_id)
        adj[r.target_id].add(r.source_id)
    return adj


def degree_centrality(kg: KnowledgeGraphV2) -> Dict[str, float]:
    adj = _build_adjacency(kg)
    n = max(len(adj) - 1, 1)
    return {node: round(len(neighbors) / n, 4) for node, neighbors in adj.items()}


def connected_components(kg: KnowledgeGraphV2) -> List[List[str]]:
    adj = _build_adjacency(kg)
    visited: Set[str] = set()
    components: List[List[str]] = []
    for node in adj:
        if node in visited:
            continue
        component: List[str] = []
        queue = deque([node])
        visited.add(node)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adj[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=len, reverse=True)


def label_propagation_communities(kg: KnowledgeGraphV2, max_iterations: int = 20) -> Dict[str, int]:
    """Deterministic label propagation: each node adopts the most common
    label among its neighbors (ties broken by lowest label id for determinism).
    """
    adj = _build_adjacency(kg)
    nodes = sorted(adj.keys())
    labels = {node: i for i, node in enumerate(nodes)}

    for _ in range(max_iterations):
        changed = False
        for node in nodes:
            neighbors = adj[node]
            if not neighbors:
                continue
            counts: Dict[int, int] = defaultdict(int)
            for neighbor in neighbors:
                counts[labels[neighbor]] += 1
            best_label = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            if best_label != labels[node]:
                labels[node] = best_label
                changed = True
        if not changed:
            break

    # Renumber communities 0..k-1 deterministically
    unique_labels = sorted(set(labels.values()))
    remap = {old: new for new, old in enumerate(unique_labels)}
    return {node: remap[label] for node, label in labels.items()}


def dependency_chain(kg: KnowledgeGraphV2, source_id: str, target_id: str, max_depth: int = 6) -> Optional[List[str]]:
    """Shortest path (BFS) between two entities, treating all edges as undirected."""
    adj = _build_adjacency(kg)
    if source_id not in adj or target_id not in adj:
        return None
    if source_id == target_id:
        return [source_id]

    visited = {source_id}
    queue: deque = deque([[source_id]])
    while queue:
        path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue
        last = path[-1]
        for neighbor in sorted(adj[last]):
            if neighbor in visited:
                continue
            new_path = path + [neighbor]
            if neighbor == target_id:
                return new_path
            visited.add(neighbor)
            queue.append(new_path)
    return None


def graph_metrics_summary(kg: KnowledgeGraphV2) -> Dict[str, object]:
    components = connected_components(kg)
    communities = label_propagation_communities(kg)
    centrality = degree_centrality(kg)
    top_central = sorted(centrality.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "node_count": len(centrality),
        "component_count": len(components),
        "largest_component_size": len(components[0]) if components else 0,
        "community_count": len(set(communities.values())) if communities else 0,
        "top_central_nodes": [{"id": node, "centrality": score} for node, score in top_central],
    }
