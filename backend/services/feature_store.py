"""M13 Phase 5 — Institutional feature store.

Computes and caches technical, statistical, and alpha features from
OHLCV DataFrames.  All computations are deterministic numpy/pandas.

Features produced
-----------------
  Returns family   : returns, log_returns, rolling_returns_{n}
  Volatility       : rolling_vol_{n}, atr_{n}
  Momentum         : momentum_{n}, rsi_{n}
  Mean reversion   : z_score_{n}, bb_upper/lower/pct_b_{n}
  Volume           : vwap, volume_ma_{n}, volume_ratio
  Trend            : macd, macd_signal, macd_hist, ema_{n}
  Risk             : rolling_sharpe_{n}, rolling_sortino_{n}
  Statistical      : rolling_skew_{n}, rolling_kurt_{n},
                     rolling_corr_{other}_{n}
  Regime           : market_regime, trend_strength
"""
from __future__ import annotations

import hashlib
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_ANN = 252.0


# ---------------------------------------------------------------------------
# Feature metadata
# ---------------------------------------------------------------------------

@dataclass
class FeatureDefinition:
    name: str
    group: str
    description: str
    depends_on: List[str]      # required OHLCV columns
    lookback: int              # minimum rows needed


FEATURE_CATALOG: List[FeatureDefinition] = [
    FeatureDefinition("returns", "returns", "Simple daily returns", ["close"], 2),
    FeatureDefinition("log_returns", "returns", "Log daily returns", ["close"], 2),
    FeatureDefinition("rolling_vol_21", "volatility", "21-day rolling volatility (ann)", ["close"], 22),
    FeatureDefinition("rolling_vol_63", "volatility", "63-day rolling volatility (ann)", ["close"], 64),
    FeatureDefinition("atr_14", "volatility", "Average True Range 14", ["high", "low", "close"], 15),
    FeatureDefinition("rsi_14", "momentum", "RSI 14-period", ["close"], 15),
    FeatureDefinition("macd", "momentum", "MACD line (12-26)", ["close"], 27),
    FeatureDefinition("macd_signal", "momentum", "MACD signal (9)", ["close"], 36),
    FeatureDefinition("macd_hist", "momentum", "MACD histogram", ["close"], 36),
    FeatureDefinition("momentum_21", "momentum", "21-day price momentum", ["close"], 22),
    FeatureDefinition("momentum_63", "momentum", "63-day price momentum", ["close"], 64),
    FeatureDefinition("z_score_21", "mean_reversion", "21-day z-score", ["close"], 22),
    FeatureDefinition("z_score_63", "mean_reversion", "63-day z-score", ["close"], 64),
    FeatureDefinition("bb_upper_20", "mean_reversion", "Bollinger upper band 20", ["close"], 21),
    FeatureDefinition("bb_lower_20", "mean_reversion", "Bollinger lower band 20", ["close"], 21),
    FeatureDefinition("bb_pct_b_20", "mean_reversion", "%B indicator 20", ["close"], 21),
    FeatureDefinition("vwap", "volume", "VWAP (single-day cumulative)", ["high", "low", "close", "volume"], 1),
    FeatureDefinition("volume_ma_20", "volume", "20-day volume moving average", ["volume"], 21),
    FeatureDefinition("volume_ratio", "volume", "Volume / 20d MA ratio", ["volume"], 21),
    FeatureDefinition("ema_12", "trend", "12-day EMA", ["close"], 12),
    FeatureDefinition("ema_26", "trend", "26-day EMA", ["close"], 26),
    FeatureDefinition("ema_50", "trend", "50-day EMA", ["close"], 50),
    FeatureDefinition("rolling_sharpe_63", "risk", "63-day rolling Sharpe (ann)", ["close"], 64),
    FeatureDefinition("rolling_sortino_63", "risk", "63-day rolling Sortino (ann)", ["close"], 64),
    FeatureDefinition("rolling_skew_63", "statistics", "63-day rolling skewness", ["close"], 64),
    FeatureDefinition("rolling_kurt_63", "statistics", "63-day rolling kurtosis", ["close"], 64),
    FeatureDefinition("market_regime", "regime", "Market regime: 1=bull, -1=bear, 0=neutral", ["close"], 51),
    FeatureDefinition("trend_strength", "regime", "ADX-like trend strength 0–1", ["high", "low", "close"], 15),
]

FEATURE_NAMES: List[str] = [f.name for f in FEATURE_CATALOG]


# ---------------------------------------------------------------------------
# Feature computation helpers
# ---------------------------------------------------------------------------

def _returns(close: pd.Series) -> pd.Series:
    return close.pct_change()


