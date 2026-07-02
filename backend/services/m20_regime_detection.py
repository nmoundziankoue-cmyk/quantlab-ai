"""M20 — Regime Detection Engine.

Detects market regimes (BULL, BEAR, HIGH_VOL, LOW_VOL, RANGING) from price
series using pure-Python moving averages, realized volatility, and momentum
signals.  No external scientific libraries required.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RegimeType(str, Enum):
    """Market regime classification.

    Attributes:
        BULL: Uptrending market (positive MA crossover + positive momentum).
        BEAR: Downtrending market (negative MA crossover + negative momentum).
        HIGH_VOL: Realized volatility significantly above long-term average.
        LOW_VOL: Realized volatility significantly below long-term average.
        RANGING: No clear directional or volatility signal.
    """

    BULL = "BULL"
    BEAR = "BEAR"
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"
    RANGING = "RANGING"


# ---------------------------------------------------------------------------
# Domain dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RegimePoint:
    """Regime classification at a single point in time.

    Attributes:
        date: ISO date string for this observation.
        regime: Detected regime type.
        confidence: Detection confidence in [0, 1].
        indicators: Raw indicator values used for classification.
    """

    date: str
    regime: RegimeType
    confidence: float
    indicators: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "date": self.date,
            "regime": self.regime.value,
            "confidence": self.confidence,
            "indicators": self.indicators,
        }


@dataclass
class RegimeResult:
    """Full regime detection result for a ticker.

    Attributes:
        ticker: Instrument symbol.
        detection_id: Unique UUID for this detection run.
        current_regime: Most recently detected regime.
        current_confidence: Confidence for the current regime.
        history: Per-bar regime history (sorted ascending by date).
        num_observations: Number of price bars processed.
        transitions: Number of regime changes detected.
        regime_durations: Average duration (bars) per regime type.
    """

    ticker: str
    detection_id: str
    current_regime: RegimeType
    current_confidence: float
    history: List[RegimePoint]
    num_observations: int
    transitions: int
    regime_durations: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "ticker": self.ticker,
            "detection_id": self.detection_id,
            "current_regime": self.current_regime.value,
            "current_confidence": self.current_confidence,
            "history": [p.to_dict() for p in self.history],
            "num_observations": self.num_observations,
            "transitions": self.transitions,
            "regime_durations": self.regime_durations,
        }


@dataclass
class RegimeSummary:
    """Compact summary across all detected tickers.

    Attributes:
        tickers: List of tickers with results cached.
        current_regimes: Mapping of ticker → current regime.
        dominant_regime: Most common current regime across tickers.
        regime_counts: Count of tickers per regime type.
    """

    tickers: List[str]
    current_regimes: Dict[str, str]
    dominant_regime: str
    regime_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "tickers": self.tickers,
            "current_regimes": self.current_regimes,
            "dominant_regime": self.dominant_regime,
            "regime_counts": self.regime_counts,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sma(prices: List[float], window: int) -> float:
    """Compute simple moving average over the last `window` prices."""
    if not prices:
        return 0.0
    tail = prices[-window:] if len(prices) >= window else prices
    return sum(tail) / len(tail)


def _realized_vol_annual(prices: List[float], window: int) -> float:
    """Compute annualised realised volatility from the last `window` prices."""
    n = min(window, len(prices))
    if n < 2:
        return 0.0
    tail = prices[-n:]
    rets = [(tail[i] - tail[i - 1]) / tail[i - 1] for i in range(1, len(tail)) if tail[i - 1] > 0]
    if not rets:
        return 0.0
    mean_r = sum(rets) / len(rets)
    variance = sum((r - mean_r) ** 2 for r in rets) / len(rets)
    return math.sqrt(variance * 252)


def _momentum(prices: List[float], window: int) -> float:
    """Fractional price change over the last `window` bars."""
    if len(prices) <= window or prices[-1 - window] <= 0:
        return 0.0
    return (prices[-1] - prices[-1 - window]) / prices[-1 - window]


def _classify(
    fast_ma: float,
    slow_ma: float,
    momentum_20d: float,
    recent_vol: float,
    long_vol: float,
    vol_high_thresh: float,
    vol_low_thresh: float,
    momentum_thresh: float,
) -> Tuple[RegimeType, float, Dict[str, float]]:
    """Classify market regime from computed indicators.

    Args:
        fast_ma: Fast simple moving average value.
        slow_ma: Slow simple moving average value.
        momentum_20d: 20-bar fractional price change.
        recent_vol: Recent annualised realised volatility.
        long_vol: Long-term annualised realised volatility.
        vol_high_thresh: Vol-ratio threshold above which HIGH_VOL is declared.
        vol_low_thresh: Vol-ratio threshold below which LOW_VOL is declared.
        momentum_thresh: Absolute momentum threshold for BULL/BEAR.

    Returns:
        Tuple of (RegimeType, confidence, indicator dict).
    """
    vol_ratio = recent_vol / long_vol if long_vol > 1e-9 else 1.0
    ma_signal = 1.0 if fast_ma > slow_ma else -1.0

    indicators: Dict[str, float] = {
        "fast_ma": fast_ma,
        "slow_ma": slow_ma,
        "ma_signal": ma_signal,
        "momentum_20d": momentum_20d,
        "realized_vol_recent": recent_vol,
        "realized_vol_long": long_vol,
        "vol_ratio": vol_ratio,
    }

    if vol_ratio >= vol_high_thresh:
        excess = min((vol_ratio - vol_high_thresh) / vol_high_thresh, 1.0)
        confidence = 0.50 + 0.50 * excess
        return RegimeType.HIGH_VOL, round(min(confidence, 1.0), 4), indicators

    if vol_ratio <= vol_low_thresh and long_vol > 1e-9:
        deficit = min((vol_low_thresh - vol_ratio) / vol_low_thresh, 1.0)
        confidence = 0.50 + 0.50 * deficit
        return RegimeType.LOW_VOL, round(min(confidence, 1.0), 4), indicators

    if ma_signal > 0 and momentum_20d >= momentum_thresh:
        confidence = 0.50 + min(abs(momentum_20d) / (momentum_thresh * 4), 0.50)
        return RegimeType.BULL, round(min(confidence, 1.0), 4), indicators

    if ma_signal < 0 and momentum_20d <= -momentum_thresh:
        confidence = 0.50 + min(abs(momentum_20d) / (momentum_thresh * 4), 0.50)
        return RegimeType.BEAR, round(min(confidence, 1.0), 4), indicators

    return RegimeType.RANGING, 0.50, indicators


def _count_transitions(history: List[RegimePoint]) -> int:
    """Count the number of regime transitions in a history list."""
    if len(history) < 2:
        return 0
    return sum(1 for i in range(1, len(history)) if history[i].regime != history[i - 1].regime)


def _average_durations(history: List[RegimePoint]) -> Dict[str, float]:
    """Compute average consecutive run length per regime type."""
    if not history:
        return {}
    durations: Dict[str, List[int]] = {}
    run_regime = history[0].regime.value
    run_len = 1
    for i in range(1, len(history)):
        if history[i].regime.value == run_regime:
            run_len += 1
        else:
            durations.setdefault(run_regime, []).append(run_len)
            run_regime = history[i].regime.value
            run_len = 1
    durations.setdefault(run_regime, []).append(run_len)
    return {k: sum(v) / len(v) for k, v in durations.items()}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RegimeDetectionEngine:
    """Detects market regimes from price series using pure-Python indicators.

    Uses a combination of:
    - Simple MA crossover (configurable fast/slow windows)
    - 20-bar price momentum
    - Realised volatility ratio (recent vs long-term)

    State is cached per ticker and can be retrieved after detection.

    Attributes:
        fast_window: Number of bars for the fast SMA.
        slow_window: Number of bars for the slow SMA.
        vol_window: Number of bars for recent realised vol.
        vol_lookback: Number of bars for long-term realised vol.
        vol_high_threshold: Vol-ratio above which HIGH_VOL is declared.
        vol_low_threshold: Vol-ratio below which LOW_VOL is declared.
        momentum_threshold: Fractional momentum threshold for BULL/BEAR.
    """

    def __init__(
        self,
        fast_window: int = 50,
        slow_window: int = 200,
        vol_window: int = 20,
        vol_lookback: int = 252,
        vol_high_threshold: float = 1.5,
        vol_low_threshold: float = 0.5,
        momentum_threshold: float = 0.02,
    ) -> None:
        """Initialise the engine with indicator parameters.

        Args:
            fast_window: Fast SMA window in bars.
            slow_window: Slow SMA window in bars.
            vol_window: Recent realised vol window in bars.
            vol_lookback: Long-term realised vol window in bars.
            vol_high_threshold: Vol-ratio threshold to declare HIGH_VOL.
            vol_low_threshold: Vol-ratio threshold to declare LOW_VOL.
            momentum_threshold: Absolute fractional return to confirm BULL/BEAR.
        """
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.vol_window = vol_window
        self.vol_lookback = vol_lookback
        self.vol_high_threshold = vol_high_threshold
        self.vol_low_threshold = vol_low_threshold
        self.momentum_threshold = momentum_threshold
        self._results: Dict[str, RegimeResult] = {}

    # ------------------------------------------------------------------
    # Core detection
    # ------------------------------------------------------------------

    def detect(self, ticker: str, bars: List[Any]) -> RegimeResult:
        """Detect regime from a sequence of OHLCV bars.

        Args:
            ticker: Instrument symbol.
            bars: List of objects with `.date` and `.close` attributes,
                  or dicts with ``"date"`` and ``"close"`` keys.

        Returns:
            RegimeResult with full history and current regime.
        """
        def _close(b: Any) -> float:
            return b["close"] if isinstance(b, dict) else b.close

        def _date(b: Any) -> str:
            return b["date"] if isinstance(b, dict) else b.date

        sorted_bars = sorted(bars, key=_date)
        closes = [_close(b) for b in sorted_bars]
        dates = [_date(b) for b in sorted_bars]
        return self._detect_from_series(ticker, dates, closes)

    def detect_from_returns(
        self, ticker: str, daily_returns: List[float], start_price: float = 100.0
    ) -> RegimeResult:
        """Detect regime from a daily-return series.

        Reconstructs a synthetic price series (compounded from returns) and
        applies the standard detection pipeline.

        Args:
            ticker: Instrument symbol.
            daily_returns: Fractional daily returns.
            start_price: Synthetic starting price (default 100).

        Returns:
            RegimeResult with full history.
        """
        closes = [start_price]
        for r in daily_returns:
            closes.append(closes[-1] * (1.0 + r))
        dates = [f"T{i:04d}" for i in range(len(closes))]
        return self._detect_from_series(ticker, dates, closes)

    def _detect_from_series(
        self, ticker: str, dates: List[str], closes: List[float]
    ) -> RegimeResult:
        """Internal: run detection on aligned date/close lists.

        Args:
            ticker: Instrument symbol.
            dates: Ordered ISO date strings.
            closes: Close prices aligned with dates.

        Returns:
            RegimeResult stored in the cache.
        """
        history: List[RegimePoint] = []
        min_bars = max(self.slow_window + 1, self.vol_lookback + 1, 21)

        for i in range(len(closes)):
            subset = closes[: i + 1]
            fast_ma = _sma(subset, self.fast_window)
            slow_ma = _sma(subset, self.slow_window)
            mom = _momentum(subset, min(20, i))
            recent_vol = _realized_vol_annual(subset, self.vol_window)
            long_vol = _realized_vol_annual(subset, self.vol_lookback)
            regime, conf, indics = _classify(
                fast_ma, slow_ma, mom, recent_vol, long_vol,
                self.vol_high_threshold, self.vol_low_threshold, self.momentum_threshold,
            )
            if i >= 1:
                history.append(RegimePoint(date=dates[i], regime=regime, confidence=conf, indicators=indics))

        if not history:
            history.append(RegimePoint(
                date=dates[-1] if dates else "T0000",
                regime=RegimeType.RANGING,
                confidence=0.5,
                indicators={},
            ))

        current = history[-1]
        result = RegimeResult(
            ticker=ticker,
            detection_id=str(uuid.uuid4()),
            current_regime=current.regime,
            current_confidence=current.confidence,
            history=history,
            num_observations=len(closes),
            transitions=_count_transitions(history),
            regime_durations=_average_durations(history),
        )
        self._results[ticker] = result
        return result

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_result(self, ticker: str) -> Optional[RegimeResult]:
        """Return the cached detection result for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            RegimeResult if cached, else None.
        """
        return self._results.get(ticker)

    def get_current_regime(self, ticker: str) -> Optional[RegimePoint]:
        """Return the most recent regime point for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            Most recent RegimePoint, or None if ticker unknown.
        """
        result = self._results.get(ticker)
        return result.history[-1] if result and result.history else None

    def get_history(self, ticker: str) -> List[RegimePoint]:
        """Return the full regime history for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            List of RegimePoint objects, empty if ticker unknown.
        """
        result = self._results.get(ticker)
        return result.history if result else []

    def list_tickers(self) -> List[str]:
        """Return all tickers with cached detection results.

        Returns:
            Sorted list of ticker symbols.
        """
        return sorted(self._results.keys())

    def get_summary(self) -> RegimeSummary:
        """Summarise current regimes across all cached tickers.

        Returns:
            RegimeSummary with dominant regime and per-regime counts.
        """
        current: Dict[str, str] = {}
        counts: Dict[str, int] = {}
        for ticker, result in self._results.items():
            reg = result.current_regime.value
            current[ticker] = reg
            counts[reg] = counts.get(reg, 0) + 1
        dominant = max(counts, key=counts.get) if counts else RegimeType.RANGING.value
        return RegimeSummary(
            tickers=sorted(self._results.keys()),
            current_regimes=current,
            dominant_regime=dominant,
            regime_counts=counts,
        )

    def compare_regimes(self, tickers: List[str]) -> Dict[str, Any]:
        """Compare current regimes across a list of tickers.

        Args:
            tickers: Tickers to compare.

        Returns:
            Dict mapping ticker → regime info (regime, confidence).
        """
        out: Dict[str, Any] = {}
        for t in tickers:
            r = self._results.get(t)
            if r:
                out[t] = {"regime": r.current_regime.value, "confidence": r.current_confidence}
            else:
                out[t] = {"regime": None, "confidence": None}
        return out

    def reset(self) -> None:
        """Clear all cached detection results."""
        self._results.clear()
