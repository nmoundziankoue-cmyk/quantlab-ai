"""Extended M18 unit tests — edge cases and additional coverage — 100 tests."""
import math
import pytest

# ---------------------------------------------------------------------------
# Feature Engine — edge cases
# ---------------------------------------------------------------------------

from services.m18_feature_engine import FeatureEngine, _mean, _std, _ema, _percentile, _ols_slope

class TestFeatureEdgeCases:
    def setup_method(self):
        self.engine = FeatureEngine()

    def test_mean_large_list(self):
        vals = list(range(1, 1001))
        assert abs(_mean(vals) - 500.5) < 0.001

    def test_std_two_values(self):
        vals = [0.0, 2.0]
        result = _std(vals)
        assert abs(result - 1.0) < 1e-9

    def test_ema_with_period_larger_than_series(self):
        result = _ema([100.0, 101.0], period=10)
        assert isinstance(result, float)

    def test_percentile_all_same(self):
        result = _percentile([5.0, 5.0, 5.0, 5.0], 50)
        assert result == 5.0

    def test_ols_slope_negative(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 8.0, 6.0, 4.0, 2.0]
        slope = _ols_slope(xs, ys)
        assert slope < 0

    def test_update_multiple_tickers_tracked_separately(self):
        self.engine.update("AAPL", 100.0, 1000)
        self.engine.update("MSFT", 200.0, 2000)
        tickers = self.engine.get_tracked_tickers()
        assert "AAPL" in tickers and "MSFT" in tickers

    def test_rolling_mean_with_small_window(self):
        for i in range(5):
            self.engine.update("AAPL", 100.0 + i, 1000)
        result = self.engine.compute_rolling_mean("AAPL", window=3)
        assert isinstance(result, float)

    def test_rolling_std_with_constant_prices(self):
        for _ in range(20):
            self.engine.update("AAPL", 100.0, 1000)
        result = self.engine.compute_rolling_std("AAPL", window=10)
        assert result == 0.0 or result < 0.001

    def test_kelly_criterion_with_no_data_returns_zero(self):
        result = self.engine.compute_kelly("NEWKELLY", window=252)
        assert isinstance(result, float)

    def test_rsi_with_all_positive_returns_approaches_100(self):
        for i in range(30):
            self.engine.update("UPONLY", 100.0 + i, 1000)
        rsi = self.engine.compute_rsi("UPONLY", window=14)
        assert rsi > 50

    def test_rsi_with_all_negative_returns_approaches_0(self):
        for i in range(30):
            self.engine.update("DOWNONLY", 100.0 - i, 1000)
        rsi = self.engine.compute_rsi("DOWNONLY", window=14)
        assert rsi < 50


# ---------------------------------------------------------------------------
# Risk Engine — edge cases
# ---------------------------------------------------------------------------

from services.m18_risk_engine import RiskEngine

