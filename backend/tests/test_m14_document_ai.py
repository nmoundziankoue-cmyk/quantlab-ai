"""M14 Phase 12 — Tests: document AI (Phase 5)."""
import pytest
from services.document_ai import (
    NEROutput,
    extract_entities,
    extract_keywords,
    extract_topics,
    sentiment_score,
    risk_score,
    uncertainty_score,
    novelty_score,
    readability_score,
    summarize,
    answer_question,
    SemanticEmbedder,
    HashEmbedder,
    get_default_embedder,
    DocumentEnrichment,
    enrich_document,
)

POSITIVE_TEXT = (
    "The company delivered outstanding results with record revenue growth. "
    "Profit margins expanded significantly, beating all expectations. "
    "Management is confident about the future outlook and raised guidance."
)

NEGATIVE_TEXT = (
    "The company faces significant litigation risk and regulatory investigation. "
    "Revenue declined sharply due to supply chain disruptions and adverse market conditions. "
    "Management issued a profit warning and expects a challenging environment ahead."
)

LONG_TEXT = (
    "Apple Inc reported strong quarterly earnings. Revenue grew 15% year over year to $90 billion. "
    "The board approved a new $80 billion share repurchase program. "
    "Tim Cook, CEO, stated the company remains committed to innovation. "
    "However, currency headwinds and uncertain macroeconomic conditions pose risks. "
    "Supply chain constraints may impact future quarters. Management expects improvement. "
    "The gross margin expanded to 45% reflecting strong pricing power and operational efficiency. "
    "Services revenue hit a record high at $21 billion. Wearables also showed strong growth."
)


# ---------------------------------------------------------------------------
# NER
# ---------------------------------------------------------------------------

def test_extract_entities_returns_ner_output():
    result = extract_entities(LONG_TEXT)
    assert isinstance(result, NEROutput)


def test_extract_entities_tickers():
    result = extract_entities("AAPL and MSFT reported earnings today.")
    assert isinstance(result.tickers, list)


def test_extract_entities_companies():
    result = extract_entities(LONG_TEXT)
    assert isinstance(result.companies, list)


def test_extract_entities_executives():
    result = extract_entities("Tim Cook, CEO of Apple, made the announcement.")
    assert isinstance(result.executives, list)
    assert any("Tim" in e or "Cook" in e for e in result.executives)


def test_extract_entities_has_tickers_field():
    result = extract_entities("AAPL traded higher today.")
    assert hasattr(result, "tickers")
    assert hasattr(result, "companies")
    assert hasattr(result, "executives")


def test_extract_entities_empty_text():
    result = extract_entities("")
    assert isinstance(result, NEROutput)


# ---------------------------------------------------------------------------
# Keywords & Topics
# ---------------------------------------------------------------------------

def test_extract_keywords_returns_list():
    kws = extract_keywords(LONG_TEXT)
    assert isinstance(kws, list)


def test_extract_keywords_have_term_and_score():
    kws = extract_keywords(LONG_TEXT)
    for kw in kws:
        # May be (term, count) tuple or {"term": ..., "score": ...} dict
        assert len(kw) >= 2


def test_extract_keywords_nonempty():
    kws = extract_keywords(LONG_TEXT)
    assert len(kws) > 0


def test_extract_topics_returns_list():
    topics = extract_topics(LONG_TEXT)
    assert isinstance(topics, list)


def test_extract_topics_from_financial_text():
    topics = extract_topics("Revenue grew 15%, earnings beat estimates, new buyback program.")
    assert isinstance(topics, list)


def test_extract_topics_empty():
    topics = extract_topics("")
    assert isinstance(topics, list)


# ---------------------------------------------------------------------------
# Sentiment / Risk / Uncertainty
# ---------------------------------------------------------------------------

def test_sentiment_positive_text():
    score = sentiment_score(POSITIVE_TEXT)
    assert score > 0  # Positive text → positive sentiment


def test_sentiment_negative_text():
    score = sentiment_score(NEGATIVE_TEXT)
    assert score < 0  # Negative text → negative sentiment


def test_sentiment_range():
    for text in [POSITIVE_TEXT, NEGATIVE_TEXT, LONG_TEXT, ""]:
        s = sentiment_score(text)
        assert -1.0 <= s <= 1.0


def test_sentiment_deterministic():
    s1 = sentiment_score(LONG_TEXT)
    s2 = sentiment_score(LONG_TEXT)
    assert s1 == s2


def test_risk_score_high_risk():
    s = risk_score(NEGATIVE_TEXT)
    assert s > 0  # Contains risk/litigation/regulatory words


def test_risk_score_low_risk():
    s = risk_score("Revenue grew 10% in a stable market environment.")
    assert s >= 0


def test_risk_score_range():
    for text in [POSITIVE_TEXT, NEGATIVE_TEXT, LONG_TEXT]:
        assert 0 <= risk_score(text) <= 1.0


