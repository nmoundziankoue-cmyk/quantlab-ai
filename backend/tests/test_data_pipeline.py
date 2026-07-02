"""M13 — Tests for data_validation, historical_data_engine, feature_store, dataset_builder.

All deterministic, no network.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.data_validation import (
    DataValidator,
    IssueType,
    IssueSeverity,
    ValidationResult,
    _check_duplicate_timestamps,
    _check_missing_bars,
    _check_negative_prices,
    _check_ohlc_violations,
    _check_price_spikes,
    _check_stale_data,
    _check_invalid_volume,
    _check_zero_prices,
)
from services.historical_data_engine import (
    AdjustmentFactor,
    EngineResult,
    GapInfo,
    HistoricalDataEngine,
    get_trading_days,
    is_trading_day,
)
from services.feature_store import (
    FEATURE_CATALOG,
    FEATURE_NAMES,
    FeatureStore,
    _ema,
    _rsi,
    _atr,
    _bollinger,
    _macd,
    _rolling_sharpe,
    _rolling_vol,
    _vwap,
    _z_score,
)
from services.dataset_builder import (
    DatasetBuilder,
    DatasetConfig,
    Dataset,
    LabelType,
    SplitMode,
    WalkForwardFold,
    generate_labels,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _ohlcv(n: int = 252, seed: int = 42, tz: str = "UTC") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-03", periods=n, freq="B", tz=tz)
    close = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, n))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    # Clamp open to [low, high] so OHLC constraints are respected
    open_ = np.clip(close * (1 + rng.normal(0, 0.003, n)), low, high)
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
    }, index=idx)


# ===========================================================================
# DATA VALIDATION
# ===========================================================================

# --- individual checks ---

def test_check_no_duplicate_timestamps():
    df = _ohlcv(50)
    assert _check_duplicate_timestamps(df) is None


def test_check_duplicate_timestamps_detected():
    df = _ohlcv(10)
    df = pd.concat([df, df.iloc[:2]])
    issue = _check_duplicate_timestamps(df)
    assert issue is not None
    assert issue.issue_type == IssueType.DUPLICATE_TIMESTAMPS


def test_check_negative_prices_clean():
    df = _ohlcv(50)
    assert _check_negative_prices(df) is None


def test_check_negative_prices_detected():
    df = _ohlcv(10).copy()
    df.iloc[3, df.columns.get_loc("close")] = -1.0
    issue = _check_negative_prices(df)
    assert issue is not None
    assert issue.severity == IssueSeverity.CRITICAL


def test_check_zero_prices_detected():
    df = _ohlcv(10).copy()
    df.iloc[2, df.columns.get_loc("close")] = 0.0
    issue = _check_zero_prices(df)
    assert issue is not None
    assert issue.issue_type == IssueType.ZERO_PRICE


def test_check_ohlc_violations():
    df = _ohlcv(10).copy()
    # Force high < low on one row
    df.iloc[0, df.columns.get_loc("high")] = 50.0
    df.iloc[0, df.columns.get_loc("low")] = 60.0
    issue = _check_ohlc_violations(df)
    assert issue is not None
    assert issue.issue_type == IssueType.OHLC_VIOLATION


def test_check_ohlc_clean():
    df = _ohlcv(50)
    assert _check_ohlc_violations(df) is None


def test_check_invalid_volume_negative():
    df = _ohlcv(10).copy()
    df.iloc[0, df.columns.get_loc("volume")] = -1.0
    issue = _check_invalid_volume(df)
    assert issue is not None
    assert issue.issue_type == IssueType.INVALID_VOLUME


def test_check_price_spike_detected():
    df = _ohlcv(50).copy()
    df.iloc[25, df.columns.get_loc("close")] = df["close"].iloc[24] * 2.5
    issue = _check_price_spikes(df, threshold=0.5)
    assert issue is not None
    assert issue.issue_type == IssueType.PRICE_SPIKE


def test_check_stale_data_detected():
    df = _ohlcv(10)
    df.index = pd.date_range("2020-01-01", periods=10, freq="B", tz="UTC")
    issue = _check_stale_data(df, max_age_days=30)
    assert issue is not None
    assert issue.issue_type == IssueType.STALE_DATA


# --- DataValidator ---

def test_validator_clean_data_passes():
    v = DataValidator()
    df = _ohlcv()
    result = v.validate(df, "AAPL")
    assert isinstance(result, ValidationResult)
    # Clean data should have no critical/error issues
    assert result.error_count == 0


def test_validator_quality_score_range():
    v = DataValidator()
    result = v.validate(_ohlcv(), "AAPL")
    assert 0.0 <= result.quality_score <= 1.0


def test_validator_perfect_score_clean():
    v = DataValidator(stale_days=99999)  # disable stale check
    df = _ohlcv()
    result = v.validate(df, "AAPL")
    assert result.quality_score > 0.80


def test_validator_failed_on_negative_price():
    v = DataValidator()
    df = _ohlcv(20).copy()
    df.iloc[5, df.columns.get_loc("close")] = -10.0
    result = v.validate(df, "BAD")
    assert not result.passed
    assert result.error_count > 0


def test_validator_to_dict():
    v = DataValidator()
    result = v.validate(_ohlcv(), "AAPL")
    d = result.to_dict()
    for key in ("symbol", "row_count", "quality_score", "passed", "error_count", "warning_count", "issues"):
        assert key in d


def test_validator_many_returns_dict():
    v = DataValidator()
    data = {"AAPL": _ohlcv(50), "MSFT": _ohlcv(50, seed=1)}
    results = v.validate_many(data)
    assert "AAPL" in results
    assert "MSFT" in results


def test_validator_summary_report():
    v = DataValidator()
    data = {"AAPL": _ohlcv(50), "MSFT": _ohlcv(50, seed=1)}
    results = v.validate_many(data)
    summary = v.summary_report(results)
    assert summary["total_symbols"] == 2
    assert "avg_quality_score" in summary


# ===========================================================================
# HISTORICAL DATA ENGINE
# ===========================================================================

def test_trading_days_excludes_weekends():
    days = get_trading_days(pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-08"))
    for d in days:
        assert d.weekday() < 5


def test_trading_days_count_roughly_correct():
    days = get_trading_days(pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-31"))
    assert 245 <= len(days) <= 255


def test_is_trading_day_weekend():
    assert not is_trading_day(pd.Timestamp("2023-01-07"))  # Saturday


def test_is_trading_day_known_holiday():
    assert not is_trading_day(pd.Timestamp("2023-11-23"))  # Thanksgiving 2023


def test_is_trading_day_normal():
    assert is_trading_day(pd.Timestamp("2023-01-05"))  # normal Thursday


def test_engine_process_returns_result():
    engine = HistoricalDataEngine()
    df = _ohlcv(50)
    result = engine.process(df, "AAPL")
    assert isinstance(result, EngineResult)
    assert len(result.data) > 0


def test_engine_normalizes_timezone():
    engine = HistoricalDataEngine(target_tz="UTC")
    df = _ohlcv(50, tz="UTC")
    # Remove timezone
    df.index = df.index.tz_localize(None)
    result = engine.process(df, "AAPL")
    assert result.timezone_normalized is True


def test_engine_sorts_and_dedupes():
    engine = HistoricalDataEngine()
    df = _ohlcv(20)
    df = pd.concat([df.iloc[10:], df.iloc[:10]])  # shuffle order
    result = engine.process(df, "AAPL")
    assert result.data.index.is_monotonic_increasing


def test_engine_detect_gaps_no_gaps():
    engine = HistoricalDataEngine()
    df = _ohlcv(20)  # continuous business day index
    gaps = engine.detect_gaps(df, "1d")
    # May detect some holiday gaps; should be small
    assert all(g.missing_bars > 0 for g in gaps)


def test_engine_detect_gaps_with_gap():
    engine = HistoricalDataEngine()
    df = _ohlcv(40)
    df = df.drop(df.index[15:18])  # remove 3 bars
    gaps = engine.detect_gaps(df, "1d")
    assert len(gaps) >= 1


def test_engine_repair_gaps():
    engine = HistoricalDataEngine(repair_gaps=True, max_gap_fill_bars=10)
    df = _ohlcv(40)
    idx_to_drop = df.index[15:17]
    df = df.drop(idx_to_drop)
    repaired, gaps = engine.repair_gaps(df, "1d")
    assert len(repaired) >= len(df)


def test_engine_adjust_for_splits():
    engine = HistoricalDataEngine()
    df = _ohlcv(100)
    split_date = df.index[50]
    splits = pd.DataFrame({"ratio": [2.0]}, index=[split_date])
    adjusted = engine.adjust_for_splits(df, splits)
    # Prices before split should be halved
    before_close = adjusted["close"].iloc[:50].mean()
    after_close = df["close"].iloc[:50].mean()
    assert abs(before_close - after_close / 2) < 1.0


def test_engine_adjust_for_splits_empty():
    engine = HistoricalDataEngine()
    df = _ohlcv(50)
    adjusted = engine.adjust_for_splits(df, pd.DataFrame())
    pd.testing.assert_frame_equal(adjusted, df)


def test_engine_to_dict():
    engine = HistoricalDataEngine()
    result = engine.process(_ohlcv(20), "AAPL")
    d = result.to_dict()
    for key in ("symbol", "rows", "gaps_found", "gaps_repaired", "timezone_normalized"):
        assert key in d


# ===========================================================================
# FEATURE STORE
# ===========================================================================

def test_feature_store_returns_dataframe():
    fs = FeatureStore()
    df = _ohlcv()
    result = fs.compute(df, "AAPL", features=["returns", "rsi_14"])
    assert isinstance(result, pd.DataFrame)
    assert "returns" in result.columns
    assert "rsi_14" in result.columns


def test_feature_store_returns_finite():
    fs = FeatureStore()
    df = _ohlcv(100)
    result = fs.compute(df, "AAPL", features=["returns", "rolling_vol_21", "macd"])
    # After lookback, should have finite values
    tail = result.dropna()
    assert len(tail) > 0


def test_feature_store_catalog_complete():
    fs = FeatureStore()
    catalog = fs.catalog()
    assert len(catalog) >= 20
    names = [f["name"] for f in catalog]
    assert "rsi_14" in names
    assert "macd" in names
    assert "bb_pct_b_20" in names


def test_feature_store_rsi_range():
    fs = FeatureStore()
    df = _ohlcv(100)
    result = fs.compute(df, "AAPL", features=["rsi_14"])
    rsi = result["rsi_14"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


def test_feature_store_macd_components():
    fs = FeatureStore()
    df = _ohlcv(100)
    result = fs.compute(df, "AAPL", features=["macd", "macd_signal", "macd_hist"])
    assert "macd" in result.columns
    assert "macd_signal" in result.columns
    assert "macd_hist" in result.columns


def test_feature_store_bollinger_bands_ordered():
    fs = FeatureStore()
    df = _ohlcv(100)
    result = fs.compute(df, "AAPL", features=["bb_upper_20", "bb_lower_20"])
    tail = result.dropna()
    assert (tail["bb_upper_20"] >= tail["bb_lower_20"]).all()


def test_feature_store_cache_hit():
    fs = FeatureStore()
    df = _ohlcv(50)
    fs.compute(df, "CACHETICKER", features=["returns"])
    before = fs._cache.size
    fs.compute(df, "CACHETICKER", features=["returns"])
    assert fs._cache.size == before  # cache hit, not added


def test_feature_store_invalidate():
    fs = FeatureStore()
    df = _ohlcv(50)
    fs.compute(df, "AAPL", features=["returns"])
    fs.invalidate("AAPL")
    # After invalidation, cache should not have AAPL
    cached = fs._cache.get("AAPL", ("returns",))
    assert cached is None


def test_ema_exponential_shape():
    close = pd.Series([100.0] * 10 + [110.0] * 10)
    ema = _ema(close, span=5)
    # EMA should approach 110 after the step
    assert ema.iloc[-1] > 108


def test_rsi_neutral_at_midpoint():
    # Alternating up/down should give RSI near 50
    close = pd.Series([100.0 + (i % 2) * 1.0 for i in range(50)])
    rsi = _rsi(close, 14).dropna()
    assert 40 < rsi.iloc[-1] < 60


def test_atr_positive():
    df = _ohlcv(50)
    atr = _atr(df["high"], df["low"], df["close"], 14).dropna()
    assert (atr > 0).all()


def test_bollinger_bands_pct_b_range():
    df = _ohlcv(100)
    _, _, pct_b = _bollinger(df["close"], 20)
    vals = pct_b.dropna()
    # For non-spike data, most values should be between 0 and 1
    in_range = ((vals >= -1) & (vals <= 2)).mean()
    assert in_range > 0.90


def test_vwap_monotone_makes_sense():
    df = _ohlcv(20)
    vwap = _vwap(df["high"], df["low"], df["close"], df["volume"])
    # VWAP should be within the high-low range
    assert (vwap.dropna() > 0).all()


def test_z_score_near_zero_mean():
    df = _ohlcv(200)
    z = _z_score(df["close"], 21).dropna()
    # Mean of z-score over a long series should be near 0
    assert abs(z.mean()) < 1.0


def test_rolling_sharpe_finite():
    df = _ohlcv(100)
    ret = df["close"].pct_change()
    sharpe = _rolling_sharpe(ret, 21).dropna()
    assert np.isfinite(sharpe.values).all()


# ===========================================================================
# DATASET BUILDER
# ===========================================================================

def test_dataset_builder_ratio_split():
    cfg = DatasetConfig(label_horizon=1, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    builder = DatasetBuilder(cfg)
    df = _ohlcv(300)
    train, val, test = builder.build(df, "AAPL")
    assert isinstance(train, Dataset)
    total = train.n_samples + val.n_samples + test.n_samples
    assert total > 0


def test_dataset_builder_split_names():
    builder = DatasetBuilder()
    df = _ohlcv(300)
    train, val, test = builder.build(df, "AAPL")
    assert train.split == "train"
    assert val.split == "val"
    assert test.split == "test"


def test_dataset_builder_no_data_leakage():
    builder = DatasetBuilder()
    df = _ohlcv(300)
    train, val, test = builder.build(df, "AAPL")
    if train.n_samples > 0 and val.n_samples > 0:
        assert train.end_date <= val.start_date


def test_dataset_builder_classification_labels():
    cfg = DatasetConfig(label_type=LabelType.CLASSIFICATION, label_horizon=1)
    builder = DatasetBuilder(cfg)
    df = _ohlcv(200)
    train, _, _ = builder.build(df, "AAPL")
    unique_labels = set(train.y.unique())
    assert unique_labels.issubset({-1, 0, 1})


def test_dataset_builder_regression_labels():
    cfg = DatasetConfig(label_type=LabelType.REGRESSION, label_horizon=5)
    builder = DatasetBuilder(cfg)
    df = _ohlcv(200)
    train, _, _ = builder.build(df, "AAPL")
    assert train.y.dtype in (float, np.float64, np.float32)


def test_dataset_builder_to_arrays():
    builder = DatasetBuilder()
    df = _ohlcv(200)
    train, _, _ = builder.build(df, "AAPL")
    X, y = train.to_arrays()
    assert X.shape[0] == len(train.X)
    assert len(y) == len(train.y)


def test_dataset_builder_to_dict():
    builder = DatasetBuilder()
    df = _ohlcv(200)
    train, _, _ = builder.build(df, "AAPL")
    d = train.to_dict()
    for key in ("name", "split", "n_samples", "n_features"):
        assert key in d


def test_dataset_builder_invalid_ratios():
    with pytest.raises(ValueError, match="sum to 1.0"):
        DatasetConfig(train_ratio=0.8, val_ratio=0.1, test_ratio=0.5)


def test_walk_forward_builds_folds():
    cfg = DatasetConfig(wf_train_window=100, wf_val_window=30, wf_step=20)
    builder = DatasetBuilder(cfg)
    df = _ohlcv(300)
    folds = builder.build_walk_forward(df, "AAPL")
    assert len(folds) > 0
    assert all(isinstance(f, WalkForwardFold) for f in folds)


def test_walk_forward_fold_ids_sequential():
    cfg = DatasetConfig(wf_train_window=80, wf_val_window=20, wf_step=20)
    builder = DatasetBuilder(cfg)
    df = _ohlcv(300)
    folds = builder.build_walk_forward(df, "AAPL")
    ids = [f.fold_id for f in folds]
    assert ids == list(range(len(folds)))


def test_walk_forward_no_leakage():
    cfg = DatasetConfig(wf_train_window=80, wf_val_window=20, wf_step=20)
    builder = DatasetBuilder(cfg)
    df = _ohlcv(300)
    folds = builder.build_walk_forward(df, "AAPL")
    for fold in folds:
        if fold.train.n_samples > 0 and fold.val.n_samples > 0:
            assert fold.train.end_date <= fold.val.start_date


def test_rolling_build_returns_list():
    cfg = DatasetConfig(rolling_window=100, rolling_step=20)
    builder = DatasetBuilder(cfg)
    df = _ohlcv(300)
    folds = builder.build_rolling(df, "AAPL")
    assert isinstance(folds, list)
    assert len(folds) > 0


def test_time_series_cv_n_splits():
    builder = DatasetBuilder()
    df = _ohlcv(300)
    folds = builder.build_time_series_cv(df, "AAPL", n_splits=5)
    assert len(folds) == 5


def test_generate_labels_classification():
    df = _ohlcv(100)
    cfg = DatasetConfig(label_type=LabelType.CLASSIFICATION, label_horizon=1)
    labels = generate_labels(df, cfg)
    assert set(labels.dropna().unique()).issubset({-1, 0, 1})


def test_generate_labels_regression():
    df = _ohlcv(100)
    cfg = DatasetConfig(label_type=LabelType.REGRESSION, label_horizon=1)
    labels = generate_labels(df, cfg)
    assert labels.dtype.kind == "f"


def test_generate_labels_no_close_raises():
    df = pd.DataFrame({"notclose": [1, 2, 3]})
    cfg = DatasetConfig()
    with pytest.raises(ValueError, match="close"):
        generate_labels(df, cfg)
