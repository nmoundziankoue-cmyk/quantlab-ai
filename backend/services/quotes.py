"""Market data service for Milestone 2 / M10.

Provides:
- Full real-time quotes (price, change, fundamentals, 52-week range)
- Batch quotes for multiple tickers
- Historical OHLCV with interval support
- News feed per ticker with financial-sentiment scoring
- Economic calendar (Fed meeting dates + key monthly releases)

Cache strategy (M10):
  - Namespaced keys via ``cache.ns_get / cache.ns_set``
  - Cache hits/misses reported to ``MetricsCollector``
  - Stale-while-revalidate for ``get_quote``:
      fresh (< QUOTE_FRESH_TTL) → serve immediately
      stale (< QUOTE_STALE_TTL) → serve + background refresh
      expired → block and fetch fresh
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

from config import settings
from schemas.market import (
    BatchQuoteRead,
    CalendarRead,
    EconEvent,
    NewsArticle,
    NewsRead,
    OHLCVPoint,
    OHLCVRead,
    QuoteRead,
    SentimentRead,
)
from services.cache import cache
from services.metrics import metrics

# ---------------------------------------------------------------------------
# Stale-while-revalidate configuration
# ---------------------------------------------------------------------------

QUOTE_FRESH_TTL: int = 30    # seconds — serve without background refresh
QUOTE_STALE_TTL: int = 300   # seconds — serve stale + trigger background refresh
QUOTE_MAX_TTL: int = 600     # seconds — cache entry max lifetime

_refreshing_tickers: set[str] = set()
_refresh_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Sentiment lexicon
# ---------------------------------------------------------------------------

_BULLISH: frozenset[str] = frozenset({
    "surge", "surges", "rally", "rallies", "gain", "gains", "rise", "rises",
    "jump", "jumps", "beat", "beats", "exceed", "exceeds", "strong", "record",
    "profit", "profits", "growth", "upgrade", "buy", "bullish", "boom",
    "recover", "recovers", "outperform", "positive", "high", "upside", "lift",
    "lifts", "soar", "soars", "breakout", "opportunity",
})

_BEARISH: frozenset[str] = frozenset({
    "fall", "falls", "drop", "drops", "crash", "crashes", "decline", "declines",
    "plunge", "plunges", "miss", "misses", "weak", "loss", "losses", "negative",
    "downgrade", "sell", "bearish", "recession", "risk", "risks", "concern",
    "concerns", "warn", "warns", "warning", "low", "underperform", "cut", "cuts",
    "layoff", "layoffs", "debt", "downside", "fear", "fears", "selloff",
    "collapse", "bankruptcy",
})


def _score_headline(title: str) -> float:
    """Score a headline from -1.0 (very bearish) to +1.0 (very bullish)."""
    words = title.lower().split()
    bull = sum(1 for w in words if w.rstrip(".,!?;:") in _BULLISH)
    bear = sum(1 for w in words if w.rstrip(".,!?;:") in _BEARISH)
    total = bull + bear
    if total == 0:
        return 0.0
    return round((bull - bear) / total, 3)


def _label(score: float) -> str:
    if score > 0.15:
        return "bullish"
    if score < -0.15:
        return "bearish"
    return "neutral"


def _signal(score: float) -> str:
    if score > 0.4:
        return "Strong Buy"
    if score > 0.15:
        return "Buy"
    if score < -0.4:
        return "Strong Sell"
    if score < -0.15:
        return "Sell"
    return "Hold"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        return None if (f != f or f == float("inf") or f == float("-inf")) else f
    except Exception:
        return None


def _safe_int(val) -> Optional[int]:
    try:
        return int(val)
    except Exception:
        return None


def _fi_attr(fi, name: str):
    """Read an attribute from a fast_info object without raising on KeyError."""
    try:
        return getattr(fi, name, None)
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Public API — Quote
# ---------------------------------------------------------------------------

def _fetch_and_cache_quote(ticker: str, ns_key: str) -> QuoteRead:
    """Fetch a fresh quote from yfinance and store it in cache."""
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        info = t.info or {}
    except Exception as exc:
        raise ValueError(f"Cannot fetch quote for {ticker}: {exc}") from exc

    price = _safe_float(_fi_attr(fi, "last_price"))
    if price is None:
        raise ValueError(f"No price data for ticker '{ticker}' — it may be delisted or invalid")

    prev_close = _safe_float(_fi_attr(fi, "previous_close")) or price
    change = round(price - prev_close, 4)
    change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0

    try:
        quote = QuoteRead(
            ticker=ticker,
            name=info.get("shortName") or info.get("longName") or ticker,
            exchange=info.get("exchange") or _fi_attr(fi, "exchange") or "—",
            currency=info.get("currency") or _fi_attr(fi, "currency") or "USD",
            price=round(price, 4),
            change=change,
            change_pct=change_pct,
            prev_close=round(prev_close, 4),
            open=_safe_float(info.get("regularMarketOpen") or _fi_attr(fi, "open")),
            day_high=_safe_float(info.get("dayHigh") or _fi_attr(fi, "day_high")),
            day_low=_safe_float(info.get("dayLow") or _fi_attr(fi, "day_low")),
            volume=_safe_int(info.get("regularMarketVolume") or _fi_attr(fi, "last_volume")),
            avg_volume=_safe_int(info.get("averageVolume")),
            market_cap=_safe_float(info.get("marketCap") or _fi_attr(fi, "market_cap")),
            pe_ratio=_safe_float(info.get("trailingPE")),
            forward_pe=_safe_float(info.get("forwardPE")),
            eps=_safe_float(info.get("trailingEps")),
            dividend_yield=_safe_float(info.get("dividendYield")),
            week_52_high=_safe_float(
                info.get("fiftyTwoWeekHigh") or _fi_attr(fi, "fifty_two_week_high")
            ),
            week_52_low=_safe_float(
                info.get("fiftyTwoWeekLow") or _fi_attr(fi, "fifty_two_week_low")
            ),
            sector=info.get("sector") or "Unknown",
            industry=info.get("industry") or "Unknown",
            fetched_at=_now_iso(),
        )
    except Exception as exc:
        raise ValueError(f"Failed to build quote for {ticker}: {exc}") from exc

    envelope = {"data": quote.model_dump(), "fetched_at": time.time()}
    cache.ns_set(ns_key, envelope, ttl=QUOTE_MAX_TTL)
    return quote


def _schedule_background_refresh(ticker: str, ns_key: str) -> None:
    """Trigger a background quote refresh if one isn't already running."""
    with _refresh_lock:
        if ticker in _refreshing_tickers:
            return
        _refreshing_tickers.add(ticker)

    def _run():
        try:
            _fetch_and_cache_quote(ticker, ns_key)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Background refresh failed for %s: %s", ticker, exc)
        finally:
            with _refresh_lock:
                _refreshing_tickers.discard(ticker)

    threading.Thread(target=_run, daemon=True, name=f"quote-refresh-{ticker}").start()


