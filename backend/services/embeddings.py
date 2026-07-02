"""Embedding service — TF-IDF based fallback (no external API required).

Architecture is compatible with pgvector: embeddings are stored as JSONB
arrays of floats and can be swapped for real embeddings by replacing
compute_embedding() and updating the model field.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for",
    "from", "has", "have", "he", "in", "is", "it", "its", "of", "on",
    "or", "that", "the", "this", "to", "was", "were", "will", "with",
    "i", "we", "they", "their", "our", "you", "your",
}

EMBEDDING_DIM = 128
EMBEDDING_MODEL = "tfidf-128-v1"


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def _term_frequencies(tokens: List[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def _hash_to_index(term: str, dim: int) -> int:
    h = int(hashlib.md5(term.encode()).hexdigest(), 16)
    return h % dim


def _hash_to_sign(term: str) -> float:
    h = int(hashlib.sha1(term.encode()).hexdigest(), 16)
    return 1.0 if h % 2 == 0 else -1.0


# ---------------------------------------------------------------------------
# Core embedding
# ---------------------------------------------------------------------------

def compute_embedding(text: str) -> List[float]:
    """Compute a deterministic dense embedding using random hash projection.

    Properties:
    - Deterministic for the same input text
    - Preserves rough semantic similarity for overlapping vocabulary
    - 128-dimensional unit-norm vector
    - Compatible with cosine similarity
    """
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * EMBEDDING_DIM

    tf = _term_frequencies(tokens)
    vector = [0.0] * EMBEDDING_DIM

    for term, freq in tf.items():
        idx = _hash_to_index(term, EMBEDDING_DIM)
        sign = _hash_to_sign(term)
        vector[idx] += sign * freq

    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]

    return vector


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_by_similarity(query_embedding: List[float], candidates: List[Tuple[str, List[float]]]) -> List[Tuple[str, float]]:
    """Rank (id, embedding) pairs by cosine similarity to query."""
    scored = [(cid, cosine_similarity(query_embedding, emb)) for cid, emb in candidates]
    return sorted(scored, key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# Keyword scoring (BM25-lite)
# ---------------------------------------------------------------------------

def keyword_score(query: str, text: str) -> float:
    query_tokens = set(_tokenize(query))
    text_tokens = _tokenize(text)
    if not query_tokens or not text_tokens:
        return 0.0
    text_set = set(text_tokens)
    matches = query_tokens & text_set
    return len(matches) / len(query_tokens)


def hybrid_score(query: str, text: str, query_embedding: List[float], text_embedding: List[float], alpha: float = 0.6) -> float:
    """Weighted combination of semantic and keyword score."""
    sem = cosine_similarity(query_embedding, text_embedding)
    kw = keyword_score(query, text)
    return alpha * sem + (1 - alpha) * kw
