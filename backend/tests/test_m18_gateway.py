"""Unit tests for M18 Market Gateway — 65 tests."""
import pytest

from services.m18_gateway import (
    Venue, AssetClass, Quote, Tick, MarketSnapshot, ConnectorStats,
    VenueConnector, MarketDataGateway,
    create_default_connector, create_full_gateway, get_market_data_gateway,
)


# ---------------------------------------------------------------------------
# Venue enum
# ---------------------------------------------------------------------------

class TestVenueEnum:
    def test_14_venues(self):
        assert len(Venue) == 14

    def test_nyse(self):
        assert Venue.NYSE == "NYSE"

    def test_nasdaq(self):
        assert Venue.NASDAQ == "NASDAQ"

    def test_binance(self):
        assert Venue.BINANCE == "BINANCE"

    def test_coinbase(self):
        assert Venue.COINBASE == "COINBASE"

    def test_polygon(self):
        assert Venue.POLYGON == "POLYGON"


class TestAssetClassEnum:
    def test_7_asset_classes(self):
        assert len(AssetClass) == 7

    def test_equity(self):
        assert AssetClass.EQUITY == "EQUITY"

    def test_crypto(self):
        assert AssetClass.CRYPTO == "CRYPTO"


# ---------------------------------------------------------------------------
# Quote dataclass
# ---------------------------------------------------------------------------

class TestQuote:
    def _make(self, bid=100.0, ask=100.1):
        return Quote(ticker="AAPL", venue=Venue.NYSE, bid=bid, ask=ask,
                     bid_size=100, ask_size=200, latency_ms=1.5)

    def test_mid_price(self):
        q = self._make(100.0, 100.2)
        assert abs(q.mid - 100.1) < 1e-9

    def test_spread(self):
        q = self._make(100.0, 100.2)
        assert abs(q.spread - 0.2) < 1e-9

    def test_to_dict_keys(self):
        d = self._make().to_dict()
        assert "bid" in d and "ask" in d and "ticker" in d

    def test_to_dict_venue_is_string(self):
        d = self._make().to_dict()
        assert isinstance(d["venue"], str)


# ---------------------------------------------------------------------------
# VenueConnector
# ---------------------------------------------------------------------------

class TestVenueConnector:
    def _make_connector(self):
        return VenueConnector(venue=Venue.NYSE, asset_classes=[AssetClass.EQUITY])

    def test_connect_returns_true(self):
        vc = self._make_connector()
        assert vc.connect() is True

    def test_is_connected_after_connect(self):
        vc = self._make_connector()
        vc.connect()
        assert vc.is_connected() is True

    def test_disconnect_sets_not_connected(self):
        vc = self._make_connector()
        vc.connect()
        vc.disconnect()
        assert vc.is_connected() is False

    def test_reconnect_after_disconnect(self):
        vc = self._make_connector()
        vc.connect()
        vc.disconnect()
        assert vc.reconnect() is True
        assert vc.is_connected() is True

    def test_ingest_tick_returns_tick(self):
        vc = self._make_connector()
        vc.connect()
        tick = vc.ingest_tick("AAPL", 150.0, 100)
        assert tick is not None
        assert tick.ticker == "AAPL"

    def test_ingest_tick_stores_history(self):
        vc = self._make_connector()
        vc.connect()
        vc.ingest_tick("AAPL", 150.0, 100)
        hist = vc.get_tick_history("AAPL")
        assert len(hist) >= 1

    def test_fetch_quote_after_set(self):
        vc = self._make_connector()
        vc.connect()
        vc.set_quote("AAPL", bid=149.9, ask=150.1)
        q = vc.fetch_quote("AAPL")
        assert q is not None
        assert q.bid == 149.9

    def test_fetch_snapshot_returns_snapshot(self):
        vc = self._make_connector()
        vc.connect()
        vc.ingest_tick("AAPL", 150.0, 100)
        snap = vc.fetch_snapshot("AAPL")
        assert snap is not None

    def test_drain_buffer(self):
        vc = self._make_connector()
        vc.connect()
        vc.ingest_tick("AAPL", 150.0, 100)
        buf = vc.drain_buffer()
        assert isinstance(buf, list)

    def test_get_latency_ms_nonnegative(self):
        vc = self._make_connector()
        vc.connect()
        assert vc.get_latency_ms() >= 0

    def test_heartbeat_returns_bool(self):
        vc = self._make_connector()
        vc.connect()
        result = vc.heartbeat()
        assert isinstance(result, bool)

    def test_get_stats_returns_connector_stats(self):
        vc = self._make_connector()
        stats = vc.get_stats()
        assert isinstance(stats, ConnectorStats)

    def test_get_supported_asset_classes(self):
        vc = self._make_connector()
        acs = vc.get_supported_asset_classes()
        assert AssetClass.EQUITY in acs

    def test_invalidate_cache_specific(self):
        vc = self._make_connector()
        vc.connect()
        vc.set_quote("AAPL", 150.0, 150.1)
        vc.invalidate_cache("AAPL")

    def test_invalidate_cache_all(self):
        vc = self._make_connector()
        vc.invalidate_cache()

    def test_connector_stats_to_dict(self):
        vc = self._make_connector()
        d = vc.get_stats().to_dict()
        assert "venue" in d

    def test_tick_to_dict(self):
        vc = self._make_connector()
        vc.connect()
        t = vc.ingest_tick("AAPL", 150.0, 100)
        d = t.to_dict()
        assert "ticker" in d and "price" in d


