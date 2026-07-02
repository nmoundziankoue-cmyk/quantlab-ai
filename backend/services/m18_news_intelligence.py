"""M18 — News Intelligence: real-time news ingestion, NLP, and sentiment analysis.

Implements news ingestion, rule-based sentiment scoring, entity extraction,
topic classification, trend detection, sector impact mapping, and a news-driven
market signal generator.

Pure Python, no external libraries.
"""
from __future__ import annotations

import math
import re
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NewsSentiment(str, Enum):
    """Sentiment label for a news item."""
    VERY_POSITIVE = "VERY_POSITIVE"
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    VERY_NEGATIVE = "VERY_NEGATIVE"


class NewsCategory(str, Enum):
    """Broad category of news content."""
    EARNINGS = "EARNINGS"
    MACRO = "MACRO"
    REGULATORY = "REGULATORY"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    PRODUCT = "PRODUCT"
    MANAGEMENT = "MANAGEMENT"
    GEOPOLITICAL = "GEOPOLITICAL"
    LEGAL = "LEGAL"
    DIVIDEND = "DIVIDEND"
    ANALYST = "ANALYST"
    MARKET = "MARKET"
    OTHER = "OTHER"


class MarketSignalStrength(str, Enum):
    """Strength of a news-driven market signal."""
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


# ---------------------------------------------------------------------------
# Sentiment lexicon (rule-based)
# ---------------------------------------------------------------------------

_POSITIVE_WORDS: Set[str] = {
    "beat", "exceeds", "record", "growth", "profit", "gain", "surge",
    "jump", "rise", "rally", "strong", "improved", "upgrade", "positive",
    "outperform", "buy", "boost", "increase", "accelerate", "expand",
    "dividend", "acquisition", "merger", "approved", "wins", "launch",
    "innovative", "revenue", "earnings", "profit", "above", "consensus",
}

_NEGATIVE_WORDS: Set[str] = {
    "miss", "below", "loss", "decline", "fall", "drop", "plunge", "weak",
    "downgrade", "sell", "cut", "reduce", "slow", "contraction", "recession",
    "lawsuit", "investigation", "fraud", "layoff", "bankruptcy", "warning",
    "shortfall", "disappointing", "concern", "risk", "penalty", "breach",
    "fine", "resign", "probe", "debt", "default", "downward", "deteriorate",
}

_INTENSIFIERS: Set[str] = {"very", "significantly", "sharply", "notably", "major", "massive"}


def _tokenise(text: str) -> List[str]:
    return re.findall(r"\b[a-z]+\b", text.lower())


def _score_text(text: str) -> float:
    """Rule-based sentiment score in [-1, +1]."""
    tokens = _tokenise(text)
    score = 0.0
    intensifier = False
    for token in tokens:
        if token in _INTENSIFIERS:
            intensifier = True
            continue
        if token in _POSITIVE_WORDS:
            score += 1.5 if intensifier else 1.0
        elif token in _NEGATIVE_WORDS:
            score -= 1.5 if intensifier else 1.0
        intensifier = False
    n = len(tokens) or 1
    return max(-1.0, min(1.0, score / math.sqrt(n)))


def _classify_sentiment(score: float) -> NewsSentiment:
    if score >= 0.4:
        return NewsSentiment.VERY_POSITIVE
    if score >= 0.1:
        return NewsSentiment.POSITIVE
    if score <= -0.4:
        return NewsSentiment.VERY_NEGATIVE
    if score <= -0.1:
        return NewsSentiment.NEGATIVE
    return NewsSentiment.NEUTRAL


# ---------------------------------------------------------------------------
# Topic / Category classification
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORDS: Dict[NewsCategory, Set[str]] = {
    NewsCategory.EARNINGS: {"earnings", "revenue", "eps", "guidance", "quarterly", "results", "beat", "miss"},
    NewsCategory.MACRO: {"gdp", "inflation", "rate", "fed", "central", "bank", "pmi", "employment", "macro"},
    NewsCategory.REGULATORY: {"regulation", "sec", "compliance", "antitrust", "approval", "approved", "denied"},
    NewsCategory.MERGER_ACQUISITION: {"acquisition", "merger", "deal", "takeover", "buyout", "acquire"},
    NewsCategory.PRODUCT: {"launch", "product", "release", "innovation", "patent", "technology"},
    NewsCategory.MANAGEMENT: {"ceo", "cfo", "resign", "appoint", "executive", "board", "leadership"},
    NewsCategory.GEOPOLITICAL: {"war", "sanction", "tariff", "trade", "geopolitical", "election"},
    NewsCategory.LEGAL: {"lawsuit", "court", "judgment", "fine", "settle", "litigation", "probe"},
    NewsCategory.DIVIDEND: {"dividend", "payout", "distribution", "special"},
    NewsCategory.ANALYST: {"upgrade", "downgrade", "target", "price", "analyst", "rating", "recommendation"},
}


