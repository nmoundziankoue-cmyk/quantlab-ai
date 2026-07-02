"""M13 — Institutional market data API router.

Prefix: /market-data
Tags:   Market Data
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from schemas.market_data import (
    CapabilitiesMatrixResponse,
    CacheStatsResponse,
    DatasetRequest,
    DatasetResponse,
    DatasetSplitInfo,
    FeatureRequest,
    FeatureResponse,
    HealthSummaryResponse,
    OHLCVBar,
    OHLCVRequest,
    OHLCVResponse,
    ProviderInfoResponse,
    ValidationRequest,
    ValidationResponse,
    WarehousePartitionInfo,
    WarehouseStatsResponse,
)
from services.data_provider import (
    ALL_PROVIDER_CLASSES,
    DataCapability,
    DataProviderRouter,
    MockDataProvider,
    get_default_router,
)
from services.data_warehouse import (
    DataType,
    DataWarehouse,
    Timeframe,
    get_default_warehouse,
)
from services.data_validation import DataValidator
from services.feature_store import FeatureStore, FEATURE_NAMES
from services.dataset_builder import (
    DatasetBuilder,
    DatasetConfig,
    LabelType,
    SplitMode,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["Market Data"])

# Shared singletons (one per process)
_validator = DataValidator()
_feature_store = FeatureStore()
_dataset_builder = DatasetBuilder()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bars_to_df(bars: List[OHLCVBar]) -> pd.DataFrame:
    """Convert API bar list → DatetimeIndex DataFrame."""
    records = [b.model_dump() for b in bars]
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    return df


def _df_to_bars(df: pd.DataFrame) -> List[OHLCVBar]:
    bars = []
    for ts, row in df.iterrows():
        bars.append(OHLCVBar(
            timestamp=str(ts),
            open=float(row.get("open", 0)),
            high=float(row.get("high", 0)),
            low=float(row.get("low", 0)),
            close=float(row.get("close", 0)),
            volume=float(row.get("volume", 0)),
        ))
    return bars


# ---------------------------------------------------------------------------
# Provider endpoints
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=List[ProviderInfoResponse])
def list_providers() -> List[ProviderInfoResponse]:
    """List all registered providers with health and latency."""
    router_inst = get_default_router()
    health = {h["provider"]: h for h in router_inst.health_summary()}
    latency = {l["provider"]: l for l in router_inst.latency_summary()}
    caps = router_inst.capabilities_matrix()

    results = []
    for name, cap_list in caps.items():
        h = health.get(name, {})
        lat = latency.get(name, {})
        results.append(ProviderInfoResponse(
            name=name,
            priority=0,
            capabilities=cap_list,
            is_healthy=h.get("is_healthy", True),
            p50_latency_ms=lat.get("p50_ms", 0.0),
            p95_latency_ms=lat.get("p95_ms", 0.0),
            error_rate=lat.get("error_rate", 0.0),
        ))
    return results


@router.get("/providers/capabilities", response_model=CapabilitiesMatrixResponse)
def capabilities_matrix() -> CapabilitiesMatrixResponse:
    return CapabilitiesMatrixResponse(
        providers=get_default_router().capabilities_matrix()
    )


@router.get("/providers/health", response_model=HealthSummaryResponse)
def provider_health() -> HealthSummaryResponse:
    router_inst = get_default_router()
    return HealthSummaryResponse(
        providers=router_inst.health_summary(),
        latency=router_inst.latency_summary(),
    )


@router.get("/providers/all-names")
def all_provider_names() -> Dict[str, List[str]]:
    """Return the names of all 11 supported provider classes."""
    return {"providers": list(ALL_PROVIDER_CLASSES.keys())}


# ---------------------------------------------------------------------------
# OHLCV history
# ---------------------------------------------------------------------------

@router.post("/ohlcv", response_model=OHLCVResponse)
def get_ohlcv(req: OHLCVRequest) -> OHLCVResponse:
    """Fetch OHLCV bars.  Uses warehouse cache when available."""
    warehouse = get_default_warehouse()
    sym = req.symbol.upper()

    # Check warehouse first
    if req.use_warehouse:
        tf_map = {"1d": Timeframe.DAILY, "1h": Timeframe.HOUR,
                  "1m": Timeframe.MINUTE_1, "5m": Timeframe.FIVE_MIN}
        tf = tf_map.get(req.interval, Timeframe.DAILY)
        cached_df = warehouse.retrieve(
            sym, DataType.OHLCV, tf,
            start=pd.Timestamp(req.start, tz="UTC"),
            end=pd.Timestamp(req.end, tz="UTC"),
        )
        if cached_df is not None and not cached_df.empty:
            return OHLCVResponse(
                symbol=sym,
                interval=req.interval,
                provider="warehouse_cache",
                bars=_df_to_bars(cached_df),
                bar_count=len(cached_df),
                from_cache=True,
            )

    # Fetch from provider
    try:
        data_router = get_default_router()
        df = data_router.get_historical_ohlcv(
            sym,
            pd.Timestamp(req.start, tz="UTC"),
            pd.Timestamp(req.end, tz="UTC"),
            req.interval,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Provider error: {exc}") from exc

    if df.empty:
        return OHLCVResponse(
            symbol=sym, interval=req.interval, provider="unknown",
            bars=[], bar_count=0,
        )

    # Store in warehouse
    if req.use_warehouse:
        try:
            warehouse.store(df, sym, DataType.OHLCV, tf, provider="live_fetch")
        except Exception as exc:
            logger.debug("Warehouse store failed (non-fatal): %s", exc)

    return OHLCVResponse(
        symbol=sym,
        interval=req.interval,
        provider="live_fetch",
        bars=_df_to_bars(df),
        bar_count=len(df),
        from_cache=False,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@router.post("/validate", response_model=ValidationResponse)
def validate_bars(req: ValidationRequest) -> ValidationResponse:
    """Validate a batch of OHLCV bars and return a quality score."""
    df = _bars_to_df(req.bars)
    result = _validator.validate(df, req.symbol.upper())
    return ValidationResponse(**result.to_dict())


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

@router.get("/features/catalog")
def feature_catalog() -> Dict[str, Any]:
    """Return the feature catalog with all available feature names."""
    return {
        "features": _feature_store.catalog(),
        "total": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
    }


@router.post("/features", response_model=FeatureResponse)
def compute_features(req: FeatureRequest) -> FeatureResponse:
    """Compute features from supplied OHLCV bars."""
    df = _bars_to_df(req.bars)

    # Add OHLCV columns required for features
    feature_df = _feature_store.compute(
        df,
        symbol=req.symbol.upper(),
        features=req.features,
        rfr_daily=req.rfr_daily,
        use_cache=False,
    )

    rows = []
    for ts, row in feature_df.iterrows():
        rec: Dict[str, Any] = {"timestamp": str(ts)}
        for col, val in row.items():
            v = float(val) if val is not None and not (isinstance(val, float) and np.isnan(val)) else None
            rec[col] = v
        rows.append(rec)

    return FeatureResponse(
        symbol=req.symbol.upper(),
        features_computed=list(feature_df.columns),
        row_count=len(feature_df),
        data=rows,
    )


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

@router.post("/datasets", response_model=DatasetResponse)
def build_dataset(req: DatasetRequest) -> DatasetResponse:
    """Build train/val/test datasets from bars with feature + label generation."""
    df = _bars_to_df(req.bars)

    label_map = {
        "classification": LabelType.CLASSIFICATION,
        "regression": LabelType.REGRESSION,
        "forecasting": LabelType.FORECASTING,
    }
    cfg = DatasetConfig(
        label_horizon=req.label_horizon,
        label_type=label_map[req.label_type],
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
        test_ratio=req.test_ratio,
        feature_cols=req.feature_cols,
        drop_na=req.drop_na,
    )

    # Compute features first
    feature_df = _feature_store.compute(df, symbol=req.symbol, use_cache=False)
    combined = pd.concat([df, feature_df], axis=1)

    builder = DatasetBuilder(cfg)
    try:
        train, val, test = builder.build(combined, symbol=req.symbol)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    splits = [
        DatasetSplitInfo(
            split=ds.split, n_samples=ds.n_samples, n_features=ds.n_features,
            start_date=str(ds.start_date) if ds.start_date else None,
            end_date=str(ds.end_date) if ds.end_date else None,
        )
        for ds in (train, val, test)
    ]

    return DatasetResponse(
        symbol=req.symbol.upper(),
        label_type=req.label_type,
        label_horizon=req.label_horizon,
        splits=splits,
        feature_names=list(train.X.columns),
        total_samples=train.n_samples + val.n_samples + test.n_samples,
    )


# ---------------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------------

@router.get("/warehouse/stats", response_model=WarehouseStatsResponse)
def warehouse_stats() -> WarehouseStatsResponse:
    stats = get_default_warehouse().warehouse_stats()
    return WarehouseStatsResponse(
        symbol_count=stats["symbol_count"],
        partition_count=stats["partition_count"],
        total_rows=stats["total_rows"],
        total_mb=stats["total_mb"],
        write_count=stats["write_count"],
        read_count=stats["read_count"],
        cache_hit_rate=stats["cache_hit_rate"],
    )


@router.get("/warehouse/partitions", response_model=List[WarehousePartitionInfo])
def list_partitions(
    symbol: Optional[str] = Query(None),
    data_type: Optional[str] = Query(None),
) -> List[WarehousePartitionInfo]:
    all_meta = get_default_warehouse().get_all_metadata()
    if symbol:
        all_meta = [m for m in all_meta if m["symbol"] == symbol.upper()]
    if data_type:
        all_meta = [m for m in all_meta if m["data_type"] == data_type]
    return [
        WarehousePartitionInfo(
            symbol=m["symbol"],
            data_type=m["data_type"],
            timeframe=m["timeframe"],
            version=m["version"],
            provider=m["provider"],
            row_count=m["row_count"],
            start_ts=m["start_ts"],
            end_ts=m["end_ts"],
            quality_score=m["quality_score"],
            is_expired=m["is_expired"],
            size_bytes=m["size_bytes"],
        )
        for m in all_meta
    ]


@router.delete("/warehouse/cleanup")
def cleanup_warehouse() -> Dict[str, int]:
    removed = get_default_warehouse().cleanup()
    return {"removed_partitions": removed}


# ---------------------------------------------------------------------------
# Cache stats
# ---------------------------------------------------------------------------

@router.get("/cache/stats", response_model=CacheStatsResponse)
def cache_stats() -> CacheStatsResponse:
    wh = get_default_warehouse()
    stats = wh.warehouse_stats()
    cache = stats.get("cache", {})
    return CacheStatsResponse(
        size=cache.get("size", 0),
        maxsize=cache.get("maxsize", 0),
        ttl_seconds=cache.get("ttl_seconds", 0.0),
        hit_rate=stats.get("cache_hit_rate", 0.0),
    )
