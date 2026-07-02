"""M13 Phase 6 — Institutional dataset builder.

Generates train / validation / test splits and walk-forward windows
from OHLCV feature DataFrames.  Supports classification, regression,
and forecasting label generation.  All operations are deterministic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums / config
# ---------------------------------------------------------------------------

class SplitMode(Enum):
    RATIO = "ratio"              # fixed train/val/test percentages
    DATE = "date"                # explicit cut dates
    ROLLING = "rolling"          # rolling window
    WALK_FORWARD = "walk_forward"


class LabelType(Enum):
    CLASSIFICATION = "classification"  # up/down/flat
    REGRESSION = "regression"          # future return (float)
    FORECASTING = "forecasting"        # future price sequence


@dataclass
class DatasetConfig:
    label_horizon: int = 1                  # bars ahead for label
    label_type: LabelType = LabelType.CLASSIFICATION
    classification_threshold: float = 0.001 # ±0.1% for up/down

    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15

    rolling_window: int = 252
    rolling_step: int = 21

    wf_train_window: int = 252
    wf_val_window: int = 63
    wf_step: int = 21

    feature_cols: Optional[List[str]] = None
    drop_na: bool = True
    shuffle: bool = False  # never shuffle time-series data by default

    def __post_init__(self) -> None:
        if abs(self.train_ratio + self.val_ratio + self.test_ratio - 1.0) > 1e-6:
            raise ValueError("train + val + test ratios must sum to 1.0")


@dataclass
class Dataset:
    name: str
    X: pd.DataFrame
    y: pd.Series
    split: str                  # "train" | "val" | "test"
    start_date: Optional[pd.Timestamp] = None
    end_date: Optional[pd.Timestamp] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def n_samples(self) -> int:
        return len(self.X)

    @property
    def n_features(self) -> int:
        return self.X.shape[1]

    def to_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        return self.X.values, self.y.values

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "split": self.split,
            "n_samples": self.n_samples,
            "n_features": self.n_features,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "label_type": self.metadata.get("label_type"),
            "label_horizon": self.metadata.get("label_horizon"),
        }


@dataclass
class WalkForwardFold:
    fold_id: int
    train: Dataset
    val: Dataset
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fold_id": self.fold_id,
            "train": self.train.to_dict(),
            "val": self.val.to_dict(),
        }


# ---------------------------------------------------------------------------
# Label generators
# ---------------------------------------------------------------------------

def _generate_classification_labels(
    close: pd.Series,
    horizon: int,
    threshold: float,
) -> pd.Series:
    """Return 1 (up), -1 (down), 0 (flat) for horizon-day forward return."""
    fwd_return = close.shift(-horizon) / close - 1
    labels = pd.Series(0, index=close.index, dtype=int)
    labels[fwd_return > threshold] = 1
    labels[fwd_return < -threshold] = -1
    return labels


def _generate_regression_labels(
    close: pd.Series,
    horizon: int,
) -> pd.Series:
    """Return the horizon-day forward return as a float."""
    return (close.shift(-horizon) / close - 1).rename("target")


def _generate_forecasting_labels(
    close: pd.Series,
    horizon: int,
) -> pd.DataFrame:
    """Return columns t+1, t+2, ..., t+horizon of future close prices."""
    cols = {}
    for h in range(1, horizon + 1):
        cols[f"t+{h}"] = close.shift(-h)
    return pd.DataFrame(cols, index=close.index)


def generate_labels(
    df: pd.DataFrame,
    config: DatasetConfig,
) -> pd.Series:
    """Generate a label Series from the DataFrame's ``close`` column."""
    if "close" not in df.columns:
        raise ValueError("DataFrame must have a 'close' column to generate labels")
    close = df["close"]
    if config.label_type == LabelType.CLASSIFICATION:
        return _generate_classification_labels(
            close, config.label_horizon, config.classification_threshold
        )
    if config.label_type == LabelType.REGRESSION:
        return _generate_regression_labels(close, config.label_horizon)
    if config.label_type == LabelType.FORECASTING:
        # For forecasting return the t+horizon only (single target)
        return (close.shift(-config.label_horizon)).rename(f"close_t+{config.label_horizon}")
    raise ValueError(f"Unknown label type: {config.label_type}")


# ---------------------------------------------------------------------------
# DatasetBuilder
# ---------------------------------------------------------------------------

