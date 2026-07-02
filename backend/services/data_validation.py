"""M13 Phase 4 — Market data quality validation engine.

Validates OHLCV DataFrames and returns structured quality scores.
All operations are deterministic and work on pandas DataFrames only.
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
# Issue types
# ---------------------------------------------------------------------------

class IssueType(Enum):
    MISSING_BARS = "missing_bars"
    DUPLICATE_TIMESTAMPS = "duplicate_timestamps"
    NEGATIVE_PRICE = "negative_price"
    ZERO_PRICE = "zero_price"
    INVALID_VOLUME = "invalid_volume"
    OHLC_VIOLATION = "ohlc_violation"       # high < low, close outside range
    PRICE_SPIKE = "price_spike"             # extreme single-bar move
    SPLIT_INCONSISTENCY = "split_inconsistency"
    DIVIDEND_INCONSISTENCY = "dividend_inconsistency"
    TIMEZONE_ERROR = "timezone_error"
    STALE_DATA = "stale_data"
    WEEKEND_BAR = "weekend_bar"             # bar on non-trading day
    ZERO_VOLUME_CLOSE = "zero_volume_close" # zero volume on close day


class IssueSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    issue_type: IssueType
    severity: IssueSeverity
    description: str
    rows_affected: int = 0
    indices: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.issue_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "rows_affected": self.rows_affected,
            "sample_indices": [str(i) for i in self.indices[:5]],
        }


@dataclass
class ValidationResult:
    symbol: str
    row_count: int
    issues: List[ValidationIssue] = field(default_factory=list)
    quality_score: float = 1.0             # 0–1; 1.0 = perfect
    passed: bool = True

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity in (IssueSeverity.ERROR, IssueSeverity.CRITICAL))

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "row_count": self.row_count,
            "quality_score": round(self.quality_score, 4),
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
        }


# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------

def _check_duplicate_timestamps(df: pd.DataFrame) -> Optional[ValidationIssue]:
    dupes = df.index[df.index.duplicated()]
    if len(dupes):
        return ValidationIssue(
            IssueType.DUPLICATE_TIMESTAMPS,
            IssueSeverity.ERROR,
            f"Found {len(dupes)} duplicate timestamps",
            rows_affected=len(dupes),
            indices=list(dupes[:5]),
        )
    return None


def _check_negative_prices(df: pd.DataFrame) -> Optional[ValidationIssue]:
    price_cols = [c for c in ("open", "high", "low", "close") if c in df.columns]
    if not price_cols:
        return None
    mask = (df[price_cols] < 0).any(axis=1)
    if mask.any():
        return ValidationIssue(
            IssueType.NEGATIVE_PRICE,
            IssueSeverity.CRITICAL,
            f"Negative prices in {mask.sum()} rows",
            rows_affected=int(mask.sum()),
            indices=list(df.index[mask][:5]),
        )
    return None


def _check_zero_prices(df: pd.DataFrame) -> Optional[ValidationIssue]:
    if "close" not in df.columns:
        return None
    mask = df["close"] == 0
    if mask.any():
        return ValidationIssue(
            IssueType.ZERO_PRICE,
            IssueSeverity.ERROR,
            f"Zero close price in {mask.sum()} rows",
            rows_affected=int(mask.sum()),
            indices=list(df.index[mask][:5]),
        )
    return None


def _check_ohlc_violations(df: pd.DataFrame) -> Optional[ValidationIssue]:
    needed = {"open", "high", "low", "close"}
    if not needed.issubset(df.columns):
        return None
    hl_viol = df["high"] < df["low"]
    close_viol = (df["close"] > df["high"]) | (df["close"] < df["low"])
    open_viol = (df["open"] > df["high"]) | (df["open"] < df["low"])
    mask = hl_viol | close_viol | open_viol
    if mask.any():
        return ValidationIssue(
            IssueType.OHLC_VIOLATION,
            IssueSeverity.ERROR,
            f"OHLC constraint violations in {mask.sum()} rows",
            rows_affected=int(mask.sum()),
            indices=list(df.index[mask][:5]),
        )
    return None


def _check_invalid_volume(df: pd.DataFrame) -> Optional[ValidationIssue]:
    if "volume" not in df.columns:
        return None
    mask = df["volume"] < 0
    if mask.any():
        return ValidationIssue(
            IssueType.INVALID_VOLUME,
            IssueSeverity.ERROR,
            f"Negative volume in {mask.sum()} rows",
            rows_affected=int(mask.sum()),
            indices=list(df.index[mask][:5]),
        )
    return None


def _check_price_spikes(
    df: pd.DataFrame,
    threshold: float = 0.50,
) -> Optional[ValidationIssue]:
    if "close" not in df.columns or len(df) < 2:
        return None
    pct_change = df["close"].pct_change().abs()
    mask = pct_change > threshold
    if mask.any():
        return ValidationIssue(
            IssueType.PRICE_SPIKE,
            IssueSeverity.WARNING,
            f"Price spike >{threshold*100:.0f}% detected in {mask.sum()} rows",
            rows_affected=int(mask.sum()),
            indices=list(df.index[mask][:5]),
        )
    return None


def _check_missing_bars(
    df: pd.DataFrame,
    expected_freq: Optional[str] = None,
) -> Optional[ValidationIssue]:
    """Check for gaps using the inferred or supplied frequency."""
    if len(df) < 2:
        return None
    try:
        inferred = expected_freq or pd.infer_freq(df.index)
        if inferred is None:
            return None
        full_idx = pd.date_range(df.index.min(), df.index.max(), freq=inferred)
        # Exclude weekends for daily data
        if inferred in ("B", "D", "1D", "1d"):
            full_idx = full_idx[full_idx.dayofweek < 5]
        missing_count = len(full_idx.difference(df.index))
        if missing_count > 0:
            return ValidationIssue(
                IssueType.MISSING_BARS,
                IssueSeverity.WARNING,
                f"~{missing_count} bars missing from expected {inferred} sequence",
                rows_affected=missing_count,
            )
    except Exception as exc:
        logger.debug("Missing-bar check failed: %s", exc)
    return None


def _check_stale_data(
    df: pd.DataFrame,
    max_age_days: float = 5.0,
) -> Optional[ValidationIssue]:
    if not len(df):
        return None
    try:
        last_ts = pd.Timestamp(df.index.max())
        if last_ts.tzinfo is None:
            last_ts = last_ts.tz_localize("UTC")
        now = pd.Timestamp.now(tz="UTC")
        age_days = (now - last_ts).total_seconds() / 86400
        if age_days > max_age_days:
            return ValidationIssue(
                IssueType.STALE_DATA,
                IssueSeverity.WARNING,
                f"Last bar is {age_days:.1f} days old (threshold {max_age_days})",
                rows_affected=1,
            )
    except Exception as exc:
        logger.debug("Stale-data check failed: %s", exc)
    return None


def _check_timezone(df: pd.DataFrame) -> Optional[ValidationIssue]:
    if not isinstance(df.index, pd.DatetimeIndex):
        return ValidationIssue(
            IssueType.TIMEZONE_ERROR,
            IssueSeverity.INFO,
            "Index is not a DatetimeIndex",
        )
    if df.index.tz is None:
        return ValidationIssue(
            IssueType.TIMEZONE_ERROR,
            IssueSeverity.INFO,
            "Index has no timezone (naive). UTC recommended.",
        )
    return None


# ---------------------------------------------------------------------------
# Validator class
# ---------------------------------------------------------------------------

class DataValidator:
    """Validate OHLCV DataFrames and return quality-scored results."""

    # Penalty weights per issue (deducted from quality_score)
    _PENALTIES: Dict[str, float] = {
        IssueSeverity.CRITICAL.value: 0.40,
        IssueSeverity.ERROR.value: 0.20,
        IssueSeverity.WARNING.value: 0.05,
        IssueSeverity.INFO.value: 0.01,
    }

    def __init__(
        self,
        spike_threshold: float = 0.50,
        stale_days: float = 5.0,
        expected_freq: Optional[str] = None,
    ) -> None:
        self._spike_threshold = spike_threshold
        self._stale_days = stale_days
        self._expected_freq = expected_freq

    def validate(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> ValidationResult:
        """Run all validation rules and return a ValidationResult."""
        issues: List[ValidationIssue] = []

        for check_fn in [
            lambda d: _check_duplicate_timestamps(d),
            lambda d: _check_negative_prices(d),
            lambda d: _check_zero_prices(d),
            lambda d: _check_ohlc_violations(d),
            lambda d: _check_invalid_volume(d),
            lambda d: _check_price_spikes(d, self._spike_threshold),
            lambda d: _check_missing_bars(d, self._expected_freq),
            lambda d: _check_stale_data(d, self._stale_days),
            lambda d: _check_timezone(d),
        ]:
            try:
                issue = check_fn(df)
                if issue:
                    issues.append(issue)
            except Exception as exc:
                logger.debug("Validation check failed: %s", exc)

        quality_score = 1.0
        for issue in issues:
            penalty = self._PENALTIES.get(issue.severity.value, 0.0)
            if issue.rows_affected and len(df) > 0:
                row_fraction = min(1.0, issue.rows_affected / len(df))
                penalty *= (0.2 + 0.8 * row_fraction)
            quality_score -= penalty

        quality_score = max(0.0, min(1.0, quality_score))
        has_critical_or_error = any(
            i.severity in (IssueSeverity.CRITICAL, IssueSeverity.ERROR) for i in issues
        )

        return ValidationResult(
            symbol=symbol,
            row_count=len(df),
            issues=issues,
            quality_score=quality_score,
            passed=not has_critical_or_error,
        )

    def validate_many(
        self,
        data: Dict[str, pd.DataFrame],
    ) -> Dict[str, ValidationResult]:
        return {sym: self.validate(df, sym) for sym, df in data.items()}

    def summary_report(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results.values() if r.passed)
        avg_score = np.mean([r.quality_score for r in results.values()]) if results else 0.0
        return {
            "total_symbols": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total if total > 0 else 0.0, 4),
            "avg_quality_score": round(float(avg_score), 4),
            "symbols_with_errors": [s for s, r in results.items() if not r.passed],
        }
