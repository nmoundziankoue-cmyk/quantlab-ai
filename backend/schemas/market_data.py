"""M13 — Pydantic v2 schemas for market data API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class ProviderInfoResponse(BaseModel):
    name: str
    priority: int
    capabilities: List[str]
    is_healthy: bool
    p50_latency_ms: float
    p95_latency_ms: float
    error_rate: float


class CapabilitiesMatrixResponse(BaseModel):
    providers: Dict[str, List[str]]


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------

class OHLCVBar(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    start: str = Field(..., description="ISO date string, e.g. 2023-01-01")
    end: str = Field(..., description="ISO date string, e.g. 2023-12-31")
    interval: str = Field("1d", description="1d|1h|5m|1m")
    provider: Optional[str] = None
    use_warehouse: bool = True

    @model_validator(mode="after")
    def check_dates(self) -> "OHLCVRequest":
        try:
            import pandas as pd
            s = pd.Timestamp(self.start)
            e = pd.Timestamp(self.end)
            if s >= e:
                raise ValueError("start must be before end")
        except Exception as exc:
            raise ValueError(f"Invalid date: {exc}") from exc
        return self


class OHLCVResponse(BaseModel):
    symbol: str
    interval: str
    provider: str
    bars: List[OHLCVBar]
    bar_count: int
    from_cache: bool = False
    quality_score: Optional[float] = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationIssueSchema(BaseModel):
    type: str
    severity: str
    description: str
    rows_affected: int
    sample_indices: List[str]


class ValidationRequest(BaseModel):
    symbol: str
    bars: List[OHLCVBar]


class ValidationResponse(BaseModel):
    symbol: str
    row_count: int
    quality_score: float
    passed: bool
    error_count: int
    warning_count: int
    issues: List[ValidationIssueSchema]


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

class FeatureRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    bars: List[OHLCVBar]
    features: Optional[List[str]] = None
    rfr_daily: float = Field(0.0, ge=0.0)

    @model_validator(mode="after")
    def check_bars(self) -> "FeatureRequest":
        if len(self.bars) < 2:
            raise ValueError("At least 2 bars required for feature computation")
        return self


class FeatureResponse(BaseModel):
    symbol: str
    features_computed: List[str]
    row_count: int
    data: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

class DatasetRequest(BaseModel):
    symbol: str
    bars: List[OHLCVBar]
    label_horizon: int = Field(1, ge=1, le=252)
    label_type: str = Field("classification", pattern="^(classification|regression|forecasting)$")
    train_ratio: float = Field(0.70, gt=0.0, lt=1.0)
    val_ratio: float = Field(0.15, gt=0.0, lt=1.0)
    test_ratio: float = Field(0.15, gt=0.0, lt=1.0)
    feature_cols: Optional[List[str]] = None
    drop_na: bool = True

    @model_validator(mode="after")
    def check_ratios(self) -> "DatasetRequest":
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"train + val + test must sum to 1.0, got {total:.3f}")
        return self


class DatasetSplitInfo(BaseModel):
    split: str
    n_samples: int
    n_features: int
    start_date: Optional[str]
    end_date: Optional[str]


class DatasetResponse(BaseModel):
    symbol: str
    label_type: str
    label_horizon: int
    splits: List[DatasetSplitInfo]
    feature_names: List[str]
    total_samples: int


# ---------------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------------

class WarehouseStatsResponse(BaseModel):
    symbol_count: int
    partition_count: int
    total_rows: int
    total_mb: float
    write_count: int
    read_count: int
    cache_hit_rate: float


class WarehousePartitionInfo(BaseModel):
    symbol: str
    data_type: str
    timeframe: str
    version: int
    provider: str
    row_count: int
    start_ts: Optional[str]
    end_ts: Optional[str]
    quality_score: float
    is_expired: bool
    size_bytes: int


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class CacheStatsResponse(BaseModel):
    size: int
    maxsize: int
    ttl_seconds: float
    hit_rate: float


# ---------------------------------------------------------------------------
# Provider health
# ---------------------------------------------------------------------------

class HealthSummaryResponse(BaseModel):
    providers: List[Dict[str, Any]]
    latency: List[Dict[str, Any]]
