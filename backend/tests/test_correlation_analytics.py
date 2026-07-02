"""Tests for M4 correlation analytics service.

All tests are pure numerical — no network calls.
"""
import numpy as np
import pandas as pd
import pytest

from services.correlation_analytics import (
    compute_all_correlation_analytics,
    compute_correlation_matrix,
    compute_hierarchical_clusters,
    compute_mst,
    compute_rolling_correlation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def returns_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = rng.normal(0.0003, 0.012, (300, 4))
    return pd.DataFrame(data, columns=["AAPL", "MSFT", "GOOG", "AMZN"])


@pytest.fixture
def small_df() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    data = rng.normal(0, 0.01, (100, 2))
    return pd.DataFrame(data, columns=["A", "B"])


@pytest.fixture
def correlated_df() -> pd.DataFrame:
    """Two perfectly correlated assets and two independent ones."""
    rng = np.random.default_rng(0)
    base = rng.normal(0, 0.01, 200)
    return pd.DataFrame({
        "A": base,
        "B": base + rng.normal(0, 0.0001, 200),  # near-perfect correlation with A
        "C": rng.normal(0, 0.01, 200),
        "D": rng.normal(0, 0.01, 200),
    })


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

class TestCorrelationMatrix:
    def test_square_matrix(self, returns_df):
        result = compute_correlation_matrix(returns_df)
        n = len(returns_df.columns)
        assert len(result["matrix"]) == n
        assert all(len(row) == n for row in result["matrix"])

    def test_diagonal_is_one(self, returns_df):
        result = compute_correlation_matrix(returns_df)
        for i, row in enumerate(result["matrix"]):
            assert abs(row[i] - 1.0) < 1e-6

    def test_symmetric(self, returns_df):
        result = compute_correlation_matrix(returns_df)
        m = result["matrix"]
        n = len(m)
        for i in range(n):
            for j in range(i + 1, n):
                assert abs(m[i][j] - m[j][i]) < 1e-10

    def test_values_between_minus1_and_1(self, returns_df):
        result = compute_correlation_matrix(returns_df)
        for row in result["matrix"]:
            for val in row:
                assert -1.0 <= val <= 1.0 + 1e-10

    def test_tickers_match_input(self, returns_df):
        result = compute_correlation_matrix(returns_df)
        assert result["tickers"] == returns_df.columns.tolist()

    def test_summary_contains_mean(self, returns_df):
        result = compute_correlation_matrix(returns_df)
        assert "mean_correlation" in result["summary"]

    def test_high_correlation_detected(self, correlated_df):
        result = compute_correlation_matrix(correlated_df)
        # A and B are nearly perfectly correlated
        a_idx = result["tickers"].index("A")
        b_idx = result["tickers"].index("B")
        assert result["matrix"][a_idx][b_idx] > 0.99

    def test_spearman_method(self, returns_df):
        result = compute_correlation_matrix(returns_df, method="spearman")
        assert result["method"] == "spearman"


# ---------------------------------------------------------------------------
# Rolling correlation
# ---------------------------------------------------------------------------

class TestRollingCorrelation:
    def test_returns_dates_and_values(self, returns_df):
        result = compute_rolling_correlation(returns_df, "AAPL", "MSFT", window=30)
        assert "dates" in result
        assert "values" in result
        assert len(result["dates"]) == len(result["values"])

    def test_values_in_range(self, returns_df):
        result = compute_rolling_correlation(returns_df, "AAPL", "MSFT", window=30)
        for v in result["values"]:
            assert -1.0 <= v <= 1.0 + 1e-10

    def test_invalid_ticker_raises(self, returns_df):
        with pytest.raises(ValueError):
            compute_rolling_correlation(returns_df, "AAPL", "NONEXISTENT", window=30)

    def test_correlated_series_high_rolling(self, correlated_df):
        result = compute_rolling_correlation(correlated_df, "A", "B", window=20)
        # All rolling windows should show near-perfect correlation
        for v in result["values"]:
            assert v > 0.95


# ---------------------------------------------------------------------------
# Hierarchical clustering
# ---------------------------------------------------------------------------

class TestHierarchicalClusters:
    def test_returns_cluster_labels(self, returns_df):
        result = compute_hierarchical_clusters(returns_df, n_clusters=2)
        assert len(result["cluster_labels"]) == len(returns_df.columns)

    def test_n_clusters_respected(self, returns_df):
        for n in [2, 3, 4]:
            result = compute_hierarchical_clusters(returns_df, n_clusters=n)
            unique = set(result["cluster_labels"])
            assert len(unique) == n

    def test_cluster_summary_structure(self, returns_df):
        result = compute_hierarchical_clusters(returns_df, n_clusters=2)
        for key, summary in result["cluster_summary"].items():
            assert "members" in summary
            assert "size" in summary
            assert "avg_within_correlation" in summary

    def test_closely_correlated_in_same_cluster(self, correlated_df):
        result = compute_hierarchical_clusters(correlated_df, n_clusters=2)
        labels = dict(zip(result["tickers"], result["cluster_labels"]))
        # A and B should end up in the same cluster
        assert labels["A"] == labels["B"]


# ---------------------------------------------------------------------------
# Minimum spanning tree
# ---------------------------------------------------------------------------

class TestMST:
    def test_correct_edge_count(self, returns_df):
        result = compute_mst(returns_df)
        n = len(returns_df.columns)
        # MST of n nodes has exactly n-1 edges
        assert result["n_edges"] == n - 1

    def test_correct_node_count(self, returns_df):
        result = compute_mst(returns_df)
        assert result["n_nodes"] == len(returns_df.columns)

    def test_edge_structure(self, returns_df):
        result = compute_mst(returns_df)
        for edge in result["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "distance" in edge
            assert "correlation" in edge

    def test_distance_positive(self, returns_df):
        result = compute_mst(returns_df)
        for edge in result["edges"]:
            assert edge["distance"] >= 0.0

    def test_correlation_in_range(self, returns_df):
        result = compute_mst(returns_df)
        for edge in result["edges"]:
            assert -1.0 <= edge["correlation"] <= 1.0 + 1e-10

    def test_single_node(self):
        df = pd.DataFrame({"A": np.random.normal(0, 0.01, 100)})
        result = compute_mst(df)
        assert result["n_nodes"] == 1
        assert result["n_edges"] == 0


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------

class TestComputeAll:
    def test_returns_all_sections(self, small_df):
        result = compute_all_correlation_analytics(small_df)
        assert "correlation_matrix" in result
        assert "clustering" in result
        assert "mst" in result

    def test_mst_consistent_with_standalone(self, returns_df):
        combined = compute_all_correlation_analytics(returns_df)
        standalone = compute_mst(returns_df)
        assert combined["mst"]["n_edges"] == standalone["n_edges"]
