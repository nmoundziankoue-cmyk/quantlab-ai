"""M18 — Universal Market Data Gateway: modular multi-venue connector framework.

Supports 14 venues (NYSE, NASDAQ, TSX, CME, ICE, Binance, Coinbase, Kraken,
Bybit, OKX, Polygon, Alpaca, TwelveData, Yahoo Finance).

Features per connector:
  websocket simulation, reconnect logic, heartbeat, latency measurement,
  buffering, throttling, compression (simulated), caching, replay, snapshots,
  historical synchronisation.

Pure Python; no real websocket connections — the connector layer is designed
for simulation and testing.  In production the VenueConnector interface would
wrap a real websocket client; here it uses an in-memory tick store.
"""
from __future__ import annotations

import math
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Venue enumeration
# ---------------------------------------------------------------------------

class Venue(str, Enum):
    """All venues supported by the M18 gateway."""

    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    TSX = "TSX"
    CME = "CME"
    ICE = "ICE"
    BINANCE = "BINANCE"
    COINBASE = "COINBASE"
    KRAKEN = "KRAKEN"
    BYBIT = "BYBIT"
    OKX = "OKX"
    POLYGON = "POLYGON"
    ALPACA = "ALPACA"
    TWELVEDATA = "TWELVEDATA"
    YAHOO_FINANCE = "YAHOO_FINANCE"


class AssetClass(str, Enum):
    """Asset class supported at a venue."""

    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    CRYPTO = "CRYPTO"
    FX = "FX"
    FIXED_INCOME = "FIXED_INCOME"
    ETF = "ETF"


# ---------------------------------------------------------------------------
# Market data structures
# ---------------------------------------------------------------------------

@dataclass
class Quote:
    """Best-bid/offer snapshot from a venue.

    Args:
        ticker: Instrument symbol.
        venue: Originating venue.
        bid: Best bid price.
        ask: Best ask price.
        bid_size: Bid quantity.
        ask_size: Ask quantity.
        timestamp: UTC time of quote.
        latency_ms: Round-trip latency to fetch this quote.
    """

    ticker: str
    venue: Venue
    bid: float
    ask: float
    bid_size: float = 0.0
    ask_size: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0

    @property
    def mid(self) -> float:
        """Mid-point of bid and ask."""
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        """Absolute bid-ask spread."""
        return self.ask - self.bid

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "venue": self.venue.value,
            "bid": round(self.bid, 6),
            "ask": round(self.ask, 6),
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "mid": round(self.mid, 6),
            "spread": round(self.spread, 6),
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": round(self.latency_ms, 3),
        }


@dataclass
class Tick:
    """Last-sale tick: price and volume.

    Args:
        ticker: Instrument symbol.
        venue: Originating venue.
        price: Last trade price.
        volume: Last trade volume.
        timestamp: UTC timestamp.
    """

    ticker: str
    venue: Venue
    price: float
    volume: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "venue": self.venue.value,
            "price": round(self.price, 6),
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MarketSnapshot:
    """Full market data snapshot for an instrument.

    Args:
        ticker: Instrument symbol.
        venue: Source venue.
        bid: Best bid.
        ask: Best ask.
        last: Last trade price.
        volume: Daily volume.
        high: Daily high.
        low: Daily low.
        open_price: Opening price.
        vwap: Volume-weighted average price.
        timestamp: Snapshot time UTC.
    """

    ticker: str
    venue: Venue
    bid: float
    ask: float
    last: float
    volume: float
    high: float
    low: float
    open_price: float
    vwap: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "venue": self.venue.value,
            "bid": round(self.bid, 6),
            "ask": round(self.ask, 6),
            "last": round(self.last, 6),
            "volume": self.volume,
            "high": round(self.high, 6),
            "low": round(self.low, 6),
            "open": round(self.open_price, 6),
            "vwap": round(self.vwap, 6),
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Connector stats
# ---------------------------------------------------------------------------

