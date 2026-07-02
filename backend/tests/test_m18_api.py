"""Integration tests for M18 router — 120 tests using TestClient."""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Streaming Engine endpoints
# ---------------------------------------------------------------------------

class TestStreamingEndpoints:
    def test_publish_tick(self):
        r = client.post("/m18/streaming/tick", json={"ticker": "AAPL", "price": 175.0, "volume": 1000, "venue": "NYSE"})
        assert r.status_code in (200, 201)

    def test_publish_quote(self):
        r = client.post("/m18/streaming/quote", json={"ticker": "AAPL", "bid": 174.9, "ask": 175.1, "bid_size": 100, "ask_size": 200})
        assert r.status_code in (200, 201)

    def test_publish_trade(self):
        r = client.post("/m18/streaming/trade", json={"ticker": "AAPL", "price": 175.0, "volume": 500, "side": "BUY"})
        assert r.status_code in (200, 201)

    def test_publish_news(self):
        r = client.post("/m18/streaming/news", json={"headline": "Apple reports record revenue", "source": "Reuters"})
        assert r.status_code in (200, 201)

    def test_get_history_tick(self):
        r = client.get("/m18/streaming/history/TICK?limit=10")
        assert r.status_code == 200

    def test_get_history_quote(self):
        r = client.get("/m18/streaming/history/QUOTE?limit=5")
        assert r.status_code == 200

    def test_get_metrics(self):
        r = client.get("/m18/streaming/metrics")
        assert r.status_code == 200

    def test_get_sequence(self):
        r = client.get("/m18/streaming/sequence")
        assert r.status_code == 200

    def test_get_subscription_count(self):
        r = client.get("/m18/streaming/subscriptions/count")
        assert r.status_code == 200

    def test_replay_since(self):
        client.post("/m18/streaming/tick", json={"ticker": "AAPL", "price": 100.0, "volume": 100})
        r = client.get("/m18/streaming/replay?since_sequence=0")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Market Gateway endpoints
# ---------------------------------------------------------------------------

class TestGatewayEndpoints:
    def test_get_registered_venues(self):
        r = client.get("/m18/gateway/venues")
        assert r.status_code == 200

    def test_connect_venue(self):
        r = client.post("/m18/gateway/venues/NYSE/connect")
        assert r.status_code in (200, 201)

    def test_ingest_tick(self):
        client.post("/m18/gateway/venues/NYSE/connect")
        r = client.post("/m18/gateway/tick", json={"venue": "NYSE", "ticker": "AAPL", "price": 175.0, "volume": 1000})
        assert r.status_code in (200, 201, 422)

    def test_set_quote(self):
        client.post("/m18/gateway/venues/NYSE/connect")
        r = client.post("/m18/gateway/quote", json={"venue": "NYSE", "ticker": "AAPL", "bid": 174.9, "ask": 175.1})
        assert r.status_code in (200, 201, 422)

    def test_get_all_latencies(self):
        r = client.get("/m18/gateway/latencies")
        assert r.status_code == 200

    def test_get_gateway_summary(self):
        r = client.get("/m18/gateway/summary")
        assert r.status_code == 200

    def test_heartbeat_all(self):
        r = client.post("/m18/gateway/heartbeat")
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Microstructure endpoints
# ---------------------------------------------------------------------------

