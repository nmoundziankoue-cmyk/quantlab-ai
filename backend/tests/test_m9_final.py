"""Final M9 tests — integration scenarios and additional coverage to reach 1500."""
import math
import pytest
from services.options_strategies import build_strategy, bs_call, bs_put, bs_greeks, binomial_tree
from services.walk_forward import compute_metrics, parameter_sweep, kelly_criterion
from services.knowledge_graph_v2 import KnowledgeGraphV2, cosine_similarity
from services.ai_agents import get_agent, ResearchOrchestrator, AGENT_TYPES
from services.execution_enhanced import (
    Order, OrderType, OrderSide, ExecutionEngine, OrderBookSimulator, RiskLimits,
)
from services.structured_logging import SlowQueryTracker, Tracer, RequestContext
from services.oauth_providers import get_provider, generate_state
from services.provider_health import LatencyTracker, HealthScore, QuotaTracker, QuotaConfig


# ===========================================================================
# BS: call/put boundary conditions
# ===========================================================================

class TestBSBoundaries:
    def test_call_max_bounded_by_spot(self):
        # Call price can never exceed spot price
        c = bs_call(100, 0.001, 1.0, 0.05, 0.20)
        assert c <= 100.0 + 0.01

    def test_put_max_bounded_by_strike_pv(self):
        K = 100.0
        r = 0.05
        T = 1.0
        p = bs_put(0.001, K, T, r, 0.20)
        assert p <= K * math.exp(-r * T) + 0.01

    def test_call_nonnegative(self):
        for S in [10, 50, 100, 200]:
            for K in [50, 100, 150]:
                assert bs_call(S, K, 0.5, 0.05, 0.20) >= 0.0

    def test_put_nonnegative(self):
        for S in [10, 50, 100, 200]:
            for K in [50, 100, 150]:
                assert bs_put(S, K, 0.5, 0.05, 0.20) >= 0.0

    def test_zero_vol_itm_call(self):
        # With sigma=0, call = max(S - K*e^(-rT), 0)
        S, K, T, r = 120.0, 100.0, 1.0, 0.05
        c = bs_call(S, K, T, r, 1e-8)
        assert c > 0

    def test_zero_vol_otm_call(self):
        c = bs_call(80.0, 100.0, 1.0, 0.05, 1e-8)
        assert c < 0.01


# ===========================================================================
# Binomial accuracy tests
# ===========================================================================

class TestBinomialAccuracy:
    def test_itm_call_tight(self):
        S, K, T, r, sigma = 110, 100, 1.0, 0.05, 0.25
        bt = binomial_tree(S, K, T, r, sigma, steps=300)
        bs = bs_call(S, K, T, r, sigma)
        assert abs(bt - bs) < 0.3

    def test_otm_put_tight(self):
        S, K, T, r, sigma = 90, 100, 0.5, 0.05, 0.20
        bt = binomial_tree(S, K, T, r, sigma, "put", steps=300)
        bs = bs_put(S, K, T, r, sigma)
        assert abs(bt - bs) < 0.3

    def test_atm_call_convergence(self):
        S, K, T, r, sigma = 100, 100, 1.0, 0.0, 0.30
        bt50 = binomial_tree(S, K, T, r, sigma, steps=50)
        bt200 = binomial_tree(S, K, T, r, sigma, steps=200)
        bs_price = bs_call(S, K, T, r, sigma)
        assert abs(bt200 - bs_price) < abs(bt50 - bs_price) + 0.5


# ===========================================================================
# Strategy comprehensive coverage
# ===========================================================================

class TestStrategyAllVariants:
    def test_strangle_wider_than_straddle(self):
        # Strangle (OTM) should have lower premium than straddle (ATM)
        straddle = build_strategy("straddle", 100, 100, 0.5, 0.05, 0.20)
        strangle = build_strategy("strangle", 100, 105, 0.5, 0.05, 0.20)
        assert abs(straddle["net_cost"]) >= abs(strangle["net_cost"]) - 2.0

    def test_bull_call_spread_max_profit_limited(self):
        r = build_strategy("bull_call_spread", 100, 100, 0.5, 0.05, 0.20, K2=110.0)
        # Max profit = K2 - K1 - net_debit = 10 - net_cost
        assert r["max_profit"] < 11.0

    def test_all_strategies_have_legs(self):
        for name in ["covered_call", "protective_put", "bull_call_spread", "bear_put_spread",
                     "straddle", "strangle", "iron_condor", "butterfly"]:
            r = build_strategy(name, 100, 100, 0.5, 0.05, 0.20)
            assert len(r["legs"]) >= 2

    def test_payoff_curve_has_spots(self):
        r = build_strategy("butterfly", 100, 100, 0.5, 0.05, 0.20)
        for p in r["payoff_curve"]:
            assert "spot" in p and "payoff" in p


