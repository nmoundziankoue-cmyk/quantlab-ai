"""M14 Phase 2 — Alternative-data document ingestion pipeline.

In-memory, deterministic document warehouse for SEC filings and other
alternative-data documents.  Mirrors the M13 `data_warehouse.py` design:
versioned partitions, checksum-based deduplication, gzip+pickle compression,
and a simple inverted-index hook for downstream search (Phase 8).

No network or database dependency — callers supply already-fetched text.
"""
from __future__ import annotations

import gzip
import hashlib
import pickle
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = __import__("logging").getLogger(__name__)


class FilingType(Enum):
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    PROXY = "PROXY"
    FORM_13F = "13F"
    FORM_13D = "13D"
    INSIDER_FORM4 = "FORM4"
    TRANSCRIPT = "TRANSCRIPT"
    NEWS = "NEWS"
    PATENT = "PATENT"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"


@dataclass
class DocumentMetadata:
    doc_id: str
    symbol: str
    filing_type: FilingType
    source: str
    version: int
    checksum: str
    size_bytes: int
    created_at: float = field(default_factory=time.time)
    published_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "symbol": self.symbol,
            "filing_type": self.filing_type.value,
            "source": self.source,
            "version": self.version,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "extra": self.extra,
        }


@dataclass
class StoredDocument:
    doc_id: str
    symbol: str
    filing_type: FilingType
    text: str
    meta: DocumentMetadata


def _checksum(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def _compress(text: str) -> bytes:
    return gzip.compress(pickle.dumps(text, protocol=4))


def _decompress(data: bytes) -> str:
    return pickle.loads(gzip.decompress(data))


def extract_metadata(text: str) -> Dict[str, Any]:
    """Heuristic metadata extraction: word count, line count, has-tables guess."""
    lines = text.splitlines()
    words = text.split()
    return {
        "word_count": len(words),
        "line_count": len(lines),
        "char_count": len(text),
        "has_numeric_tables": sum(1 for w in words if w.replace(",", "").replace(".", "").replace("$", "").isdigit()) > 10,
    }


class DocumentStore:
    """Versioned, deduplicated, checksum-validated document warehouse.

    Storage model: ``_store[symbol][filing_type][doc_id] -> {version: StoredDocument}``
    """

    def __init__(self, compress: bool = True) -> None:
        self._store: Dict[str, Dict[str, Dict[str, Dict[int, StoredDocument]]]] = {}
        self._compressed: Dict[str, bytes] = {}
        self._checksums_seen: Dict[str, str] = {}  # doc_id -> latest checksum
        self._lock = threading.RLock()
        self._compress = compress
        self._ingest_count = 0
        self._dedup_skips = 0
        # Simple inverted index: token -> set of doc_ids (built lazily by index())
        self._index: Dict[str, set] = {}

    def ingest(
        self,
        doc_id: str,
        symbol: str,
        filing_type: FilingType,
        text: str,
        source: str = "unknown",
        published_at: Optional[str] = None,
    ) -> DocumentMetadata:
        """Ingest a document.  Returns metadata; increments version on changed content.

        If the checksum matches the most recent version for this ``doc_id``,
        the ingest is treated as a duplicate and skipped (no new version).
        """
        if not text or not text.strip():
            raise ValueError("Cannot ingest empty document text")

        sym = symbol.upper()
        chk = _checksum(text)

        with self._lock:
            if self._checksums_seen.get(doc_id) == chk:
                self._dedup_skips += 1
                existing = self._get_latest(sym, filing_type, doc_id)
                if existing is not None:
                    return existing.meta
            self._checksums_seen[doc_id] = chk

            self._store.setdefault(sym, {}).setdefault(filing_type.value, {}).setdefault(doc_id, {})
            versions = self._store[sym][filing_type.value][doc_id]
            version = max(versions.keys(), default=0) + 1

            meta = DocumentMetadata(
                doc_id=doc_id,
                symbol=sym,
                filing_type=filing_type,
                source=source,
                version=version,
                checksum=chk,
                size_bytes=len(text.encode("utf-8")),
                published_at=published_at,
                extra=extract_metadata(text),
            )

            stored_text = text
            if self._compress:
                self._compressed[f"{doc_id}:{version}"] = _compress(text)
                stored_text = ""

            doc = StoredDocument(doc_id=doc_id, symbol=sym, filing_type=filing_type, text=stored_text, meta=meta)
            versions[version] = doc
            self._ingest_count += 1
            return meta

    def _get_latest(self, symbol: str, filing_type: FilingType, doc_id: str) -> Optional[StoredDocument]:
        versions = self._store.get(symbol, {}).get(filing_type.value, {}).get(doc_id, {})
        if not versions:
            return None
        latest_version = max(versions.keys())
        return versions[latest_version]

    def get(self, doc_id: str, symbol: str, filing_type: FilingType, version: Optional[int] = None) -> Optional[StoredDocument]:
        sym = symbol.upper()
        with self._lock:
            versions = self._store.get(sym, {}).get(filing_type.value, {}).get(doc_id, {})
            if not versions:
                return None
            v = version if version is not None else max(versions.keys())
            doc = versions.get(v)
            if doc is None:
                return None
            if self._compress:
                text = _decompress(self._compressed[f"{doc_id}:{v}"])
                return StoredDocument(doc_id=doc.doc_id, symbol=doc.symbol, filing_type=doc.filing_type, text=text, meta=doc.meta)
            return doc

    def list_documents(self, symbol: Optional[str] = None, filing_type: Optional[FilingType] = None) -> List[DocumentMetadata]:
        results: List[DocumentMetadata] = []
        with self._lock:
            symbols = [symbol.upper()] if symbol else list(self._store.keys())
            for sym in symbols:
                ft_map = self._store.get(sym, {})
                fts = [filing_type.value] if filing_type else list(ft_map.keys())
                for ft in fts:
                    for doc_id, versions in ft_map.get(ft, {}).items():
                        latest = max(versions.keys())
                        results.append(versions[latest].meta)
        return results

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            doc_count = sum(
                len(doc_map)
                for sym_map in self._store.values()
                for doc_map in sym_map.values()
            )
            version_count = sum(
                len(versions)
                for sym_map in self._store.values()
                for doc_map in sym_map.values()
                for versions in doc_map.values()
            )
            return {
                "symbol_count": len(self._store),
                "document_count": doc_count,
                "version_count": version_count,
                "ingest_count": self._ingest_count,
                "dedup_skips": self._dedup_skips,
            }

    # ------------------------------------------------------------------
    # Indexing hook (consumed by alt_search.py)
    # ------------------------------------------------------------------

    def all_documents_full(self) -> List[StoredDocument]:
        """Return the latest version of every document, with text decompressed."""
        results = []
        with self._lock:
            for sym, ft_map in self._store.items():
                for ft, doc_map in ft_map.items():
                    for doc_id, versions in doc_map.items():
                        latest = max(versions.keys())
                        doc = versions[latest]
                        text = _decompress(self._compressed[f"{doc_id}:{latest}"]) if self._compress else doc.text
                        results.append(StoredDocument(doc_id=doc.doc_id, symbol=doc.symbol, filing_type=doc.filing_type, text=text, meta=doc.meta))
        return results


_default_store: Optional[DocumentStore] = None


def get_default_document_store() -> DocumentStore:
    global _default_store
    if _default_store is None:
        _default_store = DocumentStore()
    return _default_store
