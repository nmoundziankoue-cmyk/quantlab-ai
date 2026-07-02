"""Correlation analytics service — M4.

Computes correlation matrices, rolling correlations, hierarchical clustering,
and minimum spanning tree (MST) for portfolio assets.

All computation is pure NumPy/SciPy/networkx — no database calls.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import networkx as nx
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

def compute_correlation_matrix(
    returns_df: pd.DataFrame,
    method: str = "pearson",
) -> Dict[str, Any]:
    """Compute pairwise return correlation matrix.

    Parameters
    ----------
    returns_df : DataFrame with tickers as columns, daily returns as values.
    method : ``"pearson"``, ``"spearman"``, or ``"kendall"``.

    Returns
    -------
    Dict with ``tickers``, ``matrix`` (list of lists), and ``summary``.
    """
    rets = returns_df.dropna(how="all").ffill()
    tickers = rets.columns.tolist()

    if method == "spearman":
        corr = rets.rank().corr()
    elif method == "kendall":
        corr = rets.corr(method="kendall")
    else:
        corr = rets.corr()

    corr = corr.clip(-1.0, 1.0)
    n = len(tickers)

    # Off-diagonal upper triangle for summary stats
    upper_vals = []
    for i in range(n):
        for j in range(i + 1, n):
            upper_vals.append(float(corr.iloc[i, j]))

    return {
        "tickers": tickers,
        "method": method,
        "matrix": [[round(float(v), 4) for v in row] for row in corr.values],
        "summary": {
            "mean_correlation": round(float(np.mean(upper_vals)), 4) if upper_vals else None,
            "median_correlation": round(float(np.median(upper_vals)), 4) if upper_vals else None,
            "max_correlation": round(float(max(upper_vals)), 4) if upper_vals else None,
            "min_correlation": round(float(min(upper_vals)), 4) if upper_vals else None,
            "pct_above_0_7": round(sum(v > 0.7 for v in upper_vals) / len(upper_vals) * 100, 1) if upper_vals else None,
            "pct_below_0": round(sum(v < 0.0 for v in upper_vals) / len(upper_vals) * 100, 1) if upper_vals else None,
        },
    }


# ---------------------------------------------------------------------------
# Rolling correlation
# ---------------------------------------------------------------------------

def compute_rolling_correlation(
    returns_df: pd.DataFrame,
    ticker_a: str,
    ticker_b: str,
    window: int = 60,
) -> Dict[str, Any]:
    """Rolling correlation between two assets.

    Returns
    -------
    Dict with ``dates`` and ``values`` lists.
    """
    if ticker_a not in returns_df.columns or ticker_b not in returns_df.columns:
        raise ValueError(f"One or both tickers not found in returns data.")

    rets = returns_df[[ticker_a, ticker_b]].dropna()
    rolling = rets[ticker_a].rolling(window).corr(rets[ticker_b]).dropna()

    return {
        "ticker_a": ticker_a,
        "ticker_b": ticker_b,
        "window": window,
        "dates": [str(d.date()) if hasattr(d, "date") else str(d) for d in rolling.index],
        "values": [round(float(v), 4) for v in rolling.values],
    }


# ---------------------------------------------------------------------------
# Hierarchical clustering
# ---------------------------------------------------------------------------

def compute_hierarchical_clusters(
    returns_df: pd.DataFrame,
    n_clusters: int = 3,
    linkage_method: str = "ward",
) -> Dict[str, Any]:
    """Cluster assets by correlation distance using hierarchical clustering.

    Returns
    -------
    Dict with ``tickers``, ``cluster_labels``, ``linkage_matrix``,
    ``cluster_summary``.
    """
    rets = returns_df.dropna(how="all").ffill()
    tickers = rets.columns.tolist()
    n = len(tickers)

    if n < 2:
        return {"tickers": tickers, "cluster_labels": [1] * n, "clusters": {}}

    corr = rets.corr().clip(-1.0, 1.0)
    dist = np.sqrt((1.0 - corr) / 2.0)
    condensed = squareform(dist.values, checks=False)

    link = linkage(condensed, method=linkage_method)
    labels = fcluster(link, n_clusters, criterion="maxclust").tolist()

    # Group tickers by cluster
    cluster_groups: Dict[int, List[str]] = {}
    for ticker, label in zip(tickers, labels):
        cluster_groups.setdefault(label, []).append(ticker)

    # Average within-cluster correlation
    cluster_summary = {}
    for label, members in cluster_groups.items():
        if len(members) > 1:
            sub_corr = corr.loc[members, members]
            n_m = len(members)
            upper = [float(sub_corr.iloc[i, j]) for i in range(n_m) for j in range(i + 1, n_m)]
            avg_corr = float(np.mean(upper)) if upper else 1.0
        else:
            avg_corr = 1.0
        cluster_summary[str(label)] = {
            "members": members,
            "size": len(members),
            "avg_within_correlation": round(avg_corr, 4),
        }

    return {
        "tickers": tickers,
        "cluster_labels": labels,
        "n_clusters": n_clusters,
        "linkage_method": linkage_method,
        "cluster_summary": cluster_summary,
        "linkage_matrix": link.tolist(),
    }


# ---------------------------------------------------------------------------
# Minimum Spanning Tree
# ---------------------------------------------------------------------------

def compute_mst(
    returns_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Compute the Minimum Spanning Tree of the asset correlation network.

    Uses Kruskal's algorithm on the correlation distance matrix.

    Returns
    -------
    Dict with ``nodes`` and ``edges`` suitable for force-directed graph rendering.
    """
    rets = returns_df.dropna(how="all").ffill()
    tickers = rets.columns.tolist()
    n = len(tickers)

    if n < 2:
        return {"nodes": [{"id": t, "degree": 0} for t in tickers], "edges": [], "n_nodes": n, "n_edges": 0}

    corr = rets.corr().clip(-1.0, 1.0)
    dist = np.sqrt((1.0 - corr) / 2.0)

    G = nx.Graph()
    for i, t in enumerate(tickers):
        G.add_node(t)

    for i in range(n):
        for j in range(i + 1, n):
            G.add_edge(tickers[i], tickers[j], weight=float(dist.iloc[i, j]))

    mst = nx.minimum_spanning_tree(G, weight="weight")

    # Compute node centrality (degree in MST)
    degree = dict(mst.degree())

    nodes = [
        {
            "id": t,
            "degree": degree.get(t, 0),
        }
        for t in tickers
    ]

    edges = []
    for u, v, data in mst.edges(data=True):
        corr_val = float(corr.loc[u, v])
        edges.append({
            "source": u,
            "target": v,
            "distance": round(float(data["weight"]), 4),
            "correlation": round(corr_val, 4),
        })

    return {
        "nodes": nodes,
        "edges": sorted(edges, key=lambda e: e["distance"]),
        "n_nodes": len(nodes),
        "n_edges": len(edges),
    }


# ---------------------------------------------------------------------------
# Combined analytics entry point
# ---------------------------------------------------------------------------

def compute_all_correlation_analytics(
    returns_df: pd.DataFrame,
    n_clusters: int = 3,
) -> Dict[str, Any]:
    """Run the full correlation analytics suite."""
    return {
        "correlation_matrix": compute_correlation_matrix(returns_df),
        "clustering": compute_hierarchical_clusters(returns_df, n_clusters=n_clusters),
        "mst": compute_mst(returns_df),
    }
