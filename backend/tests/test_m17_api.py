"""M17 API integration tests — all 35 endpoints via TestClient."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token"}


def get(path, **kwargs):
    return client.get(path, headers=AUTH, **kwargs)


def post(path, data, **kwargs):
    return client.post(path, json=data, headers=AUTH, **kwargs)


def delete(path, **kwargs):
    return client.delete(path, headers=AUTH, **kwargs)


# ---------------------------------------------------------------------------
# OMS endpoints
# ---------------------------------------------------------------------------

class TestOMSAPI:
    def test_submit_market_order(self):
        r = post("/trading/orders/submit", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "order_type": "MARKET"})
        assert r.status_code == 200
        data = r.json()
        assert "order_id" in data

    def test_submit_limit_order(self):
        r = post("/trading/orders/submit", {"ticker": "MSFT", "side": "BUY", "quantity": 50, "order_type": "LIMIT", "limit_price": 420.0})
        assert r.status_code == 200

    def test_submit_stop_order(self):
        r = post("/trading/orders/submit", {"ticker": "NVDA", "side": "SELL", "quantity": 100, "order_type": "STOP", "stop_price": 800.0})
        assert r.status_code == 200

    def test_get_all_orders(self):
        r = get("/trading/orders")
        assert r.status_code == 200
        assert "orders" in r.json()

    def test_get_open_orders(self):
        r = get("/trading/orders/open")
        assert r.status_code == 200
        assert "orders" in r.json()

    def test_order_summary(self):
        r = get("/trading/orders/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_orders" in data

    def test_cancel_valid_order(self):
        r = post("/trading/orders/submit", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "order_type": "LIMIT", "limit_price": 170.0})
        oid = r.json()["order_id"]
        r2 = post(f"/trading/orders/{oid}/cancel", {})
        assert r2.status_code == 200

    def test_record_fill(self):
        r = post("/trading/orders/submit", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "order_type": "MARKET"})
        oid = r.json()["order_id"]
        r2 = post(f"/trading/orders/{oid}/fill", {"quantity": 100, "price": 175.0})
        assert r2.status_code == 200

    def test_get_order_by_id(self):
        r = post("/trading/orders/submit", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "order_type": "MARKET"})
        oid = r.json()["order_id"]
        r2 = get(f"/trading/orders/{oid}")
        assert r2.status_code == 200

    def test_create_bracket(self):
        r = post("/trading/orders/bracket", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "take_profit_price": 185.0, "stop_loss_price": 165.0})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Execution endpoints
# ---------------------------------------------------------------------------

class TestExecutionAPI:
    def test_estimate_slippage(self):
        r = post("/trading/execution/slippage", {"order_quantity": 10000, "arrival_price": 175.0, "adv": 500000, "volatility": 0.02})
        assert r.status_code == 200
        assert "estimated_slippage_bps" in r.json()

    def test_estimate_market_impact(self):
        r = post("/trading/execution/market-impact", {"order_quantity": 10000, "adv": 500000, "price": 175.0, "volatility": 0.02})
        assert r.status_code == 200

    def test_simulate_fill(self):
        r = post("/trading/execution/simulate-fill", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "arrival_price": 175.0, "adv": 500000, "volatility": 0.02})
        assert r.status_code == 200
        assert "avg_fill_price" in r.json()

    def test_execution_quality(self):
        r = post("/trading/execution/quality", {"ticker": "AAPL", "side": "BUY", "avg_fill_price": 175.35, "benchmark_price": 175.0, "quantity": 500, "commission_usd": 2.5})
        assert r.status_code == 200
        assert "score" in r.json()


# ---------------------------------------------------------------------------
# Portfolio Accounting endpoints
# ---------------------------------------------------------------------------

class TestAccountingAPI:
    def test_deposit(self):
        r = post("/trading/accounting/deposit", {"amount": 1000000, "description": "Test"})
        assert r.status_code == 200

    def test_withdraw(self):
        post("/trading/accounting/deposit", {"amount": 1000000, "description": "Init"})
        r = post("/trading/accounting/withdraw", {"amount": 100000, "description": "Test withdraw"})
        assert r.status_code == 200

    def test_book_trade(self):
        r = post("/trading/accounting/book-trade", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "avg_price": 175.0, "commission": 2.5})
        assert r.status_code == 200

    def test_nav(self):
        r = post("/trading/accounting/nav", {"prices": {"AAPL": 175.0}})
        assert r.status_code == 200
        assert "nav" in r.json()

    def test_snapshot(self):
        r = post("/trading/accounting/snapshot", {"prices": {}})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Position Engine endpoints
# ---------------------------------------------------------------------------

class TestPositionsAPI:
    def test_open_position(self):
        r = post("/trading/positions/open", {"ticker": "AAPL", "quantity": 100, "price": 175.0})
        assert r.status_code == 200

    def test_close_position(self):
        post("/trading/positions/open", {"ticker": "AAPL", "quantity": 100, "price": 175.0})
        r = post("/trading/positions/close", {"ticker": "AAPL", "quantity": 100, "price": 180.0})
        assert r.status_code == 200

    def test_all_positions(self):
        r = post("/trading/positions/all", {"prices": {}})
        assert r.status_code == 200
        assert "positions" in r.json()

    def test_exposure_report(self):
        r = post("/trading/positions/exposure", {"prices": {"AAPL": 175.0}, "nav": 1000000})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Risk Limits endpoints
# ---------------------------------------------------------------------------

class TestRiskAPI:
    def test_get_limits(self):
        r = get("/trading/risk/limits")
        assert r.status_code == 200
        assert "limits" in r.json()

    def test_add_limit(self):
        r = post("/trading/risk/limits/add", {"limit_type": "MAX_ORDER_SIZE", "hard_limit": 500000.0, "description": "API test"})
        assert r.status_code == 200

    def test_pre_trade_check(self):
        r = post("/trading/risk/check", {"ticker": "AAPL", "side": "BUY", "quantity": 100, "price": 175.0, "nav": 1000000, "cash": 100000, "sector": "TECHNOLOGY", "gross_leverage": 1.0, "sector_weights": {"TECHNOLOGY": 0.25}})
        assert r.status_code == 200
        assert "result" in r.json()


# ---------------------------------------------------------------------------
# Trade Analytics endpoints
# ---------------------------------------------------------------------------

class TestAnalyticsAPI:
    def test_add_trade(self):
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        r = post("/trading/analytics/trades/add", {"trade_id": "API-T1", "ticker": "AAPL", "side": "BUY", "quantity": 100, "entry_price": 170.0, "exit_price": 180.0, "entry_datetime": now, "exit_datetime": now, "commission": 2.5, "pnl": 1000.0, "sector": "TECHNOLOGY"})
        assert r.status_code == 200

    def test_trade_statistics(self):
        r = get("/trading/analytics/trades/statistics")
        assert r.status_code == 200

    def test_portfolio_performance(self):
        r = post("/trading/analytics/portfolio-performance", {"returns": [0.01, 0.02, -0.005, 0.015], "periods_per_year": 252})
        assert r.status_code == 200
        assert "sharpe_ratio" in r.json()

    def test_kelly_fraction(self):
        r = post("/trading/analytics/kelly", {"win_rate": 0.6, "avg_win": 500.0, "avg_loss": 300.0})
        assert r.status_code == 200
        assert "kelly_fraction" in r.json()


# ---------------------------------------------------------------------------
# TCA endpoints
# ---------------------------------------------------------------------------

class TestTCAAPI:
    def test_record_tca_trade(self):
        r = post("/trading/tca/record", {"trade_id": "API-TCA1", "ticker": "AAPL", "side": "BUY", "quantity": 1000, "arrival_price": 175.0, "avg_fill_price": 175.35, "commission_usd": 5.0, "spread_bps": 4.0, "broker_id": "GS"})
        assert r.status_code == 200

    def test_analyse_tca(self):
        r = post("/trading/tca/analyse", {"trade_id": "API-TCA2", "ticker": "AAPL", "side": "BUY", "quantity": 1000, "decision_price": 175.0, "arrival_price": 175.0, "avg_fill_price": 175.35, "commission_usd": 5.0, "spread_bps": 4.0, "benchmark_price": 175.0})
        assert r.status_code == 200

    def test_tca_report(self):
        r = get("/trading/tca/report")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Broker Management endpoints
# ---------------------------------------------------------------------------

class TestBrokerAPI:
    def test_register_broker(self):
        r = post("/trading/brokers/register", {"name": "API Test Broker", "supported_asset_classes": ["EQUITY"], "supported_exchanges": ["NYSE"]})
        assert r.status_code == 200
        assert "broker_id" in r.json()

    def test_get_all_brokers(self):
        r = get("/trading/brokers")
        assert r.status_code == 200
        assert "brokers" in r.json()

    def test_broker_statistics(self):
        r = get("/trading/brokers/statistics")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Paper Trading endpoints
# ---------------------------------------------------------------------------

class TestPaperTradingAPI:
    def test_update_prices(self):
        r = post("/trading/paper/prices", {"prices": {"AAPL": 175.0, "MSFT": 420.0}})
        assert r.status_code == 200

    def test_market_order(self):
        post("/trading/paper/prices", {"prices": {"AAPL": 175.0}})
        r = post("/trading/paper/market-order", {"ticker": "AAPL", "side": "BUY", "quantity": 100})
        assert r.status_code == 200

    def test_paper_account(self):
        r = get("/trading/paper/account")
        assert r.status_code == 200

    def test_paper_positions(self):
        r = get("/trading/paper/positions")
        assert r.status_code == 200

    def test_paper_fills(self):
        r = get("/trading/paper/fills")
        assert r.status_code == 200

    def test_paper_reset(self):
        r = post("/trading/paper/reset", {})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Performance Attribution endpoints
# ---------------------------------------------------------------------------

class TestAttributionAPI:
    def test_brinson_attribution(self):
        holdings = [
            {"category": "Technology", "portfolio_weight": 0.25, "benchmark_weight": 0.20, "portfolio_return": 0.08, "benchmark_return": 0.05},
            {"category": "Financials", "portfolio_weight": 0.75, "benchmark_weight": 0.80, "portfolio_return": 0.05, "benchmark_return": 0.04},
        ]
        bench_return = sum(h["benchmark_weight"] * h["benchmark_return"] for h in holdings)
        r = post("/trading/attribution/brinson", {"holdings": holdings, "benchmark_total_return": bench_return, "model": "BRINSON"})
        assert r.status_code == 200
        data = r.json()
        assert "active_return" in data

    def test_factor_attribution(self):
        factors = [
            {"factor_name": "Market", "portfolio_exposure": 1.05, "benchmark_exposure": 1.00, "factor_return": 0.04},
            {"factor_name": "Value", "portfolio_exposure": 0.20, "benchmark_exposure": 0.00, "factor_return": 0.01},
        ]
        r = post("/trading/attribution/factor", {"factors": factors})
        assert r.status_code == 200
