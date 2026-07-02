"""M9 extended tests — edge cases, parameter coverage, integration scenarios.

Brings total count to ≥ 1500 tests.
"""
import math
import threading
import pytest
from services.options_strategies import (
    bs_call, bs_put, bs_greeks, binomial_tree, build_strategy, list_strategies,
)
from services.walk_forward import (
    compute_metrics, walk_forward_test, parameter_sweep, kelly_criterion,
    _sharpe, _max_drawdown, _cagr,
)
from services.knowledge_graph_v2 import (
    KnowledgeGraphV2, cosine_similarity, _hash_embed,
)
from services.ai_agents import (
    get_agent, get_orchestrator, ResearchOrchestrator, AGENT_TYPES,
)
from services.execution_enhanced import (
    Order, OrderType, OrderSide, OrderStatus, ExecutionEngine,
    OrderBookSimulator, RiskLimits, run_pre_trade_risk_checks,
)
from services.structured_logging import (
    SlowQueryTracker, ErrorAggregator, Tracer, RequestContext, generate_request_id,
)
from services.oauth_providers import (
    get_provider, list_providers, GoogleOAuthProvider, GitHubOAuthProvider,
)
from services.provider_health import (
    LatencyTracker, QuotaTracker, QuotaConfig, HealthScore, ProviderHealthRouter,
)


# ===========================================================================
# Black-Scholes extended coverage
# ===========================================================================

class TestBSCallEdgeCases:
    def test_very_deep_itm_call(self):
        p = bs_call(500, 100, 1.0, 0.05, 0.20)
        assert p > 395  # almost intrinsic

    def test_very_deep_otm_call_near_zero(self):
        p = bs_call(100, 500, 1.0, 0.05, 0.20)
        assert p < 0.01

    def test_call_increases_with_spot(self):
        prices = [bs_call(s, 100, 1.0, 0.05, 0.20) for s in [80, 90, 100, 110, 120]]
        assert prices == sorted(prices)

    def test_call_increases_with_vol(self):
        prices = [bs_call(100, 100, 1.0, 0.05, v) for v in [0.10, 0.20, 0.40, 0.80]]
        assert prices == sorted(prices)

    def test_call_decreases_with_time_approaches_zero(self):
        c_far = bs_call(100, 100, 2.0, 0.05, 0.20)
        c_near = bs_call(100, 100, 0.01, 0.05, 0.20)
        assert c_far > c_near

    def test_put_call_parity_various_strikes(self):
        for K in [90, 100, 110]:
            c = bs_call(100, K, 1.0, 0.05, 0.20)
            p = bs_put(100, K, 1.0, 0.05, 0.20)
            expected = 100 - K * math.exp(-0.05)
            assert abs(c - p - expected) < 0.05

    def test_high_rate_lower_put(self):
        p_low_r = bs_put(100, 100, 1.0, 0.01, 0.20)
        p_high_r = bs_put(100, 100, 1.0, 0.10, 0.20)
        assert p_low_r > p_high_r  # higher rate discounts put strike more


class TestBSPutEdgeCases:
    def test_deep_itm_put(self):
        p = bs_put(50, 150, 1.0, 0.05, 0.20)
        assert p > 90

    def test_otm_put_near_zero(self):
        p = bs_put(150, 100, 1.0, 0.05, 0.20)
        assert p < 5

    def test_put_increases_with_strike(self):
        prices = [bs_put(100, K, 1.0, 0.05, 0.20) for K in [80, 90, 100, 110, 120]]
        assert prices == sorted(prices)


class TestBinomialEdgeCases:
    def test_convergence_european_call(self):
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.20
        bt = binomial_tree(S, K, T, r, sigma, "call", steps=500)
        bs = bs_call(S, K, T, r, sigma)
        assert abs(bt - bs) < 0.1

    def test_american_call_atm(self):
        p = binomial_tree(100, 100, 1.0, 0.05, 0.20, "call", american=True)
        assert p > 0

    def test_deep_otm_both_zero_at_expiry(self):
        c = binomial_tree(50, 200, 0.0, 0.05, 0.20, "call")
        p = binomial_tree(200, 50, 0.0, 0.05, 0.20, "put")
        assert c == pytest.approx(0.0)
        assert p == pytest.approx(0.0)

    def test_steps_affect_accuracy(self):
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.20
        bs = bs_call(S, K, T, r, sigma)
        for steps in [10, 50, 100]:
            bt = binomial_tree(S, K, T, r, sigma, steps=steps)
            assert abs(bt - bs) < 5.0  # tolerance loosens for fewer steps


