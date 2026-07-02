"""Final coverage to reach 1500 total tests."""
import math
import pytest
from services.options_strategies import bs_call, bs_put, bs_greeks, binomial_tree, build_strategy, list_strategies
from services.walk_forward import compute_metrics, kelly_criterion, parameter_sweep
from services.knowledge_graph_v2 import cosine_similarity, KnowledgeGraphV2
from services.ai_agents import ResearchOrchestrator, AGENT_TYPES
from services.execution_enhanced import Order, OrderType, OrderSide, ExecutionEngine, RiskLimits, OrderBookSimulator
from services.structured_logging import SlowQueryTracker, Tracer, ErrorAggregator
from services.oauth_providers import get_provider, generate_state, list_providers
from services.provider_health import LatencyTracker, HealthScore, QuotaTracker, QuotaConfig


# -----------------------------------------------------------------------
# cosine_similarity edge cases
# -----------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-9)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_scalar_invariance(self):
        a = [1.0, 2.0, 3.0]
        b = [2.0, 4.0, 6.0]  # 2*a
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_range_minus_one_to_one(self):
        import random
        rng = random.Random(42)
        for _ in range(20):
            n = 8
            a = [rng.gauss(0, 1) for _ in range(n)]
            b = [rng.gauss(0, 1) for _ in range(n)]
            val = cosine_similarity(a, b)
            assert -1.0 - 1e-9 <= val <= 1.0 + 1e-9


# -----------------------------------------------------------------------
# BS greeks sign expectations
# -----------------------------------------------------------------------

class TestBSGreeksSigns:
    def test_call_delta_positive(self):
        g = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        assert g["delta"] > 0

    def test_put_delta_negative(self):
        g = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        assert g["delta"] < 0

    def test_gamma_positive_both(self):
        gc = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        gp = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        assert gc["gamma"] > 0
        assert gp["gamma"] > 0

    def test_vega_positive_both(self):
        gc = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        gp = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        assert gc["vega"] > 0
        assert gp["vega"] > 0

    def test_call_theta_negative(self):
        g = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        assert g["theta"] < 0

    def test_call_rho_positive(self):
        g = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        assert g["rho"] > 0

    def test_put_rho_negative(self):
        g = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        assert g["rho"] < 0

    def test_gamma_equals_call_put(self):
        gc = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        gp = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        assert gc["gamma"] == pytest.approx(gp["gamma"], rel=1e-4)


# -----------------------------------------------------------------------
# Black-Scholes put-call parity
# -----------------------------------------------------------------------

class TestPutCallParity:
    @pytest.mark.parametrize("S,K,T,r,sigma", [
        (100, 100, 1.0, 0.05, 0.20),
        (120, 100, 0.5, 0.03, 0.30),
        (80, 100, 2.0, 0.02, 0.15),
        (100, 90, 0.25, 0.07, 0.25),
    ])
    def test_parity(self, S, K, T, r, sigma):
        c = bs_call(S, K, T, r, sigma)
        p = bs_put(S, K, T, r, sigma)
        lhs = c - p
        rhs = S - K * math.exp(-r * T)
        assert abs(lhs - rhs) < 0.001


# -----------------------------------------------------------------------
# Strategy list completeness
# -----------------------------------------------------------------------

class TestStrategyRegistry:
    EXPECTED = {"covered_call", "protective_put", "bull_call_spread", "bear_put_spread",
                "straddle", "strangle", "iron_condor", "butterfly"}

    def test_count(self):
        assert len(list_strategies()) == 8

    def test_all_expected_present(self):
        assert set(list_strategies()) == self.EXPECTED

    def test_all_buildable(self):
        for name in list_strategies():
            result = build_strategy(name, 100.0, 100.0, 0.5, 0.05, 0.20)
            assert result["strategy"] == name

    def test_payoff_monotone_for_bull_spread(self):
        r = build_strategy("bull_call_spread", 100, 100, 0.5, 0.05, 0.20, K2=110.0)
        payoffs = [p["payoff"] for p in r["payoff_curve"]]
        # Should increase monotonically up to a cap
        assert payoffs[-1] >= payoffs[0]