def _classify_category(text: str) -> NewsCategory:
    tokens = set(_tokenise(text))
    best_cat = NewsCategory.OTHER
    best_score = 0
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        score = len(tokens & keywords)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


# ---------------------------------------------------------------------------
# Entity extraction (ticker mentions)
# ---------------------------------------------------------------------------

def _extract_tickers(text: str, known_tickers: Optional[Set[str]] = None) -> List[str]:
    """Extract uppercase 1-5 letter ticker symbols from text."""
    candidates = re.findall(r"\b([A-Z]{1,5})\b", text)
    if known_tickers:
        return [t for t in candidates if t in known_tickers]
    common_stopwords = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN",
                        "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "HAS", "HIM",
                        "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "TWO",
                        "WHO", "BOY", "DID", "US", "AN", "AT", "BE", "BY", "DO", "GO",
                        "IF", "IN", "IS", "IT", "ME", "MY", "NO", "OF", "ON", "OR",
                        "SO", "TO", "UP", "WE", "CEO", "CFO", "COO", "CTO", "SEC",
                        "ETF", "FED", "IPO", "GDP", "PMI", "EPS", "CPI", "EUR", "USD",
                        "GBP", "JPY", "A", "B", "C", "D", "E", "F", "G", "H", "I",
                        "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
                        "V", "W", "X", "Y", "Z", "SAYS", "SAID", "WILL", "FROM", "WITH"}
    seen: Set[str] = set()
    result: List[str] = []
    for t in candidates:
        if t not in common_stopwords and t not in seen:
            seen.add(t)
            result.append(t)
    return result


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NewsArticle:
    """A processed news article with NLP annotations.

    Args:
        article_id: Unique identifier.
        headline: Article headline.
        body: Full article body.
        source: News source name.
        sentiment: Classified sentiment.
        sentiment_score: Numeric sentiment in [-1, +1].
        category: Detected news category.
        tickers_mentioned: Extracted ticker symbols.
        sectors_impacted: Relevant sectors.
        market_signal: Generated trading signal.
        signal_strength: Signal strength.
        published_at: Publication time UTC.
        ingested_at: Ingestion time UTC.
        url: Original article URL.
        tags: Arbitrary tags.
    """

    article_id: str
    headline: str
    body: str
    source: str
    sentiment: NewsSentiment
    sentiment_score: float
    category: NewsCategory
    tickers_mentioned: List[str]
    sectors_impacted: List[str]
    market_signal: str
    signal_strength: MarketSignalStrength
    published_at: datetime
    ingested_at: datetime
    url: str
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "article_id": self.article_id,
            "headline": self.headline,
            "body": self.body[:500],
            "source": self.source,
            "sentiment": self.sentiment.value,
            "sentiment_score": round(self.sentiment_score, 4),
            "category": self.category.value,
            "tickers_mentioned": self.tickers_mentioned,
            "sectors_impacted": self.sectors_impacted,
            "market_signal": self.market_signal,
            "signal_strength": self.signal_strength.value,
            "published_at": self.published_at.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "url": self.url,
            "tags": self.tags,
        }


@dataclass
class TickerSentimentSummary:
    """Aggregated sentiment summary for a ticker.

    Args:
        ticker: Instrument symbol.
        article_count: Number of articles referencing this ticker.
        avg_sentiment_score: Average score in [-1, +1].
        sentiment_label: Dominant sentiment label.
        recent_articles: Last N article headlines.
        positive_count: Articles with positive/very_positive sentiment.
        negative_count: Articles with negative/very_negative sentiment.
        trend: "IMPROVING", "WORSENING", or "STABLE".
    """

    ticker: str
    article_count: int
    avg_sentiment_score: float
    sentiment_label: NewsSentiment
    recent_articles: List[str]
    positive_count: int
    negative_count: int
    trend: str

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "article_count": self.article_count,
            "avg_sentiment_score": round(self.avg_sentiment_score, 4),
            "sentiment_label": self.sentiment_label.value,
            "recent_articles": self.recent_articles,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "trend": self.trend,
        }


