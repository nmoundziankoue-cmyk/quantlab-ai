"""M13 — API tests for /market-data router.

Uses FastAPI TestClient — no network calls.
All data is synthetic, injected via request body.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bars(n: int = 100, seed: int = 0) -> list:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-02", periods=n, freq="B", tz="UTC")
    close = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, n))
    bars = []
    for i, ts in enumerate(idx):
        bars.append({
            "timestamp": ts.isoformat(),
            "open": float(close[i] * (1 + rng.normal(0, 0.001))),
            "high": float(close[i] * (1 + abs(rng.normal(0, 0.005)))),
            "low": float(close[i] * (1 - abs(rng.normal(0, 0.005)))),
            "close": float(close[i]),
            "volume": float(rng.integers(1_000_000, 5_000_000)),
        })
    return bars


# ===========================================================================
# GET /market-data/providers
# ===========================================================================

def test_list_providers_200():
    res = client.get("/market-data/providers")
    assert res.status_code == 200


def test_list_providers_returns_list():
    res = client.get("/market-data/providers")
    data = res.json()
    assert isinstance(data, list)


def test_list_providers_has_yahoo():
    res = client.get("/market-data/providers")
    names = [p["name"] for p in res.json()]
    assert "yahoo_finance" in names


def test_providers_capabilities_endpoint():
    res = client.get("/market-data/providers/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data


def test_providers_health_endpoint():
    res = client.get("/market-data/providers/health")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    assert "latency" in data


def test_all_provider_names_11():
    res = client.get("/market-data/providers/all-names")
    assert res.status_code == 200
    names = res.json()["providers"]
    assert len(names) == 11
    assert "sec_edgar" in names
    assert "polygon" in names


# ===========================================================================
# POST /market-data/validate
# ===========================================================================

def test_validate_clean_bars_200():
    bars = _make_bars(50)
    res = client.post("/market-data/validate", json={"symbol": "AAPL", "bars": bars})
    assert res.status_code == 200


def test_validate_returns_quality_score():
    bars = _make_bars(50)
    res = client.post("/market-data/validate", json={"symbol": "AAPL", "bars": bars})
    data = res.json()
    assert "quality_score" in data
    assert 0.0 <= data["quality_score"] <= 1.0


def test_validate_returns_passed_flag():
    bars = _make_bars(50)
    res = client.post("/market-data/validate", json={"symbol": "AAPL", "bars": bars})
    data = res.json()
    assert "passed" in data
    assert isinstance(data["passed"], bool)


def test_validate_bad_data_detected():
    bars = _make_bars(20)
    bars[5]["close"] = -100.0   # inject negative price
    res = client.post("/market-data/validate", json={"symbol": "BAD", "bars": bars})
    assert res.status_code == 200
    data = res.json()
    assert not data["passed"]
    assert data["error_count"] > 0


def test_validate_issues_list():
    bars = _make_bars(20)
    res = client.post("/market-data/validate", json={"symbol": "AAPL", "bars": bars})
    data = res.json()
    assert "issues" in data
    assert isinstance(data["issues"], list)


# ===========================================================================
# GET /market-data/features/catalog
# ===========================================================================

def test_feature_catalog_200():
    res = client.get("/market-data/features/catalog")
    assert res.status_code == 200


def test_feature_catalog_has_features():
    res = client.get("/market-data/features/catalog")
    data = res.json()
    assert "features" in data
    assert len(data["features"]) >= 20


def test_feature_catalog_includes_rsi():
    res = client.get("/market-data/features/catalog")
    names = [f["name"] for f in res.json()["features"]]
    assert "rsi_14" in names


# ===========================================================================
# POST /market-data/features
# ===========================================================================

def test_compute_features_200():
    bars = _make_bars(100)
    res = client.post("/market-data/features", json={
        "symbol": "AAPL",
        "bars": bars,
        "features": ["returns", "rsi_14"],
    })
    assert res.status_code == 200


def test_compute_features_returns_requested():
    bars = _make_bars(100)
    res = client.post("/market-data/features", json={
        "symbol": "AAPL",
        "bars": bars,
        "features": ["returns", "rsi_14", "macd"],
    })
    data = res.json()
    assert "returns" in data["features_computed"]
    assert "rsi_14" in data["features_computed"]


def test_compute_features_row_count():
    bars = _make_bars(100)
    res = client.post("/market-data/features", json={
        "symbol": "AAPL",
        "bars": bars,
        "features": ["returns"],
    })
    data = res.json()
    assert data["row_count"] == 100


def test_compute_features_too_few_bars_422():
    res = client.post("/market-data/features", json={
        "symbol": "AAPL",
        "bars": _make_bars(1),
        "features": ["returns"],
    })
    assert res.status_code == 422


def test_compute_features_data_has_timestamps():
    bars = _make_bars(50)
    res = client.post("/market-data/features", json={
        "symbol": "AAPL",
        "bars": bars,
        "features": ["returns"],
    })
    data = res.json()
    assert all("timestamp" in row for row in data["data"])


# ===========================================================================
# POST /market-data/datasets
# ===========================================================================

def test_build_dataset_200():
    bars = _make_bars(300)
    res = client.post("/market-data/datasets", json={
        "symbol": "AAPL",
        "bars": bars,
        "label_horizon": 1,
        "label_type": "classification",
    })
    assert res.status_code == 200


def test_build_dataset_splits_present():
    bars = _make_bars(300)
    res = client.post("/market-data/datasets", json={
        "symbol": "AAPL",
        "bars": bars,
        "label_horizon": 1,
        "label_type": "classification",
    })
    data = res.json()
    assert "splits" in data
    split_names = [s["split"] for s in data["splits"]]
    assert "train" in split_names
    assert "val" in split_names
    assert "test" in split_names


def test_build_dataset_total_samples_positive():
    bars = _make_bars(300)
    res = client.post("/market-data/datasets", json={
        "symbol": "AAPL", "bars": bars,
        "label_horizon": 1, "label_type": "regression",
    })
    data = res.json()
    assert data["total_samples"] > 0


def test_build_dataset_bad_ratios_422():
    bars = _make_bars(300)
    res = client.post("/market-data/datasets", json={
        "symbol": "AAPL", "bars": bars,
        "label_horizon": 1, "label_type": "classification",
        "train_ratio": 0.8, "val_ratio": 0.5, "test_ratio": 0.5,
    })
    assert res.status_code == 422


def test_build_dataset_regression_type():
    bars = _make_bars(300)
    res = client.post("/market-data/datasets", json={
        "symbol": "AAPL", "bars": bars,
        "label_horizon": 5, "label_type": "regression",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["label_type"] == "regression"


def test_build_dataset_invalid_label_type_422():
    bars = _make_bars(300)
    res = client.post("/market-data/datasets", json={
        "symbol": "AAPL", "bars": bars,
        "label_type": "unknown_type",
    })
    assert res.status_code == 422


# ===========================================================================
# GET /market-data/warehouse/stats
# ===========================================================================

def test_warehouse_stats_200():
    res = client.get("/market-data/warehouse/stats")
    assert res.status_code == 200


def test_warehouse_stats_keys():
    res = client.get("/market-data/warehouse/stats")
    data = res.json()
    for key in ("symbol_count", "partition_count", "total_rows", "total_mb", "write_count"):
        assert key in data


# ===========================================================================
# GET /market-data/warehouse/partitions
# ===========================================================================

def test_warehouse_partitions_200():
    res = client.get("/market-data/warehouse/partitions")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ===========================================================================
# DELETE /market-data/warehouse/cleanup
# ===========================================================================

def test_warehouse_cleanup_200():
    res = client.delete("/market-data/warehouse/cleanup")
    assert res.status_code == 200
    data = res.json()
    assert "removed_partitions" in data


# ===========================================================================
# GET /market-data/cache/stats
# ===========================================================================

def test_cache_stats_200():
    res = client.get("/market-data/cache/stats")
    assert res.status_code == 200


def test_cache_stats_keys():
    res = client.get("/market-data/cache/stats")
    data = res.json()
    for key in ("size", "maxsize", "ttl_seconds", "hit_rate"):
        assert key in data