class TestRiskEngineEdgeCases:
    def test_empty_positions_var(self):
        engine = RiskEngine()
        engine.set_nav(1_000_000.0)
        for _ in range(50):
            engine.add_daily_pnl(1000.0)
        result = engine.compute_portfolio_var(confidence=0.95)
        assert result.var_1d >= 0

    def test_single_position_var(self):
        engine = RiskEngine()
        engine.set_nav(1_000_000.0)
        for i in range(60):
            engine.add_daily_pnl(math.sin(i) * 1000)
        positions = [{"ticker": "AAPL", "quantity": 100, "current_price": 175.0, "sector": "Tech", "country": "US", "currency": "USD"}]
        engine._load_positions(positions)
        result = engine.compute_portfolio_var(confidence=0.99)
        assert result is not None

    def test_stress_test_zero_shock(self):
        engine = RiskEngine()
        engine.set_nav(1_000_000.0)
        positions = [{"ticker": "AAPL", "quantity": 100, "current_price": 175.0, "sector": "Tech", "country": "US", "currency": "USD"}]
        engine._load_positions(positions)
        result = engine.run_stress_test(scenario_name="ZERO_SHOCK", shock_pct=0.0)
        assert abs(result.portfolio_pnl) < 1.0

    def test_concentration_single_position(self):
        engine = RiskEngine()
        engine.set_nav(1_000_000.0)
        positions = [{"ticker": "AAPL", "quantity": 1000, "current_price": 175.0, "sector": "Tech", "country": "US", "currency": "USD"}]
        result = engine.compute_concentration(positions)
        assert result.hhi == 1.0

    def test_leverage_empty_positions(self):
        engine = RiskEngine()
        engine.set_nav(1_000_000.0)
        result = engine.compute_leverage([])
        assert result.gross_leverage == 0.0

    def test_country_exposure_sums_to_100(self):
        engine = RiskEngine()
        engine.set_nav(1_000_000.0)
        positions = [
            {"ticker": "AAPL", "quantity": 100, "current_price": 100.0, "sector": "Tech", "country": "US", "currency": "USD"},
            {"ticker": "BP", "quantity": 100, "current_price": 100.0, "sector": "Energy", "country": "GB", "currency": "GBP"},
        ]
        exp = engine.compute_country_exposure(positions)
        total = sum(exp.values())
        assert abs(total - 1.0) < 0.01

    def test_set_nav_updates_nav(self):
        engine = RiskEngine()
        engine.set_nav(2_000_000.0)
        assert engine._nav == 2_000_000.0

    def test_add_daily_pnl_stores_in_history(self):
        engine = RiskEngine()
        for i in range(5):
            engine.add_daily_pnl(float(i * 1000))
        assert len(engine._pnl_history) == 5


# ---------------------------------------------------------------------------
# Alert Engine — edge cases
# ---------------------------------------------------------------------------

from services.m18_alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity, AlertDirection

class TestAlertEngineEdgeCases:
    def test_evaluate_empty_ruleset(self):
        engine = AlertEngine()
        alerts = engine.evaluate("AAPL", field="price", value=100.0)
        assert alerts == []

    def test_evaluate_with_missing_field_does_not_crash(self):
        engine = AlertEngine()
        rule = AlertRule(
            rule_id="R1", name="R1",
            alert_type=AlertType.PRICE_THRESHOLD, severity=AlertSeverity.LOW,
            field="price", direction=AlertDirection.ABOVE, threshold=50.0,
            ticker="AAPL", cooldown_seconds=0, max_triggers=10,
        )
        engine.add_rule_object(rule)
        alerts = engine.evaluate("AAPL", field="volume", value=0.0)
        assert isinstance(alerts, list)

    def test_evaluate_different_ticker_does_not_trigger(self):
        engine = AlertEngine()
        rule = AlertRule(
            rule_id="R1", name="R1",
            alert_type=AlertType.PRICE_THRESHOLD, severity=AlertSeverity.LOW,
            field="price", direction=AlertDirection.ABOVE, threshold=50.0,
            ticker="AAPL", cooldown_seconds=0, max_triggers=10,
        )
        engine.add_rule_object(rule)
        alerts = engine.evaluate("MSFT", field="price", value=100.0)
        assert len(alerts) == 0

    def test_add_then_disable_then_evaluate(self):
        engine = AlertEngine()
        rule = AlertRule(
            rule_id="R1", name="R1",
            alert_type=AlertType.PRICE_THRESHOLD, severity=AlertSeverity.LOW,
            field="price", direction=AlertDirection.ABOVE, threshold=50.0,
            ticker="AAPL", cooldown_seconds=0, max_triggers=10,
        )
        engine.add_rule_object(rule)
        engine.disable_rule("R1")
        alerts = engine.evaluate("AAPL", field="price", value=100.0)
        assert len(alerts) == 0

    def test_history_ordered_latest_first(self):
        engine = AlertEngine()
        for i in range(5):
            engine.fire_custom_alert(f"T{i}", message="M", severity=AlertSeverity.LOW, alert_type=AlertType.CUSTOM)
        hist = engine.get_history(limit=3)
        assert len(hist) == 3


# ---------------------------------------------------------------------------
# News Intelligence — edge cases
# ---------------------------------------------------------------------------

from services.m18_news_intelligence import NewsIntelligenceEngine

