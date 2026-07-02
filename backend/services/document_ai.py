"""M14 Phase 5 — Document AI / NLP enrichment.

Deterministic, lexicon- and heuristic-based NLP enrichment: NER, topics,
keywords, sentiment, risk/novelty/readability scoring, extractive
summarization, a simple keyword-overlap QA hook, and a semantic-embeddings
interface that reuses the M9 hash-embedding scheme so results are
reproducible without any ML model or network dependency.

The `embed()` function and `SemanticEmbedder` interface are intentionally
pluggable: a future LLM-backed embedder can be swapped in without changing
callers, by subclassing `SemanticEmbedder` and overriding `embed_text`.
"""
from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from services.knowledge_graph_v2 import _hash_embed, cosine_similarity

# ---------------------------------------------------------------------------
# Lexicons
# ---------------------------------------------------------------------------

_POSITIVE_WORDS = {
    "growth", "beat", "surge", "profit", "record", "strong", "gain", "upgrade",
    "positive", "exceed", "outperform", "robust", "expansion", "improve",
    "accelerate", "momentum", "success", "win", "opportunity",
}
_NEGATIVE_WORDS = {
    "miss", "loss", "decline", "fall", "crash", "risk", "warning", "downgrade",
    "negative", "cut", "weak", "slowdown", "litigation", "investigation",
    "recall", "bankruptcy", "default", "impairment", "layoff", "delay",
}
_UNCERTAINTY_WORDS = {
    "may", "might", "could", "uncertain", "unclear", "possibly", "potential",
    "depends", "volatility", "unpredictable", "contingent", "risk", "exposure",
}
_RISK_WORDS = {
    "litigation", "investigation", "regulatory", "default", "bankruptcy",
    "impairment", "covenant", "breach", "fraud", "penalty", "fine", "recall",
    "downgrade", "going concern", "material weakness",
}
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "for", "on",
    "with", "as", "by", "at", "be", "this", "that", "from", "are", "was",
    "were", "will", "has", "have", "had", "its", "their", "we", "our",
}

_WORD_RE = re.compile(r"[A-Za-z']+")
_TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


# ---------------------------------------------------------------------------
# Named entity recognition (rule-based)
# ---------------------------------------------------------------------------

_COMPANY_SUFFIXES = ("Inc", "Corp", "Corporation", "Co", "Ltd", "LLC", "Holdings", "Group", "PLC")
_COMPANY_RE = re.compile(
    r"\b([A-Z][A-Za-z&]+(?:\s+[A-Z][A-Za-z&]+){0,3}\s+(?:" + "|".join(_COMPANY_SUFFIXES) + r")\.?)\b"
)
_EXEC_RE = re.compile(
    r"\b([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){1,2}),?\s+"
    r"(CEO|CFO|COO|CTO|President|Chairman|Chairwoman|Chief Executive Officer|"
    r"Chief Financial Officer|Chief Operating Officer)\b"
)

_COMMON_WORDS = {"A", "I", "THE", "AN", "IN", "OF", "OR", "AND", "TO", "IS", "IT", "BE", "DO", "NO", "ON", "AT", "IF", "US", "EPS", "CEO", "CFO"}


@dataclass
class NEROutput:
    companies: List[str] = field(default_factory=list)
    tickers: List[str] = field(default_factory=list)
    executives: List[str] = field(default_factory=list)


def extract_entities(text: str) -> NEROutput:
    companies = sorted(set(_COMPANY_RE.findall(text)))
    tickers = sorted({t for t in _TICKER_RE.findall(text) if t not in _COMMON_WORDS})
    execs = sorted({f"{name.strip()} ({title})" for name, title in _EXEC_RE.findall(text)})
    return NEROutput(companies=companies, tickers=tickers, executives=execs)


# ---------------------------------------------------------------------------
# Topic / keyword extraction
# ---------------------------------------------------------------------------

def extract_keywords(text: str, top_k: int = 10) -> List[Tuple[str, int]]:
    tokens = [t for t in _tokenize(text) if t not in _STOPWORDS and len(t) > 2]
    counts = Counter(tokens)
    return counts.most_common(top_k)


_TOPIC_LEXICON: Dict[str, set] = {
    "earnings": {"earnings", "revenue", "eps", "profit", "quarter", "guidance"},
    "regulatory": {"sec", "regulation", "compliance", "investigation", "lawsuit"},
    "mergers_acquisitions": {"merger", "acquisition", "acquire", "takeover", "deal"},
    "leadership": {"ceo", "cfo", "chairman", "appoint", "resign", "succession"},
    "product": {"launch", "product", "release", "innovation", "patent"},
    "macro": {"inflation", "rates", "fed", "recession", "gdp", "unemployment"},
}


def extract_topics(text: str) -> List[str]:
    tokens = set(_tokenize(text))
    matched = [topic for topic, lex in _TOPIC_LEXICON.items() if tokens & lex]
    return sorted(matched)


# ---------------------------------------------------------------------------
# Sentiment / risk / novelty / readability scoring
# ---------------------------------------------------------------------------

def sentiment_score(text: str) -> float:
    tokens = _tokenize(text)
    pos = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 4)