def get_quote(ticker: str) -> QuoteRead:
    """Return a full real-time quote for *ticker*.

    Cache strategy (stale-while-revalidate):
    - age < QUOTE_FRESH_TTL: serve immediately (cache hit)
    - age < QUOTE_STALE_TTL: serve stale + trigger background refresh (cache hit)
    - expired: block and fetch fresh (cache miss)

    Raises:
        ValueError: If yfinance returns no data for the ticker.
    """
    ns_key = f"quote:{ticker}"
    envelope = cache.ns_get(ns_key)

    if envelope and isinstance(envelope, dict):
        age = time.time() - envelope.get("fetched_at", 0)
        cached_data = envelope.get("data")
        if cached_data:
            if age < QUOTE_STALE_TTL:
                metrics.inc_cache_hit()
                if age >= QUOTE_FRESH_TTL:
                    _schedule_background_refresh(ticker, ns_key)
                return QuoteRead(**cached_data)

    metrics.inc_cache_miss()
    return _fetch_and_cache_quote(ticker, ns_key)


def get_current_prices(tickers: list[str]) -> dict[str, "Decimal"]:
    """Return a {ticker: Decimal(price)} map for use by paper trading engine.

    Silently omits tickers for which no price can be fetched.
    """
    from decimal import Decimal
    result: dict[str, Decimal] = {}
    for ticker in tickers:
        try:
            q = get_quote(ticker)
            result[ticker] = Decimal(str(q.price))
        except Exception:
            pass
    return result


