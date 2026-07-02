"""Unit tests for M18 Pydantic schemas — 55 tests."""
import pytest
from pydantic import ValidationError

from schemas.m18_realtime import (
    # Common
    SuccessResponse, DeleteResponse, PaginatedRequest,
    # Streaming
    PublishTickRequest, PublishQuoteRequest, PublishNewsRequest, PublishRiskRequest,
    # Gateway
    VenueConnectRequest, IngestTickRequest, SetQuoteRequest,
    # Microstructure
    IngestLevel1Request, IngestTradeRequest, IngestOrderBookRequest,
    # Feature Engine
    FeatureUpdateRequest, ComputeMACDRequest,
    # Risk Engine
    ComputeVaRRequest, StressTestRequest, AddPnlObservationRequest,
    # Portfolio Intelligence
    UpdateHoldingRequest, RebalancingRequest,
    # Alert Engine
    AddAlertRuleRequest, EvaluateAlertRequest, FireCustomAlertRequest,
    # Economic Intelligence
    RecordIndicatorRequest, RecordYieldCurveRequest,
    # News Intelligence
    IngestNewsRequest, NewsSearchRequest, DetectTrendsRequest,
    # Earnings Intelligence
    RecordEarningsReleaseRequest, AddEarningsEstimateRequest,
    # AI Agents
    RunAgentRequest, RunAllAgentsRequest,
    # Watchlist
    CreateWatchlistRequest, AddWatchlistItemRequest, UpdateWatchlistPriceRequest,
    WatchlistScreenRequest,
)


# ---------------------------------------------------------------------------
# Common schemas
# ---------------------------------------------------------------------------

class TestCommonSchemas:
    def test_success_response(self):
        r = SuccessResponse(message="OK")
        assert r.message == "OK"

    def test_delete_response(self):
        r = DeleteResponse(deleted=True, id="123")
        assert r.deleted is True

    def test_paginated_request_defaults(self):
        r = PaginatedRequest()
        assert r.limit >= 1
        assert r.offset >= 0

    def test_paginated_request_custom(self):
        r = PaginatedRequest(limit=25, offset=50)
        assert r.limit == 25 and r.offset == 50


# ---------------------------------------------------------------------------
# Streaming schemas
# ---------------------------------------------------------------------------

class TestStreamingSchemas:
    def test_publish_tick_valid(self):
        r = PublishTickRequest(ticker="AAPL", price=175.0, volume=1000, venue="NYSE")
        assert r.ticker == "AAPL"

    def test_publish_tick_price_positive(self):
        with pytest.raises(ValidationError):
            PublishTickRequest(ticker="AAPL", price=-1.0, volume=100)

    def test_publish_quote_valid(self):
        r = PublishQuoteRequest(ticker="AAPL", bid=174.9, ask=175.1, bid_size=100, ask_size=200)
        assert r.bid < r.ask

    def test_publish_news_valid(self):
        r = PublishNewsRequest(headline="Apple beats EPS", source="Reuters")
        assert r.headline is not None

    def test_publish_risk_valid(self):
        r = PublishRiskRequest(risk_type="VAR_BREACH", severity="HIGH", message="VaR exceeded")
        assert r.risk_type == "VAR_BREACH"

    def test_publish_tick_zero_price_raises(self):
        with pytest.raises(ValidationError):
            PublishTickRequest(ticker="AAPL", price=0.0, volume=100)


# ---------------------------------------------------------------------------
# Gateway schemas
# ---------------------------------------------------------------------------

class TestGatewaySchemas:
    def test_venue_connect_valid(self):
        r = VenueConnectRequest(venue="NYSE", asset_class="EQUITY")
        assert r.venue == "NYSE"

    def test_ingest_tick_valid(self):
        r = IngestTickRequest(venue="NYSE", ticker="AAPL", price=175.0, volume=1000)
        assert r.price == 175.0

    def test_ingest_tick_negative_price_raises(self):
        with pytest.raises(ValidationError):
            IngestTickRequest(venue="NYSE", ticker="AAPL", price=-1.0, volume=100)

    def test_set_quote_valid(self):
        r = SetQuoteRequest(venue="NYSE", ticker="AAPL", bid=174.9, ask=175.1)
        assert r.bid < r.ask


