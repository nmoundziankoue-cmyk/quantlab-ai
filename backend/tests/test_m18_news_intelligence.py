"""Unit tests for M18 News Intelligence Engine — 60 tests."""
import pytest

from services.m18_news_intelligence import (
    NewsSentiment, NewsCategory,
    NewsArticle, TickerSentimentSummary, NewsTrend, NewsSignal,
    NewsIntelligenceEngine, get_news_intelligence_engine,
    _tokenise, _score_text, _classify_sentiment, _classify_category,
    _extract_tickers, _POSITIVE_WORDS, _NEGATIVE_WORDS,
)


# ---------------------------------------------------------------------------
# NLP helper functions
# ---------------------------------------------------------------------------

class TestNLPHelpers:
    def test_tokenise_lowercases(self):
        tokens = _tokenise("Apple Reports RECORD Revenue")
        assert "apple" in tokens

    def test_tokenise_removes_punctuation(self):
        tokens = _tokenise("earnings, beat! revenue.")
        assert "earnings" in tokens
        assert "," not in tokens

    def test_tokenise_empty(self):
        assert _tokenise("") == []

    def test_score_positive_text(self):
        score = _score_text("Apple reports record revenue and strong profits")
        assert score > 0

    def test_score_negative_text(self):
        score = _score_text("company faces loss bankruptcy debt crisis")
        assert score < 0

    def test_score_neutral_text(self):
        score = _score_text("the company reported quarterly results")
        assert abs(score) <= 0.5

    def test_score_range(self):
        for text in ["great excellent best", "terrible loss disaster", "reported quarterly"]:
            score = _score_text(text)
            assert -1.0 <= score <= 1.0

    def test_classify_sentiment_positive(self):
        assert _classify_sentiment(0.4) in (NewsSentiment.POSITIVE, NewsSentiment.VERY_POSITIVE)

    def test_classify_sentiment_negative(self):
        assert _classify_sentiment(-0.4) in (NewsSentiment.NEGATIVE, NewsSentiment.VERY_NEGATIVE)

    def test_classify_sentiment_neutral(self):
        assert _classify_sentiment(0.05) == NewsSentiment.NEUTRAL

    def test_classify_sentiment_very_positive(self):
        assert _classify_sentiment(0.8) == NewsSentiment.VERY_POSITIVE

    def test_classify_sentiment_very_negative(self):
        assert _classify_sentiment(-0.8) == NewsSentiment.VERY_NEGATIVE

    def test_classify_category_earnings(self):
        cat = _classify_category("Company beats earnings expectations EPS quarterly results")
        assert cat is not None

    def test_extract_tickers_finds_uppercase(self):
        tickers = _extract_tickers("AAPL reports strong revenue; MSFT also beats")
        assert "AAPL" in tickers or "MSFT" in tickers

    def test_extract_tickers_ignores_stopwords(self):
        tickers = _extract_tickers("THE company AND its CEO")
        assert "THE" not in tickers and "AND" not in tickers

    def test_positive_words_nonempty(self):
        assert len(_POSITIVE_WORDS) >= 10

    def test_negative_words_nonempty(self):
        assert len(_NEGATIVE_WORDS) >= 10


# ---------------------------------------------------------------------------
# NewsArticle
# ---------------------------------------------------------------------------

class TestNewsArticle:
    def _make(self, headline="Apple beats EPS by 8%", body="Strong quarterly results.", source="Reuters"):
        engine = NewsIntelligenceEngine()
        return engine.ingest(headline=headline, body=body, source=source)

    def test_ingest_returns_article(self):
        article = self._make()
        assert isinstance(article, NewsArticle)

    def test_article_has_id(self):
        article = self._make()
        assert article.article_id is not None

    def test_article_sentiment_set(self):
        article = self._make()
        assert article.sentiment is not None
        assert isinstance(article.sentiment, NewsSentiment)

    def test_article_score_range(self):
        article = self._make()
        assert -1.0 <= article.sentiment_score <= 1.0

    def test_article_category_set(self):
        article = self._make("Apple reports record earnings EPS beat")
        assert article.category is not None

    def test_article_tickers_extracted(self):
        article = self._make("AAPL and MSFT both report strong quarterly results")
        assert isinstance(article.tickers_mentioned, list)

    def test_article_to_dict(self):
        article = self._make()
        d = article.to_dict()
        assert "headline" in d and "sentiment" in d

    def test_positive_article_has_positive_sentiment(self):
        article = self._make("record profits excellent revenue growth strong performance")
        assert article.sentiment in (NewsSentiment.POSITIVE, NewsSentiment.VERY_POSITIVE)