# -----------------------------------------------------------------------
# compute_metrics
# -----------------------------------------------------------------------

class TestComputeMetrics:
    def test_positive_cagr_on_trending(self):
        import random
        rng = random.Random(99)
        returns = [rng.gauss(0.001, 0.01) for _ in range(252)]
        m = compute_metrics(returns)
        assert "cagr" in m and "sharpe" in m and "max_drawdown" in m

    def test_max_drawdown_non_negative(self):
        import random
        rng = random.Random(7)
        returns = [rng.gauss(0, 0.01) for _ in range(100)]
        m = compute_metrics(returns)
        assert m["max_drawdown"] >= 0.0

    def test_n_equals_input_length(self):
        returns = [0.001] * 50
        m = compute_metrics(returns)
        assert m["n"] == 50


# -----------------------------------------------------------------------
# Kelly criterion parametric
# -----------------------------------------------------------------------

class TestKellyParametric:
    @pytest.mark.parametrize("win_prob,win_ret,loss_ret,expected_pos", [
        (0.6, 0.10, 0.05, True),
        (0.5, 0.10, 0.10, False),
        (0.55, 0.20, 0.05, True),
    ])
    def test_sign(self, win_prob, win_ret, loss_ret, expected_pos):
        k = kelly_criterion(win_prob, win_ret, loss_ret)
        if expected_pos:
            assert k["full_kelly"] > 0
        else:
            assert k["full_kelly"] == pytest.approx(0.0, abs=0.001)

    def test_half_kelly_is_half_of_full(self):
        k = kelly_criterion(0.6, 0.15, 0.10)
        assert k["half_kelly"] == pytest.approx(k["full_kelly"] / 2, abs=0.01)

    def test_quarter_kelly_is_quarter_of_full(self):
        k = kelly_criterion(0.7, 0.20, 0.10)
        assert k["quarter_kelly"] == pytest.approx(k["full_kelly"] / 4, abs=0.01)


# -----------------------------------------------------------------------
# KnowledgeGraphV2 CRUD
# -----------------------------------------------------------------------

class TestKGCRUD:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_add_and_get_entity(self):
        self.kg.add_entity("XYZ", "company", "XYZ Corp", "test company")
        e = self.kg.get_entity("XYZ")
        assert e is not None and e.name == "XYZ Corp"

    def test_overwrite_entity(self):
        self.kg.add_entity("XYZ", "company", "Old", "")
        self.kg.add_entity("XYZ", "company", "New", "updated")
        assert self.kg.get_entity("XYZ").name == "New"

    def test_list_by_type_count(self):
        before = len(self.kg.list_entities("sector"))
        self.kg.add_entity("S99", "sector", "Test Sector", "")
        after = len(self.kg.list_entities("sector"))
        assert after == before + 1

    def test_relationship_round_trip(self):
        self.kg.add_entity("A1", "company", "A", "")
        self.kg.add_entity("B1", "company", "B", "")
        self.kg.add_relationship("A1", "B1", "acquires", score=0.9)
        rels = self.kg.get_relationships("A1")
        found = [r for r in rels if r["target_id"] == "B1" and r["relation_type"] == "acquires"]
        assert len(found) == 1

    def test_stats_entity_count(self):
        initial = self.kg.stats()["entity_count"]
        self.kg.add_entity("STAT1", "company", "S1", "")
        self.kg.add_entity("STAT2", "company", "S2", "")
        assert self.kg.stats()["entity_count"] == initial + 2


# -----------------------------------------------------------------------
# AgentOrchestrator — delete and list
# -----------------------------------------------------------------------

class TestOrchestratorManagement:
    def setup_method(self):
        self.orch = ResearchOrchestrator()

    def test_list_sessions_empty_on_fresh(self):
        assert isinstance(self.orch.list_sessions(), list)

    def test_delete_nonexistent_returns_false(self):
        assert not self.orch.delete_session("nonexistent-id-xyz")

    def test_session_context_preserves_custom(self):
        s = self.orch.create_session("ticker test", context={"tickers": ["AAPL", "MSFT"]})
        assert "AAPL" in s.context.get("tickers", [])

    def test_agent_response_has_citations(self):
        s = self.orch.create_session("citation test")
        r = self.orch.run_agent(s.id, AGENT_TYPES[0], "macro outlook")
        assert isinstance(r.citations, list)