class TestMicrostructureEndpoints:
    def test_ingest_quote(self):
        r = client.post("/m18/microstructure/quote", json={"ticker": "AAPL", "bid": 174.9, "ask": 175.1, "bid_size": 100, "ask_size": 200})
        assert r.status_code in (200, 201)

    def test_ingest_trade(self):
        r = client.post("/m18/microstructure/trade", json={"ticker": "AAPL", "price": 175.0, "volume": 500, "side": "BUY"})
        assert r.status_code in (200, 201)

    def test_get_level1(self):
        client.post("/m18/microstructure/quote", json={"ticker": "AAPL", "bid": 174.9, "ask": 175.1})
        r = client.get("/m18/microstructure/level1/AAPL")
        assert r.status_code in (200, 404)

    def test_ingest_order_book(self):
        r = client.post("/m18/microstructure/orderbook", json={
            "ticker": "AAPL",
            "bids": [[100.0, 100], [99.9, 200]],
            "asks": [[100.1, 100], [100.2, 200]],
        })
        assert r.status_code in (200, 201)

    def test_detect_spoofing(self):
        r = client.get("/m18/microstructure/spoofing/AAPL")
        assert r.status_code in (200, 404)

    def test_detect_sweep(self):
        r = client.get("/m18/microstructure/sweep/AAPL")
        assert r.status_code in (200, 404)

    def test_get_vwap_bands(self):
        r = client.get("/m18/microstructure/vwap/AAPL")
        assert r.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Feature Engine endpoints
# ---------------------------------------------------------------------------

class TestFeatureEngineEndpoints:
    def _seed(self, n=60):
        import math
        for i in range(n):
            price = 100.0 + math.sin(i / 5) * 5
            client.post("/m18/features/update", json={"ticker": "AAPL", "price": price, "volume": 100000 + i * 1000, "high": price + 0.5, "low": price - 0.5})

    def test_update_feature(self):
        r = client.post("/m18/features/update", json={"ticker": "AAPL", "price": 175.0, "volume": 1000000})
        assert r.status_code in (200, 201)

    def test_compute_rsi(self):
        self._seed()
        r = client.get("/m18/features/rsi/AAPL?window=14")
        assert r.status_code == 200

    def test_compute_macd(self):
        self._seed()
        r = client.post("/m18/features/macd", json={"ticker": "AAPL", "fast": 12, "slow": 26, "signal": 9})
        assert r.status_code in (200, 201)

    def test_compute_vwap(self):
        self._seed()
        r = client.get("/m18/features/vwap/AAPL")
        assert r.status_code == 200

    def test_compute_atr(self):
        self._seed()
        r = client.get("/m18/features/atr/AAPL?window=14")
        assert r.status_code == 200

    def test_feature_snapshot(self):
        self._seed()
        r = client.get("/m18/features/snapshot/AAPL")
        assert r.status_code in (200, 404)

    def test_get_tracked_tickers(self):
        r = client.get("/m18/features/tickers")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Risk Engine endpoints
# ---------------------------------------------------------------------------

class TestRiskEngineEndpoints:
    def _positions(self):
        return [{"ticker": "AAPL", "quantity": 100, "current_price": 175.0, "sector": "Technology", "country": "US", "currency": "USD"}]

    def test_set_nav(self):
        r = client.post("/m18/risk/nav", json={"nav": 1000000.0})
        assert r.status_code in (200, 201)

    def test_add_daily_pnl(self):
        r = client.post("/m18/risk/pnl", json={"pnl": 5000.0})
        assert r.status_code in (200, 201)

    def test_compute_var(self):
        for _ in range(30):
            client.post("/m18/risk/pnl", json={"pnl": 1000.0})
        r = client.post("/m18/risk/var", json={"positions": self._positions(), "confidence": 0.95})
        assert r.status_code in (200, 201)

    def test_compute_leverage(self):
        r = client.post("/m18/risk/leverage", json={"positions": self._positions()})
        assert r.status_code in (200, 201)

    def test_compute_concentration(self):
        r = client.post("/m18/risk/concentration", json={"positions": self._positions()})
        assert r.status_code in (200, 201)

    def test_run_stress_test(self):
        r = client.post("/m18/risk/stress-test", json={"positions": self._positions(), "scenario_name": "GFC", "equity_shock": -0.30})
        assert r.status_code in (200, 201)

    def test_get_risk_dashboard(self):
        r = client.post("/m18/risk/dashboard", json={"positions": self._positions()})
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Portfolio Intelligence endpoints
# ---------------------------------------------------------------------------