@dataclass
class ConnectorStats:
    """Operational statistics for a venue connector.

    Args:
        venue: Venue this stat block refers to.
        connected: Whether the connector is currently connected.
        messages_received: Total messages received since connection.
        messages_buffered: Messages waiting in the inbound buffer.
        reconnect_count: Total reconnection attempts.
        avg_latency_ms: Exponentially weighted average latency.
        last_heartbeat: Timestamp of last heartbeat response.
        throttle_events: Number of messages dropped due to throttling.
        bytes_received: Simulated total bytes received.
        cache_hits: Number of cache hits on quote lookups.
        cache_misses: Number of cache misses.
    """

    venue: Venue
    connected: bool
    messages_received: int
    messages_buffered: int
    reconnect_count: int
    avg_latency_ms: float
    last_heartbeat: Optional[datetime]
    throttle_events: int
    bytes_received: int
    cache_hits: int
    cache_misses: int

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "venue": self.venue.value,
            "connected": self.connected,
            "messages_received": self.messages_received,
            "messages_buffered": self.messages_buffered,
            "reconnect_count": self.reconnect_count,
            "avg_latency_ms": round(self.avg_latency_ms, 3),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "throttle_events": self.throttle_events,
            "bytes_received": self.bytes_received,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
        }


# ---------------------------------------------------------------------------
# Connector (one per venue)
# ---------------------------------------------------------------------------