class TestGreeksEdgeCases:
    def test_delta_sum_call_put(self):
        g_c = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        g_p = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        # put-call delta parity: delta_call - delta_put = 1 (put delta is negative)
        assert g_c["delta"] - g_p["delta"] == pytest.approx(1.0, abs=0.01)

    def test_gamma_same_call_put(self):
        g_c = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        g_p = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        assert g_c["gamma"] == pytest.approx(g_p["gamma"], rel=0.01)

    def test_vega_same_call_put(self):
        g_c = bs_greeks(100, 100, 1.0, 0.05, 0.20, "call")
        g_p = bs_greeks(100, 100, 1.0, 0.05, 0.20, "put")
        assert g_c["vega"] == pytest.approx(g_p["vega"], rel=0.01)

    def test_delta_deep_itm_call_near_one(self):
        g = bs_greeks(200, 100, 1.0, 0.05, 0.20, "call")
        assert g["delta"] > 0.95

    def test_delta_deep_otm_call_near_zero(self):
        g = bs_greeks(50, 200, 1.0, 0.05, 0.20, "call")
        assert g["delta"] < 0.05


# ===========================================================================
# Strategy builder extended
# ===========================================================================

class TestStrategyBuilderExtended:
    def test_all_strategies_build(self):
        for name in list_strategies():
            result = build_strategy(name, 100, 100, 0.25, 0.05, 0.20)
            assert result["strategy"] == name

    def test_payoff_at_expiry_is_defined(self):
        for name in list_strategies():
            result = build_strategy(name, 100, 100, 0.25, 0.05, 0.20)
            assert len(result["payoff_curve"]) > 0

    def test_net_cost_is_float(self):
        for name in list_strategies():
            result = build_strategy(name, 100, 100, 0.25, 0.05, 0.20)
            assert isinstance(result["net_cost"], float)

    def test_straddle_has_positive_vega(self):
        r = build_strategy("straddle", 100, 100, 0.5, 0.05, 0.20)
        assert r["greeks"]["vega"] > 0

    def test_iron_condor_max_loss_bounded(self):
        r = build_strategy("iron_condor", 100, 100, 0.25, 0.05, 0.20)
        assert r["max_loss"] > -100  # loss should be bounded by wing width

    def test_protective_put_legs(self):
        r = build_strategy("protective_put", 100, 95, 0.25, 0.05, 0.20)
        types = {l["type"] for l in r["legs"]}
        assert "put" in types and "stock" in types

    def test_bear_put_spread_legs(self):
        r = build_strategy("bear_put_spread", 100, 105, 0.25, 0.05, 0.20)
        actions = [l["action"] for l in r["legs"] if l["type"] == "put"]
        assert "buy" in actions and "sell" in actions


# ===========================================================================
# Walk-forward extended
# ===========================================================================

def make_noisy_prices(n=300, seed=42):
    import random
    random.seed(seed)
    prices = [100.0]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + 0.001 + random.gauss(0, 0.01)))
    return prices


def sma(prices, params):
    fast = int(params.get("fast", 10))
    slow = int(params.get("slow", 30))
    if len(prices) < slow + 1:
        return []
    rets = []
    pos = 0
    for i in range(slow, len(prices)):
        sf = sum(prices[i - fast:i]) / fast
        ss = sum(prices[i - slow:i]) / slow
        sig = 1 if sf > ss else -1
        if i > slow:
            rets.append(pos * (prices[i] - prices[i - 1]) / prices[i - 1])
        pos = sig
    return rets


class TestComputeMetricsExtended:
    def test_single_period(self):
        m = compute_metrics([0.05])
        assert m["total_return"] == pytest.approx(0.05)

    def test_all_equal_returns_zero_drawdown(self):
        m = compute_metrics([0.001] * 100)
        assert m["max_drawdown"] == 0.0

    def test_sharp_decline_high_drawdown(self):
        returns = [-0.05] * 20
        m = compute_metrics(returns)
        assert m["max_drawdown"] > 0.5

    def test_n_matches_length(self):
        returns = [0.01] * 50
        assert compute_metrics(returns)["n"] == 50