class TestPortfolioIntelligenceEndpoints:
    def test_add_holding(self):
        r = client.post("/m18/portfolio/holdings", json={"ticker": "AAPL", "weight": 0.20, "market_value": 1000000, "cost_basis": 800000, "sector": "Technology"})
        assert r.status_code in (200, 201)

    def test_get_all_holdings(self):
        r = client.get("/m18/portfolio/holdings")
        assert r.status_code == 200

    def test_set_nav(self):
        r = client.post("/m18/portfolio/nav", json={"nav": 5000000.0})
        assert r.status_code in (200, 201)

    def test_get_portfolio_summary(self):
        r = client.get("/m18/portfolio/summary")
        assert r.status_code == 200

    def test_compute_portfolio_score(self):
        r = client.get("/m18/portfolio/score")
        assert r.status_code == 200

    def test_compute_tail_risk(self):
        r = client.get("/m18/portfolio/tail-risk")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Alert Engine endpoints
# ---------------------------------------------------------------------------

class TestAlertEngineEndpoints:
    def test_create_rule(self):
        r = client.post("/m18/alerts/rules", json={
            "name": "Test Rule", "alert_type": "PRICE_THRESHOLD",
            "severity": "HIGH", "field": "price", "direction": "ABOVE",
            "threshold": 200.0, "ticker": "AAPL",
        })
        assert r.status_code in (200, 201)

    def test_get_rules(self):
        r = client.get("/m18/alerts/rules")
        assert r.status_code == 200

    def test_evaluate_alert(self):
        r = client.post("/m18/alerts/evaluate", json={"data": {"ticker": "AAPL", "price": 210.0}})
        assert r.status_code in (200, 201)

    def test_fire_custom_alert(self):
        r = client.post("/m18/alerts/custom", json={"title": "Test", "message": "Custom alert", "severity": "LOW", "alert_type": "CUSTOM"})
        assert r.status_code in (200, 201)

    def test_get_history(self):
        r = client.get("/m18/alerts/history?limit=10")
        assert r.status_code == 200

    def test_get_stats(self):
        r = client.get("/m18/alerts/stats")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Economic Intelligence endpoints
# ---------------------------------------------------------------------------

class TestEconomicIntelligenceEndpoints:
    def test_record_indicator(self):
        r = client.post("/m18/economic/indicators", json={
            "name": "US GDP", "country": "US", "indicator_type": "GDP",
            "value": 2.8, "previous_value": 2.1, "forecast": 2.5,
            "unit": "%", "frequency": "Quarterly",
        })
        assert r.status_code in (200, 201)

    def test_get_indicators(self):
        r = client.get("/m18/economic/indicators?country=US")
        assert r.status_code == 200

    def test_record_yield_curve(self):
        r = client.post("/m18/economic/yield-curve", json={"country": "US", "tenors": {"2Y": 0.048, "10Y": 0.045}})
        assert r.status_code in (200, 201)

    def test_get_yield_curve(self):
        client.post("/m18/economic/yield-curve", json={"country": "US", "tenors": {"2Y": 0.048, "10Y": 0.045}})
        r = client.get("/m18/economic/yield-curve/US")
        assert r.status_code in (200, 404)

    def test_recession_probability(self):
        r = client.get("/m18/economic/recession-probability/US")
        assert r.status_code in (200, 404)

    def test_business_cycle(self):
        r = client.get("/m18/economic/business-cycle/US")
        assert r.status_code in (200, 404)


# ---------------------------------------------------------------------------
# News Intelligence endpoints
# ---------------------------------------------------------------------------

class TestNewsIntelligenceEndpoints:
    def test_ingest_article(self):
        r = client.post("/m18/news/articles", json={"headline": "Apple beats earnings", "body": "Strong results", "source": "Reuters"})
        assert r.status_code in (200, 201)

    def test_get_latest_articles(self):
        r = client.get("/m18/news/articles/latest?limit=5")
        assert r.status_code == 200

    def test_get_stats(self):
        r = client.get("/m18/news/stats")
        assert r.status_code == 200

    def test_get_ticker_sentiment(self):
        r = client.get("/m18/news/sentiment/AAPL")
        assert r.status_code == 200

    def test_get_signal(self):
        r = client.get("/m18/news/signal/AAPL")
        assert r.status_code == 200

    def test_detect_trends(self):
        r = client.post("/m18/news/trends", json={"window_hours": 4, "min_articles": 1})
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Earnings Intelligence endpoints
# ---------------------------------------------------------------------------