class DatasetBuilder:
    """Build train/val/test or walk-forward datasets from feature DataFrames."""

    def __init__(self, config: Optional[DatasetConfig] = None) -> None:
        self._config = config or DatasetConfig()

    def build(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        mode: SplitMode = SplitMode.RATIO,
        val_date: Optional[pd.Timestamp] = None,
        test_date: Optional[pd.Timestamp] = None,
    ) -> Tuple[Dataset, Dataset, Dataset]:
        """Return (train, val, test) datasets."""
        cfg = self._config
        feature_df, labels = self._prepare(df, cfg)

        if mode == SplitMode.RATIO:
            return self._ratio_split(feature_df, labels, cfg, symbol)
        if mode == SplitMode.DATE:
            if val_date is None or test_date is None:
                raise ValueError("val_date and test_date required for DATE mode")
            return self._date_split(feature_df, labels, cfg, symbol, val_date, test_date)
        raise ValueError(f"Unsupported mode for build(): {mode}")

    def build_rolling(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
    ) -> List[Tuple[Dataset, Dataset]]:
        """Build a list of (train, val) pairs using a rolling window."""
        cfg = self._config
        feature_df, labels = self._prepare(df, cfg)
        folds: List[Tuple[Dataset, Dataset]] = []

        step = cfg.rolling_step
        window = cfg.rolling_window
        val_size = int(window * cfg.val_ratio)
        train_size = window - val_size
        n = len(feature_df)

        i = 0
        while i + window <= n:
            train_end = i + train_size
            val_end = i + window

            train_slice = feature_df.iloc[i:train_end]
            train_labels = labels.iloc[i:train_end]
            val_slice = feature_df.iloc[train_end:val_end]
            val_labels = labels.iloc[train_end:val_end]

            train_ds = self._make_dataset(train_slice, train_labels, "train", symbol)
            val_ds = self._make_dataset(val_slice, val_labels, "val", symbol)
            folds.append((train_ds, val_ds))
            i += step

        return folds

    def build_walk_forward(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
    ) -> List[WalkForwardFold]:
        """Build walk-forward folds — expanding or rolling train window."""
        cfg = self._config
        feature_df, labels = self._prepare(df, cfg)
        folds: List[WalkForwardFold] = []
        n = len(feature_df)

        train_w = cfg.wf_train_window
        val_w = cfg.wf_val_window
        step = cfg.wf_step
        fold_id = 0
        start = 0

        while start + train_w + val_w <= n:
            train_sl = feature_df.iloc[start : start + train_w]
            train_lb = labels.iloc[start : start + train_w]
            val_sl = feature_df.iloc[start + train_w : start + train_w + val_w]
            val_lb = labels.iloc[start + train_w : start + train_w + val_w]

            train_ds = self._make_dataset(train_sl, train_lb, "train", symbol)
            val_ds = self._make_dataset(val_sl, val_lb, "val", symbol)
            folds.append(WalkForwardFold(fold_id=fold_id, train=train_ds, val=val_ds))
            fold_id += 1
            start += step

        return folds

    def build_time_series_cv(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        n_splits: int = 5,
    ) -> List[Tuple[Dataset, Dataset]]:
        """Sklearn-style TimeSeriesSplit without data leakage."""
        cfg = self._config
        feature_df, labels = self._prepare(df, cfg)
        n = len(feature_df)
        fold_size = n // (n_splits + 1)
        folds: List[Tuple[Dataset, Dataset]] = []

        for i in range(1, n_splits + 1):
            train_end = i * fold_size
            val_end = min(train_end + fold_size, n)
            train_sl = feature_df.iloc[:train_end]
            train_lb = labels.iloc[:train_end]
            val_sl = feature_df.iloc[train_end:val_end]
            val_lb = labels.iloc[train_end:val_end]
            train_ds = self._make_dataset(train_sl, train_lb, "train", symbol)
            val_ds = self._make_dataset(val_sl, val_lb, "val", symbol)
            folds.append((train_ds, val_ds))

        return folds

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _prepare(
        self, df: pd.DataFrame, cfg: DatasetConfig
    ) -> Tuple[pd.DataFrame, pd.Series]:
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        labels = generate_labels(df, cfg)
        feature_df = df.drop(columns=["open", "high", "low", "close", "volume"],
                              errors="ignore")

        if cfg.feature_cols:
            available = [c for c in cfg.feature_cols if c in feature_df.columns]
            feature_df = feature_df[available]

        combined = feature_df.copy()
        combined["__label__"] = labels

        if cfg.drop_na:
            combined = combined.dropna()

        feature_df = combined.drop(columns=["__label__"])
        labels = combined["__label__"]

        return feature_df, labels

    def _ratio_split(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cfg: DatasetConfig,
        symbol: str,
    ) -> Tuple[Dataset, Dataset, Dataset]:
        n = len(X)
        train_end = int(n * cfg.train_ratio)
        val_end = train_end + int(n * cfg.val_ratio)

        train_ds = self._make_dataset(X.iloc[:train_end], y.iloc[:train_end], "train", symbol)
        val_ds = self._make_dataset(X.iloc[train_end:val_end], y.iloc[train_end:val_end], "val", symbol)
        test_ds = self._make_dataset(X.iloc[val_end:], y.iloc[val_end:], "test", symbol)
        return train_ds, val_ds, test_ds

    def _date_split(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cfg: DatasetConfig,
        symbol: str,
        val_date: pd.Timestamp,
        test_date: pd.Timestamp,
    ) -> Tuple[Dataset, Dataset, Dataset]:
        train_ds = self._make_dataset(X.loc[:val_date], y.loc[:val_date], "train", symbol)
        val_ds = self._make_dataset(X.loc[val_date:test_date], y.loc[val_date:test_date], "val", symbol)
        test_ds = self._make_dataset(X.loc[test_date:], y.loc[test_date:], "test", symbol)
        return train_ds, val_ds, test_ds

    def _make_dataset(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        split: str,
        symbol: str,
    ) -> Dataset:
        cfg = self._config
        start = pd.Timestamp(X.index.min()) if len(X) > 0 else None
        end = pd.Timestamp(X.index.max()) if len(X) > 0 else None
        return Dataset(
            name=f"{symbol}_{split}",
            X=X,
            y=y,
            split=split,
            start_date=start,
            end_date=end,
            metadata={
                "label_type": cfg.label_type.value,
                "label_horizon": cfg.label_horizon,
                "symbol": symbol,
            },
        )