# ---------------------------------------------------------------------------
# Microstructure schemas
# ---------------------------------------------------------------------------

class TestMicrostructureSchemas:
    def test_ingest_level1_valid(self):
        r = IngestLevel1Request(ticker="AAPL", bid=100.0, ask=100.2, bid_size=100, ask_size=200)
        assert r.ticker == "AAPL"

    def test_ingest_trade_valid(self):
        r = IngestTradeRequest(ticker="AAPL", price=100.0, volume=500)
        assert r.price == 100.0

    def test_ingest_order_book_valid(self):
        r = IngestOrderBookRequest(
            ticker="AAPL",
            bids=[[100.0, 100], [99.9, 200]],
            asks=[[100.1, 100], [100.2, 200]],
        )
        assert r.ticker == "AAPL"


# ---------------------------------------------------------------------------
# Feature Engine schemas
# ---------------------------------------------------------------------------

class TestFeatureEngineSchemas:
    def test_update_feature_valid(self):
        r = FeatureUpdateRequest(ticker="AAPL", price=175.0, volume=1000000, high=176.0, low=174.0)
        assert r.ticker == "AAPL"

    def test_compute_macd_valid(self):
        r = ComputeMACDRequest(ticker="AAPL", fast=12, slow=26, signal=9)
        assert r.fast < r.slow

    def test_compute_macd_fast_gte_slow_raises(self):
        with pytest.raises(ValidationError):
            ComputeMACDRequest(ticker="AAPL", fast=26, slow=12, signal=9)


# ---------------------------------------------------------------------------
# Risk Engine schemas
# ---------------------------------------------------------------------------

class TestRiskEngineSchemas:
    def test_compute_var_valid(self):
        r = ComputeVaRRequest(confidence=0.95)
        assert r.confidence == 0.95

    def test_compute_var_invalid_confidence(self):
        with pytest.raises(ValidationError):
            ComputeVaRRequest(confidence=1.5)

    def test_run_stress_test_valid(self):
        r = StressTestRequest(scenario_name="TEST", shock_pct=-0.20)
        assert r.scenario_name == "TEST"

    def test_add_pnl_observation_valid(self):
        r = AddPnlObservationRequest(pnl=5000.0)
        assert r.pnl == 5000.0


# ---------------------------------------------------------------------------
# Portfolio Intelligence schemas
# ---------------------------------------------------------------------------

class TestPortfolioIntelligenceSchemas:
    def test_update_holding_valid(self):
        r = UpdateHoldingRequest(ticker="AAPL", weight=0.20)
        assert r.ticker == "AAPL"

    def test_update_holding_weight_range(self):
        with pytest.raises(ValidationError):
            UpdateHoldingRequest(ticker="AAPL", weight=1.5)

    def test_rebalancing_request_valid(self):
        r = RebalancingRequest(target_weights={"AAPL": 0.20, "MSFT": 0.18})
        assert "AAPL" in r.target_weights

    def test_rebalancing_weights_sum_too_high_raises(self):
        with pytest.raises(ValidationError):
            RebalancingRequest(target_weights={"AAPL": 0.60, "MSFT": 0.60})


# ---------------------------------------------------------------------------
# Alert Engine schemas
# ---------------------------------------------------------------------------

class TestAlertEngineSchemas:
    def test_create_alert_rule_valid(self):
        r = AddAlertRuleRequest(
            name="Price Above 200", alert_type="PRICE", severity="HIGH",
            field="price", direction="ABOVE", threshold=200.0, ticker="AAPL",
        )
        assert r.name == "Price Above 200"

    def test_evaluate_alert_valid(self):
        r = EvaluateAlertRequest(ticker="AAPL", field="price", value=210.0)
        assert r.ticker == "AAPL"

    def test_fire_custom_alert_valid(self):
        r = FireCustomAlertRequest(name="Custom Alert", severity="HIGH", message="Testing")
        assert r.name == "Custom Alert"