def get_batch_quotes(tickers: list[str]) -> BatchQuoteRead:
    """Return quotes for multiple tickers.

    Successful quotes are keyed by ticker; failures are recorded in ``errors``.
    """
    quotes: dict[str, QuoteRead] = {}
    errors: dict[str, str] = {}

    for ticker in tickers:
        try:
            quotes[ticker] = get_quote(ticker)
        except Exception as exc:
            errors[ticker] = str(exc)

    return BatchQuoteRead(quotes=quotes, errors=errors)


# ---------------------------------------------------------------------------
# Public API — OHLCV
# ---------------------------------------------------------------------------

_VALID_INTERVALS = frozenset({"1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d", "1wk", "1mo"})
_VALID_PERIODS = frozenset({"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"})


def get_ohlcv(
    ticker: str,
    interval: str = "1d",
    period: str = "6mo",
) -> OHLCVRead:
    """Return historical OHLCV bars for *ticker*.

    Args:
        ticker:   Uppercase ticker symbol.
        interval: Bar size (``1d``, ``1wk``, ``1h``, ``5m``, …).
        period:   Look-back window (``6mo``, ``1y``, ``ytd``, …).

    Raises:
        ValueError: If the interval/period combination is invalid or yfinance returns no data.
    """
    interval = interval if interval in _VALID_INTERVALS else "1d"
    period = period if period in _VALID_PERIODS else "6mo"

    key = f"ohlcv:{ticker}:{interval}:{period}"
    cached = cache.ns_get(key)
    if cached:
        metrics.inc_cache_hit()
        return OHLCVRead(**cached)

    try:
        raw = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        raise ValueError(f"yfinance OHLCV failed for {ticker}: {exc}") from exc

    if raw is None or raw.empty:
        raise ValueError(f"No OHLCV data returned for '{ticker}'")

    # Flatten MultiIndex columns (yfinance ≥ 0.2 style)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]

    required = {"Open", "High", "Low", "Close"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"OHLCV data missing columns {missing} for '{ticker}'")

    raw = raw.dropna(subset=list(required))
    has_volume = "Volume" in raw.columns

    data: list[OHLCVPoint] = []
    for idx, row in raw.iterrows():
        # idx is a Timestamp for time-based intervals, or a date
        if hasattr(idx, "strftime"):
            time_str = idx.strftime("%Y-%m-%d") if interval in {"1d", "1wk", "1mo"} else idx.isoformat()
        else:
            time_str = str(idx)

        data.append(
            OHLCVPoint(
                time=time_str,
                open=round(float(row["Open"]), 4),
                high=round(float(row["High"]), 4),
                low=round(float(row["Low"]), 4),
                close=round(float(row["Close"]), 4),
                volume=int(row["Volume"]) if has_volume and pd.notna(row["Volume"]) else 0,
            )
        )

    result = OHLCVRead(ticker=ticker, interval=interval, period=period, data=data)
    metrics.inc_cache_miss()
    cache.ns_set(key, result.model_dump(), ttl=settings.ohlcv_cache_ttl_seconds)
    return result