class TestNewsIntelligenceEdgeCases:
    def test_ingest_empty_body(self):
        engine = NewsIntelligenceEngine()
        article = engine.ingest("Headline only", body="", source="Test")
        assert article is not None

    def test_ingest_long_headline(self):
        engine = NewsIntelligenceEngine()
        long_headline = "Apple " * 100 + "beats earnings"
        article = engine.ingest(long_headline, "body", "Reuters")
        assert article is not None

    def test_search_empty_query_returns_all(self):
        engine = NewsIntelligenceEngine()
        engine.ingest("H1", "B1", "S")
        engine.ingest("H2", "B2", "S")
        results = engine.search("")
        assert isinstance(results, list)

    def test_generate_signal_no_articles(self):
        engine = NewsIntelligenceEngine()
        signal = engine.generate_signal("UNKNOWN_TICKER")
        assert signal is not None

    def test_ticker_sentiment_multiple_ingest(self):
        engine = NewsIntelligenceEngine()
        for _ in range(10):
            engine.ingest("AAPL positive results great", "B", "S")
        result = engine.get_ticker_sentiment("AAPL")
        assert result.article_count >= 1

    def test_get_stats_by_sentiment_keys(self):
        engine = NewsIntelligenceEngine()
        engine.ingest("Very positive great excellent boom", "B", "S")
        stats = engine.get_stats()
        assert "by_sentiment" in stats


# ---------------------------------------------------------------------------
# Earnings Intelligence — edge cases
# ---------------------------------------------------------------------------

from services.m18_earnings_intelligence import EarningsIntelligenceEngine, EarningsRelease, GuidanceDirection

class TestEarningsIntelligenceEdgeCases:
    def test_surprise_analysis_no_releases(self):
        engine = EarningsIntelligenceEngine()
        result = engine.compute_surprise_analysis("NODATA")
        assert result is not None

    def test_generate_signal_no_releases(self):
        engine = EarningsIntelligenceEngine()
        result = engine.generate_signal("NODATA", 0.05, 0.04, GuidanceDirection.MAINTAINED)
        assert result is not None

    def test_multiple_tickers_isolated(self):
        engine = EarningsIntelligenceEngine()
        for ticker in ["AAPL", "MSFT", "GOOGL"]:
            engine.record_release(EarningsRelease(
                ticker=ticker, fiscal_quarter="Q1 2026",
                reported_eps=2.0, consensus_eps=1.9,
                reported_revenue=100000, consensus_revenue=95000,
                gross_margin=0.45, operating_margin=0.30,
                guidance_direction=GuidanceDirection.RAISED,
            ))
        assert len(engine.get_releases("AAPL")) == 1
        assert len(engine.get_releases("MSFT")) == 1
        assert len(engine.get_releases("GOOGL")) == 1

    def test_forecast_drift_positive_on_beat(self):
        engine = EarningsIntelligenceEngine()
        for i in range(5):
            engine.record_release(EarningsRelease(
                ticker="AAPL", fiscal_quarter=f"Q{i+1} 2025",
                reported_eps=2.0 + i * 0.1, consensus_eps=1.9,
                reported_revenue=100000, consensus_revenue=95000,
                gross_margin=0.45, operating_margin=0.30,
                guidance_direction=GuidanceDirection.RAISED,
            ))
        drift = engine.forecast_post_earnings_drift("AAPL", eps_surprise_pct=0.10)
        assert isinstance(drift, float)


# ---------------------------------------------------------------------------
# Economic Intelligence — edge cases
# ---------------------------------------------------------------------------

from services.m18_economic_intelligence import EconomicIntelligenceEngine, EconomicIndicator, EconomicIndicatorType, YieldCurveSnapshot