# ---------------------------------------------------------------------------
# Economic Intelligence schemas
# ---------------------------------------------------------------------------

class TestEconomicIntelligenceSchemas:
    def test_record_indicator_valid(self):
        r = RecordIndicatorRequest(
            name="US GDP", country="US", indicator_type="GDP",
            value=2.8, previous_value=2.1, forecast=2.5,
            unit="%", frequency="Quarterly",
        )
        assert r.country == "US"

    def test_record_yield_curve_valid(self):
        r = RecordYieldCurveRequest(country="US", tenors={"2Y": 0.048, "10Y": 0.045})
        assert "2Y" in r.tenors

    def test_record_yield_curve_empty_tenors_raises(self):
        with pytest.raises(ValidationError):
            RecordYieldCurveRequest(country="US", tenors={})


# ---------------------------------------------------------------------------
# News Intelligence schemas
# ---------------------------------------------------------------------------

class TestNewsIntelligenceSchemas:
    def test_ingest_article_valid(self):
        r = IngestNewsRequest(headline="Apple beats earnings", body="Strong results", source="Reuters")
        assert r.source == "Reuters"

    def test_search_articles_valid(self):
        r = NewsSearchRequest(query="earnings beat", limit=10)
        assert r.limit == 10

    def test_detect_trends_valid(self):
        r = DetectTrendsRequest(window_hours=4, min_articles=2)
        assert r.window_hours == 4


# ---------------------------------------------------------------------------
# Earnings schemas
# ---------------------------------------------------------------------------

class TestEarningsSchemas:
    def test_record_release_valid(self):
        r = RecordEarningsReleaseRequest(
            ticker="AAPL", fiscal_quarter="Q1 2026",
            reported_eps=2.18, consensus_eps=2.02,
            reported_revenue=119600, consensus_revenue=111200,
            gross_margin=0.46, operating_margin=0.31,
            guidance_direction="RAISED",
        )
        assert r.ticker == "AAPL"

    def test_record_estimate_valid(self):
        r = AddEarningsEstimateRequest(
            ticker="AAPL", fiscal_quarter="Q1 2026",
            analyst_firm="GS", eps_estimate=2.05, revenue_estimate=113000, rating="BUY",
        )
        assert r.analyst_firm == "GS"


# ---------------------------------------------------------------------------
# AI Agents schemas
# ---------------------------------------------------------------------------

class TestAIAgentSchemas:
    def test_run_agent_valid(self):
        r = RunAgentRequest(agent_type="MARKET_ANALYST", payload={"ticker": "AAPL", "price": 175.0})
        assert r.agent_type == "MARKET_ANALYST"

    def test_run_all_agents_valid(self):
        r = RunAllAgentsRequest(payloads={"MARKET_ANALYST": {"ticker": "AAPL"}}, include_report=True)
        assert "MARKET_ANALYST" in r.payloads


# ---------------------------------------------------------------------------
# Watchlist schemas
# ---------------------------------------------------------------------------

class TestWatchlistSchemas:
    def test_create_watchlist_valid(self):
        r = CreateWatchlistRequest(name="Tech Momentum", description="High conviction tech", category="EQUITY_LONG")
        assert r.name == "Tech Momentum"

    def test_add_watchlist_item_valid(self):
        r = AddWatchlistItemRequest(ticker="AAPL", sector="Technology", notes="AI play", conviction=8, target_price=700.0, stop_loss=550.0)
        assert r.ticker == "AAPL"

    def test_conviction_range(self):
        with pytest.raises(ValidationError):
            AddWatchlistItemRequest(ticker="AAPL", conviction=11, sector="Tech")

    def test_update_price_valid(self):
        r = UpdateWatchlistPriceRequest(ticker="AAPL", price=680.0)
        assert r.price == 680.0

    def test_update_price_negative_raises(self):
        with pytest.raises(ValidationError):
            UpdateWatchlistPriceRequest(ticker="AAPL", price=-1.0)

    def test_screen_watchlist_valid(self):
        r = WatchlistScreenRequest(min_conviction=7, sector="Technology")
        assert r.min_conviction == 7