def _log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(1))


def _rolling_vol(returns: pd.Series, window: int) -> pd.Series:
    return returns.rolling(window).std() * np.sqrt(_ANN)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def _macd(close: pd.Series) -> tuple:
    fast = _ema(close, 12)
    slow = _ema(close, 26)
    macd_line = fast - slow
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal
    return macd_line, signal, hist


def _bollinger(close: pd.Series, window: int = 20) -> tuple:
    ma = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    pct_b = (close - lower) / ((upper - lower).replace(0, np.nan))
    return upper, lower, pct_b


def _vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    typical_price = (high + low + close) / 3
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def _rolling_sharpe(returns: pd.Series, window: int, rfr_daily: float = 0.0) -> pd.Series:
    excess = returns - rfr_daily
    mean_e = excess.rolling(window).mean()
    std_e = excess.rolling(window).std()
    return (mean_e / std_e.replace(0, np.nan)) * np.sqrt(_ANN)


def _rolling_sortino(returns: pd.Series, window: int, rfr_daily: float = 0.0) -> pd.Series:
    excess = returns - rfr_daily
    mean_e = excess.rolling(window).mean()
    down = excess.clip(upper=0)
    down_std = down.rolling(window).std()
    return (mean_e / down_std.replace(0, np.nan)) * np.sqrt(_ANN)


def _z_score(close: pd.Series, window: int) -> pd.Series:
    ma = close.rolling(window).mean()
    std = close.rolling(window).std()
    return (close - ma) / std.replace(0, np.nan)


def _market_regime(close: pd.Series) -> pd.Series:
    """Simple regime: 1=bull (above 50-day EMA), -1=bear, 0=neutral."""
    ema50 = _ema(close, 50)
    regime = pd.Series(0, index=close.index, dtype=float)
    regime[close > ema50 * 1.01] = 1.0
    regime[close < ema50 * 0.99] = -1.0
    return regime