# ---------------------------------------------------------------------------
# Public API — News & Sentiment
# ---------------------------------------------------------------------------

def get_news(ticker: str, max_articles: int = 15) -> NewsRead:
    """Fetch recent news for *ticker* with per-article sentiment scores.

    Args:
        ticker:       Uppercase ticker symbol.
        max_articles: Maximum articles to return (default 15).

    Returns:
        NewsRead with articles, per-article sentiment, and aggregate signal.
    """
    key = f"news:{ticker}"
    cached = cache.ns_get(key)
    if cached:
        metrics.inc_cache_hit()
        return NewsRead(**cached)

    try:
        raw_news = yf.Ticker(ticker).news or []
    except Exception:
        raw_news = []

    articles: list[NewsArticle] = []
    for item in raw_news[:max_articles]:
        if not isinstance(item, dict):
            continue

        # yfinance 1.1.x nests everything under a "content" key
        content = item.get("content") or item
        if not isinstance(content, dict):
            continue

        title = content.get("title") or item.get("title") or ""
        if not title:
            continue

        score = _score_headline(title)

        # Publisher — nested under provider.displayName in 1.1.x
        provider = content.get("provider") or {}
        publisher = (
            provider.get("displayName")
            or item.get("publisher")
            or "Unknown"
        )

        # Link — clickThroughUrl.url or canonicalUrl.url in 1.1.x
        click_url = (content.get("clickThroughUrl") or {}).get("url")
        canon_url = (content.get("canonicalUrl") or {}).get("url")
        link = click_url or canon_url or item.get("link") or item.get("url") or ""

        # Published date — ISO string in 1.1.x ("2026-06-27T12:00:00Z"), unix ts in legacy
        pub_raw = content.get("pubDate") or item.get("providerPublishTime") or item.get("published") or ""
        try:
            if isinstance(pub_raw, str) and "T" in pub_raw:
                pub_dt = pub_raw  # already ISO
            else:
                pub_dt = datetime.fromtimestamp(int(pub_raw), tz=timezone.utc).isoformat()
        except Exception:
            pub_dt = _now_iso()

        # Related tickers — legacy field; 1.1.x doesn't expose them per article
        related = [
            t.upper()
            for t in (item.get("relatedTickers") or [])
            if isinstance(t, str)
        ]

        articles.append(
            NewsArticle(
                uuid=str(content.get("id") or item.get("id") or uuid.uuid4()),
                title=title,
                publisher=publisher,
                link=link,
                published_at=pub_dt,
                related_tickers=related,
                sentiment_score=score,
                sentiment_label=_label(score),
            )
        )

    # Aggregate sentiment
    if articles:
        avg_score = round(sum(a.sentiment_score for a in articles) / len(articles), 3)
    else:
        avg_score = 0.0

    result = NewsRead(
        ticker=ticker,
        articles=articles,
        overall_score=avg_score,
        overall_label=_label(avg_score),
        signal=_signal(avg_score),
    )
    metrics.inc_cache_miss()
    cache.ns_set(key, result.model_dump(), ttl=settings.news_cache_ttl_seconds)
    return result


def get_sentiment(ticker: str) -> SentimentRead:
    """Return a condensed sentiment snapshot for *ticker*."""
    news = get_news(ticker)
    return SentimentRead(
        ticker=ticker,
        score=news.overall_score,
        label=news.overall_label,
        signal=news.signal,
        article_count=len(news.articles),
    )


# ---------------------------------------------------------------------------
# Public API — Economic Calendar
# ---------------------------------------------------------------------------