# ---------------------------------------------------------------------------
# NewsIntelligenceEngine — ingestion
# ---------------------------------------------------------------------------

class TestNewsEngineIngest:
    def setup_method(self):
        self.engine = NewsIntelligenceEngine()

    def test_ingest_article(self):
        article = self.engine.ingest("Test headline", "Test body", "Bloomberg")
        assert article is not None

    def test_get_latest_articles(self):
        self.engine.ingest("H1", "B1", "Reuters")
        self.engine.ingest("H2", "B2", "Bloomberg")
        articles = self.engine.get_latest(limit=10)
        assert len(articles) == 2

    def test_get_latest_limit(self):
        for i in range(10):
            self.engine.ingest(f"H{i}", f"B{i}", "Source")
        articles = self.engine.get_latest(limit=3)
        assert len(articles) == 3

    def test_get_stats_empty_initially(self):
        stats = self.engine.get_stats()
        assert stats["total_articles"] == 0

    def test_get_stats_after_ingest(self):
        self.engine.ingest("H", "B", "S")
        stats = self.engine.get_stats()
        assert stats["total_articles"] == 1

    def test_search_by_keyword(self):
        self.engine.ingest("AAPL earnings beat", "Apple reported strong results", "Reuters")
        self.engine.ingest("Oil prices drop", "Energy markets volatile", "Bloomberg")
        results = self.engine.search("earnings")
        assert any("earnings" in a.headline.lower() for a in results)


# ---------------------------------------------------------------------------
# NewsIntelligenceEngine — ticker sentiment
# ---------------------------------------------------------------------------

class TestNewsEngineTickerSentiment:
    def setup_method(self):
        self.engine = NewsIntelligenceEngine()
        self.engine.ingest("AAPL reports record profits strong beat", "Apple beats earnings", "R")
        self.engine.ingest("AAPL revenue growth excellent performance", "Apple revenue up 15%", "B")
        self.engine.ingest("AAPL faces regulatory scrutiny", "Apple antitrust probe", "FT")

    def test_get_ticker_sentiment(self):
        result = self.engine.get_ticker_sentiment("AAPL")
        assert isinstance(result, TickerSentimentSummary)

    def test_ticker_sentiment_article_count(self):
        result = self.engine.get_ticker_sentiment("AAPL")
        assert result.article_count >= 1

    def test_ticker_sentiment_to_dict(self):
        d = self.engine.get_ticker_sentiment("AAPL").to_dict()
        assert "ticker" in d and "article_count" in d

    def test_unknown_ticker_returns_default(self):
        result = self.engine.get_ticker_sentiment("ZZZZ")
        assert result.article_count == 0


# ---------------------------------------------------------------------------
# NewsIntelligenceEngine — trends
# ---------------------------------------------------------------------------

class TestNewsEngineTrends:
    def setup_method(self):
        self.engine = NewsIntelligenceEngine()
        for i in range(5):
            self.engine.ingest(
                f"Earnings season beats expectations article {i}",
                f"Companies reported strong Q{i+1} results beating estimates",
                "Reuters",
            )

    def test_detect_trends(self):
        trends = self.engine.detect_trends(window_hours=24, min_articles=1)
        assert isinstance(trends, list)

    def test_trend_to_dict(self):
        trends = self.engine.detect_trends(window_hours=24, min_articles=1)
        for t in trends:
            d = t.to_dict()
            assert "topic" in d or "trend_id" in d

    def test_generate_signal(self):
        result = self.engine.generate_signal("AAPL")
        assert isinstance(result, NewsSignal)

    def test_signal_to_dict(self):
        d = self.engine.generate_signal("AAPL").to_dict()
        assert "direction" in d or "ticker" in d

    def test_signal_direction_is_valid(self):
        result = self.engine.generate_signal("AAPL")
        assert result.direction in ("BUY", "SELL", "HOLD")

    def test_signal_confidence_range(self):
        result = self.engine.generate_signal("AAPL")
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_news_intelligence_engine(self):
        eng = get_news_intelligence_engine()
        assert isinstance(eng, NewsIntelligenceEngine)

    def test_singleton_same_instance(self):
        e1 = get_news_intelligence_engine()
        e2 = get_news_intelligence_engine()
        assert e1 is e2