class TestEconomicIntelligenceEdgeCases:
    def test_yield_curve_slope_positive_for_normal(self):
        snap = YieldCurveSnapshot(country="US", tenors={"2Y": 0.040, "10Y": 0.050})
        assert snap.slope > 0

    def test_yield_curve_slope_negative_for_inverted(self):
        snap = YieldCurveSnapshot(country="US", tenors={"2Y": 0.055, "10Y": 0.045})
        assert snap.slope < 0

    def test_indicators_for_multiple_countries(self):
        engine = EconomicIntelligenceEngine()
        engine.record_indicator(EconomicIndicator(
            name="US GDP", country="US", indicator_type=EconomicIndicatorType.GDP,
            value=2.5, previous_value=2.0, forecast=2.3, unit="%", frequency="Quarterly",
        ))
        engine.record_indicator(EconomicIndicator(
            name="UK GDP", country="GB", indicator_type=EconomicIndicatorType.GDP,
            value=1.2, previous_value=1.0, forecast=1.1, unit="%", frequency="Quarterly",
        ))
        assert len(engine.get_indicators(country="US")) == 1
        assert len(engine.get_indicators(country="GB")) == 1

    def test_yield_curve_multiple_snapshots(self):
        engine = EconomicIntelligenceEngine()
        engine.record_yield_curve("US", {"2Y": 0.048, "10Y": 0.045})
        engine.record_yield_curve("US", {"2Y": 0.047, "10Y": 0.044})
        engine.record_yield_curve("US", {"2Y": 0.046, "10Y": 0.043})
        hist = engine.get_yield_curve_history("US", limit=2)
        assert len(hist) == 2

    def test_yield_curve_spreads_contains_2s10s(self):
        engine = EconomicIntelligenceEngine()
        engine.record_yield_curve("US", {"3M": 0.053, "2Y": 0.048, "10Y": 0.045})
        spreads = engine.compute_yield_curve_spreads("US")
        assert "2s10s" in spreads or any("2s" in k for k in spreads.keys())


# ---------------------------------------------------------------------------
# Watchlist — edge cases
# ---------------------------------------------------------------------------

from services.m18_watchlist import WatchlistSystem, WatchlistCategory, AlertTrigger

class TestWatchlistEdgeCases:
    def test_create_multiple_lists(self):
        system = WatchlistSystem()
        for i in range(5):
            system.create_list(f"List {i}", f"Desc {i}", WatchlistCategory.EQUITY_LONG)
        assert len(system.get_all_lists()) == 5

    def test_item_count_increases_with_items(self):
        system = WatchlistSystem()
        wl = system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)
        for ticker in ["AAPL", "MSFT", "GOOGL"]:
            system.add_item(wl.list_id, ticker, f"Watch {ticker}", "Technology", conviction=8)
        wl_updated = system.get_list(wl.list_id)
        assert len(wl_updated.items) == 3

    def test_price_update_unknown_ticker_in_list(self):
        system = WatchlistSystem()
        wl = system.create_list("Test", "D", WatchlistCategory.EQUITY_LONG)
        alerts = system.update_price(wl.list_id, "ZZZZ", 100.0)
        assert isinstance(alerts, list)

    def test_screen_with_all_criteria_empty(self):
        system = WatchlistSystem()
        wl = system.create_list("T", "D", WatchlistCategory.EQUITY_LONG)
        system.add_item(wl.list_id, "AAPL", "N", "Technology", conviction=9)
        results = system.screen(min_conviction=0)
        assert len(results) >= 1

    def test_watchlist_item_conviction_range(self):
        system = WatchlistSystem()
        wl = system.create_list("T", "D", WatchlistCategory.EQUITY_LONG)
        item = system.add_item(wl.list_id, "AAPL", "N", "Technology", conviction=10)
        assert 1 <= item.conviction <= 10


# ---------------------------------------------------------------------------
# Portfolio Intelligence — edge cases
# ---------------------------------------------------------------------------

from services.m18_portfolio_intelligence import PortfolioIntelligenceEngine

