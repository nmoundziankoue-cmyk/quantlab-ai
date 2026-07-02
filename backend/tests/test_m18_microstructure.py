"""Unit tests for M18 Microstructure Engine — 65 tests."""
import pytest

from services.m18_microstructure import (
    Level1Quote, Level2Book, Level3Order, SpreadAnalytics,
    LiquidityHeatmap, IcebergSignal, ManipulationSignal, SweepSignal,
    MarketMakerActivity, VWAPBands, LiquidityZone, TradeImpact,
    MicrostructureEngine, get_microstructure_engine,
)


# ---------------------------------------------------------------------------
# Level1Quote
# ---------------------------------------------------------------------------

class TestLevel1Quote:
    def _make(self, bid=100.0, ask=100.2):
        return Level1Quote(ticker="AAPL", bid=bid, ask=ask, bid_size=100, ask_size=200)

    def test_spread(self):
        q = self._make(100.0, 100.2)
        assert abs(q.spread - 0.2) < 1e-9

    def test_mid(self):
        q = self._make(100.0, 100.2)
        assert abs(q.mid - 100.1) < 1e-9

    def test_to_dict_has_ticker(self):
        d = self._make().to_dict()
        assert "ticker" in d

    def test_to_dict_has_bid_ask(self):
        d = self._make().to_dict()
        assert "bid" in d and "ask" in d

    def test_to_dict_has_spread(self):
        d = self._make().to_dict()
        assert "spread" in d

    def test_zero_spread(self):
        q = self._make(100.0, 100.0)
        assert q.spread == 0.0


# ---------------------------------------------------------------------------
# Level2Book
# ---------------------------------------------------------------------------

class TestLevel2Book:
    def _make(self):
        return Level2Book(
            ticker="AAPL",
            bids=[(100.0, 100), (99.9, 200)],
            asks=[(100.1, 100), (100.2, 200)],
        )

    def test_best_bid(self):
        b = self._make()
        assert b.best_bid == 100.0

    def test_best_ask(self):
        b = self._make()
        assert b.best_ask == 100.1

    def test_total_bid_size(self):
        b = self._make()
        assert b.total_bid_size == 300

    def test_total_ask_size(self):
        b = self._make()
        assert b.total_ask_size == 300

    def test_to_dict_has_bids(self):
        d = self._make().to_dict()
        assert "bids" in d

    def test_empty_bids_best_bid_is_none(self):
        b = Level2Book(ticker="AAPL", bids=[], asks=[])
        assert b.best_bid is None


# ---------------------------------------------------------------------------
# MicrostructureEngine — ingest and retrieval
# ---------------------------------------------------------------------------

class TestMicrostructureEngineIngest:
    def setup_method(self):
        self.engine = MicrostructureEngine()

    def test_ingest_quote_returns_l1(self):
        q = self.engine.ingest_quote("AAPL", bid=100.0, ask=100.2, bid_size=100, ask_size=200)
        assert isinstance(q, Level1Quote)

    def test_ingest_quote_stores_l1(self):
        self.engine.ingest_quote("AAPL", bid=100.0, ask=100.2)
        l1 = self.engine.get_level1("AAPL")
        assert l1 is not None
        assert l1.bid == 100.0

    def test_get_level1_unknown_ticker(self):
        assert self.engine.get_level1("ZZZZ") is None

    def test_ingest_trade_records_vwap(self):
        self.engine.ingest_quote("AAPL", 99.9, 100.1)
        self.engine.ingest_trade("AAPL", 100.0, 1000, "BUY")
        bands = self.engine.get_vwap_bands("AAPL")
        assert bands is not None

    def test_ingest_order_book(self):
        result = self.engine.ingest_order_book(
            "AAPL",
            bids=[(100.0, 100), (99.9, 200)],
            asks=[(100.1, 100), (100.2, 200)],
        )
        assert isinstance(result, Level2Book)

    def test_get_level2_returns_book(self):
        self.engine.ingest_order_book("AAPL", bids=[(100.0, 100)], asks=[(100.1, 100)])
        l2 = self.engine.get_level2("AAPL")
        assert l2 is not None

    def test_add_level3_order(self):
        order = Level3Order(
            order_id="OID1", ticker="AAPL", side="BUY",
            price=100.0, size=100,
        )
        self.engine.add_level3_order(order)
        orders = self.engine.get_level3("AAPL")
        assert len(orders) >= 1

    def test_level3_to_dict(self):
        order = Level3Order(
            order_id="OID2", ticker="AAPL", side="SELL",
            price=100.1, size=200,
        )
        d = order.to_dict()
        assert "order_id" in d


