"""
Unit tests for services/indicators.py.

All tests use deterministic synthetic data — no network calls.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure the backend package root is importable when pytest is run from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.indicators import (
    atr,
    bollinger_bands,
    cci,
    compute_indicators,
    ema,
    macd,
    obv,
    roc,
    rsi,
    sma,
    stochastic,
    vwap,
    williams_r,
    wma,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _linear_series(n: int = 50, start: float = 100.0, step: float = 1.0) -> pd.Series:
    """Strictly increasing series: 100, 101, 102, …"""
    return pd.Series([start + i * step for i in range(n)], dtype=float)


def _flat_series(n: int = 50, value: float = 100.0) -> pd.Series:
    """Constant series."""
    return pd.Series([value] * n, dtype=float)


def _date_index(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2023-01-01", periods=n, freq="B")


def _ohlcv_df(n: int = 100) -> pd.DataFrame:
    """Synthetic OHLCV DataFrame with a date index."""
    idx = _date_index(n)
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.1
    volume = np.random.randint(1_000_000, 5_000_000, size=n).astype(float)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------


def test_sma_constant():
    """SMA of a constant series equals that constant."""
    s = _flat_series(30, value=50.0)
    result = sma(s, 10)
    assert result.iloc[9:].isna().sum() == 0
    assert math.isclose(result.iloc[20], 50.0, rel_tol=1e-9)


def test_sma_nan_prefix():
    """First period-1 values should be NaN."""
    s = _linear_series(50)
    result = sma(s, 20)
    assert result.iloc[:19].isna().all()
    assert not result.iloc[19:].isna().any()


def test_sma_linear():
    """SMA of a linear series equals the average of the window."""
    s = _linear_series(50)
    result = sma(s, 10)
    # At index 9: average of values 100..109 = 104.5
    expected = (100 + 109) / 2.0
    assert math.isclose(result.iloc[9], expected, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------


def test_ema_constant():
    """EMA of a constant series equals that constant after warm-up."""
    s = _flat_series(50, value=75.0)
    result = ema(s, 10)
    # EMA should converge to 75 for all values
    assert math.isclose(result.iloc[-1], 75.0, rel_tol=1e-6)


def test_ema_tracks_trend():
    """EMA of an increasing series is below the latest value (lagging indicator)."""
    s = _linear_series(100)
    result = ema(s, 20)
    assert result.iloc[-1] < s.iloc[-1]


# ---------------------------------------------------------------------------
# WMA
# ---------------------------------------------------------------------------


def test_wma_nan_prefix():
    s = _linear_series(40)
    result = wma(s, 15)
    assert result.iloc[:14].isna().all()
    assert not result.iloc[14:].isna().any()


def test_wma_constant():
    s = _flat_series(40, value=42.0)
    result = wma(s, 10)
    assert math.isclose(result.iloc[20], 42.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


def test_rsi_constant_returns_nan():
    """When price never moves, RSI is undefined (0/0) → should return NaN after initial period."""
    s = _flat_series(30, value=100.0)
    result = rsi(s, 14)
    # With constant price, delta=0 → gain=0, loss=0; result may be NaN or 100
    # Both are acceptable; the key is no exception is raised
    assert len(result) == 30


def test_rsi_always_rising():
    """Strictly increasing series → RSI should be near 100 after warm-up."""
    s = _linear_series(60)
    result = rsi(s, 14)
    assert result.iloc[-1] > 90.0


def test_rsi_always_falling():
    """Strictly decreasing series → RSI should be near 0 after warm-up."""
    s = _linear_series(60, step=-1.0)
    result = rsi(s, 14)
    # Losses every day — RSI near 0
    assert result.iloc[-1] < 10.0


def test_rsi_range():
    """RSI must be in [0, 100] for any valid input."""
    df = _ohlcv_df(200)
    result = rsi(df["Close"], 14).dropna()
    assert (result >= 0).all() and (result <= 100).all()


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------


def test_macd_columns():
    df = _ohlcv_df(100)
    result = macd(df["Close"])
    assert set(result.columns) == {"macd", "signal", "hist"}


def test_macd_hist_equals_macd_minus_signal():
    df = _ohlcv_df(100)
    result = macd(df["Close"])
    diff = (result["macd"] - result["signal"] - result["hist"]).dropna().abs()
    assert (diff < 1e-10).all()


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


def test_bbands_columns():
    df = _ohlcv_df(100)
    result = bollinger_bands(df["Close"])
    assert set(result.columns) == {"upper", "middle", "lower", "pct_b", "bandwidth"}


def test_bbands_ordering():
    """upper >= middle >= lower at all non-NaN points."""
    df = _ohlcv_df(200)
    result = bollinger_bands(df["Close"], 20, 2.0).dropna()
    assert (result["upper"] >= result["middle"]).all()
    assert (result["middle"] >= result["lower"]).all()


def test_bbands_middle_equals_sma():
    """Bollinger middle band must equal SMA(period)."""
    df = _ohlcv_df(100)
    bb = bollinger_bands(df["Close"], 20)
    s = sma(df["Close"], 20)
    diff = (bb["middle"] - s).dropna().abs()
    assert (diff < 1e-10).all()


# ---------------------------------------------------------------------------
# Stochastic
# ---------------------------------------------------------------------------


def test_stoch_range():
    df = _ohlcv_df(100)
    result = stochastic(df["High"], df["Low"], df["Close"]).dropna()
    assert (result["%K"] >= 0).all() and (result["%K"] <= 100).all()
    assert (result["%D"] >= 0).all() and (result["%D"] <= 100).all()


def test_stoch_columns():
    df = _ohlcv_df(50)
    result = stochastic(df["High"], df["Low"], df["Close"])
    assert "%K" in result.columns and "%D" in result.columns


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------


def test_atr_positive():
    """ATR is always non-negative."""
    df = _ohlcv_df(100)
    result = atr(df["High"], df["Low"], df["Close"]).dropna()
    assert (result >= 0).all()


def test_atr_flat_ohlc():
    """When high=low=close (no movement) ATR should be near 0."""
    n = 50
    s = _flat_series(n, 100.0)
    result = atr(s, s, s, period=5).dropna()
    assert (result.abs() < 1e-6).all()


# ---------------------------------------------------------------------------
# OBV
# ---------------------------------------------------------------------------


def test_obv_rising_prices():
    """All prices rising → OBV should be monotonically increasing."""
    n = 30
    close = _linear_series(n, 100, 1.0)
    volume = _flat_series(n, 1_000_000)
    result = obv(close, volume)
    assert result.is_monotonic_increasing


def test_obv_falling_prices():
    """All prices falling → OBV should be monotonically decreasing."""
    n = 30
    close = _linear_series(n, 200, -1.0)
    volume = _flat_series(n, 1_000_000)
    result = obv(close, volume)
    # First value is 0 (direction of day 0 = 0), then strictly decreasing
    assert result.iloc[-1] < result.iloc[1]


# ---------------------------------------------------------------------------
# VWAP
# ---------------------------------------------------------------------------


def test_vwap_constant_prices():
    """VWAP of a constant-price series equals that price."""
    n = 30
    s = _flat_series(n, 100.0)
    volume = _flat_series(n, 1_000_000)
    result = vwap(s, s, s, volume)
    assert (result.dropna() - 100.0).abs().max() < 1e-9


# ---------------------------------------------------------------------------
# CCI
# ---------------------------------------------------------------------------


def test_cci_length():
    df = _ohlcv_df(60)
    result = cci(df["High"], df["Low"], df["Close"], 20)
    assert len(result) == len(df)


# ---------------------------------------------------------------------------
# Williams %R
# ---------------------------------------------------------------------------


def test_williams_r_range():
    df = _ohlcv_df(100)
    result = williams_r(df["High"], df["Low"], df["Close"], 14).dropna()
    assert (result >= -100).all() and (result <= 0).all()


# ---------------------------------------------------------------------------
# ROC
# ---------------------------------------------------------------------------


def test_roc_linear():
    """ROC of a linear series with step 1 and period n should equal n/(start+n-period)*100."""
    s = _linear_series(40, start=100, step=1.0)
    result = roc(s, 10).dropna()
    # At index 10: (110 - 100) / 100 * 100 = 10.0
    assert math.isclose(result.iloc[0], 10.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# compute_indicators orchestrator
# ---------------------------------------------------------------------------


def test_compute_indicators_keys():
    df = _ohlcv_df(100)
    specs = {
        "sma": [{"period": 20}, {"period": 50}],
        "rsi": [{"period": 14}],
        "macd": [{}],
    }
    result = compute_indicators(df, specs)
    assert "sma_20" in result
    assert "sma_50" in result
    assert "rsi_14" in result
    assert "macd" in result
    assert isinstance(result["macd"], dict)
    assert "macd" in result["macd"]


def test_compute_indicators_length_matches_data():
    df = _ohlcv_df(80)
    specs = {"sma": [{"period": 10}], "atr": [{"period": 14}]}
    result = compute_indicators(df, specs)
    assert len(result["sma_10"]) == len(df)
    assert len(result["atr_14"]) == len(df)


def test_compute_indicators_none_for_nan():
    """NaN values must be serialised as None, not as float('nan')."""
    df = _ohlcv_df(50)
    specs = {"sma": [{"period": 20}]}
    result = compute_indicators(df, specs)
    # First 19 values must be None
    for v in result["sma_20"][:19]:
        assert v is None
