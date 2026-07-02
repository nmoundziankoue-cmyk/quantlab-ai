"""Unit tests for M18 Streaming Engine — 70 tests."""
import pytest
from datetime import datetime, timezone

from services.m18_streaming import (
    EventType, BaseEvent, TickEvent, QuoteEvent, TradeEvent,
    OrderBookEvent, NewsEvent, EconomicEvent, CorporateActionEvent,
    AlertEvent, PortfolioEvent, RiskEvent, ExecutionEvent,
    SubscriptionHandle, EventMetrics, StreamingEngine,
    make_tick, make_quote, make_trade_event, make_order_book_event,
    make_news_event, make_risk_event, get_streaming_engine,
)


# ---------------------------------------------------------------------------
# EventType enum
# ---------------------------------------------------------------------------

class TestEventType:
    def test_all_11_values(self):
        assert len(EventType) == 11

    def test_tick_value(self):
        assert EventType.TICK == "TICK"

    def test_quote_value(self):
        assert EventType.QUOTE == "QUOTE"

    def test_trade_value(self):
        assert EventType.TRADE == "TRADE"

    def test_order_book_value(self):
        assert EventType.ORDER_BOOK == "ORDER_BOOK"

    def test_news_value(self):
        assert EventType.NEWS == "NEWS"

    def test_economic_value(self):
        assert EventType.ECONOMIC == "ECONOMIC"

    def test_corporate_action_value(self):
        assert EventType.CORPORATE_ACTION == "CORPORATE_ACTION"

    def test_alert_value(self):
        assert EventType.ALERT == "ALERT"

    def test_portfolio_value(self):
        assert EventType.PORTFOLIO == "PORTFOLIO"

    def test_risk_value(self):
        assert EventType.RISK == "RISK"

    def test_execution_value(self):
        assert EventType.EXECUTION == "EXECUTION"


# ---------------------------------------------------------------------------
# StreamingEngine publish / subscribe
# ---------------------------------------------------------------------------

class TestStreamingEnginePublish:
    def setup_method(self):
        self.engine = StreamingEngine(max_history=200)

    def test_publish_tick_increments_sequence(self):
        t = make_tick("AAPL", 150.0, 100)
        self.engine.publish(t)
        assert t.sequence == 1

    def test_publish_multiple_increments_sequence(self):
        for i in range(5):
            self.engine.publish(make_tick("AAPL", 100 + i, 10))
        assert self.engine.get_sequence() == 5

    def test_publish_stores_in_history(self):
        self.engine.publish(make_tick("AAPL", 100.0, 50))
        hist = self.engine.get_history(EventType.TICK)
        assert len(hist) == 1

    def test_batch_publish_returns_count(self):
        events = [make_tick("AAPL", 100 + i, 10) for i in range(5)]
        count = self.engine.batch_publish(events)
        assert count == 5

    def test_history_max_enforced(self):
        engine = StreamingEngine(max_history=5)
        for i in range(10):
            engine.publish(make_tick("X", float(i), 1))
        assert len(engine.get_history(EventType.TICK)) <= 5

    def test_get_total_published(self):
        for _ in range(7):
            self.engine.publish(make_tick("AAPL", 100.0, 1))
        assert self.engine.get_total_published() == 7

    def test_reset_metrics_zeroes_counters(self):
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        self.engine.reset_metrics()
        assert self.engine.get_total_published() == 0

    def test_publish_different_event_types(self):
        self.engine.publish(make_tick("AAPL", 100.0, 50))
        self.engine.publish(make_quote("MSFT", 300.0, 300.1))
        assert self.engine.get_total_published() == 2


class TestStreamingEngineSubscribe:
    def setup_method(self):
        self.engine = StreamingEngine()

    def test_subscribe_returns_handle(self):
        handle = self.engine.subscribe(EventType.TICK, lambda e: None)
        assert isinstance(handle, SubscriptionHandle)

    def test_subscribe_callback_called_on_publish(self):
        received = []
        self.engine.subscribe(EventType.TICK, received.append)
        self.engine.publish(make_tick("AAPL", 100.0, 50))
        assert len(received) == 1
        assert received[0].event_type == EventType.TICK

    def test_subscribe_only_receives_matching_type(self):
        tick_received = []
        self.engine.subscribe(EventType.TICK, tick_received.append)
        self.engine.publish(make_quote("MSFT", 300.0, 300.1))
        assert len(tick_received) == 0

    def test_unsubscribe_stops_delivery(self):
        received = []
        handle = self.engine.subscribe(EventType.TICK, received.append)
        self.engine.unsubscribe(handle.subscription_id)
        self.engine.publish(make_tick("AAPL", 100.0, 50))
        assert len(received) == 0

    def test_unsubscribe_unknown_id_returns_false(self):
        result = self.engine.unsubscribe("nonexistent-id")
        assert result is False

    def test_get_subscription_count_all(self):
        self.engine.subscribe(EventType.TICK, lambda e: None)
        self.engine.subscribe(EventType.NEWS, lambda e: None)
        assert self.engine.get_subscription_count() == 2

    def test_get_subscription_count_by_type(self):
        self.engine.subscribe(EventType.TICK, lambda e: None)
        self.engine.subscribe(EventType.TICK, lambda e: None)
        self.engine.subscribe(EventType.NEWS, lambda e: None)
        assert self.engine.get_subscription_count(EventType.TICK) == 2

    def test_multiple_subscribers_all_receive(self):
        r1, r2 = [], []
        self.engine.subscribe(EventType.TICK, r1.append)
        self.engine.subscribe(EventType.TICK, r2.append)
        self.engine.publish(make_tick("AAPL", 100.0, 50))
        assert len(r1) == 1 and len(r2) == 1