@dataclass
class NewsTrend:
    """An emerging topic/trend detected in the news stream.

    Args:
        trend_id: Unique ID.
        topic: Topic label.
        article_count: Articles referencing this topic in the window.
        velocity: Rate of increase (articles/hour).
        avg_sentiment: Average sentiment score.
        top_tickers: Most-mentioned tickers.
        description: Human-readable trend summary.
        detected_at: Detection time.
    """

    trend_id: str
    topic: str
    article_count: int
    velocity: float
    avg_sentiment: float
    top_tickers: List[str]
    description: str
    detected_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "trend_id": self.trend_id,
            "topic": self.topic,
            "article_count": self.article_count,
            "velocity": round(self.velocity, 2),
            "avg_sentiment": round(self.avg_sentiment, 4),
            "top_tickers": self.top_tickers,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class NewsSignal:
    """A trading signal derived from news analytics.

    Args:
        signal_id: Unique ID.
        ticker: Target ticker.
        direction: BUY / SELL / HOLD.
        confidence: Model confidence (0-1).
        source_articles: Article IDs that contributed.
        rationale: Plain-English explanation.
        generated_at: Signal generation time.
    """

    signal_id: str
    ticker: str
    direction: str
    confidence: float
    source_articles: List[str]
    rationale: str
    generated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "signal_id": self.signal_id,
            "ticker": self.ticker,
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
            "source_articles": self.source_articles,
            "rationale": self.rationale,
            "generated_at": self.generated_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Sector keyword map
# ---------------------------------------------------------------------------

_SECTOR_KEYWORDS: Dict[str, Set[str]] = {
    "Technology": {"software", "cloud", "ai", "chip", "semiconductor", "data", "tech", "cyber"},
    "Energy": {"oil", "gas", "pipeline", "energy", "refinery", "coal", "solar", "wind"},
    "Healthcare": {"drug", "fda", "clinical", "hospital", "pharma", "biotech", "health"},
    "Financials": {"bank", "loan", "credit", "insurance", "mortgage", "rate", "fed"},
    "Consumer": {"retail", "consumer", "brand", "store", "shop", "e-commerce"},
    "Industrials": {"manufacturing", "industrial", "supply", "aerospace", "defense"},
    "Materials": {"mining", "steel", "copper", "lithium", "commodity"},
    "Real Estate": {"reit", "property", "mortgage", "housing", "commercial"},
    "Utilities": {"utility", "electric", "water", "gas", "grid", "power"},
    "Communication": {"media", "telecom", "social", "streaming", "broadcast"},
}


def _infer_sectors(text: str) -> List[str]:
    tokens = set(_tokenise(text))
    sectors: List[str] = []
    for sector, kws in _SECTOR_KEYWORDS.items():
        if tokens & kws:
            sectors.append(sector)
    return sectors or ["General"]


# ---------------------------------------------------------------------------
# News Intelligence Engine
# ---------------------------------------------------------------------------

