"""M13 — Tests for services/data_warehouse.py.

All deterministic, in-memory — no network or disk I/O.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from services.data_warehouse import (
    DataType,
    DataWarehouse,
    PartitionMetadata,
    Timeframe,
    WarehousePartition,
    _LRUCache,
    get_default_warehouse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ohlcv(n: int = 100, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="B", tz="UTC")
    close = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, n))
    return pd.DataFrame({
        "open": close * (1 + rng.normal(0, 0.001, n)),
        "high": close * (1 + np.abs(rng.normal(0, 0.005, n))),
        "low": close * (1 - np.abs(rng.normal(0, 0.005, n))),
        "close": close,
        "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
    }, index=idx)


def _fresh() -> DataWarehouse:
    return DataWarehouse()


# ===========================================================================
# _LRUCache
# ===========================================================================

def test_lru_put_get():
    cache = _LRUCache(maxsize=5, ttl_seconds=300)
    cache.put("key1", "value1")
    assert cache.get("key1") == "value1"


def test_lru_miss_returns_none():
    cache = _LRUCache()
    assert cache.get("missing") is None


def test_lru_evicts_oldest_on_overflow():
    cache = _LRUCache(maxsize=3, ttl_seconds=300)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)   # should evict "a"
    assert cache.get("a") is None
    assert cache.get("d") == 4


def test_lru_ttl_expiry():
    cache = _LRUCache(maxsize=10, ttl_seconds=0.01)
    cache.put("key", "value")
    time.sleep(0.05)
    assert cache.get("key") is None


def test_lru_invalidate():
    cache = _LRUCache()
    cache.put("k", 99)
    cache.invalidate("k")
    assert cache.get("k") is None


def test_lru_clear():
    cache = _LRUCache()
    cache.put("a", 1)
    cache.put("b", 2)
    cache.clear()
    assert cache.size == 0


def test_lru_stats():
    cache = _LRUCache(maxsize=10, ttl_seconds=300)
    cache.put("x", 1)
    stats = cache.stats()
    assert stats["size"] == 1
    assert stats["maxsize"] == 10


# ===========================================================================
# DataWarehouse — store
# ===========================================================================

def test_store_returns_metadata():
    wh = _fresh()
    df = _ohlcv()
    meta = wh.store(df, "AAPL", DataType.OHLCV, Timeframe.DAILY, provider="mock")
    assert isinstance(meta, PartitionMetadata)
    assert meta.row_count == len(df)
    assert meta.symbol == "AAPL"
    assert meta.provider == "mock"


def test_store_empty_df_raises():
    wh = _fresh()
    with pytest.raises(ValueError, match="empty"):
        wh.store(pd.DataFrame(), "AAPL", DataType.OHLCV, Timeframe.DAILY)


def test_store_increments_version():
    wh = _fresh()
    df = _ohlcv()
    m1 = wh.store(df, "AAPL", DataType.OHLCV, Timeframe.DAILY)
    m2 = wh.store(df, "AAPL", DataType.OHLCV, Timeframe.DAILY)
    assert m2.version == m1.version + 1


def test_store_symbol_uppercased():
    wh = _fresh()
    df = _ohlcv()
    meta = wh.store(df, "aapl", DataType.OHLCV, Timeframe.DAILY)
    assert meta.symbol == "AAPL"


def test_store_checksum_populated():
    wh = _fresh()
    meta = wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    assert meta.checksum != ""


def test_store_size_bytes_positive():
    wh = _fresh()
    meta = wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    assert meta.size_bytes > 0


def test_store_with_ttl():
    wh = _fresh()
    meta = wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY, ttl_seconds=1000)
    assert meta.ttl_seconds == 1000
    assert not meta.is_expired


# ===========================================================================
# DataWarehouse — retrieve
# ===========================================================================

def test_retrieve_returns_df():
    wh = _fresh()
    df = _ohlcv()
    wh.store(df, "AAPL", DataType.OHLCV, Timeframe.DAILY)
    result = wh.retrieve("AAPL", DataType.OHLCV, Timeframe.DAILY)
    assert result is not None
    assert len(result) == len(df)


def test_retrieve_missing_returns_none():
    wh = _fresh()
    result = wh.retrieve("ZZZZ", DataType.OHLCV, Timeframe.DAILY)
    assert result is None


def test_retrieve_specific_version():
    wh = _fresh()
    df1 = _ohlcv(50)
    df2 = _ohlcv(100)
    wh.store(df1, "AAPL", DataType.OHLCV, Timeframe.DAILY)
    wh.store(df2, "AAPL", DataType.OHLCV, Timeframe.DAILY)
    v1 = wh.retrieve("AAPL", DataType.OHLCV, Timeframe.DAILY, version=1)
    assert v1 is not None
    assert len(v1) == 50


def test_retrieve_slices_by_date():
    wh = _fresh()
    df = _ohlcv(200)
    wh.store(df, "AAPL", DataType.OHLCV, Timeframe.DAILY)
    start = pd.Timestamp("2023-03-01", tz="UTC")
    end = pd.Timestamp("2023-04-30", tz="UTC")
    result = wh.retrieve("AAPL", DataType.OHLCV, Timeframe.DAILY, start=start, end=end)
    assert result is not None
    assert result.index.min() >= start
    assert result.index.max() <= end


def test_retrieve_expired_returns_none():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY, ttl_seconds=0.001)
    time.sleep(0.01)
    result = wh.retrieve("AAPL", DataType.OHLCV, Timeframe.DAILY, use_cache=False)
    assert result is None


def test_retrieve_uses_cache_on_second_call():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    wh.retrieve("AAPL", DataType.OHLCV, Timeframe.DAILY)
    hits_before = wh._cache_hits
    wh.retrieve("AAPL", DataType.OHLCV, Timeframe.DAILY)
    assert wh._cache_hits > hits_before


# ===========================================================================
# DataWarehouse — list / metadata
# ===========================================================================

def test_list_symbols_empty():
    wh = _fresh()
    assert wh.list_symbols() == []


def test_list_symbols_after_store():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    wh.store(_ohlcv(), "MSFT", DataType.OHLCV, Timeframe.DAILY)
    symbols = wh.list_symbols()
    assert "AAPL" in symbols
    assert "MSFT" in symbols


def test_list_symbols_by_data_type():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    wh.store(_ohlcv(), "AAPL", DataType.TICKS, Timeframe.TICK)
    assert "AAPL" in wh.list_symbols(DataType.TICKS)


def test_list_timeframes():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.HOUR)
    tfs = wh.list_timeframes("AAPL", DataType.OHLCV)
    assert Timeframe.DAILY.value in tfs
    assert Timeframe.HOUR.value in tfs


def test_get_all_metadata():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    wh.store(_ohlcv(), "MSFT", DataType.OHLCV, Timeframe.DAILY)
    meta = wh.get_all_metadata()
    assert len(meta) == 2
    assert all("symbol" in m for m in meta)


def test_get_latest_metadata():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    meta = wh.get_latest_metadata("AAPL", DataType.OHLCV, Timeframe.DAILY)
    assert meta is not None
    assert meta.symbol == "AAPL"


# ===========================================================================
# DataWarehouse — stats and cleanup
# ===========================================================================

def test_warehouse_stats_keys():
    wh = _fresh()
    stats = wh.warehouse_stats()
    for key in ("symbol_count", "partition_count", "total_rows", "total_mb", "write_count", "read_count", "cache_hit_rate"):
        assert key in stats


def test_warehouse_stats_after_store():
    wh = _fresh()
    wh.store(_ohlcv(100), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    stats = wh.warehouse_stats()
    assert stats["symbol_count"] == 1
    assert stats["partition_count"] == 1
    assert stats["total_rows"] == 100
    assert stats["write_count"] == 1


def test_cleanup_removes_expired():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY, ttl_seconds=0.001)
    time.sleep(0.02)
    removed = wh.cleanup()
    assert removed == 1


def test_cleanup_preserves_non_expired():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY, ttl_seconds=9999)
    removed = wh.cleanup()
    assert removed == 0


def test_multiple_data_types_stored():
    wh = _fresh()
    wh.store(_ohlcv(), "AAPL", DataType.OHLCV, Timeframe.DAILY)
    wh.store(_ohlcv(10), "AAPL", DataType.DIVIDENDS, Timeframe.DAILY)
    assert len(wh.list_symbols()) == 1   # same symbol
    meta = wh.get_all_metadata()
    assert len(meta) == 2


def test_compressed_store_and_retrieve():
    wh = _fresh()
    df = _ohlcv()
    meta = wh.store(df, "AAPL", DataType.OHLCV, Timeframe.DAILY, compress=True)
    assert meta.compressed is True
    result = wh.retrieve("AAPL", DataType.OHLCV, Timeframe.DAILY, use_cache=False)
    assert result is not None
    assert len(result) == len(df)


def test_get_default_warehouse_singleton():
    w1 = get_default_warehouse()
    w2 = get_default_warehouse()
    assert w1 is w2