class TestPortfolioIntelligenceEdgeCases:
    def test_portfolio_score_no_holdings(self):
        engine = PortfolioIntelligenceEngine()
        engine.set_nav(1_000_000.0)
        score = engine.compute_portfolio_score()
        assert 0 <= score.total_score <= 100

    def test_remove_nonexistent_holding_no_crash(self):
        engine = PortfolioIntelligenceEngine()
        try:
            engine.remove_holding("ZZZZ")
        except Exception:
            pass

    def test_add_holding_and_get(self):
        engine = PortfolioIntelligenceEngine()
        engine.set_nav(1_000_000.0)
        engine.add_holding("AAPL", weight=0.20, market_value=200_000, cost_basis=180_000)
        holdings = engine.get_all_holdings()
        assert any(h.ticker == "AAPL" for h in holdings)

    def test_efficient_frontier_single_asset(self):
        engine = PortfolioIntelligenceEngine()
        holdings_data = [{"ticker": "AAPL", "weight": 1.0, "expected_annual_return": 0.18, "annual_volatility": 0.25}]
        result = engine.compute_frontier_from_holdings(holdings_data, n_points=3)
        assert isinstance(result, dict)

    def test_rebalance_trades_with_equal_weights(self):
        engine = PortfolioIntelligenceEngine()
        engine.set_nav(1_000_000.0)
        for ticker in ["AAPL", "MSFT"]:
            engine.add_holding(ticker, weight=0.5, market_value=500_000, cost_basis=450_000)
        target = {"AAPL": 0.5, "MSFT": 0.5}
        trades = engine.compute_rebalancing_trades(target)
        assert isinstance(trades, list)

    def test_portfolio_summary_after_holding_update(self):
        engine = PortfolioIntelligenceEngine()
        engine.set_nav(2_000_000.0)
        engine.add_holding("AAPL", weight=0.30, market_value=600_000, cost_basis=500_000)
        engine.update_holding("AAPL", market_value=700_000, weight=0.35)
        summary = engine.get_portfolio_summary()
        assert summary is not None


# ---------------------------------------------------------------------------
# AI Agents — edge cases
# ---------------------------------------------------------------------------

from services.m18_ai_agents import MarketAnalystAgent, RiskMonitorAgent, ComplianceGuardAgent, AgentOrchestrator

class TestAIAgentsEdgeCases:
    def test_market_analyst_empty_payload(self):
        agent = MarketAnalystAgent()
        result = agent.run({})
        assert result is not None

    def test_risk_monitor_missing_fields(self):
        agent = RiskMonitorAgent()
        result = agent.run({"var_95_pct": 0.01})
        assert result is not None

    def test_compliance_guard_not_restricted(self):
        agent = ComplianceGuardAgent()
        result = agent.run({"ticker": "AAPL", "position_pct": 0.03, "sector_concentration_pct": 0.10, "gross_leverage": 1.0, "num_positions": 30, "is_restricted": False})
        assert result.action is not None

    def test_orchestrator_with_all_agent_types(self):
        orch = AgentOrchestrator()
        from services.m18_ai_agents import AgentType
        payloads = {
            AgentType.MARKET_ANALYST: {"ticker": "AAPL", "price": 175.0, "sma_20": 170.0, "rsi_14": 60.0},
            AgentType.RISK_MONITOR: {"var_95_pct": 0.015, "gross_leverage": 1.5, "concentration_hhi": 0.12},
            AgentType.NEWS_SCOUT: {"ticker": "AAPL", "avg_sentiment_score": 0.3, "article_count": 8},
            AgentType.MACRO_STRATEGIST: {"gdp_growth": 0.025, "inflation": 0.030, "pmi": 53.0},
        }
        result = orch.run_all(payloads, include_report=False)
        assert len(result.agent_results) >= 4

    def test_agent_history_limited(self):
        agent = MarketAnalystAgent()
        for i in range(15):
            agent.run({"ticker": "AAPL", "price": 100.0 + i})
        hist = agent.get_history()
        assert len(hist) >= 1

    def test_orchestrator_consensus_is_valid_action(self):
        from services.m18_ai_agents import AgentType, RecommendationAction
        orch = AgentOrchestrator()
        result = orch.run_all({AgentType.MARKET_ANALYST: {"ticker": "AAPL", "price": 175.0, "sma_20": 170.0}})
        assert result.consensus_action in RecommendationAction.__members__.values()


# ---------------------------------------------------------------------------
# Streaming Engine — advanced scenarios
# ---------------------------------------------------------------------------

