"""M15 Phase 8 — Event Clustering Engine.

Clusters events into institutional themes using keyword-based deterministic
classification. No ML models, no external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from services.event_engine import CorporateEvent, CorporateEventType
from services.macro_event_engine import MacroEvent


# ---------------------------------------------------------------------------
# Cluster themes
# ---------------------------------------------------------------------------

class EventCluster(str, Enum):
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    CLOUD = "cloud"
    CYBERSECURITY = "cybersecurity"
    SEMICONDUCTORS = "semiconductors"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    OIL = "oil"
    BANKING = "banking"
    CRYPTO = "crypto"
    EV = "ev"
    SPACE = "space"
    DEFENSE = "defense"
    SUPPLY_CHAIN = "supply_chain"
    CONSUMER = "consumer"
    ENTERPRISE_SOFTWARE = "enterprise_software"
    GENERAL = "general"


# Keyword sets for each cluster (order matters: first match wins)
_CLUSTER_KEYWORDS: Dict[EventCluster, Set[str]] = {
    EventCluster.ARTIFICIAL_INTELLIGENCE: {
        "ai", "artificial intelligence", "machine learning", "generative", "llm",
        "gpt", "neural", "deep learning", "openai", "anthropic", "nvidia",
    },
    EventCluster.CLOUD: {
        "cloud", "aws", "azure", "gcp", "saas", "paas", "iaas",
        "data center", "datacenter", "serverless", "kubernetes",
    },
    EventCluster.CYBERSECURITY: {
        "cybersecurity", "cyber", "hack", "breach", "ransomware", "vulnerability",
        "zero-day", "endpoint", "firewall", "security software",
    },
    EventCluster.SEMICONDUCTORS: {
        "semiconductor", "chip", "wafer", "fab", "foundry", "tsmc",
        "nvidia", "amd", "intel", "arm", "asml", "photolithography",
    },
    EventCluster.HEALTHCARE: {
        "fda", "drug", "pharma", "clinical trial", "biotech", "medical",
        "therapy", "vaccine", "oncology", "genomic", "biologic",
    },
    EventCluster.ENERGY: {
        "energy", "renewable", "solar", "wind", "battery", "grid",
        "power generation", "utility", "lng", "nuclear",
    },
    EventCluster.OIL: {
        "oil", "crude", "opec", "petroleum", "refinery", "natural gas",
        "pipeline", "shale", "offshore drilling",
    },
    EventCluster.BANKING: {
        "bank", "lending", "credit", "interest rate", "fed", "fomc", "yield",
        "deposits", "loan", "mortgage", "financial services",
    },
    EventCluster.CRYPTO: {
        "bitcoin", "ethereum", "crypto", "blockchain", "defi", "nft",
        "stablecoin", "token", "web3", "mining",
    },
    EventCluster.EV: {
        "electric vehicle", "ev", "tesla", "battery electric", "charging",
        "lithium", "cobalt", "range", "autonomous driving",
    },
    EventCluster.SPACE: {
        "space", "satellite", "rocket", "spacex", "nasa", "launch vehicle",
        "orbit", "constellation", "lunar",
    },
    EventCluster.DEFENSE: {
        "defense", "military", "weapon", "missile", "contractor", "pentagon",
        "nato", "armed forces", "geopolitical", "war",
    },
    EventCluster.SUPPLY_CHAIN: {
        "supply chain", "logistics", "shipping", "freight", "inventory",
        "procurement", "vendor", "sourcing", "port", "disruption",
    },
    EventCluster.CONSUMER: {
        "consumer", "retail", "e-commerce", "brand", "advertising",
        "subscription", "loyalty", "omnichannel", "d2c",
    },
    EventCluster.ENTERPRISE_SOFTWARE: {
        "enterprise software", "erp", "crm", "saas", "workflow",
        "automation", "platform", "api", "integration",
    },
}

# Sector → cluster fallback mapping
_SECTOR_CLUSTER: Dict[str, EventCluster] = {
    "technology": EventCluster.ENTERPRISE_SOFTWARE,
    "healthcare": EventCluster.HEALTHCARE,
    "energy": EventCluster.ENERGY,
    "financials": EventCluster.BANKING,
    "finance": EventCluster.BANKING,
    "consumer discretionary": EventCluster.CONSUMER,
    "consumer staples": EventCluster.CONSUMER,
    "industrials": EventCluster.SUPPLY_CHAIN,
    "materials": EventCluster.SUPPLY_CHAIN,
    "utilities": EventCluster.ENERGY,
}


# ---------------------------------------------------------------------------
# ClusterResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class ClusterResult:
    """Assignment of an event to a theme cluster."""

    event_id: str
    cluster: EventCluster
    matched_keywords: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "cluster": self.cluster.value,
            "matched_keywords": self.matched_keywords,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# EventClusteringEngine
# ---------------------------------------------------------------------------

class EventClusteringEngine:
    """Deterministic event theme clustering via keyword matching."""

    def _text_for_event(self, event: CorporateEvent) -> str:
        parts = [
            event.event_type.value,
            event.description,
            event.sector,
            event.industry,
            " ".join(event.tags),
        ]
        return " ".join(parts).lower()

    def _text_for_macro(self, event: MacroEvent) -> str:
        parts = [event.event_type.value, event.description, " ".join(str(v) for v in event.metadata.values())]
        return " ".join(parts).lower()

    def _classify_text(self, text: str, event_id: str, sector: str = "") -> ClusterResult:
        best_cluster = EventCluster.GENERAL
        best_matches: List[str] = []
        best_count = 0

        for cluster, keywords in _CLUSTER_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in text]
            if len(matches) > best_count:
                best_count = len(matches)
                best_cluster = cluster
                best_matches = matches

        # Fall back to sector-based assignment
        if best_cluster == EventCluster.GENERAL and sector:
            fallback = _SECTOR_CLUSTER.get(sector.lower())
            if fallback:
                best_cluster = fallback

        confidence = min(1.0, 0.4 + best_count * 0.15)
        if best_cluster == EventCluster.GENERAL:
            confidence = 0.3

        return ClusterResult(
            event_id=event_id,
            cluster=best_cluster,
            matched_keywords=best_matches[:5],
            confidence=round(confidence, 4),
        )

    def classify(self, event: CorporateEvent) -> ClusterResult:
        text = self._text_for_event(event)
        return self._classify_text(text, event.id, event.sector)

    def classify_macro(self, event: MacroEvent) -> ClusterResult:
        text = self._text_for_macro(event)
        return self._classify_text(text, event.id)

    def cluster_batch(self, events: List[CorporateEvent]) -> List[ClusterResult]:
        return [self.classify(ev) for ev in events]

    def cluster_distribution(self, events: List[CorporateEvent]) -> Dict[str, int]:
        """Count events per cluster."""
        dist: Dict[str, int] = {}
        for ev in events:
            result = self.classify(ev)
            k = result.cluster.value
            dist[k] = dist.get(k, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True))

    def events_by_cluster(
        self,
        events: List[CorporateEvent],
    ) -> Dict[str, List[str]]:
        """Group event IDs by cluster label."""
        groups: Dict[str, List[str]] = {}
        for ev in events:
            result = self.classify(ev)
            k = result.cluster.value
            groups.setdefault(k, []).append(ev.id)
        return groups