def _trend_strength(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Simplified ADX-like trend strength, range 0–1."""
    atr = _atr(high, low, close, window)
    price_range = close.rolling(window).max() - close.rolling(window).min()
    strength = (price_range / (atr * window).replace(0, np.nan)).clip(0, 1)
    return strength


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class _FeatureCache:
    def __init__(self, maxsize: int = 128) -> None:
        self._store: Dict[str, pd.DataFrame] = {}
        self._order: List[str] = []
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def _key(self, symbol: str, features: tuple) -> str:
        feat_hash = hashlib.md5("|".join(sorted(features)).encode()).hexdigest()[:8]
        return f"{symbol}:{feat_hash}"

    def get(self, symbol: str, features: tuple) -> Optional[pd.DataFrame]:
        with self._lock:
            k = self._key(symbol, features)
            val = self._store.get(k)
            if val is not None:
                self._order.remove(k)
                self._order.append(k)
            return val.copy() if val is not None else None

    def put(self, symbol: str, features: tuple, df: pd.DataFrame) -> None:
        with self._lock:
            k = self._key(symbol, features)
            if k in self._store:
                self._order.remove(k)
            elif len(self._store) >= self._maxsize:
                old = self._order.pop(0)
                del self._store[old]
            self._store[k] = df.copy()
            self._order.append(k)

    def invalidate(self, symbol: str) -> None:
        with self._lock:
            keys = [k for k in self._store if symbol in k]
            for k in keys:
                del self._store[k]
                if k in self._order:
                    self._order.remove(k)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# FeatureStore
# ---------------------------------------------------------------------------

class FeatureStore:
    """Compute and cache features from OHLCV DataFrames.

    Usage::

        fs = FeatureStore()
        features = fs.compute(df, "AAPL", features=["rsi_14", "macd", "rolling_vol_21"])
    """

    def __init__(self, cache_maxsize: int = 128) -> None:
        self._cache = _FeatureCache(maxsize=cache_maxsize)

    def compute(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        features: Optional[List[str]] = None,
        rfr_daily: float = 0.0,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Compute requested features and return a DataFrame of feature columns.

        If ``features`` is None, all supported features are computed.
        """
        requested = tuple(sorted(features or FEATURE_NAMES))
        if use_cache:
            cached = self._cache.get(symbol, requested)
            if cached is not None:
                return cached

        result = self._compute_all(df, set(requested), rfr_daily)

        if use_cache:
            self._cache.put(symbol, requested, result)
        return result

    def compute_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        return pd.DataFrame({
            "returns": _returns(close),
            "log_returns": _log_returns(close),
        }, index=df.index)

    def invalidate(self, symbol: str) -> None:
        self._cache.invalidate(symbol)

    def catalog(self) -> List[Dict[str, Any]]:
        return [
            {"name": f.name, "group": f.group, "description": f.description, "lookback": f.lookback}
            for f in FEATURE_CATALOG
        ]

    # ------------------------------------------------------------------
    # Internal computation
    # ------------------------------------------------------------------

    def _compute_all(
        self,
        df: pd.DataFrame,
        requested: set,
        rfr_daily: float,
    ) -> pd.DataFrame:
        cols: Dict[str, pd.Series] = {}
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        has = lambda c: c in df.columns  # noqa: E731

        close = df["close"] if has("close") else None
        high = df["high"] if has("high") else None
        low = df["low"] if has("low") else None
        volume = df["volume"] if has("volume") else None

        # Returns
        if close is not None:
            ret = _returns(close)
            log_ret = _log_returns(close)
            if "returns" in requested:
                cols["returns"] = ret
            if "log_returns" in requested:
                cols["log_returns"] = log_ret

            # Rolling returns
            for n in (5, 10, 21, 63):
                name = f"rolling_returns_{n}"
                if name in requested:
                    cols[name] = close.pct_change(n)

            # Rolling volatility
            for n in (10, 21, 63):
                name = f"rolling_vol_{n}"
                if name in requested:
                    cols[name] = _rolling_vol(ret, n)

            # Momentum
            for n in (5, 10, 21, 63):
                name = f"momentum_{n}"
                if name in requested:
                    cols[name] = close.pct_change(n)

            # Z-score
            for n in (10, 21, 63):
                name = f"z_score_{n}"
                if name in requested:
                    cols[name] = _z_score(close, n)

            # RSI
            for n in (14, 21):
                name = f"rsi_{n}"
                if name in requested:
                    cols[name] = _rsi(close, n)

            # EMA
            for n in (12, 26, 50, 200):
                name = f"ema_{n}"
                if name in requested:
                    cols[name] = _ema(close, n)

            # MACD
            if any(x in requested for x in ("macd", "macd_signal", "macd_hist")):
                macd_line, signal, hist = _macd(close)
                if "macd" in requested:
                    cols["macd"] = macd_line
                if "macd_signal" in requested:
                    cols["macd_signal"] = signal
                if "macd_hist" in requested:
                    cols["macd_hist"] = hist

            # Bollinger Bands
            for n in (20,):
                upper_name = f"bb_upper_{n}"
                lower_name = f"bb_lower_{n}"
                pct_b_name = f"bb_pct_b_{n}"
                if any(x in requested for x in (upper_name, lower_name, pct_b_name)):
                    upper, lower, pct_b = _bollinger(close, n)
                    if upper_name in requested:
                        cols[upper_name] = upper
                    if lower_name in requested:
                        cols[lower_name] = lower
                    if pct_b_name in requested:
                        cols[pct_b_name] = pct_b

            # Rolling Sharpe / Sortino
            for n in (21, 63):
                sharpe_name = f"rolling_sharpe_{n}"
                sortino_name = f"rolling_sortino_{n}"
                if sharpe_name in requested:
                    cols[sharpe_name] = _rolling_sharpe(ret, n, rfr_daily)
                if sortino_name in requested:
                    cols[sortino_name] = _rolling_sortino(ret, n, rfr_daily)

            # Rolling skew / kurt
            for n in (21, 63):
                skew_name = f"rolling_skew_{n}"
                kurt_name = f"rolling_kurt_{n}"
                if skew_name in requested:
                    cols[skew_name] = ret.rolling(n).skew()
                if kurt_name in requested:
                    cols[kurt_name] = ret.rolling(n).kurt()

            # Market regime
            if "market_regime" in requested:
                cols["market_regime"] = _market_regime(close)

        # ATR & trend strength (need HLC)
        if high is not None and low is not None and close is not None:
            for n in (14,):
                atr_name = f"atr_{n}"
                if atr_name in requested:
                    cols[atr_name] = _atr(high, low, close, n)
            if "trend_strength" in requested:
                cols["trend_strength"] = _trend_strength(high, low, close)

        # VWAP
        if all(x is not None for x in (high, low, close, volume)):
            if "vwap" in requested:
                cols["vwap"] = _vwap(high, low, close, volume)

        # Volume features
        if volume is not None:
            if "volume_ma_20" in requested:
                cols["volume_ma_20"] = volume.rolling(20).mean()
            if "volume_ratio" in requested:
                ma20 = volume.rolling(20).mean()
                cols["volume_ratio"] = volume / ma20.replace(0, np.nan)

        return pd.DataFrame(cols, index=df.index)