class NewsIntelligenceEngine:
    """Real-time news intelligence engine.

    Ingests articles, runs NLP annotation, maintains per-ticker and per-category
    indices, detects trends, and generates market signals.
    """

    _MAX_ARTICLES = 10_000

    def __init__(self) -> None:
        self._articles: Deque[NewsArticle] = deque(maxlen=self._MAX_ARTICLES)
        self._ticker_index: Dict[str, List[str]] = defaultdict(list)
        self._category_index: Dict[str, List[str]] = defaultdict(list)
        self._known_tickers: Set[str] = set()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def register_tickers(self, tickers: List[str]) -> None:
        """Register known ticker symbols to improve extraction accuracy.

        Args:
            tickers: List of instrument symbols.
        """
        self._known_tickers.update(t.upper() for t in tickers)

    def ingest(
        self,
        headline: str,
        body: str = "",
        source: str = "UNKNOWN",
        published_at: Optional[datetime] = None,
        url: str = "",
        tags: Optional[List[str]] = None,
    ) -> NewsArticle:
        """Ingest a news article and run automatic NLP annotation.

        Args:
            headline: Article headline.
            body: Full article body text.
            source: News source name.
            published_at: Publication time (UTC). Defaults to now.
            url: Original article URL.
            tags: Optional tags.

        Returns:
            Annotated NewsArticle.
        """
        full_text = f"{headline} {body}"
        score = _score_text(full_text)
        sentiment = _classify_sentiment(score)
        category = _classify_category(full_text)
        tickers = _extract_tickers(full_text, self._known_tickers or None)
        sectors = _infer_sectors(full_text)
        if score >= 0.3:
            signal_strength = MarketSignalStrength.STRONG_BULLISH
            market_signal = "STRONG_BUY"
        elif score >= 0.1:
            signal_strength = MarketSignalStrength.BULLISH
            market_signal = "BUY"
        elif score <= -0.3:
            signal_strength = MarketSignalStrength.STRONG_BEARISH
            market_signal = "STRONG_SELL"
        elif score <= -0.1:
            signal_strength = MarketSignalStrength.BEARISH
            market_signal = "SELL"
        else:
            signal_strength = MarketSignalStrength.NEUTRAL
            market_signal = "HOLD"
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            article_id=str(uuid.uuid4()),
            headline=headline,
            body=body,
            source=source,
            sentiment=sentiment,
            sentiment_score=score,
            category=category,
            tickers_mentioned=tickers,
            sectors_impacted=sectors,
            market_signal=market_signal,
            signal_strength=signal_strength,
            published_at=published_at or now,
            ingested_at=now,
            url=url,
            tags=tags or [],
        )
        self._articles.append(article)
        for t in tickers:
            self._ticker_index[t].append(article.article_id)
        self._category_index[category.value].append(article.article_id)
        return article

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_article(self, article_id: str) -> Optional[NewsArticle]:
        """Retrieve a stored article by ID.

        Args:
            article_id: Article identifier.

        Returns:
            NewsArticle or None.
        """
        for a in self._articles:
            if a.article_id == article_id:
                return a
        return None

    def search(
        self,
        query: str = "",
        ticker: Optional[str] = None,
        category: Optional[NewsCategory] = None,
        sentiment: Optional[NewsSentiment] = None,
        limit: int = 50,
    ) -> List[NewsArticle]:
        """Search articles by keyword, ticker, category, or sentiment.

        Args:
            query: Substring to match in headline or body.
            ticker: Filter by mentioned ticker.
            category: Filter by category.
            sentiment: Filter by sentiment label.
            limit: Maximum results.

        Returns:
            List of matching NewsArticle (newest first).
        """
        results = list(reversed(self._articles))
        if ticker:
            t = ticker.upper()
            results = [a for a in results if t in a.tickers_mentioned]
        if category:
            results = [a for a in results if a.category == category]
        if sentiment:
            results = [a for a in results if a.sentiment == sentiment]
        if query:
            q = query.lower()
            results = [a for a in results if q in a.headline.lower() or q in a.body.lower()]
        return results[:limit]

    def get_latest(self, limit: int = 20) -> List[NewsArticle]:
        """Return the most recently ingested articles.

        Args:
            limit: Maximum articles.

        Returns:
            List newest first.
        """
        return list(reversed(list(self._articles)))[:limit]

    # ------------------------------------------------------------------
    # Sentiment summary
    # ------------------------------------------------------------------

    def get_ticker_sentiment(
        self, ticker: str, window: int = 50
    ) -> TickerSentimentSummary:
        """Aggregate sentiment for a single ticker.

        Args:
            ticker: Instrument symbol.
            window: Number of recent articles to include.

        Returns:
            TickerSentimentSummary.
        """
        t = ticker.upper()
        articles = [a for a in reversed(self._articles) if t in a.tickers_mentioned][:window]
        if not articles:
            return TickerSentimentSummary(
                ticker=t, article_count=0, avg_sentiment_score=0.0,
                sentiment_label=NewsSentiment.NEUTRAL, recent_articles=[],
                positive_count=0, negative_count=0, trend="STABLE",
            )
        scores = [a.sentiment_score for a in articles]
        avg = sum(scores) / len(scores)
        pos = sum(1 for a in articles if a.sentiment in {NewsSentiment.POSITIVE, NewsSentiment.VERY_POSITIVE})
        neg = sum(1 for a in articles if a.sentiment in {NewsSentiment.NEGATIVE, NewsSentiment.VERY_NEGATIVE})
        if len(scores) >= 4:
            first_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            second_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            if second_half - first_half > 0.05:
                trend = "IMPROVING"
            elif first_half - second_half > 0.05:
                trend = "WORSENING"
            else:
                trend = "STABLE"
        else:
            trend = "STABLE"
        return TickerSentimentSummary(
            ticker=t,
            article_count=len(articles),
            avg_sentiment_score=avg,
            sentiment_label=_classify_sentiment(avg),
            recent_articles=[a.headline for a in articles[:5]],
            positive_count=pos,
            negative_count=neg,
            trend=trend,
        )

    # ------------------------------------------------------------------
    # Trend detection
    # ------------------------------------------------------------------

    def detect_trends(self, window_hours: float = 4.0, min_articles: int = 3) -> List[NewsTrend]:
        """Detect emerging topics in the recent news stream.

        Groups by category, counts articles in the window, and flags categories
        with above-average velocity.

        Args:
            window_hours: Hours back to look.
            min_articles: Minimum articles to qualify as a trend.

        Returns:
            List of NewsTrend sorted by velocity.
        """
        now = datetime.now(timezone.utc)
        cutoff_sec = window_hours * 3600
        recent = [a for a in self._articles
                  if (now - a.ingested_at).total_seconds() <= cutoff_sec]
        category_groups: Dict[str, List[NewsArticle]] = defaultdict(list)
        for a in recent:
            category_groups[a.category.value].append(a)
        trends: List[NewsTrend] = []
        for cat_name, articles in category_groups.items():
            if len(articles) < min_articles:
                continue
            velocity = len(articles) / window_hours
            scores = [a.sentiment_score for a in articles]
            avg_score = sum(scores) / len(scores)
            ticker_counts: Dict[str, int] = defaultdict(int)
            for a in articles:
                for t in a.tickers_mentioned:
                    ticker_counts[t] += 1
            top_tickers = sorted(ticker_counts, key=ticker_counts.get, reverse=True)[:5]  # type: ignore[arg-type]
            trends.append(NewsTrend(
                trend_id=str(uuid.uuid4()),
                topic=cat_name,
                article_count=len(articles),
                velocity=velocity,
                avg_sentiment=avg_score,
                top_tickers=top_tickers,
                description=(f"{len(articles)} articles in {cat_name} over last "
                             f"{window_hours:.0f}h (velocity={velocity:.1f}/h)"),
                detected_at=now,
            ))
        trends.sort(key=lambda t: t.velocity, reverse=True)
        return trends

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(
        self, ticker: str, window: int = 20
    ) -> NewsSignal:
        """Generate a trading signal from aggregated news sentiment.

        Args:
            ticker: Instrument symbol.
            window: Number of recent articles to consider.

        Returns:
            NewsSignal.
        """
        summary = self.get_ticker_sentiment(ticker, window=window)
        t = ticker.upper()
        score = summary.avg_sentiment_score
        if score >= 0.3:
            direction = "BUY"
            confidence = min(0.95, 0.5 + abs(score))
        elif score <= -0.3:
            direction = "SELL"
            confidence = min(0.95, 0.5 + abs(score))
        elif score >= 0.1:
            direction = "BUY"
            confidence = 0.4 + abs(score) * 0.3
        elif score <= -0.1:
            direction = "SELL"
            confidence = 0.4 + abs(score) * 0.3
        else:
            direction = "HOLD"
            confidence = 0.30
        articles = [a for a in reversed(self._articles) if t in a.tickers_mentioned][:window]
        source_ids = [a.article_id for a in articles]
        rationale = (
            f"Aggregated news sentiment for {t}: score={score:.3f}, "
            f"{summary.positive_count} positive, {summary.negative_count} negative "
            f"across {summary.article_count} articles. Trend={summary.trend}."
        )
        return NewsSignal(
            signal_id=str(uuid.uuid4()),
            ticker=t,
            direction=direction,
            confidence=confidence,
            source_articles=source_ids,
            rationale=rationale,
            generated_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics for the news engine.

        Returns:
            Dict with total_articles, by_category, by_sentiment counts.
        """
        by_cat: Dict[str, int] = defaultdict(int)
        by_sent: Dict[str, int] = defaultdict(int)
        for a in self._articles:
            by_cat[a.category.value] += 1
            by_sent[a.sentiment.value] += 1
        return {
            "total_articles": len(self._articles),
            "by_category": dict(by_cat),
            "by_sentiment": dict(by_sent),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[NewsIntelligenceEngine] = None


def get_news_intelligence_engine() -> NewsIntelligenceEngine:
    """Return the singleton NewsIntelligenceEngine.

    Returns:
        Shared NewsIntelligenceEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = NewsIntelligenceEngine()
    return _default_engine