def _fomc_dates_2025_2026() -> list[tuple[str, str, str]]:
    """Return (date, time, description) for known FOMC announcement dates."""
    return [
        # 2025 remaining
        ("2025-07-30", "14:00", "FOMC Rate Decision"),
        ("2025-09-17", "14:00", "FOMC Rate Decision"),
        ("2025-10-29", "14:00", "FOMC Rate Decision"),
        ("2025-12-10", "14:00", "FOMC Rate Decision"),
        # 2026
        ("2026-01-28", "14:00", "FOMC Rate Decision"),
        ("2026-03-18", "14:00", "FOMC Rate Decision"),
        ("2026-04-29", "14:00", "FOMC Rate Decision"),
        ("2026-06-10", "14:00", "FOMC Rate Decision"),
        ("2026-07-29", "14:00", "FOMC Rate Decision"),
        ("2026-09-16", "14:00", "FOMC Rate Decision"),
        ("2026-10-28", "14:00", "FOMC Rate Decision"),
        ("2026-12-09", "14:00", "FOMC Rate Decision"),
    ]


def _recurring_events(year: int) -> list[tuple[str, str, str, str]]:
    """Generate (date, time, event, importance) for monthly macro releases."""
    events = []
    for month in range(1, 13):
        # Non-Farm Payrolls — first Friday of the month
        d = date(year, month, 1)
        while d.weekday() != 4:  # 4 = Friday
            d += timedelta(days=1)
        events.append((d.isoformat(), "08:30", "Non-Farm Payrolls", "high"))

        # CPI — typically 10th-11th
        cpi_day = date(year, month, 10)
        if cpi_day.weekday() >= 5:  # weekend → push to Monday
            cpi_day += timedelta(days=7 - cpi_day.weekday())
        events.append((cpi_day.isoformat(), "08:30", "CPI (YoY)", "high"))

        # PPI — typically 12th-13th
        ppi_day = date(year, month, 12)
        if ppi_day.weekday() >= 5:
            ppi_day += timedelta(days=7 - ppi_day.weekday())
        events.append((ppi_day.isoformat(), "08:30", "PPI (YoY)", "medium"))

        # Retail Sales — mid-month
        rs_day = date(year, month, 15)
        if rs_day.weekday() >= 5:
            rs_day += timedelta(days=7 - rs_day.weekday())
        events.append((rs_day.isoformat(), "08:30", "Retail Sales (MoM)", "medium"))

    # GDP — quarterly (last week of Jan, Apr, Jul, Oct)
    for (m, d_) in [(1, 27), (4, 27), (7, 27), (10, 27)]:
        gd = date(year, m, d_)
        if gd.weekday() >= 5:
            gd += timedelta(days=7 - gd.weekday())
        events.append((gd.isoformat(), "08:30", "GDP (QoQ Advance)", "high"))

    return events


def get_economic_calendar(days_ahead: int = 30) -> CalendarRead:
    """Return macro events for the next *days_ahead* calendar days.

    Args:
        days_ahead: Window in calendar days from today (max 365).

    Returns:
        CalendarRead with sorted events.
    """
    days_ahead = min(days_ahead, 365)
    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    key = f"calendar:{today.isoformat()}:{days_ahead}"
    cached = cache.ns_get(key)
    if cached:
        metrics.inc_cache_hit()
        return CalendarRead(**cached)

    events: list[EconEvent] = []

    # FOMC dates
    for (d_str, t_str, desc) in _fomc_dates_2025_2026():
        d = date.fromisoformat(d_str)
        if today <= d <= end_date:
            events.append(EconEvent(date=d_str, time=t_str, event=desc, importance="high"))

    # Recurring macro
    for year in {today.year, end_date.year}:
        for (d_str, t_str, event, imp) in _recurring_events(year):
            d = date.fromisoformat(d_str)
            if today <= d <= end_date:
                events.append(
                    EconEvent(date=d_str, time=t_str, event=event, importance=imp)
                )

    events.sort(key=lambda e: e.date)

    result = CalendarRead(
        from_date=today.isoformat(),
        to_date=end_date.isoformat(),
        events=events,
    )
    metrics.inc_cache_miss()
    cache.ns_set(key, result.model_dump(), ttl=3600)  # 1h — calendar doesn't change
    return result