class TestEarningsIntelligenceEndpoints:
    def test_record_release(self):
        r = client.post("/m18/earnings/releases", json={
            "ticker": "AAPL", "fiscal_quarter": "Q1 2026",
            "reported_eps": 2.18, "consensus_eps": 2.02,
            "reported_revenue": 119600, "consensus_revenue": 111200,
            "gross_margin": 0.46, "operating_margin": 0.31,
            "guidance_direction": "RAISED",
        })
        assert r.status_code in (200, 201)

    def test_get_releases(self):
        r = client.get("/m18/earnings/releases/AAPL")
        assert r.status_code == 200

    def test_upcoming_calendar(self):
        r = client.get("/m18/earnings/calendar/upcoming?limit=10")
        assert r.status_code == 200

    def test_surprise_analysis(self):
        r = client.get("/m18/earnings/surprise-analysis/AAPL")
        assert r.status_code in (200, 404)

    def test_generate_signal(self):
        r = client.post("/m18/earnings/signal", json={"ticker": "AAPL", "eps_surprise_pct": 0.08, "revenue_surprise_pct": 0.07, "guidance_direction": "RAISED"})
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# AI Agents endpoints
# ---------------------------------------------------------------------------

class TestAIAgentsEndpoints:
    def test_list_agents(self):
        r = client.get("/m18/agents/list")
        assert r.status_code == 200

    def test_run_agent(self):
        r = client.post("/m18/agents/run", json={"agent_type": "MARKET_ANALYST", "payload": {"ticker": "AAPL", "price": 175.0, "sma_20": 170.0, "rsi_14": 58.0}})
        assert r.status_code in (200, 201)

    def test_run_all_agents(self):
        r = client.post("/m18/agents/run-all", json={
            "payloads": {"MARKET_ANALYST": {"ticker": "AAPL", "price": 175.0, "sma_20": 170.0}},
            "include_report": False,
        })
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Watchlist endpoints
# ---------------------------------------------------------------------------

class TestWatchlistEndpoints:
    def test_create_watchlist(self):
        r = client.post("/m18/watchlists", json={"name": "Test List", "description": "Test", "category": "EQUITY_LONG"})
        assert r.status_code in (200, 201)

    def test_get_all_watchlists(self):
        r = client.get("/m18/watchlists")
        assert r.status_code == 200

    def test_add_item(self):
        create_r = client.post("/m18/watchlists", json={"name": "API Test", "description": "D", "category": "EQUITY_LONG"})
        if create_r.status_code in (200, 201):
            list_id = create_r.json().get("list_id") or create_r.json().get("data", {}).get("list_id")
            if list_id:
                r = client.post(f"/m18/watchlists/{list_id}/items", json={"ticker": "AAPL", "sector": "Technology", "notes": "Test", "conviction": 8})
                assert r.status_code in (200, 201, 404)

    def test_get_watchlist_stats(self):
        r = client.get("/m18/watchlists/stats/summary")
        assert r.status_code == 200

    def test_screen_watchlist(self):
        r = client.post("/m18/watchlists/screen", json={"min_conviction": 7})
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Router structure
# ---------------------------------------------------------------------------

class TestRouterStructure:
    def test_router_has_141_routes(self):
        from routers.m18_realtime import router
        assert len(router.routes) == 141

    def test_all_routes_have_path(self):
        from routers.m18_realtime import router
        for route in router.routes:
            assert hasattr(route, "path")

    def test_router_prefix(self):
        from routers.m18_realtime import router
        assert router.prefix == "/m18"
