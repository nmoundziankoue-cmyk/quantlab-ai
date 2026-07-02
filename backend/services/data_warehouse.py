"""M13 — Institutional data warehouse.

In-memory partitioned warehouse with TTL, versioning, compression metadata,
and a pluggable cache layer.  All operations are thread-safe.

Storage model
-------------
  warehouse[symbol][timeframe][version] = WarehousePartition

where a WarehousePartition holds the DataFrame plus metadata.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import logging
import pickle
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DataType(Enum):
    OHLCV = "ohlcv"
    TICKS = "ticks"
    TRADES = "trades"
    QUOTES = "quotes"
    DIVIDENDS = "dividends"
    SPLITS = "splits"
    FUNDAMENTALS = "fundamentals"
    ECONOMIC = "economic"
    NEWS = "news"
    ANALYST = "analyst"
    INSIDER = "insider"
    ETF_HOLDINGS = "etf_holdings"
    OPTIONS = "options"


class Timeframe(Enum):
    TICK = "tick"
    SECOND = "1s"
    MINUTE = "1m"
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    THIRTY_MIN = "30m"
    HOUR = "1h"
    FOUR_HOUR = "4h"
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1mo"


# ---------------------------------------------------------------------------
# Partition and metadata
# ---------------------------------------------------------------------------

@dataclass
class PartitionMetadata:
    symbol: str
    data_type: DataType
    timeframe: Timeframe
    version: int
    provider: str
    row_count: int
    start_ts: Optional[pd.Timestamp]
    end_ts: Optional[pd.Timestamp]
    created_at: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None          # None = never expires
    compressed: bool = False
    checksum: str = ""
    size_bytes: int = 0
    quality_score: float = 1.0                   # 0–1 data quality

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "data_type": self.data_type.value,
            "timeframe": self.timeframe.value,
            "version": self.version,
            "provider": self.provider,
            "row_count": self.row_count,
            "start_ts": str(self.start_ts) if self.start_ts else None,
            "end_ts": str(self.end_ts) if self.end_ts else None,
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            "compressed": self.compressed,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "quality_score": round(self.quality_score, 4),
            "is_expired": self.is_expired,
        }


@dataclass
class WarehousePartition:
    data: pd.DataFrame
    meta: PartitionMetadata
    _compressed_bytes: Optional[bytes] = field(default=None, repr=False, compare=False)


def _checksum(df: pd.DataFrame) -> str:
    raw = pickle.dumps(df, protocol=4)
    return hashlib.md5(raw).hexdigest()[:12]


def _compress_df(df: pd.DataFrame) -> bytes:
    return gzip.compress(pickle.dumps(df, protocol=4))


def _decompress_df(data: bytes) -> pd.DataFrame:
    return pickle.loads(gzip.decompress(data))


# ---------------------------------------------------------------------------
# Cache layer
# ---------------------------------------------------------------------------

class _LRUCache:
    """Simple LRU cache with TTL."""

    def __init__(self, maxsize: int = 256, ttl_seconds: float = 300.0) -> None:
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, ts = entry
            if time.time() - ts > self._ttl:
                del self._store[key]
                if key in self._order:
                    self._order.remove(key)
                return None
            self._order.remove(key)
            self._order.append(key)
            return value

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._order.remove(key)
            elif len(self._store) >= self._maxsize:
                oldest = self._order.pop(0)
                del self._store[oldest]
            self._store[key] = (value, time.time())
            self._order.append(key)

    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._order.remove(key)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._order.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"size": len(self._store), "maxsize": self._maxsize, "ttl_seconds": self._ttl}


# ---------------------------------------------------------------------------
# Main warehouse class
# ---------------------------------------------------------------------------

class DataWarehouse:
    """Partitioned in-memory market data warehouse.

    Organises data as ``partitions[data_type][symbol][timeframe][version]``.
    Provides a read-through LRU cache, TTL expiry, automatic cleanup,
    and versioning.
    """

    def __init__(
        self,
        cache_ttl_seconds: float = 300.0,
        cache_maxsize: int = 512,
        auto_cleanup_interval: int = 60,
    ) -> None:
        # partitions[data_type.value][symbol][timeframe.value][version]
        self._store: Dict[str, Dict[str, Dict[str, Dict[int, WarehousePartition]]]] = {}
        self._lock = threading.RLock()
        self._cache = _LRUCache(maxsize=cache_maxsize, ttl_seconds=cache_ttl_seconds)
        self._cleanup_interval = auto_cleanup_interval
        self._last_cleanup = time.time()
        self._write_count = 0
        self._read_count = 0
        self._cache_hits = 0

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def store(
        self,
        df: pd.DataFrame,
        symbol: str,
        data_type: DataType,
        timeframe: Timeframe,
        provider: str = "unknown",
        ttl_seconds: Optional[float] = None,
        compress: bool = False,
        quality_score: float = 1.0,
    ) -> PartitionMetadata:
        """Store a DataFrame partition.  Returns the written metadata."""
        if df.empty:
            raise ValueError("Cannot store empty DataFrame")

        with self._lock:
            dt = data_type.value
            tf = timeframe.value
            sym = symbol.upper()

            self._store.setdefault(dt, {}).setdefault(sym, {}).setdefault(tf, {})
            existing = self._store[dt][sym][tf]
            version = max(existing.keys(), default=0) + 1

            start_ts: Optional[pd.Timestamp] = None
            end_ts: Optional[pd.Timestamp] = None
            if hasattr(df.index, "min") and len(df) > 0:
                try:
                    start_ts = pd.Timestamp(df.index.min())
                    end_ts = pd.Timestamp(df.index.max())
                except Exception as exc:
                    logger.debug("Could not read index bounds: %s", exc)

            raw_bytes = pickle.dumps(df, protocol=4)
            size_bytes = len(raw_bytes)
            chk = hashlib.md5(raw_bytes).hexdigest()[:12]

            compressed_bytes = _compress_df(df) if compress else None

            meta = PartitionMetadata(
                symbol=sym,
                data_type=data_type,
                timeframe=timeframe,
                version=version,
                provider=provider,
                row_count=len(df),
                start_ts=start_ts,
                end_ts=end_ts,
                ttl_seconds=ttl_seconds,
                compressed=compress,
                checksum=chk,
                size_bytes=size_bytes,
                quality_score=quality_score,
            )

            self._store[dt][sym][tf][version] = WarehousePartition(
                data=df if not compress else pd.DataFrame(),
                meta=meta,
                _compressed_bytes=compressed_bytes,
            )
            self._write_count += 1
            self._cache.invalidate(self._cache_key(sym, data_type, timeframe))

            if time.time() - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired()

            return meta

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def retrieve(
        self,
        symbol: str,
        data_type: DataType,
        timeframe: Timeframe,
        version: Optional[int] = None,
        start: Optional[pd.Timestamp] = None,
        end: Optional[pd.Timestamp] = None,
        use_cache: bool = True,
    ) -> Optional[pd.DataFrame]:
        """Retrieve a partition (latest version by default)."""
        sym = symbol.upper()
        ck = self._cache_key(sym, data_type, timeframe, version)

        if use_cache:
            cached = self._cache.get(ck)
            if cached is not None:
                self._cache_hits += 1
                self._read_count += 1
                df = cached
                return self._slice(df, start, end)

        with self._lock:
            partition = self._get_partition(sym, data_type, timeframe, version)
            if partition is None:
                return None
            if partition.meta.is_expired:
                self._evict(sym, data_type, timeframe, partition.meta.version)
                return None

            if partition.meta.compressed and partition._compressed_bytes:
                df = _decompress_df(partition._compressed_bytes)
            else:
                df = partition.data.copy()

        self._cache.put(ck, df)
        self._read_count += 1
        return self._slice(df, start, end)

    def get_latest_metadata(
        self,
        symbol: str,
        data_type: DataType,
        timeframe: Timeframe,
    ) -> Optional[PartitionMetadata]:
        sym = symbol.upper()
        with self._lock:
            partition = self._get_partition(sym, data_type, timeframe)
            return partition.meta if partition else None

    def list_symbols(self, data_type: Optional[DataType] = None) -> List[str]:
        with self._lock:
            if data_type:
                return sorted(self._store.get(data_type.value, {}).keys())
            symbols: set = set()
            for dt_store in self._store.values():
                symbols.update(dt_store.keys())
            return sorted(symbols)

    def list_timeframes(self, symbol: str, data_type: DataType) -> List[str]:
        sym = symbol.upper()
        with self._lock:
            return list(self._store.get(data_type.value, {}).get(sym, {}).keys())

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        results = []
        with self._lock:
            for dt_val, sym_map in self._store.items():
                for sym, tf_map in sym_map.items():
                    for tf_val, ver_map in tf_map.items():
                        for version, partition in ver_map.items():
                            results.append(partition.meta.to_dict())
        return results

    def warehouse_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_rows = 0
            total_bytes = 0
            symbol_count = set()
            partition_count = 0
            for dt_val, sym_map in self._store.items():
                for sym, tf_map in sym_map.items():
                    symbol_count.add(sym)
                    for tf_val, ver_map in tf_map.items():
                        for version, partition in ver_map.items():
                            total_rows += partition.meta.row_count
                            total_bytes += partition.meta.size_bytes
                            partition_count += 1
        return {
            "symbol_count": len(symbol_count),
            "partition_count": partition_count,
            "total_rows": total_rows,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / 1_048_576, 2),
            "write_count": self._write_count,
            "read_count": self._read_count,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": round(
                self._cache_hits / self._read_count if self._read_count > 0 else 0.0, 4
            ),
            "cache": self._cache.stats(),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(
        symbol: str,
        data_type: DataType,
        timeframe: Timeframe,
        version: Optional[int] = None,
    ) -> str:
        v = version or "latest"
        return f"{symbol}:{data_type.value}:{timeframe.value}:{v}"

    def _get_partition(
        self,
        symbol: str,
        data_type: DataType,
        timeframe: Timeframe,
        version: Optional[int] = None,
    ) -> Optional[WarehousePartition]:
        ver_map = (
            self._store
            .get(data_type.value, {})
            .get(symbol, {})
            .get(timeframe.value, {})
        )
        if not ver_map:
            return None
        if version is not None:
            return ver_map.get(version)
        latest = max(ver_map.keys())
        return ver_map[latest]

    def _evict(
        self,
        symbol: str,
        data_type: DataType,
        timeframe: Timeframe,
        version: int,
    ) -> None:
        try:
            del self._store[data_type.value][symbol][timeframe.value][version]
        except KeyError:
            logger.debug("Evict: partition not found (%s/%s/%s/v%s)", data_type.value, symbol, timeframe.value, version)

    def _cleanup_expired(self) -> int:
        """Remove all expired partitions.  Called automatically on writes."""
        removed = 0
        to_delete: List[Tuple] = []
        for dt_val, sym_map in self._store.items():
            for sym, tf_map in sym_map.items():
                for tf_val, ver_map in tf_map.items():
                    for version, partition in ver_map.items():
                        if partition.meta.is_expired:
                            to_delete.append((dt_val, sym, tf_val, version))
        for dt_val, sym, tf_val, version in to_delete:
            try:
                del self._store[dt_val][sym][tf_val][version]
                removed += 1
            except KeyError:
                logger.debug("Cleanup: partition already removed (%s/%s/%s/v%s)", dt_val, sym, tf_val, version)
        self._last_cleanup = time.time()
        return removed

    def cleanup(self) -> int:
        """Public manual cleanup.  Returns number of removed partitions."""
        with self._lock:
            return self._cleanup_expired()

    @staticmethod
    def _slice(
        df: pd.DataFrame,
        start: Optional[pd.Timestamp],
        end: Optional[pd.Timestamp],
    ) -> pd.DataFrame:
        if start is None and end is None:
            return df
        if start and end:
            return df.loc[start:end]
        if start:
            return df.loc[start:]
        return df.loc[:end]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_warehouse: Optional[DataWarehouse] = None


def get_default_warehouse() -> DataWarehouse:
    global _default_warehouse
    if _default_warehouse is None:
        _default_warehouse = DataWarehouse()
    return _default_warehouse