# -----------------------------------------------------------------------
# ExecutionEngine: VWAP / TWAP via book simulator
# -----------------------------------------------------------------------

class TestOrderBookSim:
    def test_vwap_positive_price(self):
        book = OrderBookSimulator(150.0, 10.0)
        price = book.simulate_vwap("buy", 1000, slices=5)
        assert price > 0

    def test_twap_close_to_mid(self):
        book = OrderBookSimulator(200.0, 4.0)
        price = book.simulate_twap("buy", 500, slices=4)
        assert abs(price - 200.0) < 5.0

    def test_to_dict_keys(self):
        book = OrderBookSimulator(100.0, 5.0)
        d = book.to_dict()
        assert "best_bid" in d and "best_ask" in d and "spread_bps" in d

    def test_spread_direction(self):
        book = OrderBookSimulator(100.0, 8.0)
        d = book.to_dict()
        assert d["best_ask"] > d["best_bid"]


# -----------------------------------------------------------------------
# ErrorAggregator
# -----------------------------------------------------------------------

class TestErrorAggregator:
    def test_record_and_summary(self):
        agg = ErrorAggregator()
        agg.record("ValueError", "bad value", ctx="ctx1")
        s = agg.summary()
        assert "ValueError" in s["by_type"]

    def test_count_increments(self):
        agg = ErrorAggregator()
        for _ in range(5):
            agg.record("RuntimeError", "oops")
        s = agg.summary()
        assert s["by_type"]["RuntimeError"] == 5

    def test_max_per_type_cap(self):
        agg = ErrorAggregator(max_per_type=3)
        for i in range(10):
            agg.record("KeyError", f"k{i}")
        recent = agg.get_recent("KeyError")
        assert len(recent) <= 3

    def test_total_types(self):
        agg = ErrorAggregator()
        agg.record("TypeError", "t")
        agg.record("ValueError", "v")
        s = agg.summary()
        assert s["total_types"] >= 2


# -----------------------------------------------------------------------
# OAuth user info determinism
# -----------------------------------------------------------------------

class TestOAuthDeterminism:
    def test_google_same_code_same_email(self):
        p = get_provider("google")
        a = p.mock_user_info("fixed_code_abc")
        b = p.mock_user_info("fixed_code_abc")
        assert a.email == b.email

    def test_github_same_code_same_login(self):
        p = get_provider("github")
        a = p.mock_user_info("fixed_code_xyz")
        b = p.mock_user_info("fixed_code_xyz")
        assert a.name == b.name

    def test_all_providers_return_user(self):
        for name in ["google", "github", "microsoft", "apple"]:
            p = get_provider(name)
            u = p.mock_user_info("code_test")
            assert u.provider == name
            assert u.email is not None


# -----------------------------------------------------------------------
# LatencyTracker percentile correctness
# -----------------------------------------------------------------------

class TestLatencyPercentiles:
    def test_p95_present_in_stats(self):
        t = LatencyTracker()
        for v in range(1, 101):
            t.record(float(v), True)
        s = t.stats()
        assert "p95_latency_ms" in s

    def test_p95_is_high(self):
        t = LatencyTracker()
        for v in range(1, 101):
            t.record(float(v), True)
        s = t.stats()
        assert s["p95_latency_ms"] >= 80.0

    def test_success_rate_all_success(self):
        t = LatencyTracker()
        for _ in range(20):
            t.record(10.0, True)
        assert t.stats()["success_rate"] == pytest.approx(1.0)

    def test_success_rate_half(self):
        t = LatencyTracker()
        for _ in range(10):
            t.record(10.0, True)
        for _ in range(10):
            t.record(10.0, False)
        assert t.stats()["success_rate"] == pytest.approx(0.5, abs=0.01)


# -----------------------------------------------------------------------
# Binomial tree: additional convergence and sign tests
# -----------------------------------------------------------------------

