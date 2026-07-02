"""
Vectorized technical indicator library — pure pandas / numpy, no ta-lib dependency.

All functions accept pandas Series/DataFrame inputs indexed by date and return
Series or DataFrames with the same index. NaN padding is used where insufficient
history exists (standard convention for rolling-window indicators).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Trend indicators
# ---------------------------------------------------------------------------


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average (span-based — equivalent to 2/(period+1) decay)."""
    return series.ewm(span=period, adjust=False).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average — linearly decreasing weights, newest gets highest weight."""
    weights = np.arange(1, period + 1, dtype=float)
    total = weights.sum()

    def _wma(x: np.ndarray) -> float:
        return float((x * weights).sum() / total)

    return series.rolling(period).apply(_wma, raw=True)


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """
    MACD — Moving Average Convergence/Divergence.

    Returns a DataFrame with columns: macd, signal, hist.
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": histogram},
        index=series.index,
    )


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.DataFrame:
    """
    Bollinger Bands.

    Returns a DataFrame with columns: upper, middle, lower, pct_b, bandwidth.
    pct_b = (price - lower) / (upper - lower)  — position within the bands (0-1 typically).
    bandwidth = (upper - lower) / middle * 100  — as a percentage of the middle band.
    """
    middle = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)  # population std, consistent with most platforms
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    band_width = upper - lower
    pct_b = (series - lower) / band_width.replace(0, np.nan)
    bandwidth = band_width / middle.replace(0, np.nan) * 100
    return pd.DataFrame(
        {"upper": upper, "middle": middle, "lower": lower, "pct_b": pct_b, "bandwidth": bandwidth},
        index=series.index,
    )


# ---------------------------------------------------------------------------
# Momentum indicators
# ---------------------------------------------------------------------------


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index using Wilder's smoothing (EMA with alpha=1/period).

    Industry-standard: RSI < 30 = oversold, RSI > 70 = overbought.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    result = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 (no down days) RSI is 100; NaN stays NaN (flat series)
    result = result.where(avg_loss != 0.0, other=100.0)
    return result


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    """
    Stochastic Oscillator.

    Returns DataFrame with columns: %K, %D.
    %K = fast stochastic (raw value).
    %D = SMA of %K (signal line).
    """
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    denom = (highest_high - lowest_low).replace(0.0, np.nan)
    k = 100.0 * (close - lowest_low) / denom
    d = k.rolling(d_period).mean()
    return pd.DataFrame({"%K": k, "%D": d}, index=close.index)


def cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20,
) -> pd.Series:
    """
    Commodity Channel Index.

    CCI = (Typical Price - SMA(TP, n)) / (0.015 * Mean Absolute Deviation).
    Overbought > +100, oversold < -100.
    """
    typical = (high + low + close) / 3.0
    ma = typical.rolling(period).mean()
    mad = typical.rolling(period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    return (typical - ma) / (0.015 * mad.replace(0.0, np.nan))


def williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Williams %R.

    Range: -100 to 0. Overbought near 0, oversold near -100.
    """
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    denom = (highest_high - lowest_low).replace(0.0, np.nan)
    return -100.0 * (highest_high - close) / denom


def roc(series: pd.Series, period: int = 12) -> pd.Series:
    """
    Rate of Change — percentage change over n periods.

    ROC = (close - close[n]) / close[n] * 100
    """
    return (series - series.shift(period)) / series.shift(period).replace(0.0, np.nan) * 100.0


# ---------------------------------------------------------------------------
# Volatility indicators
# ---------------------------------------------------------------------------


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Average True Range (Wilder's smoothing).

    True Range = max(high-low, |high-prev_close|, |low-prev_close|).
    ATR = Wilder's EMA of TR.
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


# ---------------------------------------------------------------------------
# Volume indicators
# ---------------------------------------------------------------------------


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On-Balance Volume — cumulative signed volume.

    OBV rises when volume is positive (close > prev close) and falls otherwise.
    """
    direction = np.sign(close.diff())
    direction.iloc[0] = 0.0
    return (direction * volume).cumsum()


def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """
    Volume-Weighted Average Price.

    Note: classic intraday VWAP resets each session. This implementation is
    cumulative over the supplied date range (appropriate for daily data).
    """
    typical_price = (high + low + close) / 3.0
    cum_tpv = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum().replace(0.0, np.nan)
    return cum_tpv / cum_vol


# ---------------------------------------------------------------------------
# High-level orchestration — compute all requested indicators in one call
# ---------------------------------------------------------------------------


def _safe_list(series: pd.Series) -> list:
    """Convert a Series to a JSON-safe list, replacing NaN with None."""
    return [None if (isinstance(v, float) and np.isnan(v)) else round(float(v), 6) for v in series]


def _safe_dict_of_lists(df: pd.DataFrame) -> dict:
    return {col: _safe_list(df[col]) for col in df.columns}


def compute_indicators(
    data: pd.DataFrame,
    indicator_specs: dict,
) -> dict:
    """
    Compute all requested indicators from a single OHLCV DataFrame.

    indicator_specs format (mirrors IndicatorRequest.indicators):
        {
            "sma": [{"period": 20}, {"period": 50}],
            "rsi": [{"period": 14}],
            "macd": [{}],
            "bbands": [{"period": 20, "std_dev": 2.0}],
            ...
        }

    Returns a flat dict of indicator_key → list | dict:
        {
            "sma_20": [...],
            "sma_50": [...],
            "rsi_14": [...],
            "macd": {"macd": [...], "signal": [...], "hist": [...]},
            "bbands_20": {"upper": [...], "middle": [...], ...},
            ...
        }
    """
    result: dict = {}

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    volume = data.get("Volume", pd.Series(np.zeros(len(data)), index=data.index))

    for ind_type, specs in indicator_specs.items():
        for spec in specs:
            p = spec.get("period") if isinstance(spec, dict) else getattr(spec, "period", None)

            if ind_type == "sma":
                period = int(p or 20)
                result[f"sma_{period}"] = _safe_list(sma(close, period))

            elif ind_type == "ema":
                period = int(p or 20)
                result[f"ema_{period}"] = _safe_list(ema(close, period))

            elif ind_type == "wma":
                period = int(p or 20)
                result[f"wma_{period}"] = _safe_list(wma(close, period))

            elif ind_type == "rsi":
                period = int(p or 14)
                result[f"rsi_{period}"] = _safe_list(rsi(close, period))

            elif ind_type == "macd":
                fast = int(spec.get("fast", 12) if isinstance(spec, dict) else getattr(spec, "fast", None) or 12)
                slow = int(spec.get("slow", 26) if isinstance(spec, dict) else getattr(spec, "slow", None) or 26)
                sig = int(spec.get("signal", 9) if isinstance(spec, dict) else getattr(spec, "signal", None) or 9)
                key = f"macd_{fast}_{slow}_{sig}" if (fast, slow, sig) != (12, 26, 9) else "macd"
                result[key] = _safe_dict_of_lists(macd(close, fast, slow, sig))

            elif ind_type == "bbands":
                period = int(p or 20)
                std = float(spec.get("std_dev", 2.0) if isinstance(spec, dict) else getattr(spec, "std_dev", None) or 2.0)
                key = f"bbands_{period}"
                result[key] = _safe_dict_of_lists(bollinger_bands(close, period, std))

            elif ind_type == "stoch":
                kp = int(spec.get("k_period", 14) if isinstance(spec, dict) else getattr(spec, "k_period", None) or 14)
                dp = int(spec.get("d_period", 3) if isinstance(spec, dict) else getattr(spec, "d_period", None) or 3)
                result[f"stoch_{kp}_{dp}"] = _safe_dict_of_lists(stochastic(high, low, close, kp, dp))

            elif ind_type == "cci":
                period = int(p or 20)
                result[f"cci_{period}"] = _safe_list(cci(high, low, close, period))

            elif ind_type == "williams_r":
                period = int(p or 14)
                result[f"williams_r_{period}"] = _safe_list(williams_r(high, low, close, period))

            elif ind_type == "roc":
                period = int(p or 12)
                result[f"roc_{period}"] = _safe_list(roc(close, period))

            elif ind_type == "atr":
                period = int(p or 14)
                result[f"atr_{period}"] = _safe_list(atr(high, low, close, period))

            elif ind_type == "obv":
                result["obv"] = _safe_list(obv(close, volume))

            elif ind_type == "vwap":
                result["vwap"] = _safe_list(vwap(high, low, close, volume))

    return result