def risk_score(text: str) -> float:
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in _RISK_WORDS)
    return round(min(1.0, hits / max(len(tokens) / 50, 1)), 4)


def uncertainty_score(text: str) -> float:
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in _UNCERTAINTY_WORDS)
    return round(min(1.0, hits / max(len(tokens) / 30, 1)), 4)


def novelty_score(text: str, corpus_texts: Optional[List[str]] = None) -> float:
    """1.0 = highly novel relative to corpus, 0.0 = near-duplicate of something seen."""
    if not corpus_texts:
        return 1.0
    target = _hash_embed(text)
    sims = [cosine_similarity(target, _hash_embed(c)) for c in corpus_texts]
    max_sim = max(sims) if sims else 0.0
    return round(max(0.0, 1.0 - max_sim), 4)


def readability_score(text: str) -> float:
    """Flesch Reading Ease approximation (0-100, higher = easier to read)."""
    sentences = [s for s in _SENTENCE_RE.split(text.strip()) if s]
    words = _WORD_RE.findall(text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    score = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    return round(max(0.0, min(100.0, score)), 2)


_VOWEL_RE = re.compile(r"[aeiouyAEIOUY]+")


def _count_syllables(word: str) -> int:
    matches = _VOWEL_RE.findall(word)
    count = len(matches)
    return max(1, count)


# ---------------------------------------------------------------------------
# Extractive summarization
# ---------------------------------------------------------------------------

def summarize(text: str, max_sentences: int = 3) -> str:
    sentences = [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    keyword_scores = dict(extract_keywords(text, top_k=30))
    scored: List[Tuple[int, float, str]] = []
    for idx, sentence in enumerate(sentences):
        tokens = _tokenize(sentence)
        score = sum(keyword_scores.get(t, 0) for t in tokens)
        scored.append((idx, score, sentence))

    top = sorted(scored, key=lambda x: x[1], reverse=True)[:max_sentences]
    top_in_order = sorted(top, key=lambda x: x[0])
    return " ".join(s for _, _, s in top_in_order)


# ---------------------------------------------------------------------------
# Question answering (extractive, keyword-overlap retrieval)
# ---------------------------------------------------------------------------

def answer_question(question: str, text: str) -> Dict[str, object]:
    """Return the sentence in ``text`` with the highest token overlap with
    ``question``. Deterministic, no LLM call — a best-effort extractive
    answer suitable until a real QA model is wired in.
    """
    q_tokens = set(_tokenize(question)) - _STOPWORDS
    sentences = [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]
    if not sentences or not q_tokens:
        return {"answer": "", "confidence": 0.0, "sentence_index": -1}

    best_idx, best_score = -1, 0.0
    for idx, sentence in enumerate(sentences):
        s_tokens = set(_tokenize(sentence))
        overlap = len(q_tokens & s_tokens)
        score = overlap / len(q_tokens)
        if score > best_score:
            best_score, best_idx = score, idx

    if best_idx == -1:
        return {"answer": "", "confidence": 0.0, "sentence_index": -1}
    return {"answer": sentences[best_idx], "confidence": round(best_score, 4), "sentence_index": best_idx}


# ---------------------------------------------------------------------------
# Semantic embeddings interface
# ---------------------------------------------------------------------------

class SemanticEmbedder(ABC):
    """Pluggable embedding interface. Default impl is the M9 hash embedder;
    a future LLM-backed embedder can subclass and override ``embed_text``.
    """

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        ...

    def similarity(self, a: str, b: str) -> float:
        return cosine_similarity(self.embed_text(a), self.embed_text(b))


class HashEmbedder(SemanticEmbedder):
    def embed_text(self, text: str) -> List[float]:
        return _hash_embed(text)


_default_embedder: Optional[SemanticEmbedder] = None


def get_default_embedder() -> SemanticEmbedder:
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = HashEmbedder()
    return _default_embedder


# ---------------------------------------------------------------------------
# Composite enrichment record
# ---------------------------------------------------------------------------

@dataclass
class DocumentEnrichment:
    entities: NEROutput
    topics: List[str]
    keywords: List[Tuple[str, int]]
    sentiment: float
    risk: float
    uncertainty: float
    readability: float
    novelty: float
    summary: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "entities": {
                "companies": self.entities.companies,
                "tickers": self.entities.tickers,
                "executives": self.entities.executives,
            },
            "topics": self.topics,
            "keywords": [{"term": k, "count": c} for k, c in self.keywords],
            "sentiment": self.sentiment,
            "risk": self.risk,
            "uncertainty": self.uncertainty,
            "readability": self.readability,
            "novelty": self.novelty,
            "summary": self.summary,
        }


def enrich_document(text: str, corpus_texts: Optional[List[str]] = None, summary_sentences: int = 3) -> DocumentEnrichment:
    return DocumentEnrichment(
        entities=extract_entities(text),
        topics=extract_topics(text),
        keywords=extract_keywords(text),
        sentiment=sentiment_score(text),
        risk=risk_score(text),
        uncertainty=uncertainty_score(text),
        readability=readability_score(text),
        novelty=novelty_score(text, corpus_texts),
        summary=summarize(text, summary_sentences),
    )