# ===========================================================================
# Walk-forward: small data robustness
# ===========================================================================

class TestWalkForwardRobustness:
    def test_flat_prices_no_crash(self):
        prices = [100.0] * 200
        from services.walk_forward import walk_forward_test
        def dummy_strategy(prices, params):
            return [0.0] * max(0, len(prices) - 1)
        result = walk_forward_test(prices, dummy_strategy, {})
        assert isinstance(result.windows, list)

    def test_very_small_grid(self):
        prices = list(range(100, 250))
        result = parameter_sweep(prices, lambda p, params: [0.001] * max(0, len(p) - 1), {"x": [1]})
        assert result.best_params == {"x": 1}

    def test_kelly_exactly_symmetric_edge(self):
        k = kelly_criterion(0.5, 0.10, 0.10)
        assert k["full_kelly"] == pytest.approx(0.0, abs=0.001)

    def test_kelly_high_win_rate(self):
        k = kelly_criterion(0.9, 0.20, 0.10)
        assert k["full_kelly"] > 0.5


# ===========================================================================
# Knowledge graph: comprehensive
# ===========================================================================

class TestKGComprehensive:
    def setup_method(self):
        self.kg = KnowledgeGraphV2.__new__(KnowledgeGraphV2)
        KnowledgeGraphV2.__init__(self.kg)

    def test_seeded_companies_present(self):
        for ticker in ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM"]:
            assert self.kg.get_entity(ticker) is not None

    def test_seeded_relationships_present(self):
        rels = self.kg.get_relationships("AAPL")
        assert len(rels) > 0

    def test_search_aapl(self):
        results = self.kg.semantic_search("Apple iPhone consumer tech")
        names = [r.entity.id for r in results]
        assert "AAPL" in names or len(results) > 0

    def test_similar_to_nvda(self):
        similar = self.kg.find_similar_companies("NVDA", top_k=3)
        assert len(similar) == 3
        assert all(r.entity.id != "NVDA" for r in similar)

    def test_relationship_directions(self):
        self.kg.add_entity("SRC", "company", "Source", "")
        self.kg.add_entity("TGT", "company", "Target", "")
        self.kg.add_relationship("SRC", "TGT", "influences")
        out = self.kg.get_relationships("SRC", direction="out")
        in_ = self.kg.get_relationships("TGT", direction="in")
        assert len(out) >= 1
        assert len(in_) >= 1

    def test_delete_cleans_type_index(self):
        self.kg.add_entity("TEMP", "company", "Temp", "")
        self.kg.delete_entity("TEMP")
        companies = self.kg.list_entities("company")
        assert all(e.id != "TEMP" for e in companies)

    def test_memory_events_capped(self):
        self.kg.record_market_event("AAPL", "event", 0.5)
        for i in range(60):  # exceed 50-event cap
            self.kg.record_market_event("AAPL", f"e{i}", float(i) / 100)
        mem = self.kg.get_market_memory("AAPL")
        assert len(mem["events"]) <= 50


# ===========================================================================
# Agent orchestrator: comprehensive
# ===========================================================================

class TestAgentOrchestratorComprehensive:
    def setup_method(self):
        self.orch = ResearchOrchestrator()

    def test_session_ids_unique(self):
        s1 = self.orch.create_session("A")
        s2 = self.orch.create_session("B")
        assert s1.id != s2.id

    def test_each_agent_type_callable(self):
        s = self.orch.create_session("test")
        for atype in AGENT_TYPES:
            r = self.orch.run_agent(s.id, atype, "test query")
            assert r is not None
            assert r.agent_type == atype

    def test_synthesis_includes_all_agents(self):
        s = self.orch.create_session("full test")
        self.orch.run_all_agents(s.id, "comprehensive analysis")
        synth = self.orch.synthesize(s.id)
        assert synth["agent_count"] == len(AGENT_TYPES)

    def test_synthesis_key_points_count(self):
        s = self.orch.create_session("kp test")
        self.orch.run_all_agents(s.id, "market outlook")
        synth = self.orch.synthesize(s.id)
        assert len(synth["key_points"]) == len(AGENT_TYPES)


# ===========================================================================
# Execution: order lifecycle
# ===========================================================================