class VenueConnector:
    """Simulated connector to a single market data venue.

    Models the connection lifecycle, tick buffering, latency measurement,
    reconnect logic, throttling, and quote caching. In production this class
    would wrap a real WebSocket or FIX connection.

    Args:
        venue: Which venue this connector represents.
        asset_classes: Asset classes available at this venue.
        base_latency_ms: Simulated round-trip baseline latency.
        max_buffer_size: Maximum ticks to retain in the inbound buffer.
        throttle_rate: Maximum ticks per second (0 = unlimited).
        heartbeat_interval_s: Seconds between heartbeat checks.
    """

    def __init__(
        self,
        venue: Venue,
        asset_classes: Optional[List[AssetClass]] = None,
        base_latency_ms: float = 5.0,
        max_buffer_size: int = 1000,
        throttle_rate: float = 0.0,
        heartbeat_interval_s: float = 30.0,
    ) -> None:
        self.venue = venue
        self.asset_classes: List[AssetClass] = asset_classes or [AssetClass.EQUITY]
        self._base_latency_ms = base_latency_ms
        self._max_buffer_size = max_buffer_size
        self._throttle_rate = throttle_rate
        self._heartbeat_interval_s = heartbeat_interval_s
        self._connected: bool = False
        self._buffer: Deque[Tick] = deque(maxlen=max_buffer_size)
        self._tick_store: Dict[str, List[Tick]] = {}
        self._quote_cache: Dict[str, Quote] = {}
        self._avg_latency_ms: float = base_latency_ms
        self._messages_received: int = 0
        self._reconnect_count: int = 0
        self._throttle_events: int = 0
        self._bytes_received: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._last_heartbeat: Optional[datetime] = None
        self._tick_token_bucket: float = 0.0
        self._last_token_refill: float = time.monotonic()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Establish the simulated connection.

        Returns:
            True on success (always in simulation).
        """
        if self._connected:
            return True
        self._connected = True
        self._last_heartbeat = datetime.now(timezone.utc)
        return True

    def disconnect(self) -> None:
        """Close the connection."""
        self._connected = False

    def reconnect(self) -> bool:
        """Disconnect then reconnect; increments reconnect counter.

        Returns:
            True after successful reconnect.
        """
        self.disconnect()
        self._reconnect_count += 1
        return self.connect()

    def is_connected(self) -> bool:
        """Return True if currently connected.

        Returns:
            Connection state.
        """
        return self._connected

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def heartbeat(self) -> bool:
        """Send a heartbeat ping and update the last-heartbeat timestamp.

        Returns:
            True if connection is alive; False if the connector was disconnected.
        """
        if not self._connected:
            return False
        self._last_heartbeat = datetime.now(timezone.utc)
        return True

    def get_last_heartbeat(self) -> Optional[datetime]:
        """Return timestamp of last successful heartbeat.

        Returns:
            UTC datetime or None if never heartbeat-ed.
        """
        return self._last_heartbeat

    # ------------------------------------------------------------------
    # Tick ingestion
    # ------------------------------------------------------------------

    def ingest_tick(self, ticker: str, price: float, volume: float) -> Optional[Tick]:
        """Ingest a simulated market data tick.

        Applies throttle logic; buffered if not over throttle limit.

        Args:
            ticker: Instrument symbol.
            price: Trade price.
            volume: Trade volume.

        Returns:
            Tick if accepted, None if throttled.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._connected:
            raise RuntimeError(f"Connector for {self.venue.value} is not connected")
        if self._throttle_rate > 0:
            now = time.monotonic()
            elapsed = now - self._last_token_refill
            self._tick_token_bucket = min(
                self._throttle_rate,
                self._tick_token_bucket + elapsed * self._throttle_rate,
            )
            self._last_token_refill = now
            if self._tick_token_bucket < 1.0:
                self._throttle_events += 1
                return None
            self._tick_token_bucket -= 1.0
        tick = Tick(
            ticker=ticker.upper(),
            venue=self.venue,
            price=price,
            volume=volume,
            timestamp=datetime.now(timezone.utc),
        )
        self._buffer.append(tick)
        store = self._tick_store.setdefault(ticker.upper(), [])
        store.append(tick)
        self._messages_received += 1
        self._bytes_received += 64
        self._update_latency()
        return tick

    def _update_latency(self) -> None:
        """Update exponentially weighted average latency."""
        alpha = 0.1
        jitter = self._base_latency_ms * 0.1
        sample = self._base_latency_ms + jitter * (hash(str(self._messages_received)) % 10 - 5) / 5
        self._avg_latency_ms = (1 - alpha) * self._avg_latency_ms + alpha * max(0.1, sample)

    # ------------------------------------------------------------------
    # Quote / Snapshot
    # ------------------------------------------------------------------

    def fetch_quote(self, ticker: str) -> Optional[Quote]:
        """Fetch the latest quote for a ticker from in-memory cache.

        Args:
            ticker: Instrument symbol.

        Returns:
            Quote if available, None otherwise.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._connected:
            raise RuntimeError(f"Connector for {self.venue.value} is not connected")
        ticker_upper = ticker.upper()
        if ticker_upper in self._quote_cache:
            self._cache_hits += 1
            return self._quote_cache[ticker_upper]
        ticks = self._tick_store.get(ticker_upper)
        if not ticks:
            self._cache_misses += 1
            return None
        last_tick = ticks[-1]
        spread_half = last_tick.price * 0.0001
        quote = Quote(
            ticker=ticker_upper,
            venue=self.venue,
            bid=last_tick.price - spread_half,
            ask=last_tick.price + spread_half,
            bid_size=100.0,
            ask_size=100.0,
            timestamp=last_tick.timestamp,
            latency_ms=self._avg_latency_ms,
        )
        self._quote_cache[ticker_upper] = quote
        self._cache_misses += 1
        return quote

    def set_quote(self, ticker: str, bid: float, ask: float,
                  bid_size: float = 100.0, ask_size: float = 100.0) -> Quote:
        """Directly set a quote in the cache (used for testing / seeding).

        Args:
            ticker: Instrument symbol.
            bid: Bid price.
            ask: Ask price.
            bid_size: Bid quantity.
            ask_size: Ask quantity.

        Returns:
            The stored Quote.
        """
        quote = Quote(
            ticker=ticker.upper(),
            venue=self.venue,
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            timestamp=datetime.now(timezone.utc),
            latency_ms=self._avg_latency_ms,
        )
        self._quote_cache[ticker.upper()] = quote
        return quote

    def fetch_snapshot(self, ticker: str) -> Optional[MarketSnapshot]:
        """Build a MarketSnapshot from the tick history.

        Args:
            ticker: Instrument symbol.

        Returns:
            MarketSnapshot or None if no tick history.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._connected:
            raise RuntimeError(f"Connector for {self.venue.value} is not connected")
        ticks = self._tick_store.get(ticker.upper())
        if not ticks:
            return None
        prices = [t.price for t in ticks]
        volumes = [t.volume for t in ticks]
        high = max(prices)
        low = min(prices)
        open_price = prices[0]
        last = prices[-1]
        total_volume = sum(volumes)
        vwap = (sum(p * v for p, v in zip(prices, volumes)) / total_volume
                if total_volume > 0 else last)
        spread_half = last * 0.0001
        return MarketSnapshot(
            ticker=ticker.upper(),
            venue=self.venue,
            bid=last - spread_half,
            ask=last + spread_half,
            last=last,
            volume=total_volume,
            high=high,
            low=low,
            open_price=open_price,
            vwap=vwap,
            timestamp=ticks[-1].timestamp,
        )

    # ------------------------------------------------------------------
    # Replay / History
    # ------------------------------------------------------------------

    def get_tick_history(
        self,
        ticker: str,
        max_ticks: int = 1000,
        limit: int = 0,
    ) -> List[Tick]:
        """Return stored tick history for a ticker.

        Args:
            ticker: Instrument symbol.
            max_ticks: Maximum ticks to return (most recent).

        Returns:
            List of Tick ordered chronologically.
        """
        ticks = self._tick_store.get(ticker.upper(), [])
        n = limit if limit > 0 else max_ticks
        return ticks[-n:]

    def drain_buffer(self) -> List[Tick]:
        """Drain and return all buffered ticks.

        Returns:
            List of Tick in order received; buffer is cleared.
        """
        items = list(self._buffer)
        self._buffer.clear()
        return items

    def get_buffer_size(self) -> int:
        """Return current number of ticks in the inbound buffer.

        Returns:
            Buffer occupancy count.
        """
        return len(self._buffer)

    # ------------------------------------------------------------------
    # Latency
    # ------------------------------------------------------------------

    def get_latency_ms(self) -> float:
        """Return the current exponentially-weighted average latency.

        Returns:
            Latency in milliseconds.
        """
        return round(self._avg_latency_ms, 3)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> ConnectorStats:
        """Return a snapshot of operational statistics.

        Returns:
            ConnectorStats dataclass.
        """
        return ConnectorStats(
            venue=self.venue,
            connected=self._connected,
            messages_received=self._messages_received,
            messages_buffered=len(self._buffer),
            reconnect_count=self._reconnect_count,
            avg_latency_ms=self._avg_latency_ms,
            last_heartbeat=self._last_heartbeat,
            throttle_events=self._throttle_events,
            bytes_received=self._bytes_received,
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
        )

    def invalidate_cache(self, ticker: Optional[str] = None) -> None:
        """Invalidate the quote cache.

        Args:
            ticker: If provided, invalidate only that ticker; else clear all.
        """
        if ticker:
            self._quote_cache.pop(ticker.upper(), None)
        else:
            self._quote_cache.clear()

    def get_supported_asset_classes(self) -> List[AssetClass]:
        """Return the asset classes supported at this venue.

        Returns:
            List of AssetClass values.
        """
        return list(self.asset_classes)


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class MarketDataGateway:
    """Universal market data gateway coordinating all venue connectors.

    Manages connector lifecycle, multi-venue quote aggregation, historical
    synchronisation, and aggregate statistics.
    """

    def __init__(self) -> None:
        self._connectors: Dict[Venue, VenueConnector] = {}

    # ------------------------------------------------------------------
    # Connector registration
    # ------------------------------------------------------------------

    def register_connector(self, connector: VenueConnector) -> None:
        """Register a VenueConnector with the gateway.

        Args:
            connector: Pre-configured VenueConnector instance.
        """
        self._connectors[connector.venue] = connector

    def get_connector(self, venue: Venue) -> Optional[VenueConnector]:
        """Retrieve a registered connector.

        Args:
            venue: Target venue.

        Returns:
            VenueConnector or None if not registered.
        """
        return self._connectors.get(venue)

    def get_registered_venues(self) -> List[Venue]:
        """Return all registered venue names.

        Returns:
            List of Venue enum values.
        """
        return list(self._connectors.keys())

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect_venue(self, venue: Venue) -> bool:
        """Connect a registered venue connector.

        Args:
            venue: Target venue.

        Returns:
            True on success, False if venue is not registered.
        """
        try:
            conn = self._get_or_raise(venue)
        except KeyError:
            return False
        return conn.connect()

    def disconnect_venue(self, venue: Venue) -> None:
        """Disconnect a registered venue connector.

        Args:
            venue: Target venue.

        Raises:
            KeyError: If venue is not registered.
        """
        self._get_or_raise(venue).disconnect()

    def connect_all(self) -> Dict[Venue, bool]:
        """Connect all registered venues.

        Returns:
            Dict mapping venue to connection success flag.
        """
        return {v: c.connect() for v, c in self._connectors.items()}

    def disconnect_all(self) -> None:
        """Disconnect all registered venues."""
        for conn in self._connectors.values():
            conn.disconnect()

    def reconnect_venue(self, venue: Venue) -> bool:
        """Reconnect a venue that may have dropped.

        Args:
            venue: Target venue.

        Returns:
            True after reconnect.
        """
        return self._get_or_raise(venue).reconnect()

    # ------------------------------------------------------------------
    # Market data operations
    # ------------------------------------------------------------------

    def ingest_tick(
        self, venue: Venue, ticker: str, price: float, volume: float
    ) -> Optional[Tick]:
        """Route a tick to the specified venue connector.

        Args:
            venue: Target venue.
            ticker: Instrument symbol.
            price: Trade price.
            volume: Trade volume.

        Returns:
            Tick if accepted; None if throttled.
        """
        return self._get_or_raise(venue).ingest_tick(ticker, price, volume)

    def fetch_quote(self, venue: Venue, ticker: str) -> Optional[Quote]:
        """Fetch a quote from a specific venue.

        Args:
            venue: Target venue.
            ticker: Instrument symbol.

        Returns:
            Quote or None.
        """
        return self._get_or_raise(venue).fetch_quote(ticker)

    def fetch_best_quote(self, ticker: str) -> Optional[Quote]:
        """Fetch the best (tightest spread) quote across all connected venues.

        Args:
            ticker: Instrument symbol.

        Returns:
            Quote with tightest spread, or None if no data.
        """
        best: Optional[Quote] = None
        for conn in self._connectors.values():
            if not conn.is_connected():
                continue
            q = conn.fetch_quote(ticker)
            if q is None:
                continue
            if best is None or q.spread < best.spread:
                best = q
        return best

    def fetch_snapshot(self, venue: Venue, ticker: str) -> Optional[MarketSnapshot]:
        """Fetch a full market snapshot from a specific venue.

        Args:
            venue: Target venue.
            ticker: Instrument symbol.

        Returns:
            MarketSnapshot or None.
        """
        return self._get_or_raise(venue).fetch_snapshot(ticker)

    def get_all_quotes(self, ticker: str) -> Dict[str, Quote]:
        """Fetch quotes from all connected venues for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            Dict mapping venue name to Quote.
        """
        result: Dict[str, Quote] = {}
        for venue, conn in self._connectors.items():
            if not conn.is_connected():
                continue
            q = conn.fetch_quote(ticker)
            if q is not None:
                result[venue.value] = q
        return result

    # ------------------------------------------------------------------
    # Latency
    # ------------------------------------------------------------------

    def get_latency(self, venue: Venue) -> float:
        """Return EWA latency for a venue.

        Args:
            venue: Target venue.

        Returns:
            Latency in milliseconds.
        """
        return self._get_or_raise(venue).get_latency_ms()

    def get_all_latencies(self) -> Dict[str, float]:
        """Return latency for all registered venues.

        Returns:
            Dict mapping venue name to latency in ms.
        """
        return {v.value: c.get_latency_ms() for v, c in self._connectors.items()}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_venue_stats(self, venue: Venue) -> ConnectorStats:
        """Return operational statistics for one venue.

        Args:
            venue: Target venue.

        Returns:
            ConnectorStats dataclass.
        """
        return self._get_or_raise(venue).get_stats()

    def get_all_stats(self) -> List[ConnectorStats]:
        """Return operational statistics for all venues.

        Returns:
            List of ConnectorStats.
        """
        return [c.get_stats() for c in self._connectors.values()]

    def get_summary(self) -> Dict[str, Any]:
        """Return a high-level gateway summary.

        Returns:
            Dict with counts and aggregate latency.
        """
        total = len(self._connectors)
        connected = sum(1 for c in self._connectors.values() if c.is_connected())
        latencies = [c.get_latency_ms() for c in self._connectors.values()]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        total_msgs = sum(c._messages_received for c in self._connectors.values())
        return {
            "total_venues": total,
            "connected_venues": connected,
            "disconnected_venues": total - connected,
            "avg_latency_ms": round(avg_lat, 3),
            "total_messages_received": total_msgs,
        }

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def heartbeat_all(self) -> Dict[str, bool]:
        """Send heartbeat to all connected venues.

        Returns:
            Dict mapping venue name to heartbeat success.
        """
        return {v.value: c.heartbeat() for v, c in self._connectors.items()}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_or_raise(self, venue: Venue) -> VenueConnector:
        conn = self._connectors.get(venue)
        if conn is None:
            raise KeyError(f"Venue {venue.value!r} not registered")
        return conn


