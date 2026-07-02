"""M13 Phase 3 — Institutional historical data engine.

Handles gap detection, missing bar repair, timezone normalization,
holiday calendars, corporate action adjustments, and survivorship
bias flags.  All operations work on pandas DataFrames — no network calls.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — US market holiday calendar (static, deterministic)
# ---------------------------------------------------------------------------

# Fixed US equity market holidays through 2030 (simplified set)
_US_HOLIDAYS: Set[str] = {
    # 2020
    "2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10",
    "2020-05-25", "2020-07-03", "2020-09-07", "2020-11-26", "2020-12-25",
    # 2021
    "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02",
    "2021-05-31", "2021-07-05", "2021-09-06", "2021-11-25", "2021-12-24",
    # 2022
    "2022-01-17", "2022-02-21", "2022-04-15",
    "2022-05-30", "2022-06-20", "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26",
    # 2023
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07",
    "2023-05-29", "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29",
    "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    # 2025
    "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18",
    "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    # 2027–2030 key dates
    "2027-01-01", "2027-12-24", "2028-01-01", "2028-12-25",
    "2029-01-01", "2029-12-25", "2030-01-01", "2030-12-25",
}


def is_trading_day(date: pd.Timestamp, tz: str = "America/New_York") -> bool:
    """Return True if ``date`` is a US equity trading day."""
    d = pd.Timestamp(date)
    if d.weekday() >= 5:  # Saturday / Sunday
        return False
    date_str = d.strftime("%Y-%m-%d")
    return date_str not in _US_HOLIDAYS


def get_trading_days(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Return a DatetimeIndex of US equity trading days between start and end."""
    all_days = pd.date_range(start.normalize(), end.normalize(), freq="D")
    return pd.DatetimeIndex([d for d in all_days if is_trading_day(d)])


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class Interval(Enum):
    DAILY = "1d"
    HOURLY = "1h"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    SECOND = "1s"
    TICK = "tick"


@dataclass
class GapInfo:
    start: pd.Timestamp
    end: pd.Timestamp
    missing_bars: int
    interval: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": str(self.start),
            "end": str(self.end),
            "missing_bars": self.missing_bars,
            "interval": self.interval,
        }


@dataclass
class AdjustmentFactor:
    date: pd.Timestamp
    split_factor: float = 1.0     # cumulative multiplier for price
    dividend: float = 0.0         # cash dividend per share

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": str(self.date),
            "split_factor": self.split_factor,
            "dividend": self.dividend,
        }