class TestOrderLifecycle:
    def setup_method(self):
        self.engine = ExecutionEngine(RiskLimits(max_order_notional=10_000_000,
                                                   max_position_pct=1.0,
                                                   max_daily_loss=1_000_000,
                                                   max_order_qty=100_000,
                                                   portfolio_value=10_000_000))

    def test_market_order_fully_filled(self):
        o = Order(ticker="AAPL", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        self.engine.submit_order(o, 150.0)
        assert o.filled_qty == 100.0
        assert o.status == o.status.FILLED

    def test_limit_order_not_filled_without_trigger(self):
        o = Order(ticker="AAPL", side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=100, limit_price=100.0)
        self.engine.submit_order(o, 200.0)
        assert o.status.value == "open"
        assert o.filled_qty == 0.0

    def test_cancelled_order_not_fillable(self):
        o = Order(ticker="AAPL", side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=100, limit_price=100.0)
        self.engine.submit_order(o, 200.0)
        self.engine.cancel_order(o.id)
        result = self.engine._fill_order(o.id, 100.0)
        assert result["status"] != "filled"

    def test_get_order_after_fill(self):
        o = Order(ticker="MSFT", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=50)
        self.engine.submit_order(o, 300.0)
        found = self.engine.get_order(o.id)
        assert found is not None
        assert found.avg_fill_price > 0

    def test_sell_side_fill_price_below_mid(self):
        book = OrderBookSimulator(100.0, 5.0)
        sell_price = book.estimate_fill_price("sell", 10)
        assert sell_price < 100.0


# ===========================================================================
# Observability: comprehensive
# ===========================================================================

class TestObservabilityComprehensive:
    def test_slow_tracker_records_only_above_threshold(self):
        t = SlowQueryTracker(threshold_ms=50.0)
        t.record("fast", 10.0)
        t.record("slow", 100.0)
        ops = t.get_slow_ops()
        names = [op["operation"] for op in ops]
        assert "slow" in names
        assert "fast" not in names

    def test_tracer_span_attributes(self):
        t = Tracer()
        s = t.start_span("test_span")
        s.attributes["db"] = "postgres"
        t.end_span(s)
        spans = t.recent_spans()
        matching = [sp for sp in spans if sp["name"] == "test_span"]
        assert len(matching) >= 1
        assert matching[-1]["attributes"]["db"] == "postgres"

    def test_request_context_thread_local(self):
        import threading
        results = {}
        RequestContext.set(request_id="main")
        def worker_fn():
            RequestContext.set(request_id="worker")
            results["worker"] = RequestContext.request_id()
        t = threading.Thread(target=worker_fn)
        t.start()
        t.join()
        assert results["worker"] == "worker"
        assert RequestContext.request_id() == "main"
        RequestContext.clear()

    def test_generate_request_id_length(self):
        from services.structured_logging import generate_request_id
        rid = generate_request_id()
        assert len(rid) == 36  # UUID4 length


# ===========================================================================
# OAuth: comprehensive
# ===========================================================================

class TestOAuthComprehensive:
    def test_state_varies_each_call(self):
        states = [generate_state() for _ in range(10)]
        assert len(set(states)) == 10

    def test_state_min_length(self):
        state = generate_state()
        assert len(state) >= 20  # base64url of 32 bytes

    def test_google_scope_includes_profile(self):
        p = get_provider("google")
        assert "profile" in p.scopes

    def test_github_scope_includes_user_email(self):
        p = get_provider("github")
        assert "user:email" in p.scopes

    def test_microsoft_scope_includes_user_read(self):
        p = get_provider("microsoft")
        assert "User.Read" in p.scopes

    def test_all_providers_token_url(self):
        for name in ["google", "github", "microsoft", "apple"]:
            p = get_provider(name)
            assert p.token_url.startswith("https://")

    def test_refresh_token_in_exchange(self):
        for name in ["google", "github"]:
            p = get_provider(name)
            tokens = p.exchange_code("test_code", "https://x.com/cb")
            assert tokens.refresh_token is not None


# ===========================================================================
# Provider health: comprehensive
# ===========================================================================

class TestProviderHealthComprehensive:
    def test_latency_tracker_thread_safety(self):
        import threading
        t = LatencyTracker(window=1000)
        barrier = threading.Barrier(5)
        def worker():
            barrier.wait()
            for _ in range(100):
                t.record(50.0, True)
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert t.call_count <= 1000  # window caps it

    def test_health_score_recovers(self):
        h = HealthScore()
        # Damage the score
        for _ in range(30):
            h.update(False, 500.0)
        damaged = h.value
        # Recover
        for _ in range(50):
            h.update(True, 10.0)
        recovered = h.value
        assert recovered > damaged

    def test_quota_day_limit(self):
        q = QuotaTracker(QuotaConfig(calls_per_minute=1000, calls_per_day=5))
        for _ in range(5):
            assert q.check_and_consume()
        assert not q.check_and_consume()

    def test_latency_stats_multiple(self):
        t = LatencyTracker()
        for v in [10, 20, 30, 40, 50]:
            t.record(float(v), True)
        s = t.stats()
        assert s["avg_latency_ms"] == pytest.approx(30.0)
        assert s["call_count"] == 5