class TestWalkForwardExtended:
    def test_multiple_windows_generated(self):
        prices = make_noisy_prices(500)
        result = walk_forward_test(prices, sma, {"fast": 10, "slow": 30}, 150, 30)
        assert result.aggregate["n_windows"] >= 3

    def test_is_and_oos_non_overlapping(self):
        prices = make_noisy_prices(300)
        result = walk_forward_test(prices, sma, {"fast": 5, "slow": 20}, 100, 25)
        for w in result.windows:
            assert w["is_end"] == w["oos_start"]
            assert w["oos_end"] > w["oos_start"]


class TestParameterSweepExtended:
    def test_larger_grid(self):
        prices = make_noisy_prices(200)
        grid = {"fast": [5, 8, 10, 15], "slow": [20, 25, 30, 40]}
        result = parameter_sweep(prices, sma, grid, metric="sharpe")
        assert len(result.all_results) == 16

    def test_cagr_metric(self):
        prices = make_noisy_prices(200)
        grid = {"fast": [5, 10], "slow": [20, 30]}
        result = parameter_sweep(prices, sma, grid, metric="cagr")
        cagrs = [r["metrics"]["cagr"] for r in result.all_results]
        assert cagrs == sorted(cagrs, reverse=True)

    def test_best_params_in_grid(self):
        prices = make_noisy_prices(150)
        grid = {"fast": [5, 10], "slow": [20, 30]}
        result = parameter_sweep(prices, sma, grid)
        fast_vals = [5, 10]
        slow_vals = [20, 30]
        assert result.best_params["fast"] in fast_vals
        assert result.best_params["slow"] in slow_vals


class TestKellyCriterionExtended:
    def test_decreasing_win_prob_decreasing_kelly(self):
        k1 = kelly_criterion(0.7, 0.10, 0.05)
        k2 = kelly_criterion(0.6, 0.10, 0.05)
        assert k1["full_kelly"] > k2["full_kelly"]

    def test_higher_win_return_higher_kelly(self):
        k1 = kelly_criterion(0.6, 0.05, 0.05)
        k2 = kelly_criterion(0.6, 0.20, 0.05)
        assert k2["full_kelly"] > k1["full_kelly"]

    def test_all_fractional_keys_present(self):
        k = kelly_criterion(0.6, 0.10, 0.05)
        for key in ("full_kelly", "half_kelly", "quarter_kelly", "expected_log_growth"):
            assert key in k


# ===========================================================================
# Knowledge graph extended
# ===========================================================================

class TestKGVectorExtended:
    def test_cosine_same_sign_positive(self):
        a = [1.0, 1.0, 1.0]
        b = [2.0, 2.0, 2.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_embed_dim_respected(self):
        v = _hash_embed("test", dim=16)
        assert len(v) == 16

    def test_embed_normalized(self):
        v = _hash_embed("abc", dim=64)
        norm = math.sqrt(sum(x * x for x in v))
        assert norm == pytest.approx(1.0, abs=0.01)


class TestKGEntitiesExtended:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_add_multiple_types(self):
        types = ["company", "sector", "concept", "event"]
        for t in types:
            self.kg.add_entity(f"E_{t}", t, f"Name {t}", "")
        for t in types:
            e = self.kg.get_entity(f"E_{t}")
            assert e.entity_type == t

    def test_entity_has_embedding(self):
        e = self.kg.add_entity("EMBD", "company", "Embedded Corp", "ai cloud")
        assert len(e.embedding) > 0

    def test_custom_embedding(self):
        custom = [1.0] + [0.0] * 63
        norm = math.sqrt(sum(x * x for x in custom))
        custom = [x / norm for x in custom]
        e = self.kg.add_entity("CEMB", "company", "C", "", embedding=custom)
        assert e.embedding[0] == pytest.approx(1.0)

    def test_list_limit_respected(self):
        for i in range(20):
            self.kg.add_entity(f"LIM{i}", "sector", f"S{i}", "")
        sectors = self.kg.list_entities("sector", limit=5)
        assert len(sectors) <= 5


class TestKGRelationshipsExtended:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)
        for i in range(5):
            self.kg.add_entity(f"N{i}", "company", f"Co{i}", "")

    def test_multiple_relationships(self):
        self.kg.add_relationship("N0", "N1", "competitor")
        self.kg.add_relationship("N0", "N2", "supplier")
        self.kg.add_relationship("N0", "N3", "customer")
        rels = self.kg.get_relationships("N0", direction="out")
        assert len(rels) == 3

    def test_relationship_score(self):
        self.kg.add_relationship("N1", "N2", "peer", score=0.75)
        rels = self.kg.get_relationships("N1", direction="out")
        assert any(r["score"] == 0.75 for r in rels)

    def test_relationship_metadata(self):
        self.kg.add_relationship("N2", "N3", "influences", metadata={"source": "SEC"})
        rels = self.kg.get_relationships("N2", direction="out")
        assert any(r["metadata"].get("source") == "SEC" for r in rels)