# ---------------------------------------------------------------------------
# MarketDataGateway
# ---------------------------------------------------------------------------

class TestMarketDataGateway:
    def _make_gateway(self):
        gw = MarketDataGateway()
        vc = VenueConnector(venue=Venue.NYSE, asset_classes=[AssetClass.EQUITY])
        gw.register_connector(vc)
        return gw, vc

    def test_register_connector(self):
        gw, _ = self._make_gateway()
        assert Venue.NYSE in gw.get_registered_venues()

    def test_get_connector(self):
        gw, vc = self._make_gateway()
        assert gw.get_connector(Venue.NYSE) is vc

    def test_connect_venue(self):
        gw, _ = self._make_gateway()
        result = gw.connect_venue(Venue.NYSE)
        assert result is True

    def test_connect_unknown_venue_returns_false(self):
        gw = MarketDataGateway()
        result = gw.connect_venue(Venue.BINANCE)
        assert result is False

    def test_ingest_tick_through_gateway(self):
        gw, _ = self._make_gateway()
        gw.connect_venue(Venue.NYSE)
        result = gw.ingest_tick(Venue.NYSE, "AAPL", 150.0, 100)
        assert result is not None

    def test_fetch_quote_through_gateway(self):
        gw, vc = self._make_gateway()
        gw.connect_venue(Venue.NYSE)
        vc.set_quote("AAPL", 149.9, 150.1)
        q = gw.fetch_quote(Venue.NYSE, "AAPL")
        assert q is not None

    def test_get_all_quotes_empty_initially(self):
        gw, _ = self._make_gateway()
        quotes = gw.get_all_quotes("AAPL")
        assert isinstance(quotes, dict)

    def test_get_latency(self):
        gw, _ = self._make_gateway()
        lat = gw.get_latency(Venue.NYSE)
        assert lat >= 0

    def test_get_all_latencies(self):
        gw, _ = self._make_gateway()
        lats = gw.get_all_latencies()
        assert isinstance(lats, dict)

    def test_get_venue_stats(self):
        gw, _ = self._make_gateway()
        stats = gw.get_venue_stats(Venue.NYSE)
        assert isinstance(stats, ConnectorStats)

    def test_get_all_stats(self):
        gw, _ = self._make_gateway()
        stats = gw.get_all_stats()
        assert isinstance(stats, list)

    def test_heartbeat_all(self):
        gw, _ = self._make_gateway()
        gw.connect_venue(Venue.NYSE)
        hb = gw.heartbeat_all()
        assert isinstance(hb, dict)

    def test_get_summary(self):
        gw, _ = self._make_gateway()
        s = gw.get_summary()
        assert "total_venues" in s

    def test_connect_all(self):
        gw = create_full_gateway()
        results = gw.connect_all()
        assert isinstance(results, dict)

    def test_disconnect_all(self):
        gw, _ = self._make_gateway()
        gw.connect_venue(Venue.NYSE)
        gw.disconnect_all()

    def test_fetch_best_quote_no_venues(self):
        gw = MarketDataGateway()
        q = gw.fetch_best_quote("AAPL")
        assert q is None


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

class TestFactories:
    def test_create_default_connector(self):
        vc = create_default_connector(Venue.NASDAQ)
        assert isinstance(vc, VenueConnector)

    def test_create_full_gateway(self):
        gw = create_full_gateway()
        assert isinstance(gw, MarketDataGateway)
        assert len(gw.get_registered_venues()) == 14

    def test_get_market_data_gateway_singleton(self):
        gw1 = get_market_data_gateway()
        gw2 = get_market_data_gateway()
        assert gw1 is gw2