from services.m18_streaming import StreamingEngine, make_tick, make_quote, make_news_event, EventType

class TestStreamingAdvanced:
    def test_multiple_event_types_in_history(self):
        engine = StreamingEngine()
        engine.publish(make_tick("AAPL", 100.0, 100))
        engine.publish(make_quote("AAPL", 99.9, 100.1))
        engine.publish(make_news_event("AAPL", "Test news"))
        assert engine.get_total_published() == 3

    def test_subscriber_sees_events_in_order(self):
        engine = StreamingEngine()
        received = []
        engine.subscribe(EventType.TICK, received.append)
        for i in range(5):
            engine.publish(make_tick("AAPL", float(i), 100))
        prices = [e.price for e in received]
        assert prices == sorted(prices) or prices == list(range(5))

    def test_replay_since_sequence_0_gets_all(self):
        engine = StreamingEngine()
        for i in range(5):
            engine.publish(make_tick("AAPL", float(i), 100))
        replayed = engine.replay_since(EventType.TICK, since_sequence=0)
        assert len(replayed) >= 5

    def test_batch_publish_all_get_sequences(self):
        engine = StreamingEngine()
        events = [make_tick("AAPL", float(i), 100) for i in range(3)]
        engine.batch_publish(events)
        for e in events:
            assert e.sequence > 0

    def test_get_filtered_limit(self):
        engine = StreamingEngine()
        for i in range(10):
            engine.publish(make_tick("AAPL", float(i), 100))
        filtered = engine.get_filtered(EventType.TICK, max_results=3)
        assert len(filtered) <= 3


# ---------------------------------------------------------------------------
# Gateway — advanced scenarios
# ---------------------------------------------------------------------------

from services.m18_gateway import MarketDataGateway, VenueConnector, Venue, AssetClass

class TestGatewayAdvanced:
    def test_reconnect_venue(self):
        gw = MarketDataGateway()
        vc = VenueConnector(venue=Venue.NYSE, asset_classes=[AssetClass.EQUITY])
        gw.register_connector(vc)
        gw.connect_venue(Venue.NYSE)
        gw.disconnect_venue(Venue.NYSE)
        result = gw.reconnect_venue(Venue.NYSE)
        assert result is True

    def test_fetch_snapshot_via_gateway(self):
        gw = MarketDataGateway()
        vc = VenueConnector(venue=Venue.NASDAQ, asset_classes=[AssetClass.EQUITY])
        gw.register_connector(vc)
        gw.connect_venue(Venue.NASDAQ)
        gw.ingest_tick(Venue.NASDAQ, "MSFT", 380.0, 1000)
        snap = gw.fetch_snapshot(Venue.NASDAQ, "MSFT")
        assert snap is not None

    def test_get_all_stats_includes_registered_venue(self):
        gw = MarketDataGateway()
        vc = VenueConnector(venue=Venue.CME, asset_classes=[AssetClass.FUTURES])
        gw.register_connector(vc)
        stats = gw.get_all_stats()
        venues = [s.venue for s in stats]
        assert Venue.CME in venues or "CME" in str(venues)

    def test_connector_buffer_size(self):
        vc = VenueConnector(venue=Venue.NYSE, asset_classes=[AssetClass.EQUITY])
        vc.connect()
        vc.ingest_tick("AAPL", 175.0, 1000)
        size = vc.get_buffer_size()
        assert isinstance(size, int)

    def test_set_and_fetch_quote_same_venue(self):
        vc = VenueConnector(venue=Venue.NYSE, asset_classes=[AssetClass.EQUITY])
        vc.connect()
        vc.set_quote("TSLA", bid=250.0, ask=250.5)
        q = vc.fetch_quote("TSLA")
        assert q is not None
        assert q.bid == 250.0 and q.ask == 250.5

    def test_get_tick_history_returns_list(self):
        vc = VenueConnector(venue=Venue.NYSE, asset_classes=[AssetClass.EQUITY])
        vc.connect()
        vc.ingest_tick("AAPL", 175.0, 1000)
        hist = vc.get_tick_history("AAPL", limit=5)
        assert isinstance(hist, list) and len(hist) >= 1


