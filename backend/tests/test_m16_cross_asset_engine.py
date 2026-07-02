"""M16 tests — Cross-Asset Engine."""
import math
import pytest
from services.cross_asset_engine import (
    CrossAssetEngine, CorrelationMethod, CorrelationMatrix,
    RollingCorrelation, DynamicBeta, RelativeStrength,
    LeadLagResult, SpilloverResult, RiskTransmissionMatrix,
    get_cross_asset_engine,
)

R1 = [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01,
      0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01]
R2 = [0.02, -0.03, 0.04, 0.01, -0.02, 0.03, 0.02, -0.02, 0.03, 0.02,
      0.02, -0.02, 0.03, 0.02, -0.02, 0.03, 0.02, -0.02, 0.03, 0.02]
R3 = [-0.01, 0.01, -0.02, 0.00, 0.01, -0.01, 0.00, 0.01, -0.01, 0.00,
       0.00,  0.01, -0.01, 0.00, 0.01, -0.01, 0.00,  0.01, -0.01, 0.00]
RETURNS_MAP = {"A": R1, "B": R2, "C": R3}

ENG = CrossAssetEngine()


class TestCorrelationMatrix:
    def test_returns_correlation_matrix(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        assert isinstance(cm, CorrelationMatrix)

    def test_tickers_sorted(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        assert cm.tickers == sorted(RETURNS_MAP.keys())

    def test_diagonal_ones(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        n = len(cm.tickers)
        for i in range(n):
            assert cm.matrix[i][i] == 1.0

    def test_symmetric(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        n = len(cm.tickers)
        for i in range(n):
            for j in range(n):
                assert abs(cm.matrix[i][j] - cm.matrix[j][i]) < 1e-9

    def test_values_in_range(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        for row in cm.matrix:
            for v in row:
                assert -1.0 <= v <= 1.0

    def test_get_method(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        corr = cm.get("A", "B")
        assert corr is not None

    def test_get_unknown_ticker_returns_none(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        assert cm.get("X", "A") is None

    def test_with_window(self):
        cm = ENG.correlation_matrix(RETURNS_MAP, window=10)
        assert cm.window == 10

    def test_rank_method(self):
        cm = ENG.correlation_matrix(RETURNS_MAP, method=CorrelationMethod.RANK)
        assert cm.method == CorrelationMethod.RANK

    def test_to_dict(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        d = cm.to_dict()
        assert "tickers" in d and "matrix" in d

    def test_highly_correlated_positive(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        ab = cm.get("A", "B")
        assert ab > 0.9

    def test_negatively_correlated(self):
        cm = ENG.correlation_matrix(RETURNS_MAP)
        ac = cm.get("A", "C")
        assert ac < 0


class TestRollingCorrelation:
    def test_returns_rolling_correlation(self):
        rc = ENG.rolling_correlation(R1, R2, "A", "B", window=10)
        assert isinstance(rc, RollingCorrelation)

    def test_correlations_list_nonempty(self):
        rc = ENG.rolling_correlation(R1, R2, "A", "B", window=10)
        assert len(rc.correlations) > 0

    def test_correlations_in_range(self):
        rc = ENG.rolling_correlation(R1, R2, "A", "B", window=10)
        for c in rc.correlations:
            assert -1.0 <= c <= 1.0

    def test_mean_correlation_positive(self):
        rc = ENG.rolling_correlation(R1, R2, "A", "B", window=10)
        assert rc.mean_correlation > 0

    def test_to_dict(self):
        rc = ENG.rolling_correlation(R1, R2, "A", "B")
        d = rc.to_dict()
        assert "correlations" in d and "mean_correlation" in d


class TestDynamicBeta:
    def test_returns_dynamic_beta(self):
        db = ENG.dynamic_beta(R1, R2, "A", "B", window=10)
        assert isinstance(db, DynamicBeta)

    def test_betas_nonempty(self):
        db = ENG.dynamic_beta(R1, R2, "A", "B", window=10)
        assert len(db.betas) > 0

    def test_current_beta_is_last(self):
        db = ENG.dynamic_beta(R1, R2, "A", "B", window=10)
        assert db.current_beta == db.betas[-1]

    def test_static_beta_float(self):
        b = ENG.static_beta(R1, R2)
        assert isinstance(b, float)

    def test_static_beta_positive(self):
        b = ENG.static_beta(R1, R2)
        assert b > 0


class TestRelativeStrength:
    def test_returns_relative_strength(self):
        rs = ENG.relative_strength(R1, R2, "A", "B")
        assert isinstance(rs, RelativeStrength)

    def test_period_correct(self):
        rs = ENG.relative_strength(R1, R2, "A", "B")
        assert rs.period == min(len(R1), len(R2))

    def test_to_dict(self):
        rs = ENG.relative_strength(R1, R2, "A", "B")
        d = rs.to_dict()
        assert "rs_ratio" in d and "information_ratio" in d

    def test_tracking_error_nonneg(self):
        rs = ENG.relative_strength(R1, R2, "A", "B")
        assert rs.tracking_error >= 0


class TestLeadLag:
    def test_returns_lead_lag_result(self):
        ll = ENG.lead_lag_analysis(R1, R2, "A", "B", max_lag=3)
        assert isinstance(ll, LeadLagResult)

    def test_lag_keys_in_range(self):
        ll = ENG.lead_lag_analysis(R1, R2, "A", "B", max_lag=3)
        lags = list(ll.correlations_by_lag.keys())
        assert min(lags) == -3 and max(lags) == 3

    def test_leader_valid(self):
        ll = ENG.lead_lag_analysis(R1, R2, "A", "B", max_lag=3)
        assert ll.leader in ("a", "b", "neither")

    def test_to_dict(self):
        ll = ENG.lead_lag_analysis(R1, R2, "A", "B")
        d = ll.to_dict()
        assert "optimal_lag" in d and "leader" in d


class TestSpillover:
    def test_spillover_score_result(self):
        res = ENG.spillover_score(R1, R2, "A", "B", lag=1)
        assert isinstance(res, SpilloverResult)

    def test_spillover_score_nonneg(self):
        res = ENG.spillover_score(R1, R2, "A", "B")
        assert 0.0 <= res.spillover_score <= 1.0

    def test_direction_valid(self):
        res = ENG.spillover_score(R1, R2, "A", "B")
        assert res.direction in ("positive", "negative", "neutral")

    def test_spillover_matrix_returns_dict(self):
        m = ENG.spillover_matrix(RETURNS_MAP)
        assert "tickers" in m and "matrix" in m

    def test_spillover_matrix_diagonal_zero(self):
        m = ENG.spillover_matrix(RETURNS_MAP)
        n = len(m["tickers"])
        for i in range(n):
            assert m["matrix"][i][i] == 0.0


class TestRiskTransmission:
    def test_returns_rtm(self):
        rtm = ENG.risk_transmission_matrix(RETURNS_MAP)
        assert isinstance(rtm, RiskTransmissionMatrix)

    def test_diagonal_zero(self):
        rtm = ENG.risk_transmission_matrix(RETURNS_MAP)
        n = len(rtm.tickers)
        for i in range(n):
            assert rtm.matrix[i][i] == 0.0

    def test_nonneg_values(self):
        rtm = ENG.risk_transmission_matrix(RETURNS_MAP)
        for row in rtm.matrix:
            for v in row:
                assert v >= 0.0

    def test_to_dict(self):
        rtm = ENG.risk_transmission_matrix(RETURNS_MAP)
        d = rtm.to_dict()
        assert "net_transmitters" in d and "net_receivers" in d


class TestSynchronization:
    def test_returns_dict(self):
        sync = ENG.market_synchronization(RETURNS_MAP)
        assert isinstance(sync, dict)

    def test_has_score(self):
        sync = ENG.market_synchronization(RETURNS_MAP)
        assert "synchronization_score" in sync

    def test_score_in_range(self):
        sync = ENG.market_synchronization(RETURNS_MAP)
        assert 0.0 <= sync["synchronization_score"] <= 1.0

    def test_single_asset_returns_zero(self):
        sync = ENG.market_synchronization({"A": R1})
        assert sync["synchronization_score"] == 0.0


class TestDependencyGraph:
    def test_returns_graph(self):
        g = ENG.dependency_graph(RETURNS_MAP)
        assert "nodes" in g and "edges" in g

    def test_node_count(self):
        g = ENG.dependency_graph(RETURNS_MAP)
        assert g["n_nodes"] == len(RETURNS_MAP)

    def test_edges_above_threshold(self):
        g = ENG.dependency_graph(RETURNS_MAP, threshold=0.5)
        for e in g["edges"]:
            assert abs(e["weight"]) >= 0.5


class TestSingleton:
    def test_singleton(self):
        a = get_cross_asset_engine()
        b = get_cross_asset_engine()
        assert a is b