# ---------------------------------------------------------------------------
# Default connector factory
# ---------------------------------------------------------------------------

_VENUE_ASSET_CLASSES: Dict[Venue, List[AssetClass]] = {
    Venue.NYSE: [AssetClass.EQUITY, AssetClass.ETF],
    Venue.NASDAQ: [AssetClass.EQUITY, AssetClass.ETF],
    Venue.TSX: [AssetClass.EQUITY, AssetClass.ETF],
    Venue.CME: [AssetClass.FUTURES, AssetClass.OPTIONS],
    Venue.ICE: [AssetClass.FUTURES, AssetClass.FIXED_INCOME],
    Venue.BINANCE: [AssetClass.CRYPTO],
    Venue.COINBASE: [AssetClass.CRYPTO],
    Venue.KRAKEN: [AssetClass.CRYPTO, AssetClass.FX],
    Venue.BYBIT: [AssetClass.CRYPTO],
    Venue.OKX: [AssetClass.CRYPTO, AssetClass.FUTURES],
    Venue.POLYGON: [AssetClass.EQUITY, AssetClass.OPTIONS, AssetClass.CRYPTO],
    Venue.ALPACA: [AssetClass.EQUITY, AssetClass.CRYPTO],
    Venue.TWELVEDATA: [AssetClass.EQUITY, AssetClass.FX, AssetClass.CRYPTO],
    Venue.YAHOO_FINANCE: [AssetClass.EQUITY, AssetClass.ETF, AssetClass.FUTURES],
}