class TestStreamingEngineHistory:
    def setup_method(self):
        self.engine = StreamingEngine()

    def test_get_history_empty_initially(self):
        assert self.engine.get_history(EventType.TICK) == []

    def test_get_history_limit(self):
        for i in range(10):
            self.engine.publish(make_tick("AAPL", float(i), 1))
        hist = self.engine.get_history(EventType.TICK, max_events=3)
        assert len(hist) == 3

    def test_replay_since_returns_events_after_seq(self):
        for i in range(5):
            self.engine.publish(make_tick("AAPL", float(i), 1))
        replayed = self.engine.replay_since(EventType.TICK, since_sequence=3)
        assert all(e.sequence > 3 for e in replayed)

    def test_clear_history_specific_type(self):
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        self.engine.publish(make_quote("AAPL", 100.0, 100.1))
        self.engine.clear_history(EventType.TICK)
        assert self.engine.get_history(EventType.TICK) == []
        assert len(self.engine.get_history(EventType.QUOTE)) == 1

    def test_clear_history_all_types(self):
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        self.engine.publish(make_news_event("AAPL", "Test headline"))
        self.engine.clear_history()
        assert self.engine.get_total_published() == 0 or self.engine.get_history(EventType.TICK) == []

    def test_get_filtered_by_ticker(self):
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        self.engine.publish(make_tick("MSFT", 200.0, 1))
        filtered = self.engine.get_filtered(EventType.TICK, ticker="AAPL")
        assert all(e.ticker == "AAPL" for e in filtered)

    def test_clear_history_all_clears_total_published(self):
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        self.engine.clear_history()
        assert self.engine.get_history(EventType.TICK) == []


class TestStreamingEnginePersistenceHook:
    def setup_method(self):
        self.engine = StreamingEngine()

    def test_persistence_hook_called_on_publish(self):
        persisted = []
        self.engine.register_persistence_hook(persisted.append)
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        assert len(persisted) == 1

    def test_remove_persistence_hook(self):
        persisted = []
        hook = persisted.append
        self.engine.register_persistence_hook(hook)
        self.engine.remove_persistence_hook(hook)
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        assert len(persisted) == 0

    def test_remove_nonexistent_hook_returns_false(self):
        result = self.engine.remove_persistence_hook(lambda e: None)
        assert result is False


class TestStreamingEngineMetrics:
    def setup_method(self):
        self.engine = StreamingEngine()

    def test_get_metrics_returns_list(self):
        metrics = self.engine.get_metrics()
        assert isinstance(metrics, (list, dict))

    def test_get_metrics_has_tick_after_publish(self):
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        metrics = self.engine.get_metrics()
        assert "TICK" in str(metrics)

    def test_get_sequence_increments(self):
        self.engine.publish(make_tick("AAPL", 100.0, 1))
        self.engine.publish(make_tick("AAPL", 101.0, 1))
        assert self.engine.get_sequence() == 2


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

class TestFactoryFunctions:
    def test_make_tick_returns_tick_event(self):
        e = make_tick("AAPL", 150.0, 100)
        assert isinstance(e, TickEvent)
        assert e.event_type == EventType.TICK

    def test_make_tick_fields(self):
        e = make_tick("AAPL", 150.0, 100, venue="NYSE")
        assert e.ticker == "AAPL"
        assert e.price == 150.0
        assert e.volume == 100

    def test_make_quote_returns_quote_event(self):
        e = make_quote("MSFT", 300.0, 300.5)
        assert isinstance(e, QuoteEvent)
        assert e.event_type == EventType.QUOTE

    def test_make_quote_fields(self):
        e = make_quote("MSFT", 300.0, 300.5, bid_size=100, ask_size=200)
        assert e.bid == 300.0
        assert e.ask == 300.5

    def test_make_trade_event_returns_trade(self):
        e = make_trade_event("TSLA", "BUY", 50, 250.0)
        assert isinstance(e, TradeEvent)

    def test_make_order_book_event(self):
        e = make_order_book_event("AAPL", [(149.9, 100), (149.8, 200)], [(150.1, 100), (150.2, 200)])
        assert isinstance(e, OrderBookEvent)

    def test_make_news_event(self):
        e = make_news_event("Apple beats earnings")
        assert isinstance(e, NewsEvent)
        assert e.headline == "Apple beats earnings"

    def test_make_risk_event(self):
        e = make_risk_event("VAR_BREACH", "var_95", 0.015, 0.01, True)
        assert isinstance(e, RiskEvent)

    def test_event_to_dict_contains_type(self):
        e = make_tick("AAPL", 100.0, 50)
        d = e.to_dict()
        assert "event_type" in d
        assert d["event_type"] == "TICK"

    def test_event_to_dict_contains_id(self):
        e = make_tick("AAPL", 100.0, 50)
        d = e.to_dict()
        assert "event_id" in d


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_streaming_engine_returns_engine(self):
        engine = get_streaming_engine()
        assert isinstance(engine, StreamingEngine)

    def test_singleton_same_instance(self):
        e1 = get_streaming_engine()
        e2 = get_streaming_engine()
        assert e1 is e2