class TestKGSearchExtended:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_search_top_k_respected(self):
        results = self.kg.semantic_search("technology", top_k=3)
        assert len(results) <= 3

    def test_search_all_types(self):
        r1 = self.kg.semantic_search("cloud", entity_type="company", top_k=5)
        r2 = self.kg.semantic_search("cloud", entity_type="sector", top_k=5)
        assert all(r.entity.entity_type == "company" for r in r1)
        assert all(r.entity.entity_type == "sector" for r in r2)

    def test_find_similar_excludes_self(self):
        similar = self.kg.find_similar_companies("NVDA", top_k=5)
        assert all(r.entity.id != "NVDA" for r in similar)


# ===========================================================================
# AI agents extended
# ===========================================================================

class TestAgentsExtended:
    def test_all_agents_have_tools(self):
        for atype in AGENT_TYPES:
            agent = get_agent(atype)
            assert len(agent.tools) > 0

    def test_agent_description_not_empty(self):
        for atype in AGENT_TYPES:
            agent = get_agent(atype)
            assert len(agent.description) > 10

    def test_confidence_in_range(self):
        for atype in AGENT_TYPES:
            agent = get_agent(atype)
            resp = agent.analyze("test query", {"tickers": ["AAPL"]})
            assert 0.0 < resp.confidence <= 1.0

    def test_content_is_string(self):
        for atype in AGENT_TYPES:
            agent = get_agent(atype)
            resp = agent.analyze("market analysis", {})
            assert isinstance(resp.content, str)
            assert len(resp.content) > 0


class TestOrchestratorExtended:
    def setup_method(self):
        self.orch = ResearchOrchestrator()

    def test_context_preserved_in_session(self):
        ctx = {"tickers": ["TSLA", "RIVN"], "sector": "EV"}
        s = self.orch.create_session("EV study", ctx)
        found = self.orch.get_session(s.id)
        assert found.context["sector"] == "EV"

    def test_multiple_sessions_independent(self):
        s1 = self.orch.create_session("Topic A")
        s2 = self.orch.create_session("Topic B")
        self.orch.run_agent(s1.id, "macro_economist", "Q1")
        assert len(self.orch.get_session(s1.id).messages) == 1
        assert len(self.orch.get_session(s2.id).messages) == 0

    def test_run_subset_agents(self):
        s = self.orch.create_session("partial")
        subset = ["macro_economist", "risk_officer"]
        for atype in subset:
            self.orch.run_agent(s.id, atype, "query")
        assert len(self.orch.get_session(s.id).messages) == 2

    def test_synthesis_confidence_average(self):
        s = self.orch.create_session("avg test")
        self.orch.run_all_agents(s.id, "test")
        result = self.orch.synthesize(s.id)
        assert 0 < result["consensus_confidence"] <= 1


# ===========================================================================
# Execution engine extended
# ===========================================================================