_VENUE_LATENCIES: Dict[Venue, float] = {
    Venue.NYSE: 0.3,
    Venue.NASDAQ: 0.3,
    Venue.TSX: 1.0,
    Venue.CME: 0.5,
    Venue.ICE: 0.8,
    Venue.BINANCE: 5.0,
    Venue.COINBASE: 8.0,
    Venue.KRAKEN: 12.0,
    Venue.BYBIT: 10.0,
    Venue.OKX: 7.0,
    Venue.POLYGON: 50.0,
    Venue.ALPACA: 45.0,
    Venue.TWELVEDATA: 60.0,
    Venue.YAHOO_FINANCE: 200.0,
}


def create_default_connector(venue: Venue) -> VenueConnector:
    """Create a VenueConnector with production-appropriate defaults.

    Args:
        venue: Target venue.

    Returns:
        Pre-configured VenueConnector instance (not yet connected).
    """
    return VenueConnector(
        venue=venue,
        asset_classes=_VENUE_ASSET_CLASSES.get(venue, [AssetClass.EQUITY]),
        base_latency_ms=_VENUE_LATENCIES.get(venue, 50.0),
    )


def create_full_gateway() -> MarketDataGateway:
    """Create a MarketDataGateway pre-populated with all 14 venue connectors.

    Returns:
        MarketDataGateway with all venues registered (not yet connected).
    """
    gw = MarketDataGateway()
    for venue in Venue:
        gw.register_connector(create_default_connector(venue))
    return gw


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_gateway: Optional[MarketDataGateway] = None


def get_market_data_gateway() -> MarketDataGateway:
    """Return the singleton MarketDataGateway.

    Returns:
        Shared MarketDataGateway instance.
    """
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = create_full_gateway()
    return _default_gateway