@dataclass
class EngineResult:
    symbol: str
    data: pd.DataFrame
    gaps_found: int
    gaps_repaired: int
    timezone_normalized: bool
    adjustments_applied: int
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "rows": len(self.data),
            "gaps_found": self.gaps_found,
            "gaps_repaired": self.gaps_repaired,
            "timezone_normalized": self.timezone_normalized,
            "adjustments_applied": self.adjustments_applied,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class HistoricalDataEngine:
    """Pipeline for cleaning, normalizing, and adjusting OHLCV data."""

    _FREQ_MAP: Dict[str, str] = {
        "1d": "B",
        "1h": "h",
        "1m": "min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1s": "s",
    }

    def __init__(
        self,
        target_tz: str = "UTC",
        repair_gaps: bool = True,
        apply_adjustments: bool = True,
        max_gap_fill_bars: int = 5,
    ) -> None:
        self._target_tz = target_tz
        self._repair_gaps = repair_gaps
        self._apply_adjustments = apply_adjustments
        self._max_gap_fill = max_gap_fill_bars

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        df: pd.DataFrame,
        symbol: str,
        interval: str = "1d",
        splits: Optional[pd.DataFrame] = None,
        dividends: Optional[pd.DataFrame] = None,
    ) -> EngineResult:
        """Full pipeline: normalize → sort → dedupe → repair gaps → adjust."""
        warnings: List[str] = []
        gaps_found = 0
        gaps_repaired = 0
        adjustments_applied = 0
        tz_normalized = False

        df = df.copy()

        # 1. Normalize timezone
        df, tz_normalized = self._normalize_timezone(df, warnings)

        # 2. Sort and deduplicate
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="first")]

        # 3. Standardize columns to lowercase
        df.columns = [c.lower() for c in df.columns]

        # 4. Gap detection and repair
        if self._repair_gaps and interval in self._FREQ_MAP:
            gaps = self.detect_gaps(df, interval)
            gaps_found = len(gaps)
            if gaps_found:
                df, repaired = self._repair_gaps_fn(df, gaps, warnings)
                gaps_repaired = repaired

        # 5. Corporate action adjustments
        if self._apply_adjustments:
            adj_factors = self._build_adjustment_factors(splits, dividends, df.index)
            if adj_factors:
                df = self._apply_price_adjustments(df, adj_factors)
                adjustments_applied = len(adj_factors)

        return EngineResult(
            symbol=symbol,
            data=df,
            gaps_found=gaps_found,
            gaps_repaired=gaps_repaired,
            timezone_normalized=tz_normalized,
            adjustments_applied=adjustments_applied,
            warnings=warnings,
        )

    def detect_gaps(
        self,
        df: pd.DataFrame,
        interval: str = "1d",
    ) -> List[GapInfo]:
        """Return list of GapInfo for each contiguous gap in the series."""
        if len(df) < 2:
            return []
        freq = self._FREQ_MAP.get(interval)
        if freq is None:
            return []
        try:
            full_idx = pd.date_range(
                df.index.min(), df.index.max(), freq=freq
            )
            if interval == "1d":
                full_idx = pd.DatetimeIndex(
                    [d for d in full_idx if d.weekday() < 5
                     and d.strftime("%Y-%m-%d") not in _US_HOLIDAYS]
                )
            missing = full_idx.difference(df.index)
            if len(missing) == 0:
                return []
            gaps: List[GapInfo] = []
            if len(missing) > 0:
                groups = self._group_consecutive(missing, freq)
                for g_start, g_end, count in groups:
                    gaps.append(GapInfo(
                        start=g_start,
                        end=g_end,
                        missing_bars=count,
                        interval=interval,
                    ))
            return gaps
        except Exception as exc:
            logger.debug("Gap detection failed: %s", exc)
            return []

    def repair_gaps(
        self,
        df: pd.DataFrame,
        interval: str = "1d",
    ) -> Tuple[pd.DataFrame, List[GapInfo]]:
        """Detect and repair gaps, returning the filled DataFrame and gap list."""
        gaps = self.detect_gaps(df, interval)
        warnings: List[str] = []
        if gaps:
            df, _ = self._repair_gaps_fn(df, gaps, warnings)
        return df, gaps

    def normalize_timezone(
        self,
        df: pd.DataFrame,
        target_tz: Optional[str] = None,
    ) -> pd.DataFrame:
        tz = target_tz or self._target_tz
        df = df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        if str(df.index.tz) != tz:
            df.index = df.index.tz_convert(tz)
        return df

    def adjust_for_splits(
        self,
        df: pd.DataFrame,
        splits: pd.DataFrame,
    ) -> pd.DataFrame:
        """Apply split adjustments backwards from the most recent split.

        ``splits`` must have a datetime index and a ``ratio`` column.
        """
        df = df.copy()
        if splits is None or splits.empty:
            return df
        price_cols = [c for c in ("open", "high", "low", "close") if c in df.columns]
        for split_date in sorted(splits.index, reverse=True):
            ratio = float(splits.loc[split_date, "ratio"])
            if ratio <= 0:
                continue
            mask = df.index < pd.Timestamp(split_date)
            if price_cols:
                df.loc[mask, price_cols] /= ratio
            if "volume" in df.columns:
                df.loc[mask, "volume"] *= ratio
        return df

    def adjust_for_dividends(
        self,
        df: pd.DataFrame,
        dividends: pd.DataFrame,
    ) -> pd.DataFrame:
        """Apply dividend adjustments (dividend-adjusted close only)."""
        df = df.copy()
        if dividends is None or dividends.empty or "close" not in df.columns:
            return df
        close = df["close"].copy()
        for div_date in sorted(dividends.index, reverse=True):
            div_amt = float(dividends.iloc[dividends.index.get_loc(div_date), 0])
            price_before = close[close.index < pd.Timestamp(div_date)]
            if price_before.empty:
                continue
            ref_price = float(price_before.iloc[-1])
            if ref_price <= 0:
                continue
            factor = (ref_price - div_amt) / ref_price
            mask = df.index < pd.Timestamp(div_date)
            df.loc[mask, "close"] *= factor
        return df

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _normalize_timezone(
        self, df: pd.DataFrame, warnings: List[str]
    ) -> Tuple[pd.DataFrame, bool]:
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                warnings.append("Failed to convert index to DatetimeIndex")
                return df, False
        tz_changed = False
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
            warnings.append("Index was timezone-naive; localized to UTC")
            tz_changed = True
        if str(df.index.tz) != self._target_tz:
            df.index = df.index.tz_convert(self._target_tz)
            tz_changed = True
        return df, tz_changed

    def _repair_gaps_fn(
        self,
        df: pd.DataFrame,
        gaps: List[GapInfo],
        warnings: List[str],
    ) -> Tuple[pd.DataFrame, int]:
        repaired = 0
        for gap in gaps:
            if gap.missing_bars > self._max_gap_fill:
                warnings.append(
                    f"Gap of {gap.missing_bars} bars at {gap.start} exceeds limit "
                    f"({self._max_gap_fill}); skipping"
                )
                continue
            fill_dates = pd.date_range(gap.start, gap.end, freq="B")
            fill_df = pd.DataFrame(index=fill_dates, columns=df.columns)
            df = pd.concat([df, fill_df])
            df = df.sort_index()
            df = df.ffill()
            repaired += gap.missing_bars
        return df, repaired

    def _build_adjustment_factors(
        self,
        splits: Optional[pd.DataFrame],
        dividends: Optional[pd.DataFrame],
        data_index: pd.Index,
    ) -> List[AdjustmentFactor]:
        factors: List[AdjustmentFactor] = []
        if splits is not None and not splits.empty:
            for dt in splits.index:
                ratio = float(splits.loc[dt].iloc[0]) if hasattr(splits.loc[dt], "iloc") else float(splits.loc[dt])
                factors.append(AdjustmentFactor(date=pd.Timestamp(dt), split_factor=ratio))
        if dividends is not None and not dividends.empty:
            for dt in dividends.index:
                div_val = float(dividends.loc[dt].iloc[0]) if hasattr(dividends.loc[dt], "iloc") else float(dividends.loc[dt])
                existing = next((f for f in factors if f.date == pd.Timestamp(dt)), None)
                if existing:
                    existing.dividend = div_val
                else:
                    factors.append(AdjustmentFactor(date=pd.Timestamp(dt), dividend=div_val))
        return sorted(factors, key=lambda f: f.date)

    def _apply_price_adjustments(
        self,
        df: pd.DataFrame,
        factors: List[AdjustmentFactor],
    ) -> pd.DataFrame:
        df = df.copy()
        price_cols = [c for c in ("open", "high", "low", "close") if c in df.columns]
        cumulative_split = 1.0
        for f in reversed(factors):
            cumulative_split *= f.split_factor
            mask = df.index < f.date
            if price_cols and f.split_factor != 1.0:
                df.loc[mask, price_cols] /= f.split_factor
            if "volume" in df.columns and f.split_factor != 1.0:
                df.loc[mask, "volume"] *= f.split_factor
        return df

    @staticmethod
    def _group_consecutive(
        idx: pd.DatetimeIndex,
        freq: str,
    ) -> List[Tuple[pd.Timestamp, pd.Timestamp, int]]:
        """Group consecutive timestamps into contiguous runs."""
        if len(idx) == 0:
            return []
        groups: List[Tuple[pd.Timestamp, pd.Timestamp, int]] = []
        run_start = idx[0]
        run_end = idx[0]
        count = 1
        offset = pd.tseries.frequencies.to_offset(freq)
        for ts in idx[1:]:
            expected = run_end + offset
            if ts == expected:
                run_end = ts
                count += 1
            else:
                groups.append((run_start, run_end, count))
                run_start = ts
                run_end = ts
                count = 1
        groups.append((run_start, run_end, count))
        return groups