def test_uncertainty_score_range():
    for text in [POSITIVE_TEXT, NEGATIVE_TEXT, LONG_TEXT]:
        assert 0 <= uncertainty_score(text) <= 1.0


def test_uncertainty_high_for_uncertain_text():
    uncertain = "We may possibly face uncertain headwinds that could potentially impact results."
    assert uncertainty_score(uncertain) > 0


# ---------------------------------------------------------------------------
# Novelty
# ---------------------------------------------------------------------------

def test_novelty_without_corpus():
    score = novelty_score(LONG_TEXT)
    assert 0 <= score <= 1.0


def test_novelty_with_identical_corpus():
    score = novelty_score(LONG_TEXT, corpus_texts=[LONG_TEXT, LONG_TEXT])
    assert score <= 0.5


def test_novelty_with_dissimilar_corpus():
    corpus = ["Weather data shows rainfall increased in Q3 across major agricultural regions."]
    score = novelty_score(LONG_TEXT, corpus_texts=corpus)
    assert score > 0.3  # Financial text vs weather text → high novelty


def test_novelty_empty_text():
    score = novelty_score("")
    assert score >= 0


# ---------------------------------------------------------------------------
# Readability
# ---------------------------------------------------------------------------

def test_readability_returns_float():
    score = readability_score(LONG_TEXT)
    assert isinstance(score, float)


def test_readability_nonnegative():
    assert readability_score(LONG_TEXT) >= 0


def test_readability_empty():
    score = readability_score("")
    assert score >= 0


# ---------------------------------------------------------------------------
# Summarization — actual signature is summarize(text, max_sentences=3)
# ---------------------------------------------------------------------------

def test_summarize_returns_string():
    result = summarize(LONG_TEXT)
    assert isinstance(result, str)


def test_summarize_nonempty():
    result = summarize(LONG_TEXT)
    assert len(result) > 0


def test_summarize_respects_max_sentences():
    s1 = summarize(LONG_TEXT, max_sentences=1)
    s3 = summarize(LONG_TEXT, max_sentences=3)
    assert len(s3) >= len(s1)


def test_summarize_empty_text():
    result = summarize("")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------

def test_answer_question_returns_dict():
    result = answer_question("What was the revenue growth?", LONG_TEXT)
    assert isinstance(result, dict)
    assert "answer" in result
    assert "confidence" in result
    assert "sentence_index" in result


def test_answer_question_confidence_range():
    result = answer_question("What is the gross margin?", LONG_TEXT)
    assert 0 <= result["confidence"] <= 1.0


def test_answer_question_no_match():
    result = answer_question("What is the color of the sky?", LONG_TEXT)
    assert result["confidence"] >= 0


def test_answer_question_deterministic():
    r1 = answer_question("What grew 15%?", LONG_TEXT)
    r2 = answer_question("What grew 15%?", LONG_TEXT)
    assert r1 == r2


# ---------------------------------------------------------------------------
# Embedder — actual API: embed_text, similarity
# ---------------------------------------------------------------------------

def test_hash_embedder_returns_vector():
    emb = HashEmbedder()
    vec = emb.embed_text("Hello world")
    assert len(vec) > 0


def test_hash_embedder_deterministic():
    emb = HashEmbedder()
    v1 = emb.embed_text("Apple earnings")
    v2 = emb.embed_text("Apple earnings")
    assert v1 == v2


def test_hash_embedder_different_texts():
    emb = HashEmbedder()
    v1 = emb.embed_text("Apple earnings beat")
    v2 = emb.embed_text("Weather forecast sunny skies")
    assert v1 != v2


def test_hash_embedder_similarity_range():
    emb = HashEmbedder()
    s = emb.similarity("Apple revenue", "Apple revenue growth")
    assert -1.0 <= s <= 1.0


def test_hash_embedder_self_similarity():
    emb = HashEmbedder()
    text = "Revenue grew 15%"
    s = emb.similarity(text, text)
    assert s > 0.9


def test_get_default_embedder():
    emb = get_default_embedder()
    assert isinstance(emb, SemanticEmbedder)


# ---------------------------------------------------------------------------
# DocumentEnrichment
# ---------------------------------------------------------------------------

def test_enrich_document_returns_enrichment():
    result = enrich_document(LONG_TEXT)
    assert isinstance(result, DocumentEnrichment)


def test_enrich_document_to_dict():
    result = enrich_document(LONG_TEXT)
    d = result.to_dict()
    assert "sentiment" in d
    assert "risk" in d
    assert "topics" in d
    assert "entities" in d
    assert "summary" in d


def test_enrich_document_deterministic():
    r1 = enrich_document(LONG_TEXT)
    r2 = enrich_document(LONG_TEXT)
    assert r1.sentiment == r2.sentiment
    assert r1.risk == r2.risk