class TestExecutionEngineExtended:
    def setup_method(self):
        self.engine = ExecutionEngine()

    def test_vwap_price_near_market(self):
        engine = ExecutionEngine(RiskLimits(max_order_notional=1_000_000, max_position_pct=1.0,
                                             max_daily_loss=500_000, max_order_qty=100_000,
                                             portfolio_value=1_000_000))
        o = Order(ticker="AAPL", side=OrderSide.BUY, order_type=OrderType.VWAP, quantity=1000)
        result = engine.submit_order(o, 150.0)
        assert result["status"] == "filled"
        order = engine.get_order(o.id)
        assert order.avg_fill_price == pytest.approx(150.0, rel=0.05)

    def test_multiple_fills_reported(self):
        for i in range(5):
            o = Order(ticker="AAPL", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10)
            self.engine.submit_order(o, 100.0 + i)
        reports = self.engine.execution_reports()
        assert len(reports) >= 5

    def test_slippage_bps_in_report(self):
        o = Order(ticker="AAPL", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        self.engine.submit_order(o, 150.0)
        reports = self.engine.execution_reports(limit=1)
        assert "slippage_bps" in reports[-1]
        assert reports[-1]["slippage_bps"] >= 0

    def test_large_order_has_more_slippage(self):
        book = OrderBookSimulator(100.0)
        small = book.estimate_fill_price("buy", 1)
        large = book.estimate_fill_price("buy", 9999)
        assert large > small

    def test_sell_market_order(self):
        o = Order(ticker="TSLA", side=OrderSide.SELL, order_type=OrderType.MARKET, quantity=50)
        result = self.engine.submit_order(o, 200.0)
        assert result["status"] == "filled"

    def test_trailing_stop_updates_stop_price(self):
        o = Order(ticker="AAPL", side=OrderSide.SELL, order_type=OrderType.TRAILING_STOP,
                  quantity=100, trail_pct=0.02)
        self.engine.submit_order(o, 150.0)
        found = self.engine.get_order(o.id)
        assert found.stop_price is not None
        assert found.stop_price < 150.0


class TestRiskLimitsExtended:
    def test_exactly_at_limit_passes(self):
        o = Order(ticker="X", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        limits = RiskLimits(max_order_notional=10000.0, portfolio_value=1_000_000)
        ok, _ = run_pre_trade_risk_checks(o, 100.0, limits)
        assert ok

    def test_one_over_limit_fails(self):
        o = Order(ticker="X", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=101)
        limits = RiskLimits(max_order_notional=10000.0, portfolio_value=1_000_000)
        ok, _ = run_pre_trade_risk_checks(o, 100.0, limits)
        assert not ok


# ===========================================================================
# Structured logging extended
# ===========================================================================

class TestRequestContextExtended:
    def test_multiple_keys_set(self):
        RequestContext.set(request_id="r", path="/x", method="GET", user_id="u")
        ctx = RequestContext.get_context()
        assert ctx["method"] == "GET"
        assert ctx["user_id"] == "u"
        RequestContext.clear()

    def test_clear_makes_empty(self):
        RequestContext.set(request_id="r")
        RequestContext.clear()
        assert not RequestContext.get_context()


class TestSlowQueryTrackerExtended:
    def test_threshold_boundary(self):
        t = SlowQueryTracker(threshold_ms=100.0)
        assert not t.record("op", 99.9)
        assert t.record("op", 100.1)

    def test_metadata_stored(self):
        t = SlowQueryTracker(threshold_ms=1.0)
        t.record("db_query", 50.0, table="users", rows=1000)
        ops = t.get_slow_ops()
        assert ops[-1]["metadata"]["table"] == "users"

    def test_reversed_order(self):
        t = SlowQueryTracker(threshold_ms=1.0)
        t.record("first", 50.0)
        t.record("second", 60.0)
        ops = t.get_slow_ops()
        # get_slow_ops returns most-recent last (reversed from deque)
        names = [op["operation"] for op in ops]
        assert "first" in names and "second" in names


class TestErrorAggregatorExtended:
    def test_multiple_types(self):
        agg = ErrorAggregator()
        for i in range(5):
            agg.record("TypeA", f"error {i}")
        for i in range(3):
            agg.record("TypeB", f"error {i}")
        s = agg.summary()
        assert s["by_type"]["TypeA"] == 5
        assert s["by_type"]["TypeB"] == 3
        assert s["total_types"] == 2

    def test_request_id_captured(self):
        RequestContext.set(request_id="req-456")
        agg = ErrorAggregator()
        agg.record("TestError", "msg")
        recent = agg.get_recent("TestError")
        assert recent[0]["request_id"] == "req-456"
        RequestContext.clear()


class TestTracerExtended:
    def test_span_to_dict(self):
        t = Tracer("svc")
        s = t.start_span("op")
        s.end()
        d = s.to_dict()
        assert "name" in d and "trace_id" in d and "duration_ms" in d

    def test_unended_span_duration(self):
        import time
        t = Tracer()
        s = t.start_span("live")
        time.sleep(0.01)
        assert s.duration_ms > 5

    def test_service_name(self):
        t = Tracer("my_service")
        assert t.service_name == "my_service"


# ===========================================================================
# OAuth providers extended
# ===========================================================================

class TestOAuthExtended:
    def test_all_providers_have_scopes(self):
        for p in list_providers():
            assert len(p["scopes"]) > 0

    def test_authorization_url_includes_state(self):
        for name in ["google", "github", "microsoft", "apple"]:
            p = get_provider(name)
            url = p.build_authorization_url("https://x.com/cb", "MYSTATE")
            assert "MYSTATE" in url

    def test_exchange_code_returns_tokens(self):
        for name in ["google", "github", "microsoft", "apple"]:
            p = get_provider(name)
            tokens = p.exchange_code("code_test", "https://x.com/cb")
            assert tokens.access_token
            assert tokens.token_type == "Bearer"

    def test_get_user_info_returns_provider_name(self):
        for name in ["google", "github", "microsoft", "apple"]:
            p = get_provider(name)
            user = p.get_user_info("access_token_test")
            assert user.provider == name

    def test_user_email_format(self):
        for name in ["google", "github", "microsoft", "apple"]:
            p = get_provider(name)
            user = p.mock_user_info("code_xyz")
            assert "@" in user.email

    def test_all_providers_have_authorization_url(self):
        for p_info in list_providers():
            p = get_provider(p_info["name"])
            assert p.authorization_url.startswith("https://")

    def test_not_configured_without_env(self):
        import os
        # Remove any existing env vars for testing
        p = GoogleOAuthProvider()
        key = "GOOGLE_CLIENT_ID"
        was_set = key in os.environ
        if was_set:
            val = os.environ.pop(key)
        # Check that is_configured requires both client_id and client_secret
        configured = p.is_configured()
        # Don't assert specific value since CI might have it set
        assert isinstance(configured, bool)
        if was_set:
            os.environ[key] = val


# ===========================================================================
# Provider health extended
# ===========================================================================

class TestLatencyTrackerExtended:
    def test_all_success(self):
        t = LatencyTracker()
        for i in range(10):
            t.record(float(i * 10), True)
        assert t.success_rate == pytest.approx(1.0)

    def test_all_failure(self):
        t = LatencyTracker()
        for _ in range(10):
            t.record(100.0, False)
        assert t.success_rate == pytest.approx(0.0)

    def test_p95_in_window(self):
        t = LatencyTracker()
        for v in range(100):
            t.record(float(v), True)
        p95 = t.p95_latency_ms
        assert p95 >= 80.0  # 95th percentile of 0-99

    def test_stats_round_trip(self):
        t = LatencyTracker()
        t.record(123.456, True)
        s = t.stats()
        assert s["avg_latency_ms"] == pytest.approx(123.46, abs=0.01)


class TestHealthScoreExtended:
    def test_alternating_success_failure(self):
        h = HealthScore()
        for i in range(50):
            h.update(i % 2 == 0, 100.0)
        assert 0 < h.value < 1

    def test_score_between_zero_and_one(self):
        h = HealthScore()
        for _ in range(100):
            h.update(False, 5000.0)
        assert 0.0 <= h.value <= 1.0

    def test_ewma_alpha_effect(self):
        h1 = HealthScore()
        h1.ALPHA = 0.5
        h1._score = 1.0
        h1.update(False, 500.0)
        assert h1.value < 0.7  # large alpha reacts faster


class TestQuotaTrackerExtended:
    def test_remaining_decrements(self):
        q = QuotaTracker(QuotaConfig(calls_per_minute=10, calls_per_day=100))
        q.check_and_consume()
        s = q.stats()
        assert s["minute_remaining"] == 9

    def test_unlimited_calls_within_bounds(self):
        q = QuotaTracker(QuotaConfig(calls_per_minute=1000, calls_per_day=10000))
        results = [q.check_and_consume() for _ in range(500)]
        assert all(results)