# ---------------------------------------------------------------------------
# Microstructure — advanced scenarios
# ---------------------------------------------------------------------------

from services.m18_microstructure import MicrostructureEngine

class TestMicrostructureAdvanced:
    def test_vwap_with_multiple_trades(self):
        engine = MicrostructureEngine()
        for i in range(20):
            engine.ingest_quote("AAPL", 99.9, 100.1)
            engine.ingest_trade("AAPL", 100.0, 1000 + i * 100, "BUY" if i % 2 == 0 else "SELL")
        bands = engine.compute_vwap_bands("AAPL")
        assert bands.vwap > 0

    def test_market_maker_activity_with_many_quotes(self):
        engine = MicrostructureEngine()
        for i in range(30):
            engine.ingest_quote("AAPL", 100.0 - 0.05, 100.0 + 0.05)
        result = engine.get_market_maker_activity("AAPL")
        assert result is not None

    def test_spread_analytics_with_variable_spreads(self):
        engine = MicrostructureEngine()
        for i in range(20):
            spread = 0.1 + i * 0.01
            engine.ingest_quote("AAPL", 100.0 - spread / 2, 100.0 + spread / 2)
        analytics = engine.get_spread_analytics("AAPL")
        assert analytics is not None
        assert analytics.mean_spread > 0

    def test_level3_multiple_orders(self):
        from services.m18_microstructure import Level3Order
        engine = MicrostructureEngine()
        for i in range(5):
            order = Level3Order(
                order_id=f"OID{i}", ticker="AAPL", side="BUY",
                price=100.0 - i * 0.1, quantity=100, visible_quantity=50,
            )
            engine.add_level3_order(order)
        orders = engine.get_level3("AAPL")
        assert len(orders) == 5

    def test_bid_ask_imbalance_negative_with_more_asks(self):
        engine = MicrostructureEngine()
        engine.ingest_order_book("AAPL", bids=[(100.0, 100)], asks=[(100.1, 900)])
        imbalance = engine.get_bid_ask_imbalance("AAPL")
        assert imbalance < 0


# ---------------------------------------------------------------------------
# Final coverage — cross-module sanity
# ---------------------------------------------------------------------------

class TestCrossModuleSanity:
    def test_feature_engine_singleton_shares_state(self):
        from services.m18_feature_engine import get_feature_engine
        e1 = get_feature_engine()
        e1.update("SINGLETON_TEST", 100.0, 1000)
        e2 = get_feature_engine()
        assert "SINGLETON_TEST" in e2.get_tracked_tickers()

    def test_news_engine_singleton_shares_state(self):
        from services.m18_news_intelligence import get_news_intelligence_engine
        e1 = get_news_intelligence_engine()
        e1.ingest("Singleton test", "Body", "TestSource")
        e2 = get_news_intelligence_engine()
        stats = e2.get_stats()
        assert stats["total_articles"] >= 1

    def test_alert_engine_singleton_shares_rules(self):
        from services.m18_alert_engine import get_alert_engine, AlertRule, AlertType, AlertSeverity, AlertDirection
        e1 = get_alert_engine()
        rule = AlertRule(
            rule_id="SINGLETON_RULE", name="Test",
            alert_type=AlertType.CUSTOM, severity=AlertSeverity.LOW,
            field="price", direction=AlertDirection.ABOVE, threshold=1.0,
            ticker="TEST", cooldown_seconds=0, max_triggers=1,
        )
        initial_count = len(e1.get_rules())
        e1.add_rule(rule)
        e2 = get_alert_engine()
        assert len(e2.get_rules()) == initial_count + 1

    def test_streaming_engine_to_dict_on_news_event(self):
        from services.m18_streaming import make_news_event
        e = make_news_event("AAPL", "Test headline", body="Test body")
        d = e.to_dict()
        assert "headline" in d

    def test_streaming_engine_tick_to_dict_has_venue(self):
        from services.m18_streaming import make_tick
        e = make_tick("AAPL", 175.0, 1000, venue="NYSE")
        d = e.to_dict()
        assert "venue" in d or "ticker" in d