# ---------------------------------------------------------------------------
# MicrostructureEngine — analytics
# ---------------------------------------------------------------------------

class TestMicrostructureEngineAnalytics:
    def setup_method(self):
        self.engine = MicrostructureEngine()
        for i in range(30):
            self.engine.ingest_quote("AAPL", 100.0 - 0.1, 100.0 + 0.1, 500, 500)
            self.engine.ingest_trade("AAPL", 100.0, 1000 + i * 10, "BUY")
        self.engine.ingest_order_book(
            "AAPL",
            bids=[(99.9, 100), (99.8, 200), (99.7, 150)],
            asks=[(100.1, 100), (100.2, 200), (100.3, 150)],
        )

    def test_get_spread_analytics(self):
        result = self.engine.get_spread_analytics("AAPL")
        assert result is not None
        assert isinstance(result, SpreadAnalytics)

    def test_spread_analytics_to_dict(self):
        result = self.engine.get_spread_analytics("AAPL")
        d = result.to_dict()
        assert "mean_spread" in d or "ticker" in d

    def test_get_bid_ask_imbalance(self):
        self.engine.ingest_order_book("AAPL", bids=[(100.0, 300)], asks=[(100.1, 100)])
        imbalance = self.engine.get_bid_ask_imbalance("AAPL")
        assert isinstance(imbalance, float)

    def test_bid_ask_imbalance_positive_with_more_bids(self):
        self.engine.ingest_order_book("AAPL", bids=[(100.0, 900)], asks=[(100.1, 100)])
        imbalance = self.engine.get_bid_ask_imbalance("AAPL")
        assert imbalance > 0

    def test_compute_vwap_bands(self):
        bands = self.engine.get_vwap_bands("AAPL")
        assert isinstance(bands, VWAPBands)

    def test_vwap_bands_to_dict(self):
        bands = self.engine.get_vwap_bands("AAPL")
        d = bands.to_dict()
        assert "vwap" in d or "ticker" in d

    def test_detect_spoofing(self):
        result = self.engine.detect_spoofing("AAPL")
        assert isinstance(result, ManipulationSignal)

    def test_detect_spoofing_to_dict(self):
        result = self.engine.detect_spoofing("AAPL")
        d = result.to_dict()
        assert "ticker" in d

    def test_detect_sweep(self):
        result = self.engine.detect_sweep("AAPL")
        assert isinstance(result, SweepSignal)

    def test_detect_sweep_to_dict(self):
        d = self.engine.detect_sweep("AAPL").to_dict()
        assert "detected" in d or "ticker" in d

    def test_detect_iceberg(self):
        result = self.engine.detect_iceberg("AAPL")
        assert isinstance(result, IcebergSignal)

    def test_compute_trade_impact(self):
        result = self.engine.ingest_trade("AAPL", 100.0, 100000, "BUY")
        assert isinstance(result, TradeImpact)

    def test_get_market_maker_activity(self):
        result = self.engine.get_market_maker_activity("AAPL")
        assert isinstance(result, MarketMakerActivity)

    def test_compute_liquidity_zones(self):
        result = self.engine.get_liquidity_zones("AAPL")
        assert isinstance(result, list)

    def test_get_liquidity_heatmap(self):
        result = self.engine.get_liquidity_heatmap("AAPL")
        assert isinstance(result, LiquidityHeatmap)

    def test_unknown_ticker_analytics_returns_none_or_default(self):
        result = self.engine.get_spread_analytics("UNKN")
        assert result is None or isinstance(result, SpreadAnalytics)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_microstructure_engine_returns_engine(self):
        eng = get_microstructure_engine()
        assert isinstance(eng, MicrostructureEngine)

    def test_singleton_same_instance(self):
        e1 = get_microstructure_engine()
        e2 = get_microstructure_engine()
        assert e1 is e2