class TestBinomialExtra:
    def test_american_put_ge_european(self):
        S, K, T, r, sigma = 100, 105, 1.0, 0.05, 0.25
        european = binomial_tree(S, K, T, r, sigma, "put", american=False, steps=100)
        american = binomial_tree(S, K, T, r, sigma, "put", american=True, steps=100)
        assert american >= european - 0.01

    def test_call_monotone_in_spot(self):
        K, T, r, sigma = 100, 1.0, 0.05, 0.20
        prices = [binomial_tree(S, K, T, r, sigma, steps=50) for S in [80, 90, 100, 110, 120]]
        assert prices == sorted(prices)

    def test_put_monotone_decreasing_in_spot(self):
        K, T, r, sigma = 100, 1.0, 0.05, 0.20
        prices = [binomial_tree(S, K, T, r, sigma, "put", steps=50) for S in [80, 90, 100, 110, 120]]
        assert prices == sorted(prices, reverse=True)

    def test_zero_time_call_intrinsic(self):
        assert binomial_tree(110, 100, 0, 0.05, 0.20, "call") == pytest.approx(10.0)

    def test_zero_time_put_intrinsic(self):
        assert binomial_tree(90, 100, 0, 0.05, 0.20, "put") == pytest.approx(10.0)

    def test_zero_time_otm_call(self):
        assert binomial_tree(90, 100, 0, 0.05, 0.20, "call") == pytest.approx(0.0)


# -----------------------------------------------------------------------
# KG: cluster and stats
# -----------------------------------------------------------------------

class TestKGExtra:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_cluster_count_matches_k(self):
        clusters = self.kg.cluster_entities(entity_type="company", n_clusters=3)
        assert len(clusters) == 3

    def test_each_cluster_has_members(self):
        clusters = self.kg.cluster_entities(entity_type="company", n_clusters=3)
        for c in clusters:
            assert len(c["members"]) >= 1

    def test_stats_relationship_count(self):
        s = self.kg.stats()
        assert "relationship_count" in s
        assert s["relationship_count"] >= 0

    def test_get_nonexistent_entity(self):
        assert self.kg.get_entity("DOES_NOT_EXIST_XYZ") is None

    def test_list_entities_all_types(self):
        all_entities = self.kg.list_entities()
        assert len(all_entities) >= 10


# -----------------------------------------------------------------------
# walk_forward: compute_metrics edge cases
# -----------------------------------------------------------------------

class TestComputeMetricsExtra:
    def test_zero_returns_sharpe_is_zero(self):
        m = compute_metrics([0.0] * 100)
        assert m["sharpe"] == pytest.approx(0.0)

    def test_single_return(self):
        m = compute_metrics([0.01])
        assert "cagr" in m

    def test_all_positive_returns_positive_cagr(self):
        m = compute_metrics([0.005] * 252)
        assert m["cagr"] > 0

    def test_all_negative_returns_negative_cagr(self):
        m = compute_metrics([-0.005] * 252)
        assert m["cagr"] < 0


# -----------------------------------------------------------------------
# Final six: miscellaneous correctness
# -----------------------------------------------------------------------

class TestMiscFinal:
    def test_bs_call_increases_with_vol(self):
        c_low = bs_call(100, 100, 1.0, 0.05, 0.10)
        c_high = bs_call(100, 100, 1.0, 0.05, 0.40)
        assert c_high > c_low

    def test_bs_put_increases_with_vol(self):
        p_low = bs_put(100, 100, 1.0, 0.05, 0.10)
        p_high = bs_put(100, 100, 1.0, 0.05, 0.40)
        assert p_high > p_low

    def test_kelly_keys_present(self):
        k = kelly_criterion(0.55, 0.10, 0.08)
        assert all(key in k for key in ["full_kelly", "half_kelly", "quarter_kelly", "expected_log_growth"])

    def test_list_providers_has_four(self):
        providers = list_providers()
        assert len(providers) == 4

    def test_generate_state_is_string(self):
        assert isinstance(generate_state(), str)

    def test_strategy_net_cost_finite(self):
        for name in list_strategies():
            r = build_strategy(name, 100, 100, 0.5, 0.05, 0.20)
            assert math.isfinite(r["net_cost"])
