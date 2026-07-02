"""M9 router integration tests — all new endpoints via FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# /providers
# ---------------------------------------------------------------------------

class TestProvidersRouter:
    def test_health_200(self):
        r = client.get("/providers/health")
        assert r.status_code == 200

    def test_health_has_provider_count(self):
        r = client.get("/providers/health")
        assert "provider_count" in r.json()

    def test_stats_200(self):
        r = client.get("/providers/stats")
        assert r.status_code == 200
        assert "providers" in r.json()

    def test_ranking_200(self):
        r = client.get("/providers/ranking")
        assert r.status_code == 200
        assert "ranked" in r.json()

    def test_stats_single_yahoo(self):
        r = client.get("/providers/stats/yahoo")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "yahoo"

    def test_stats_single_not_found(self):
        r = client.get("/providers/stats/nonexistent_provider")
        assert r.status_code == 404

    def test_cache_invalidate_all(self):
        r = client.delete("/providers/cache")
        assert r.status_code == 200
        assert r.json()["invalidated"] == "all"

    def test_cache_invalidate_ticker(self):
        r = client.delete("/providers/cache?ticker=AAPL")
        assert r.status_code == 200
        assert r.json()["invalidated"] == "AAPL"


# ---------------------------------------------------------------------------
# /options/strategies
# ---------------------------------------------------------------------------

class TestOptionsStrategiesRouter:
    def test_list_strategies(self):
        r = client.get("/options/strategies/list")
        assert r.status_code == 200
        assert len(r.json()["strategies"]) == 8

    def test_build_straddle(self):
        payload = {"strategy": "straddle", "spot": 150.0, "strike": 150.0, "expiry_T": 0.25}
        r = client.post("/options/strategies/build", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["strategy"] == "straddle"
        assert len(data["legs"]) == 2

    def test_build_iron_condor(self):
        payload = {"strategy": "iron_condor", "spot": 100.0, "strike": 100.0, "expiry_T": 0.5}
        r = client.post("/options/strategies/build", json=payload)
        assert r.status_code == 200
        assert len(r.json()["legs"]) == 4

    def test_build_unknown_strategy(self):
        payload = {"strategy": "fake_strategy", "spot": 100.0, "strike": 100.0, "expiry_T": 0.25}
        r = client.post("/options/strategies/build", json=payload)
        assert r.status_code == 400

    def test_binomial_call(self):
        payload = {"spot": 100.0, "strike": 100.0, "expiry_T": 1.0, "option_type": "call"}
        r = client.post("/options/strategies/binomial", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["price"] > 0
        assert "greeks" in data

    def test_binomial_put(self):
        payload = {"spot": 100.0, "strike": 110.0, "expiry_T": 1.0, "option_type": "put"}
        r = client.post("/options/strategies/binomial", json=payload)
        assert r.status_code == 200
        assert r.json()["price"] > 0

    def test_binomial_american_flag(self):
        payload = {"spot": 100.0, "strike": 105.0, "expiry_T": 0.5, "option_type": "put", "american": True}
        r = client.post("/options/strategies/binomial", json=payload)
        assert r.status_code == 200
        assert r.json()["american"] is True

    def test_build_covered_call(self):
        payload = {"strategy": "covered_call", "spot": 150.0, "strike": 155.0, "expiry_T": 0.25}
        r = client.post("/options/strategies/build", json=payload)
        assert r.status_code == 200

    def test_build_butterfly(self):
        payload = {"strategy": "butterfly", "spot": 100.0, "strike": 100.0, "expiry_T": 0.5}
        r = client.post("/options/strategies/build", json=payload)
        assert r.status_code == 200
        assert len(r.json()["legs"]) == 3


# ---------------------------------------------------------------------------
# /backtest/walkforward
# ---------------------------------------------------------------------------

class TestWalkForwardRouter:
    PRICES = list(range(100, 260, 1))  # 160 prices

    def test_run_returns_windows(self):
        r = client.post("/backtest/walkforward/run", json={"prices": self.PRICES, "in_sample_size": 60, "out_sample_size": 20})
        assert r.status_code == 200
        assert "windows" in r.json()

    def test_sweep_returns_best_params(self):
        r = client.post("/backtest/walkforward/sweep", json={"prices": self.PRICES})
        assert r.status_code == 200
        data = r.json()
        assert "best_params" in data
        assert "top_5" in data

    def test_kelly_positive_edge(self):
        r = client.post("/backtest/walkforward/kelly", json={"win_prob": 0.6, "win_return": 0.1, "loss_return": 0.05})
        assert r.status_code == 200
        data = r.json()
        assert data["full_kelly"] > 0
        assert data["half_kelly"] < data["full_kelly"]

    def test_kelly_zero_edge(self):
        r = client.post("/backtest/walkforward/kelly", json={"win_prob": 0.5, "win_return": 0.1, "loss_return": 0.1})
        assert r.status_code == 200
        assert r.json()["full_kelly"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# /knowledge/v2
# ---------------------------------------------------------------------------

class TestKnowledgeV2Router:
    def test_stats(self):
        r = client.get("/knowledge/v2/stats")
        assert r.status_code == 200
        assert "entity_count" in r.json()

    def test_list_entities(self):
        r = client.get("/knowledge/v2/entities")
        assert r.status_code == 200
        assert "entities" in r.json()

    def test_create_entity(self):
        r = client.post("/knowledge/v2/entities", json={"id": "TEST_ROUTER", "entity_type": "company", "name": "Test Co"})
        assert r.status_code == 200
        assert r.json()["id"] == "TEST_ROUTER"

    def test_get_entity(self):
        client.post("/knowledge/v2/entities", json={"id": "GET_TEST", "entity_type": "concept", "name": "Test"})
        r = client.get("/knowledge/v2/entities/GET_TEST")
        assert r.status_code == 200

    def test_get_nonexistent(self):
        r = client.get("/knowledge/v2/entities/DOESNOTEXIST_XYZ")
        assert r.status_code == 404

    def test_search(self):
        r = client.get("/knowledge/v2/search?q=technology+cloud")
        assert r.status_code == 200
        assert "results" in r.json()

    def test_similar_companies(self):
        r = client.get("/knowledge/v2/similar/AAPL")
        assert r.status_code == 200
        assert "similar" in r.json()

    def test_clusters(self):
        r = client.get("/knowledge/v2/clusters?entity_type=company&n=3")
        assert r.status_code == 200
        assert "clusters" in r.json()


# ---------------------------------------------------------------------------
# /agents/research
# ---------------------------------------------------------------------------

class TestAgentsResearchRouter:
    def test_list_agents(self):
        r = client.get("/agents/research/agents")
        assert r.status_code == 200
        assert len(r.json()["agents"]) == 7

    def test_create_session(self):
        r = client.post("/agents/research/sessions", json={"topic": "router test topic", "tickers": ["AAPL"]})
        assert r.status_code == 200
        data = r.json()
        assert "id" in data

    def test_list_sessions(self):
        r = client.get("/agents/research/sessions")
        assert r.status_code == 200

    def test_get_session(self):
        create_r = client.post("/agents/research/sessions", json={"topic": "get test"})
        sid = create_r.json()["id"]
        r = client.get(f"/agents/research/sessions/{sid}")
        assert r.status_code == 200

    def test_get_nonexistent_session(self):
        r = client.get("/agents/research/sessions/fake-id-xyz")
        assert r.status_code == 404

    def test_single_agent_query(self):
        create_r = client.post("/agents/research/sessions", json={"topic": "test"})
        sid = create_r.json()["id"]
        r = client.post(f"/agents/research/sessions/{sid}/query",
                       json={"agent_type": "macro_economist", "query": "rate outlook"})
        assert r.status_code == 200
        data = r.json()
        assert data["agent_type"] == "macro_economist"
        assert "confidence" in data

    def test_invalid_agent_type(self):
        create_r = client.post("/agents/research/sessions", json={"topic": "test"})
        sid = create_r.json()["id"]
        r = client.post(f"/agents/research/sessions/{sid}/query",
                       json={"agent_type": "fake_agent", "query": "test"})
        assert r.status_code == 400

    def test_multi_agent_query(self):
        create_r = client.post("/agents/research/sessions", json={"topic": "multi test"})
        sid = create_r.json()["id"]
        r = client.post(f"/agents/research/sessions/{sid}/query/all",
                       json={"query": "market outlook"})
        assert r.status_code == 200
        assert len(r.json()["responses"]) == 7

    def test_synthesis(self):
        create_r = client.post("/agents/research/sessions", json={"topic": "synth"})
        sid = create_r.json()["id"]
        client.post(f"/agents/research/sessions/{sid}/query/all", json={"query": "test"})
        r = client.get(f"/agents/research/sessions/{sid}/synthesis")
        assert r.status_code == 200
        assert "recommendation" in r.json()

    def test_delete_session(self):
        create_r = client.post("/agents/research/sessions", json={"topic": "delete me"})
        sid = create_r.json()["id"]
        r = client.delete(f"/agents/research/sessions/{sid}")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# /execution/enhanced
# ---------------------------------------------------------------------------

class TestExecutionEnhancedRouter:
    def test_submit_market_order(self):
        r = client.post("/execution/enhanced/orders", json={
            "ticker": "AAPL", "side": "buy", "order_type": "market",
            "quantity": 100, "market_price": 175.0
        })
        assert r.status_code == 200
        assert r.json()["status"] == "filled"

    def test_submit_limit_order(self):
        r = client.post("/execution/enhanced/orders", json={
            "ticker": "MSFT", "side": "buy", "order_type": "limit",
            "quantity": 50, "limit_price": 300.0, "market_price": 350.0
        })
        assert r.status_code == 200
        assert r.json()["status"] == "open"

    def test_list_orders(self):
        r = client.get("/execution/enhanced/orders")
        assert r.status_code == 200
        assert "orders" in r.json()

    def test_list_orders_by_status(self):
        r = client.get("/execution/enhanced/orders?status=filled")
        assert r.status_code == 200

    def test_execution_reports(self):
        r = client.get("/execution/enhanced/reports")
        assert r.status_code == 200
        assert "reports" in r.json()

    def test_latency_stats(self):
        r = client.get("/execution/enhanced/latency")
        assert r.status_code == 200

    def test_order_book(self):
        r = client.get("/execution/enhanced/book?mid_price=150.0&spread_bps=5.0")
        assert r.status_code == 200
        data = r.json()
        assert data["best_ask"] > data["best_bid"]

    def test_cancel_order(self):
        create_r = client.post("/execution/enhanced/orders", json={
            "ticker": "AAPL", "side": "sell", "order_type": "limit",
            "quantity": 10, "limit_price": 200.0, "market_price": 170.0
        })
        oid = create_r.json()["order_id"]
        r = client.delete(f"/execution/enhanced/orders/{oid}")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# /auth/oauth
# ---------------------------------------------------------------------------

class TestOAuthRouter:
    def test_list_providers(self):
        r = client.get("/auth/oauth/providers")
        assert r.status_code == 200
        names = [p["name"] for p in r.json()["providers"]]
        assert "google" in names

    def test_authorize_google(self):
        r = client.get("/auth/oauth/authorize/google?redirect_uri=https://example.com/cb")
        assert r.status_code == 200
        data = r.json()
        assert "authorization_url" in data
        assert "state" in data

    def test_authorize_invalid_provider(self):
        r = client.get("/auth/oauth/authorize/twitter?redirect_uri=https://example.com/cb")
        assert r.status_code == 404

    def test_token_exchange(self):
        r = client.post("/auth/oauth/token", json={
            "provider": "google",
            "code": "test_code_123",
            "redirect_uri": "https://example.com/cb"
        })
        assert r.status_code == 200
        data = r.json()
        assert "tokens" in data
        assert "user" in data
        assert data["user"]["provider"] == "google"


# ---------------------------------------------------------------------------
# /observability
# ---------------------------------------------------------------------------

class TestObservabilityRouter:
    def test_slow_queries(self):
        r = client.get("/observability/slow-queries")
        assert r.status_code == 200
        data = r.json()
        assert "slow_queries" in data

    def test_error_summary(self):
        r = client.get("/observability/errors")
        assert r.status_code == 200
        assert "by_type" in r.json()

    def test_error_detail(self):
        r = client.get("/observability/errors/TestError")
        assert r.status_code == 200

    def test_traces(self):
        r = client.get("/observability/traces")
        assert r.status_code == 200
        assert "spans" in r.json()
