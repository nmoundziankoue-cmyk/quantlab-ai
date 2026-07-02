"""M18 — Market Microstructure Engine: Level I/II/III, order book analytics,
manipulation detection (spoofing, layering, quote stuffing, sweep, iceberg).

Pure Python, no external libraries.

All detection algorithms use heuristic thresholds over rolling quote/trade
history.  This is a simulation engine — in production these would be fed
by a real order-book feed.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Level I / II / III structures
# ---------------------------------------------------------------------------

@dataclass
class Level1Quote:
    """Best bid/offer with last trade price.

    Args:
        ticker: Instrument symbol.
        bid: Best bid price.
        ask: Best ask price.
        bid_size: Best bid quantity.
        ask_size: Best ask quantity.
        last: Last trade price.
        last_size: Last trade volume.
        timestamp: UTC time.
    """

    ticker: str
    bid: float
    ask: float
    bid_size: float = 0.0
    ask_size: float = 0.0
    last: float = 0.0
    last_size: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def spread(self) -> float:
        """Absolute bid-ask spread."""
        return self.ask - self.bid

    @property
    def mid(self) -> float:
        """Mid-point price."""
        return (self.bid + self.ask) / 2.0

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "bid": round(self.bid, 6),
            "ask": round(self.ask, 6),
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "last": round(self.last, 6),
            "last_size": self.last_size,
            "spread": round(self.spread, 6),
            "mid": round(self.mid, 6),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Level2Book:
    """Full depth-of-book (Level II) snapshot.

    Args:
        ticker: Instrument symbol.
        bids: Bid levels as (price, size) sorted best-first.
        asks: Ask levels as (price, size) sorted best-first.
        timestamp: UTC snapshot time.
    """

    ticker: str
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_bid_size(self) -> float:
        """Sum of all bid quantities on book."""
        return sum(s for _, s in self.bids)

    @property
    def total_ask_size(self) -> float:
        """Sum of all ask quantities on book."""
        return sum(s for _, s in self.asks)

    @property
    def best_bid(self) -> Optional[float]:
        """Best bid price (None if empty)."""
        return self.bids[0][0] if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        """Best ask price (None if empty)."""
        return self.asks[0][0] if self.asks else None

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "bids": [[round(p, 6), s] for p, s in self.bids],
            "asks": [[round(p, 6), s] for p, s in self.asks],
            "total_bid_size": self.total_bid_size,
            "total_ask_size": self.total_ask_size,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Level3Order:
    """Individual Level III order (participant-level).

    Args:
        order_id: Exchange-assigned order ID.
        ticker: Instrument symbol.
        side: BID or ASK.
        price: Limit price.
        size: Outstanding quantity.
        timestamp: Order entry time UTC.
        participant_id: Anonymised participant identifier.
    """

    order_id: str
    ticker: str
    side: str
    price: float
    size: float = 0.0
    quantity: float = 0.0
    visible_quantity: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    participant_id: str = ""

    def __post_init__(self) -> None:
        if self.size == 0.0 and self.quantity != 0.0:
            self.size = self.quantity

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "order_id": self.order_id,
            "ticker": self.ticker,
            "side": self.side,
            "price": round(self.price, 6),
            "size": self.size,
            "timestamp": self.timestamp.isoformat(),
            "participant_id": self.participant_id,
        }


# ---------------------------------------------------------------------------
# Analytics result types
# ---------------------------------------------------------------------------

@dataclass
class SpreadAnalytics:
    """Bid-ask spread analytics over a rolling window.

    Args:
        ticker: Instrument symbol.
        current_spread: Most recent absolute spread.
        current_spread_bps: Most recent spread in basis points.
        avg_spread: Average spread over window.
        avg_spread_bps: Average spread in basis points.
        min_spread: Minimum spread seen.
        max_spread: Maximum spread seen.
        spread_volatility: Std dev of spread observations.
        samples: Number of quote samples in window.
    """

    ticker: str
    current_spread: float
    current_spread_bps: float
    avg_spread: float
    avg_spread_bps: float
    min_spread: float
    max_spread: float
    spread_volatility: float
    samples: int

    @property
    def mean_spread(self) -> float:
        """Alias for avg_spread."""
        return self.avg_spread

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        d = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in self.__dict__.items()}
        d["mean_spread"] = round(self.avg_spread, 6)
        return d


@dataclass
class LiquidityHeatmap:
    """Price-level liquidity distribution.

    Args:
        ticker: Instrument symbol.
        price_levels: List of price levels.
        bid_liquidity: Cumulative bid size at each level.
        ask_liquidity: Cumulative ask size at each level.
        hotspot_bid: Price level with maximum bid concentration.
        hotspot_ask: Price level with maximum ask concentration.
    """

    ticker: str
    price_levels: List[float]
    bid_liquidity: List[float]
    ask_liquidity: List[float]
    hotspot_bid: float
    hotspot_ask: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "price_levels": [round(p, 6) for p in self.price_levels],
            "bid_liquidity": self.bid_liquidity,
            "ask_liquidity": self.ask_liquidity,
            "hotspot_bid": round(self.hotspot_bid, 6),
            "hotspot_ask": round(self.hotspot_ask, 6),
        }


@dataclass
class IcebergSignal:
    """Detected iceberg order indicator.

    Args:
        ticker: Instrument symbol.
        detected: Whether an iceberg pattern was detected.
        estimated_hidden_size: Estimated hidden quantity behind visible size.
        confidence: Detection confidence in [0, 1].
        price: Price level where iceberg was detected.
        side: BID or ASK.
    """

    ticker: str
    detected: bool
    estimated_hidden_size: float
    confidence: float
    price: float
    side: str

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "detected": self.detected,
            "estimated_hidden_size": round(self.estimated_hidden_size, 2),
            "confidence": round(self.confidence, 4),
            "price": round(self.price, 6),
            "side": self.side,
        }


@dataclass
class ManipulationSignal:
    """Detection result for a manipulation pattern.

    Args:
        ticker: Instrument symbol.
        pattern: SPOOFING, LAYERING, QUOTE_STUFFING.
        detected: Whether the pattern was triggered.
        confidence: Detection confidence in [0, 1].
        evidence_count: Number of observations supporting detection.
        description: Human-readable summary.
    """

    ticker: str
    pattern: str
    detected: bool
    confidence: float
    evidence_count: int
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "pattern": self.pattern,
            "detected": self.detected,
            "confidence": round(self.confidence, 4),
            "evidence_count": self.evidence_count,
            "description": self.description,
        }


@dataclass
class SweepSignal:
    """Detected order book sweep (aggressive market order).

    Args:
        ticker: Instrument symbol.
        detected: Whether a sweep was detected.
        direction: BUY or SELL (aggressor side).
        levels_swept: Number of price levels consumed.
        total_volume: Total volume of the sweep.
        avg_price: Volume-weighted average execution price.
        price_impact_bps: Price displacement in basis points.
    """

    ticker: str
    detected: bool
    direction: str
    levels_swept: int
    total_volume: float
    avg_price: float
    price_impact_bps: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "detected": self.detected,
            "direction": self.direction,
            "levels_swept": self.levels_swept,
            "total_volume": self.total_volume,
            "avg_price": round(self.avg_price, 6),
            "price_impact_bps": round(self.price_impact_bps, 2),
        }


@dataclass
class MarketMakerActivity:
    """Characterisation of market-maker behaviour.

    Args:
        ticker: Instrument symbol.
        is_active: Whether market-maker quoting patterns detected.
        quote_frequency: Quotes per second observed.
        avg_spread_bps: Average spread the MM is posting.
        inventory_bias: Positive = net long inventory implied; negative = net short.
        symmetry_score: How symmetrically balanced bid/ask sizes are (0–1).
    """

    ticker: str
    is_active: bool
    quote_frequency: float
    avg_spread_bps: float
    inventory_bias: float
    symmetry_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "is_active": self.is_active,
            "quote_frequency": round(self.quote_frequency, 4),
            "avg_spread_bps": round(self.avg_spread_bps, 4),
            "inventory_bias": round(self.inventory_bias, 4),
            "symmetry_score": round(self.symmetry_score, 4),
        }


@dataclass
class VWAPBands:
    """VWAP with upper/lower standard-deviation bands.

    Args:
        ticker: Instrument symbol.
        vwap: Volume-weighted average price.
        upper_1sd: VWAP + 1 standard deviation.
        lower_1sd: VWAP - 1 standard deviation.
        upper_2sd: VWAP + 2 standard deviations.
        lower_2sd: VWAP - 2 standard deviations.
        std_dev: Price standard deviation used.
        samples: Number of trades used in calculation.
    """

    ticker: str
    vwap: float
    upper_1sd: float
    lower_1sd: float
    upper_2sd: float
    lower_2sd: float
    std_dev: float
    samples: int

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


@dataclass
class LiquidityZone:
    """A price zone with historically elevated liquidity concentration.

    Args:
        ticker: Instrument symbol.
        price_low: Lower bound of zone.
        price_high: Upper bound of zone.
        avg_size: Average resting order size in this zone.
        strength: Relative strength versus other zones (0–1).
        side: BID or ASK.
    """

    ticker: str
    price_low: float
    price_high: float
    avg_size: float
    strength: float
    side: str

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "price_low": round(self.price_low, 6),
            "price_high": round(self.price_high, 6),
            "avg_size": round(self.avg_size, 2),
            "strength": round(self.strength, 4),
            "side": self.side,
        }


@dataclass
class TradeImpact:
    """Microstructure impact analysis of a single trade.

    Args:
        ticker: Instrument symbol.
        price: Trade price.
        volume: Trade volume.
        side: BUY or SELL.
        price_impact_bps: Estimated permanent price impact in bps.
        spread_consumed_bps: Half-spread consumed.
        is_aggressive: Whether the trade crossed the spread (aggressor).
    """

    ticker: str
    price: float
    volume: float
    side: str
    price_impact_bps: float
    spread_consumed_bps: float
    is_aggressive: bool

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "price": round(self.price, 6),
            "volume": self.volume,
            "side": self.side,
            "price_impact_bps": round(self.price_impact_bps, 4),
            "spread_consumed_bps": round(self.spread_consumed_bps, 4),
            "is_aggressive": self.is_aggressive,
        }


# ---------------------------------------------------------------------------
# Per-ticker state
# ---------------------------------------------------------------------------

@dataclass
class _QuoteObs:
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: datetime


@dataclass
class _TradeObs:
    price: float
    volume: float
    side: str
    timestamp: datetime


class _TickerState:
    """Rolling microstructure state for one ticker."""

    _MAX_QUOTES = 500
    _MAX_TRADES = 500
    _MAX_L3 = 200

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        self.quotes: Deque[_QuoteObs] = deque(maxlen=self._MAX_QUOTES)
        self.trades: Deque[_TradeObs] = deque(maxlen=self._MAX_TRADES)
        self.level2: Optional[Level2Book] = None
        self.level3_orders: List[Level3Order] = []

    def add_quote(self, bid: float, ask: float,
                  bid_size: float, ask_size: float) -> None:
        """Append a new quote observation."""
        self.quotes.append(_QuoteObs(bid, ask, bid_size, ask_size,
                                     datetime.now(timezone.utc)))

    def add_trade(self, price: float, volume: float, side: str) -> None:
        """Append a new trade observation."""
        self.trades.append(_TradeObs(price, volume, side,
                                     datetime.now(timezone.utc)))

    def latest_quote(self) -> Optional[_QuoteObs]:
        """Return the most-recent quote, or None."""
        return self.quotes[-1] if self.quotes else None

    def vwap_and_std(self) -> Tuple[float, float]:
        """Compute VWAP and price std dev from trade history."""
        if not self.trades:
            return 0.0, 0.0
        total_vol = sum(t.volume for t in self.trades)
        if total_vol == 0:
            return self.trades[-1].price, 0.0
        vwap = sum(t.price * t.volume for t in self.trades) / total_vol
        variance = sum(
            t.volume * (t.price - vwap) ** 2 for t in self.trades
        ) / total_vol
        return vwap, math.sqrt(variance)


# ---------------------------------------------------------------------------
# Microstructure Engine
# ---------------------------------------------------------------------------

class MicrostructureEngine:
    """Real-time market microstructure analytics engine.

    Maintains per-ticker rolling quote/trade state and computes:
    Level I/II/III views, spread analytics, bid-ask imbalance,
    liquidity heatmaps, iceberg detection, manipulation signals,
    sweep detection, market-maker activity, VWAP bands, liquidity zones.
    """

    def __init__(self) -> None:
        self._tickers: Dict[str, _TickerState] = {}

    def _state(self, ticker: str) -> _TickerState:
        ticker = ticker.upper()
        if ticker not in self._tickers:
            self._tickers[ticker] = _TickerState(ticker)
        return self._tickers[ticker]

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_quote(
        self,
        ticker: str,
        bid: float,
        ask: float,
        bid_size: float = 100.0,
        ask_size: float = 100.0,
    ) -> Level1Quote:
        """Ingest a new quote and return a Level I view.

        Args:
            ticker: Instrument symbol.
            bid: Best bid price.
            ask: Best ask price.
            bid_size: Bid quantity.
            ask_size: Ask quantity.

        Returns:
            Level1Quote with latest values.
        """
        st = self._state(ticker)
        st.add_quote(bid, ask, bid_size, ask_size)
        last_trade = st.trades[-1] if st.trades else None
        return Level1Quote(
            ticker=ticker.upper(),
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            last=last_trade.price if last_trade else (bid + ask) / 2.0,
            last_size=last_trade.volume if last_trade else 0.0,
            timestamp=datetime.now(timezone.utc),
        )

    def ingest_trade(
        self, ticker: str, price: float, volume: float, side: str
    ) -> TradeImpact:
        """Ingest a trade and compute microstructure impact.

        Args:
            ticker: Instrument symbol.
            price: Trade price.
            volume: Trade volume.
            side: BUY or SELL.

        Returns:
            TradeImpact with price impact estimates.
        """
        st = self._state(ticker)
        st.add_trade(price, volume, side)
        q = st.latest_quote()
        if q and q.bid > 0:
            spread_half = (q.ask - q.bid) / 2.0
            spread_consumed_bps = (spread_half / q.bid) * 10_000
            is_aggressive = price >= q.ask if side == "BUY" else price <= q.bid
        else:
            spread_consumed_bps = 5.0
            is_aggressive = True
        adv = max(1.0, sum(t.volume for t in st.trades))
        participation = volume / adv
        price_impact_bps = 10.0 * math.sqrt(participation) * (1 if side == "BUY" else -1) * abs(1.0)
        return TradeImpact(
            ticker=ticker.upper(),
            price=price,
            volume=volume,
            side=side,
            price_impact_bps=abs(price_impact_bps),
            spread_consumed_bps=spread_consumed_bps,
            is_aggressive=is_aggressive,
        )

    def ingest_order_book(
        self,
        ticker: str,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
    ) -> Level2Book:
        """Update the Level II book snapshot for a ticker.

        Args:
            ticker: Instrument symbol.
            bids: (price, size) bid levels, best first.
            asks: (price, size) ask levels, best first.

        Returns:
            Updated Level2Book.
        """
        st = self._state(ticker)
        book = Level2Book(
            ticker=ticker.upper(),
            bids=sorted(bids, key=lambda x: -x[0]),
            asks=sorted(asks, key=lambda x: x[0]),
            timestamp=datetime.now(timezone.utc),
        )
        st.level2 = book
        if book.bids and book.asks:
            best_bid = book.bids[0][0]
            best_ask = book.asks[0][0]
            bid_size = book.bids[0][1]
            ask_size = book.asks[0][1]
            st.add_quote(best_bid, best_ask, bid_size, ask_size)
        return book

    def add_level3_order(self, order: Level3Order) -> None:
        """Add a Level III participant order to the state.

        Args:
            order: Level3Order instance.
        """
        st = self._state(order.ticker)
        if len(st.level3_orders) >= _TickerState._MAX_L3:
            st.level3_orders.pop(0)
        st.level3_orders.append(order)

    # ------------------------------------------------------------------
    # Level views
    # ------------------------------------------------------------------

    def get_level1(self, ticker: str) -> Optional[Level1Quote]:
        """Return the current Level I quote.

        Args:
            ticker: Instrument symbol.

        Returns:
            Level1Quote or None if no data.
        """
        st = self._state(ticker)
        q = st.latest_quote()
        if q is None:
            return None
        last_trade = st.trades[-1] if st.trades else None
        return Level1Quote(
            ticker=ticker.upper(),
            bid=q.bid,
            ask=q.ask,
            bid_size=q.bid_size,
            ask_size=q.ask_size,
            last=last_trade.price if last_trade else (q.bid + q.ask) / 2.0 if q else 0.0,
            last_size=last_trade.volume if last_trade else 0.0,
            timestamp=q.timestamp,
        )

    def get_level2(self, ticker: str) -> Optional[Level2Book]:
        """Return the current Level II book.

        Args:
            ticker: Instrument symbol.

        Returns:
            Level2Book or None.
        """
        return self._state(ticker).level2

    def get_level3(self, ticker: str) -> List[Level3Order]:
        """Return all Level III orders for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            List of Level3Order.
        """
        return list(self._state(ticker).level3_orders)

    # ------------------------------------------------------------------
    # Spread analytics
    # ------------------------------------------------------------------

    def get_spread_analytics(self, ticker: str) -> Optional[SpreadAnalytics]:
        """Compute spread analytics from rolling quote history.

        Args:
            ticker: Instrument symbol.

        Returns:
            SpreadAnalytics or None if no quotes.
        """
        st = self._state(ticker)
        if not st.quotes:
            return None
        spreads = [q.ask - q.bid for q in st.quotes]
        mids = [(q.ask + q.bid) / 2.0 for q in st.quotes]
        n = len(spreads)
        avg_spread = sum(spreads) / n
        avg_mid = sum(mids) / n
        avg_spread_bps = (avg_spread / avg_mid * 10_000) if avg_mid > 0 else 0.0
        current = spreads[-1]
        current_bps = (current / mids[-1] * 10_000) if mids[-1] > 0 else 0.0
        variance = sum((s - avg_spread) ** 2 for s in spreads) / n
        return SpreadAnalytics(
            ticker=ticker.upper(),
            current_spread=current,
            current_spread_bps=current_bps,
            avg_spread=avg_spread,
            avg_spread_bps=avg_spread_bps,
            min_spread=min(spreads),
            max_spread=max(spreads),
            spread_volatility=math.sqrt(variance),
            samples=n,
        )

    # ------------------------------------------------------------------
    # Bid-ask imbalance
    # ------------------------------------------------------------------

    def get_bid_ask_imbalance(self, ticker: str) -> float:
        """Compute order book imbalance: (bid_size - ask_size) / (bid_size + ask_size).

        Uses the Level II book if available, otherwise the latest Level I quote.

        Args:
            ticker: Instrument symbol.

        Returns:
            Imbalance in [-1, 1]. Positive = bid pressure.

        Raises:
            ValueError: If no quote data is available.
        """
        st = self._state(ticker)
        if st.level2:
            bid_total = st.level2.total_bid_size
            ask_total = st.level2.total_ask_size
        else:
            q = st.latest_quote()
            if q is None:
                raise ValueError(f"No quote data for {ticker!r}")
            bid_total, ask_total = q.bid_size, q.ask_size
        total = bid_total + ask_total
        if total == 0:
            return 0.0
        return (bid_total - ask_total) / total

    # ------------------------------------------------------------------
    # Liquidity heatmap
    # ------------------------------------------------------------------

    def get_liquidity_heatmap(
        self, ticker: str, levels: int = 10
    ) -> Optional[LiquidityHeatmap]:
        """Build a price-level liquidity concentration heatmap.

        Args:
            ticker: Instrument symbol.
            levels: Number of price levels to include per side.

        Returns:
            LiquidityHeatmap or None if no Level II data.
        """
        st = self._state(ticker)
        book = st.level2
        if book is None:
            return None
        bid_levels = book.bids[:levels]
        ask_levels = book.asks[:levels]
        all_prices = [p for p, _ in bid_levels] + [p for p, _ in ask_levels]
        bid_liq = [s for _, s in bid_levels]
        ask_liq = [s for _, s in ask_levels]
        hotspot_bid = bid_levels[bid_liq.index(max(bid_liq))][0] if bid_liq else 0.0
        hotspot_ask = ask_levels[ask_liq.index(max(ask_liq))][0] if ask_liq else 0.0
        return LiquidityHeatmap(
            ticker=ticker.upper(),
            price_levels=all_prices,
            bid_liquidity=bid_liq,
            ask_liquidity=ask_liq,
            hotspot_bid=hotspot_bid,
            hotspot_ask=hotspot_ask,
        )

    # ------------------------------------------------------------------
    # Iceberg detection
    # ------------------------------------------------------------------

    def detect_iceberg(self, ticker: str) -> IcebergSignal:
        """Detect potential iceberg orders from trade/quote patterns.

        Heuristic: if total trades at a price level exceed the visible
        book size at that level by a large factor, an iceberg is suspected.

        Args:
            ticker: Instrument symbol.

        Returns:
            IcebergSignal with detection result.
        """
        st = self._state(ticker)
        if not st.trades or not st.quotes:
            return IcebergSignal(ticker=ticker.upper(), detected=False,
                                 estimated_hidden_size=0.0, confidence=0.0,
                                 price=0.0, side="BID")
        q = st.latest_quote()
        if q is None:
            return IcebergSignal(ticker=ticker.upper(), detected=False,
                                 estimated_hidden_size=0.0, confidence=0.0,
                                 price=0.0, side="BID")
        buy_vol = sum(t.volume for t in st.trades if t.side == "BUY"
                      and abs(t.price - q.ask) < 0.01)
        visible_ask = q.ask_size
        if visible_ask > 0 and buy_vol > visible_ask * 3:
            hidden = buy_vol - visible_ask
            confidence = min(1.0, hidden / (visible_ask * 10))
            return IcebergSignal(ticker=ticker.upper(), detected=True,
                                 estimated_hidden_size=hidden,
                                 confidence=confidence, price=q.ask, side="ASK")
        sell_vol = sum(t.volume for t in st.trades if t.side == "SELL"
                       and abs(t.price - q.bid) < 0.01)
        visible_bid = q.bid_size
        if visible_bid > 0 and sell_vol > visible_bid * 3:
            hidden = sell_vol - visible_bid
            confidence = min(1.0, hidden / (visible_bid * 10))
            return IcebergSignal(ticker=ticker.upper(), detected=True,
                                 estimated_hidden_size=hidden,
                                 confidence=confidence, price=q.bid, side="BID")
        return IcebergSignal(ticker=ticker.upper(), detected=False,
                             estimated_hidden_size=0.0, confidence=0.05,
                             price=q.bid, side="BID")

    # ------------------------------------------------------------------
    # Spoofing detection
    # ------------------------------------------------------------------

    def detect_spoofing(self, ticker: str) -> ManipulationSignal:
        """Detect potential spoofing: large orders added then cancelled rapidly.

        Heuristic: high bid-ask imbalance combined with order-size volatility
        in the Level III order log.

        Args:
            ticker: Instrument symbol.

        Returns:
            ManipulationSignal for SPOOFING pattern.
        """
        st = self._state(ticker)
        evidence = 0
        if len(st.quotes) >= 5:
            imbalances = []
            for q in list(st.quotes)[-10:]:
                total = q.bid_size + q.ask_size
                imb = abs(q.bid_size - q.ask_size) / total if total > 0 else 0.0
                imbalances.append(imb)
            avg_imb = sum(imbalances) / len(imbalances)
            if avg_imb > 0.7:
                evidence += 1
            sizes = [q.bid_size + q.ask_size for q in list(st.quotes)[-10:]]
            if len(sizes) >= 3:
                mean_s = sum(sizes) / len(sizes)
                std_s = math.sqrt(sum((s - mean_s) ** 2 for s in sizes) / len(sizes))
                if mean_s > 0 and std_s / mean_s > 0.5:
                    evidence += 1
        if len(st.level3_orders) >= 3:
            recent = st.level3_orders[-10:]
            large_orders = [o for o in recent if o.size > 1000]
            if len(large_orders) >= 2:
                evidence += 1
        detected = evidence >= 2
        confidence = min(1.0, evidence / 3.0)
        return ManipulationSignal(
            ticker=ticker.upper(), pattern="SPOOFING", detected=detected,
            confidence=confidence, evidence_count=evidence,
            description="Large order placement/cancellation pattern" if detected else "No spoofing pattern",
        )

    # ------------------------------------------------------------------
    # Layering detection
    # ------------------------------------------------------------------

    def detect_layering(self, ticker: str) -> ManipulationSignal:
        """Detect layering: multiple stacked orders on one side to influence price.

        Heuristic: book has many more levels on one side with stepwise sizes.

        Args:
            ticker: Instrument symbol.

        Returns:
            ManipulationSignal for LAYERING pattern.
        """
        st = self._state(ticker)
        book = st.level2
        evidence = 0
        if book and len(book.bids) >= 5 and len(book.asks) >= 5:
            bid_sizes = [s for _, s in book.bids[:5]]
            ask_sizes = [s for _, s in book.asks[:5]]
            bid_total = sum(bid_sizes)
            ask_total = sum(ask_sizes)
            total = bid_total + ask_total
            if total > 0:
                imbalance = abs(bid_total - ask_total) / total
                if imbalance > 0.6:
                    evidence += 1
            sizes = bid_sizes if bid_total > ask_total else ask_sizes
            if len(sizes) >= 3:
                diffs = [abs(sizes[i] - sizes[i - 1]) for i in range(1, len(sizes))]
                if max(diffs) > 0 and min(diffs) / max(diffs) > 0.8:
                    evidence += 1
        if len(st.quotes) >= 3:
            recent_imb = []
            for q in list(st.quotes)[-5:]:
                t = q.bid_size + q.ask_size
                recent_imb.append((q.bid_size - q.ask_size) / t if t > 0 else 0.0)
            if recent_imb and all(x > 0.5 for x in recent_imb):
                evidence += 1
        detected = evidence >= 2
        confidence = min(1.0, evidence / 3.0)
        return ManipulationSignal(
            ticker=ticker.upper(), pattern="LAYERING", detected=detected,
            confidence=confidence, evidence_count=evidence,
            description="Stacked order layering on one side" if detected else "No layering pattern",
        )

    # ------------------------------------------------------------------
    # Quote stuffing detection
    # ------------------------------------------------------------------

    def detect_quote_stuffing(self, ticker: str) -> ManipulationSignal:
        """Detect quote stuffing: abnormally high quote frequency.

        Heuristic: more than 50 quote updates in the rolling window.

        Args:
            ticker: Instrument symbol.

        Returns:
            ManipulationSignal for QUOTE_STUFFING pattern.
        """
        st = self._state(ticker)
        n_quotes = len(st.quotes)
        evidence = 0
        if n_quotes >= 50:
            evidence += 1
        if n_quotes >= 100:
            evidence += 1
        recent = list(st.quotes)[-20:] if n_quotes >= 20 else list(st.quotes)
        if len(recent) >= 5:
            price_changes = 0
            for i in range(1, len(recent)):
                if abs(recent[i].ask - recent[i - 1].ask) < 1e-6:
                    price_changes += 1
            if price_changes / max(1, len(recent) - 1) > 0.8:
                evidence += 1
        detected = evidence >= 2
        confidence = min(1.0, evidence / 3.0)
        return ManipulationSignal(
            ticker=ticker.upper(), pattern="QUOTE_STUFFING", detected=detected,
            confidence=confidence, evidence_count=evidence,
            description="Abnormal quote update frequency" if detected else "Normal quote frequency",
        )

    # ------------------------------------------------------------------
    # Sweep detection
    # ------------------------------------------------------------------

    def detect_sweep(self, ticker: str) -> SweepSignal:
        """Detect an order book sweep from recent trade activity.

        Heuristic: consecutive trades on same side at progressively worse prices
        consuming multiple book levels.

        Args:
            ticker: Instrument symbol.

        Returns:
            SweepSignal with sweep characterisation.
        """
        st = self._state(ticker)
        if len(st.trades) < 3:
            return SweepSignal(ticker=ticker.upper(), detected=False,
                               direction="BUY", levels_swept=0,
                               total_volume=0.0, avg_price=0.0, price_impact_bps=0.0)
        recent = list(st.trades)[-10:]
        buy_run = [t for t in recent if t.side == "BUY"]
        sell_run = [t for t in recent if t.side == "SELL"]
        for run, direction in [(buy_run, "BUY"), (sell_run, "SELL")]:
            if len(run) < 3:
                continue
            prices = [t.price for t in run]
            if direction == "BUY":
                is_sweep = all(prices[i] >= prices[i - 1] for i in range(1, len(prices)))
            else:
                is_sweep = all(prices[i] <= prices[i - 1] for i in range(1, len(prices)))
            if is_sweep:
                total_vol = sum(t.volume for t in run)
                avg_price = sum(t.price * t.volume for t in run) / total_vol if total_vol > 0 else prices[0]
                impact = abs(prices[-1] - prices[0]) / prices[0] * 10_000
                unique_prices = len(set(round(p, 4) for p in prices))
                return SweepSignal(
                    ticker=ticker.upper(), detected=True, direction=direction,
                    levels_swept=unique_prices, total_volume=total_vol,
                    avg_price=avg_price, price_impact_bps=impact,
                )
        return SweepSignal(ticker=ticker.upper(), detected=False, direction="BUY",
                           levels_swept=0, total_volume=0.0, avg_price=0.0,
                           price_impact_bps=0.0)

    # ------------------------------------------------------------------
    # Market maker activity
    # ------------------------------------------------------------------

    def get_market_maker_activity(self, ticker: str) -> MarketMakerActivity:
        """Characterise market-maker presence from quote patterns.

        Args:
            ticker: Instrument symbol.

        Returns:
            MarketMakerActivity summary.
        """
        st = self._state(ticker)
        if len(st.quotes) < 3:
            return MarketMakerActivity(ticker=ticker.upper(), is_active=False,
                                       quote_frequency=0.0, avg_spread_bps=0.0,
                                       inventory_bias=0.0, symmetry_score=0.0)
        recent = list(st.quotes)[-20:]
        spreads = [q.ask - q.bid for q in recent]
        mids = [(q.ask + q.bid) / 2.0 for q in recent]
        avg_mid = sum(mids) / len(mids) if mids else 1.0
        avg_spread = sum(spreads) / len(spreads)
        avg_spread_bps = avg_spread / avg_mid * 10_000 if avg_mid > 0 else 0.0
        symmetry_scores = []
        for q in recent:
            total = q.bid_size + q.ask_size
            sym = 1.0 - abs(q.bid_size - q.ask_size) / total if total > 0 else 0.0
            symmetry_scores.append(sym)
        avg_sym = sum(symmetry_scores) / len(symmetry_scores)
        bid_sizes = [q.bid_size for q in recent]
        ask_sizes = [q.ask_size for q in recent]
        inventory_bias = (sum(bid_sizes) - sum(ask_sizes)) / (sum(bid_sizes) + sum(ask_sizes) + 1e-9)
        quote_freq = len(recent) / max(1.0, len(recent))
        is_active = avg_spread_bps < 20.0 and avg_sym > 0.5
        return MarketMakerActivity(
            ticker=ticker.upper(), is_active=is_active,
            quote_frequency=quote_freq, avg_spread_bps=avg_spread_bps,
            inventory_bias=inventory_bias, symmetry_score=avg_sym,
        )

    # ------------------------------------------------------------------
    # Queue position
    # ------------------------------------------------------------------

    def get_queue_position(self, ticker: str, price: float) -> int:
        """Estimate queue position at a given price level.

        Returns the total quantity ahead in the queue at the specified
        price level from the Level II book.

        Args:
            ticker: Instrument symbol.
            price: Price level to query.

        Returns:
            Estimated quantity ahead (0 if no data at that level).
        """
        st = self._state(ticker)
        book = st.level2
        if book is None:
            return 0
        for bid_price, bid_size in book.bids:
            if abs(bid_price - price) < 1e-6:
                return int(bid_size * 0.5)
        for ask_price, ask_size in book.asks:
            if abs(ask_price - price) < 1e-6:
                return int(ask_size * 0.5)
        return 0

    # ------------------------------------------------------------------
    # VWAP bands
    # ------------------------------------------------------------------

    def get_vwap_bands(self, ticker: str) -> Optional[VWAPBands]:
        """Compute VWAP ± 1sd and ± 2sd bands from trade history.

        Args:
            ticker: Instrument symbol.

        Returns:
            VWAPBands or None if no trade data.
        """
        st = self._state(ticker)
        if not st.trades:
            return None
        vwap, std_dev = st.vwap_and_std()
        return VWAPBands(
            ticker=ticker.upper(),
            vwap=vwap,
            upper_1sd=vwap + std_dev,
            lower_1sd=vwap - std_dev,
            upper_2sd=vwap + 2 * std_dev,
            lower_2sd=vwap - 2 * std_dev,
            std_dev=std_dev,
            samples=len(st.trades),
        )

    # ------------------------------------------------------------------
    # Liquidity zones
    # ------------------------------------------------------------------

    def get_liquidity_zones(
        self, ticker: str, n_zones: int = 5
    ) -> List[LiquidityZone]:
        """Identify price zones with elevated liquidity concentration.

        Uses the Level II book to find price clusters with the largest
        resting size.

        Args:
            ticker: Instrument symbol.
            n_zones: Maximum number of zones to return.

        Returns:
            List of LiquidityZone sorted by strength descending.
        """
        st = self._state(ticker)
        book = st.level2
        if book is None:
            return []
        zones: List[LiquidityZone] = []
        all_levels = [(p, s, "BID") for p, s in book.bids] + \
                     [(p, s, "ASK") for p, s in book.asks]
        if not all_levels:
            return []
        max_size = max(s for _, s, _ in all_levels)
        for price, size, side in sorted(all_levels, key=lambda x: -x[1])[:n_zones * 2]:
            tick_size = price * 0.001
            zones.append(LiquidityZone(
                ticker=ticker.upper(),
                price_low=price - tick_size,
                price_high=price + tick_size,
                avg_size=size,
                strength=size / max_size if max_size > 0 else 0.0,
                side=side,
            ))
        return sorted(zones, key=lambda z: -z.strength)[:n_zones]

    # ------------------------------------------------------------------
    # Aggregate stats
    # ------------------------------------------------------------------

    def get_tracked_tickers(self) -> List[str]:
        """Return all tickers with active microstructure state.

        Returns:
            List of ticker symbols.
        """
        return list(self._tickers.keys())

    def compute_vwap_bands(self, ticker: str) -> Optional[VWAPBands]:
        """Alias for get_vwap_bands."""
        return self.get_vwap_bands(ticker)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[MicrostructureEngine] = None


def get_microstructure_engine() -> MicrostructureEngine:
    """Return the singleton MicrostructureEngine.

    Returns:
        Shared MicrostructureEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = MicrostructureEngine()
    return _default_engine
