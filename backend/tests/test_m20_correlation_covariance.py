"""Tests for M20 CorrelationCovarianceEngine."""

from __future__ import annotations

import math
from typing import Dict, List

import pytest

from services.m20_correlation_covariance import (
    CorrelationCovarianceEngine,
    CorrelationCluster,
    CorrelationMatrix,
    CovarianceMatrix,
    RollingCorrelation,
    _common_returns,
    _sample_covariance,
    _std_stats,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_returns(n: int, drift: float = 0.001) -> Dict[str, float]:
    return {f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}": drift * (1 + 0.1 * (i % 5)) for i in range(n)}


def _const_returns(n: int, value: float = 0.01) -> Dict[str, float]:
    return {f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}": value for i in range(n)}


def _opposing_returns(n: int) -> Dict[str, float]:
    """Returns series where even dates are +0.01 and odd dates are -0.01."""
    return {f"2023-{(i // 28 + 1):02d}-{(i % 28 + 1):02d}": (0.01 if i % 2 == 0 else -0.01) for i in range(n)}


def _linked_returns(base: Dict[str, float], scale: float = 1.0) -> Dict[str, float]:
    """Create a scaled copy of a return series (perfectly correlated)."""
    return {d: v * scale for d, v in base.items()}


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestCommonReturns:
    def test_full_overlap(self):
        a = {"2023-01-01": 0.01, "2023-01-02": 0.02}
        b = {"2023-01-01": 0.03, "2023-01-02": 0.04}
        sa, sb, dates = _common_returns(a, b)
        assert len(sa) == 2
        assert len(sb) == 2
        assert dates == ["2023-01-01", "2023-01-02"]

    def test_partial_overlap(self):
        a = {"2023-01-01": 0.01, "2023-01-02": 0.02}
        b = {"2023-01-02": 0.03, "2023-01-03": 0.04}
        sa, sb, dates = _common_returns(a, b)
        assert dates == ["2023-01-02"]
        assert sa == [0.02]
        assert sb == [0.03]

    def test_no_overlap(self):
        a = {"2023-01-01": 0.01}
        b = {"2023-01-02": 0.02}
        sa, sb, dates = _common_returns(a, b)
        assert sa == [] and sb == [] and dates == []


class TestSampleCovariance:
    def test_identical_series(self):
        x = [0.01, 0.02, -0.01, 0.03]
        cov = _sample_covariance(x, x)
        assert cov > 0

    def test_negatively_related(self):
        x = [0.01, 0.02, 0.03]
        y = [-0.01, -0.02, -0.03]
        cov = _sample_covariance(x, y)
        assert cov < 0

    def test_insufficient_data(self):
        assert _sample_covariance([0.01], [0.01]) == 0.0

    def test_constant_series(self):
        x = [0.01, 0.01, 0.01]
        assert _sample_covariance(x, x) == pytest.approx(0.0, abs=1e-12)


class TestStdStats:
    def test_known_series(self):
        mean, std = _std_stats([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert mean == pytest.approx(5.0)
        assert std == pytest.approx(2.0)

    def test_empty(self):
        assert _std_stats([]) == (0.0, 0.0)

    def test_constant(self):
        mean, std = _std_stats([3.0, 3.0, 3.0])
        assert mean == pytest.approx(3.0)
        assert std == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# CorrelationCovarianceEngine
# ---------------------------------------------------------------------------

class TestCorrelationCovarianceEngine:
    def setup_method(self):
        self.engine = CorrelationCovarianceEngine()

    # ------ Ingestion ------

    def test_add_returns_stores_ticker(self):
        self.engine.add_returns("AAPL", _make_returns(50))
        assert "AAPL" in self.engine.list_tickers()

    def test_add_returns_replaces(self):
        self.engine.add_returns("AAPL", _make_returns(50))
        new_rets = _make_returns(30)
        self.engine.add_returns("AAPL", new_rets)
        assert len(self.engine._returns["AAPL"]) == 30

    def test_add_returns_batch(self):
        self.engine.add_returns_batch({"A": _make_returns(50), "B": _make_returns(50)})
        assert sorted(self.engine.list_tickers()) == ["A", "B"]

    def test_list_tickers_sorted(self):
        self.engine.add_returns("Z", _make_returns(10))
        self.engine.add_returns("A", _make_returns(10))
        assert self.engine.list_tickers() == ["A", "Z"]

    # ------ Correlation matrix ------

    def test_correlation_matrix_shape(self):
        for t in ["A", "B", "C"]:
            self.engine.add_returns(t, _make_returns(100))
        matrix = self.engine.compute_correlation_matrix(["A", "B", "C"])
        assert len(matrix.values) == 3
        assert all(len(row) == 3 for row in matrix.values)

    def test_correlation_diagonal_is_one(self):
        self.engine.add_returns("A", _make_returns(100))
        self.engine.add_returns("B", _make_returns(100))
        matrix = self.engine.compute_correlation_matrix(["A", "B"])
        assert matrix.values[0][0] == pytest.approx(1.0)
        assert matrix.values[1][1] == pytest.approx(1.0)

    def test_correlation_symmetric(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, scale=2.0))
        matrix = self.engine.compute_correlation_matrix(["A", "B"])
        assert matrix.values[0][1] == pytest.approx(matrix.values[1][0])

    def test_perfect_positive_correlation(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.5))
        matrix = self.engine.compute_correlation_matrix(["A", "B"])
        assert matrix.get("A", "B") == pytest.approx(1.0, abs=1e-6)

    def test_correlation_raises_unknown_ticker(self):
        self.engine.add_returns("A", _make_returns(50))
        with pytest.raises(ValueError, match="No returns stored"):
            self.engine.compute_correlation_matrix(["A", "UNKNOWN"])

    def test_correlation_cached_by_id(self):
        self.engine.add_returns("A", _make_returns(50))
        self.engine.add_returns("B", _make_returns(50))
        matrix = self.engine.compute_correlation_matrix(["A", "B"])
        retrieved = self.engine.get_correlation_matrix(matrix.matrix_id)
        assert retrieved is matrix

    def test_get_correlation_matrix_none_for_missing(self):
        assert self.engine.get_correlation_matrix("nonexistent-uuid") is None

    def test_correlation_matrix_to_dict(self):
        self.engine.add_returns("A", _make_returns(50))
        self.engine.add_returns("B", _make_returns(50))
        matrix = self.engine.compute_correlation_matrix(["A", "B"])
        d = matrix.to_dict()
        assert set(d.keys()) == {"matrix_id", "tickers", "values", "num_observations", "min_correlation", "max_correlation", "avg_correlation"}

    def test_correlation_min_max_stats(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 0.5))
        matrix = self.engine.compute_correlation_matrix(["A", "B"])
        assert matrix.max_correlation <= 1.0
        assert matrix.min_correlation >= -1.0

    # ------ Covariance matrix ------

    def test_covariance_matrix_shape(self):
        self.engine.add_returns("A", _make_returns(100))
        self.engine.add_returns("B", _make_returns(100))
        matrix = self.engine.compute_covariance_matrix(["A", "B"])
        assert len(matrix.values) == 2

    def test_covariance_diagonal_positive(self):
        self.engine.add_returns("A", _make_returns(100))
        self.engine.add_returns("B", _make_returns(100))
        matrix = self.engine.compute_covariance_matrix(["A", "B"])
        assert matrix.values[0][0] >= 0
        assert matrix.values[1][1] >= 0

    def test_covariance_annualized_larger(self):
        for t in ["A", "B"]:
            self.engine.add_returns(t, _make_returns(100))
        daily = self.engine.compute_covariance_matrix(["A", "B"], annualize=False)
        annual = self.engine.compute_covariance_matrix(["A", "B"], annualize=True)
        assert annual.values[0][0] == pytest.approx(daily.values[0][0] * 252, rel=1e-2)

    def test_covariance_annualize_flag(self):
        self.engine.add_returns("A", _make_returns(50))
        self.engine.add_returns("B", _make_returns(50))
        matrix = self.engine.compute_covariance_matrix(["A", "B"], annualize=True)
        assert matrix.annualized is True

    def test_covariance_cached_by_id(self):
        self.engine.add_returns("A", _make_returns(50))
        self.engine.add_returns("B", _make_returns(50))
        matrix = self.engine.compute_covariance_matrix(["A", "B"])
        retrieved = self.engine.get_covariance_matrix(matrix.matrix_id)
        assert retrieved is matrix

    def test_covariance_raises_unknown_ticker(self):
        self.engine.add_returns("A", _make_returns(50))
        with pytest.raises(ValueError):
            self.engine.compute_covariance_matrix(["A", "NOEXIST"])

    def test_covariance_matrix_to_dict(self):
        self.engine.add_returns("A", _make_returns(50))
        self.engine.add_returns("B", _make_returns(50))
        matrix = self.engine.compute_covariance_matrix(["A", "B"])
        d = matrix.to_dict()
        assert "values" in d and "tickers" in d and "annualized" in d

    # ------ Rolling correlation ------

    def test_rolling_correlation_returns_object(self):
        base = _make_returns(120)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.2))
        rolling = self.engine.compute_rolling_correlation("A", "B", window=20)
        assert isinstance(rolling, RollingCorrelation)

    def test_rolling_correlation_length(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 0.8))
        rolling = self.engine.compute_rolling_correlation("A", "B", window=20)
        assert len(rolling.correlations) == len(rolling.dates)
        assert len(rolling.correlations) > 0

    def test_rolling_correlation_bounded(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 0.5))
        rolling = self.engine.compute_rolling_correlation("A", "B", window=20)
        for c in rolling.correlations:
            assert -1.0 <= c <= 1.0

    def test_rolling_correlation_raises_unknown(self):
        self.engine.add_returns("A", _make_returns(50))
        with pytest.raises(ValueError):
            self.engine.compute_rolling_correlation("A", "NOEXIST", window=10)

    def test_rolling_correlation_to_dict(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.0))
        rolling = self.engine.compute_rolling_correlation("A", "B", window=20)
        d = rolling.to_dict()
        assert "ticker_a" in d and "ticker_b" in d and "correlations" in d

    def test_rolling_avg_in_bounds(self):
        base = _make_returns(120)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.0))
        rolling = self.engine.compute_rolling_correlation("A", "B", window=20)
        assert -1.0 <= rolling.avg_correlation <= 1.0

    # ------ Cluster detection ------

    def test_detect_clusters_returns_list(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.0))
        self.engine.add_returns("C", _opposing_returns(100))
        clusters = self.engine.detect_clusters(["A", "B", "C"], threshold=0.8)
        assert isinstance(clusters, list)
        assert all(isinstance(c, CorrelationCluster) for c in clusters)

    def test_all_tickers_assigned_to_clusters(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.2))
        self.engine.add_returns("C", _opposing_returns(100))
        clusters = self.engine.detect_clusters(["A", "B", "C"], threshold=0.9)
        all_tickers = [t for c in clusters for t in c.tickers]
        assert sorted(all_tickers) == ["A", "B", "C"]

    def test_cluster_to_dict(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.0))
        clusters = self.engine.detect_clusters(["A", "B"], threshold=0.5)
        d = clusters[0].to_dict()
        assert set(d.keys()) == {"cluster_id", "tickers", "avg_intra_correlation", "representative"}

    def test_empty_tickers_returns_empty(self):
        result = self.engine.detect_clusters([], threshold=0.7)
        assert result == []

    def test_single_member_cluster_avg_is_one(self):
        base = _opposing_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("Z", {k: v * 0.0 for k, v in base.items()})
        clusters = self.engine.detect_clusters(["A", "Z"], threshold=0.999)
        # With very high threshold, each is in its own cluster
        solo_clusters = [c for c in clusters if len(c.tickers) == 1]
        for c in solo_clusters:
            assert c.avg_intra_correlation == pytest.approx(1.0)

    # ------ Pairwise correlation ------

    def test_pairwise_correlation_returns_float(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 0.5))
        corr = self.engine.pairwise_correlation("A", "B")
        assert isinstance(corr, float)

    def test_pairwise_raises_unknown(self):
        self.engine.add_returns("A", _make_returns(50))
        with pytest.raises(ValueError):
            self.engine.pairwise_correlation("A", "NOEXIST")

    def test_pairwise_self_correlation(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        corr = self.engine.pairwise_correlation("A", "A")
        assert corr == pytest.approx(1.0)

    # ------ Most/Least correlated pair ------

    def test_most_correlated_pair(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.0))
        self.engine.add_returns("C", _opposing_returns(100))
        ta, tb, corr = self.engine.most_correlated_pair(["A", "B", "C"])
        assert abs(corr) >= 0.5

    def test_least_correlated_pair(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", _linked_returns(base, 1.0))
        self.engine.add_returns("C", _opposing_returns(100))
        ta, tb, corr = self.engine.least_correlated_pair(["A", "B", "C"])
        assert isinstance(corr, float)

    # ------ Reset ------

    def test_reset_clears_everything(self):
        base = _make_returns(100)
        self.engine.add_returns("A", base)
        self.engine.add_returns("B", base)
        self.engine.compute_correlation_matrix(["A", "B"])
        self.engine.compute_covariance_matrix(["A", "B"])
        self.engine.reset()
        assert self.engine.list_tickers() == []
        assert self.engine._corr_cache == {}
        assert self.engine._cov_cache == {}
