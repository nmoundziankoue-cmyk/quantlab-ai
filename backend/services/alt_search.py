"""M14 Phase 8 — Alternative-data search engine.

Full-text inverted-index search plus metadata filters (company/ticker,
executive, patent, filing type, date range, entity) and TF-IDF-lite
relevance ranking. A semantic-search hook reuses the M14 `document_ai`
hash-embedder so callers can request similarity ranking without any
external model.
"""
from __future__ import annotations

import math
import re
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from services.document_ai import extract_entities, get_default_embedder
from services.document_store import StoredDocument

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "for", "on",
    "with", "as", "by", "at", "be", "this", "that", "from", "are", "was",
}


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS]


@dataclass
class IndexedDocument:
    doc_id: str
    symbol: str
    filing_type: str
    text: str
    published_at: Optional[str]
    companies: List[str] = field(default_factory=list)
    executives: List[str] = field(default_factory=list)
    tickers: List[str] = field(default_factory=list)


@dataclass
class SearchHit:
    doc_id: str
    symbol: str
    filing_type: str
    score: float
    snippet: str


class AltSearchEngine:
    """In-memory inverted-index search over ingested alternative-data documents."""

    def __init__(self) -> None:
        self._docs: Dict[str, IndexedDocument] = {}
        self._index: Dict[str, Set[str]] = defaultdict(set)
        self._doc_freq: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def index_document(self, doc: StoredDocument) -> None:
        entities = extract_entities(doc.text)
        indexed = IndexedDocument(
            doc_id=doc.doc_id,
            symbol=doc.symbol,
            filing_type=doc.filing_type.value,
            text=doc.text,
            published_at=doc.meta.published_at,
            companies=entities.companies,
            executives=entities.executives,
            tickers=entities.tickers,
        )
        tokens = set(_tokenize(doc.text))
        with self._lock:
            if doc.doc_id in self._docs:
                self._remove_from_index(doc.doc_id)
            self._docs[doc.doc_id] = indexed
            for token in tokens:
                self._index[token].add(doc.doc_id)
                self._doc_freq[token] += 1

    def _remove_from_index(self, doc_id: str) -> None:
        old = self._docs.get(doc_id)
        if old is None:
            return
        for token in set(_tokenize(old.text)):
            self._index[token].discard(doc_id)
            self._doc_freq[token] = max(0, self._doc_freq[token] - 1)

    def index_many(self, docs: List[StoredDocument]) -> int:
        for doc in docs:
            self.index_document(doc)
        return len(docs)

    @property
    def document_count(self) -> int:
        with self._lock:
            return len(self._docs)

    def _tfidf_score(self, query_tokens: List[str], doc_id: str) -> float:
        doc = self._docs[doc_id]
        doc_tokens = _tokenize(doc.text)
        if not doc_tokens:
            return 0.0
        doc_term_counts = Counter(doc_tokens)
        n_docs = max(len(self._docs), 1)
        score = 0.0
        for term in query_tokens:
            tf = doc_term_counts.get(term, 0) / len(doc_tokens)
            df = self._doc_freq.get(term, 0)
            idf = math.log((n_docs + 1) / (df + 1)) + 1
            score += tf * idf
        return score

    def search(
        self,
        query: Optional[str] = None,
        symbol: Optional[str] = None,
        filing_type: Optional[str] = None,
        executive: Optional[str] = None,
        company: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 20,
    ) -> List[SearchHit]:
        with self._lock:
            candidates: Set[str] = set(self._docs.keys())

            if query:
                query_tokens = _tokenize(query)
                matched: Set[str] = set()
                for term in query_tokens:
                    matched |= self._index.get(term, set())
                candidates &= matched if matched else set()
            else:
                query_tokens = []

            if symbol:
                candidates = {d for d in candidates if self._docs[d].symbol == symbol.upper()}
            if filing_type:
                candidates = {d for d in candidates if self._docs[d].filing_type == filing_type}
            if executive:
                candidates = {d for d in candidates if any(executive.lower() in e.lower() for e in self._docs[d].executives)}
            if company:
                candidates = {d for d in candidates if any(company.lower() in c.lower() for c in self._docs[d].companies)}
            if since:
                candidates = {d for d in candidates if (self._docs[d].published_at or "") >= since}
            if until:
                candidates = {d for d in candidates if (self._docs[d].published_at or "9999") <= until}

            scored = []
            for doc_id in candidates:
                score = self._tfidf_score(query_tokens, doc_id) if query_tokens else 1.0
                doc = self._docs[doc_id]
                snippet = doc.text[:240]
                scored.append(SearchHit(doc_id=doc_id, symbol=doc.symbol, filing_type=doc.filing_type, score=round(score, 4), snippet=snippet))

            scored.sort(key=lambda h: h.score, reverse=True)
            return scored[:limit]

    def semantic_search(self, query: str, limit: int = 20) -> List[SearchHit]:
        embedder = get_default_embedder()
        with self._lock:
            scored = []
            for doc_id, doc in self._docs.items():
                sim = embedder.similarity(query, doc.text[:2000])
                scored.append(SearchHit(doc_id=doc_id, symbol=doc.symbol, filing_type=doc.filing_type, score=round(sim, 4), snippet=doc.text[:240]))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]

    def search_companies(self, name_fragment: str, limit: int = 20) -> List[str]:
        with self._lock:
            found: Set[str] = set()
            for doc in self._docs.values():
                for c in doc.companies:
                    if name_fragment.lower() in c.lower():
                        found.add(c)
        return sorted(found)[:limit]

    def search_executives(self, name_fragment: str, limit: int = 20) -> List[str]:
        with self._lock:
            found: Set[str] = set()
            for doc in self._docs.values():
                for e in doc.executives:
                    if name_fragment.lower() in e.lower():
                        found.add(e)
        return sorted(found)[:limit]


_default_search_engine: Optional[AltSearchEngine] = None


def get_default_search_engine() -> AltSearchEngine:
    global _default_search_engine
    if _default_search_engine is None:
        _default_search_engine = AltSearchEngine()
    return _default_search_engine
