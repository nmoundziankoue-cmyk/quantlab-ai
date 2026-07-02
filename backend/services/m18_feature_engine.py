"""M18 — Feature Engine: continuously computes 21 technical/statistical features.

Pure Python, no numpy/pandas/ta-lib.  All math uses stdlib only.

Features computed:
  Returns, Rolling Mean, Rolling Std, ATR, RSI, MACD, VWAP, TWAP,
  Realized Volatility, Beta, Correlation, Cointegration, PCA,
  Rolling Sharpe, Rolling Sortino, Rolling Drawdown, Rolling VaR,
  Expected Shortfall, Kelly, Information Ratio
"""
from __future__ import annotations

import math
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class MACDResult:
    """MACD indicator values.

    Args:
        macd_line: MACD line (fast EMA - slow EMA).
        signal_line: Signal line (EMA of MACD line).
        histogram: MACD histogram (macd_line - signal_line).
        fast_period: Fast EMA period.
        slow_period: Slow EMA period.
        signal_period: Signal EMA period.
    """

    macd_line: float
    signal_line: float
    histogram: float
    fast_period: int
    slow_period: int
    signal_period: int

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


@dataclass
class DrawdownResult:
    """Rolling drawdown metrics.

    Args:
        current_drawdown: Current drawdown as a fraction (e.g. -0.05 = -5%).
        max_drawdown: Maximum drawdown over the window.
        drawdown_duration: Number of periods in the current drawdown.
        peak_value: Rolling peak price.
        trough_value: Trough price during worst drawdown.
    """

    current_drawdown: float
    max_drawdown: float
    drawdown_duration: int
    peak_value: float
    trough_value: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


@dataclass
class CointegrationResult:
    """Cointegration test result between two price series.

    Args:
        ticker1: First instrument.
        ticker2: Second instrument.
        hedge_ratio: OLS hedge ratio (quantity of ticker2 per unit ticker1).
        spread_mean: Historical mean of the spread.
        spread_std: Historical std of the spread.
        current_spread: Most recent spread value.
        z_score: Current spread Z-score: (spread - mean) / std.
        is_cointegrated: Heuristic cointegration flag (|z_score| < 3).
    """

    ticker1: str
    ticker2: str
    hedge_ratio: float
    spread_mean: float
    spread_std: float
    current_spread: float
    z_score: float
    is_cointegrated: bool

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


@dataclass
class PCAResult:
    """PCA decomposition of a multi-ticker return matrix.

    Args:
        tickers: Input tickers.
        n_components: Number of components extracted.
        explained_variance_ratio: Fraction of variance per component.
        loadings: Component loadings per ticker (n_components x n_tickers).
        total_explained: Sum of explained variance ratios.
    """

    tickers: List[str]
    n_components: int
    explained_variance_ratio: List[float]
    loadings: List[List[float]]
    total_explained: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "tickers": self.tickers,
            "n_components": self.n_components,
            "explained_variance_ratio": [round(v, 6) for v in self.explained_variance_ratio],
            "loadings": [[round(v, 6) for v in row] for row in self.loadings],
            "total_explained": round(self.total_explained, 6),
        }


@dataclass
class FeatureSnapshot:
    """All computed features for a ticker at a point in time.

    Args:
        ticker: Instrument symbol.
        timestamp: Computation time UTC.
        price: Most recent price.
        returns_1: 1-period return.
        rolling_mean_20: 20-period rolling mean.
        rolling_std_20: 20-period rolling std.
        atr_14: 14-period ATR.
        rsi_14: 14-period RSI.
        macd: MACD result (may be None if insufficient data).
        vwap: VWAP.
        twap: TWAP.
        realized_vol_20: 20-period realised volatility (annualised).
        rolling_sharpe_60: 60-period rolling Sharpe.
        rolling_sortino_60: 60-period rolling Sortino.
        rolling_drawdown: Rolling drawdown result.
        var_95_20: 95% VaR over 20 periods.
        es_95_20: 95% Expected Shortfall over 20 periods.
        kelly: Kelly fraction.
    """

    ticker: str
    timestamp: datetime
    price: float
    returns_1: float
    rolling_mean_20: float
    rolling_std_20: float
    atr_14: float
    rsi_14: float
    macd: Optional[MACDResult]
    vwap: float
    twap: float
    realized_vol_20: float
    rolling_sharpe_60: float
    rolling_sortino_60: float
    rolling_drawdown: Optional[DrawdownResult]
    var_95_20: float
    es_95_20: float
    kelly: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "timestamp": self.timestamp.isoformat(),
            "price": round(self.price, 6),
            "returns_1": round(self.returns_1, 6),
            "rolling_mean_20": round(self.rolling_mean_20, 6),
            "rolling_std_20": round(self.rolling_std_20, 6),
            "atr_14": round(self.atr_14, 6),
            "rsi_14": round(self.rsi_14, 4),
            "macd": self.macd.to_dict() if self.macd else None,
            "vwap": round(self.vwap, 6),
            "twap": round(self.twap, 6),
            "realized_vol_20": round(self.realized_vol_20, 6),
            "rolling_sharpe_60": round(self.rolling_sharpe_60, 6),
            "rolling_sortino_60": round(self.rolling_sortino_60, 6),
            "rolling_drawdown": self.rolling_drawdown.to_dict() if self.rolling_drawdown else None,
            "var_95_20": round(self.var_95_20, 6),
            "es_95_20": round(self.es_95_20, 6),
            "kelly": round(self.kelly, 6),
        }


# ---------------------------------------------------------------------------
# Internal math helpers (pure Python)
# ---------------------------------------------------------------------------

def _mean(xs: List[float]) -> float:
    """Return the arithmetic mean of a list."""
    if not xs:
        return 0.0
    return sum(xs) / len(xs)


def _std(xs: List[float], ddof: int = 0) -> float:
    """Return the population or sample standard deviation."""
    n = len(xs)
    if n <= ddof:
        return 0.0
    m = _mean(xs)
    variance = sum((x - m) ** 2 for x in xs) / (n - ddof)
    return math.sqrt(variance)


def _ema(values: List[float], period: int) -> float:
    """Compute the EMA of the last `period` values using the last value."""
    if not values:
        return 0.0
    k = 2.0 / (period + 1.0)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1.0 - k)
    return ema


def _ema_series(values: List[float], period: int) -> List[float]:
    """Return EMA series for all values."""
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    ema = values[0]
    result = [ema]
    for v in values[1:]:
        ema = v * k + ema * (1.0 - k)
        result.append(ema)
    return result


def _covariance(xs: List[float], ys: List[float]) -> float:
    """Compute sample covariance of two equal-length lists."""
    n = len(xs)
    if n < 2 or len(ys) != n:
        return 0.0
    mx, my = _mean(xs), _mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)


def _pearson_r(xs: List[float], ys: List[float]) -> float:
    """Compute Pearson correlation coefficient."""
    sx, sy = _std(xs, ddof=1), _std(ys, ddof=1)
    if sx == 0 or sy == 0:
        return 0.0
    return _covariance(xs, ys) / (sx * sy)


def _percentile(values: List[float], pct: float) -> float:
    """Return the p-th percentile of a sorted list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    idx = pct / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _ols_slope(xs: List[float], ys: List[float]) -> float:
    """Compute OLS slope (beta) of ys on xs."""
    cov = _covariance(xs, ys)
    var_x = _std(xs, ddof=1) ** 2
    if var_x == 0:
        return 0.0
    return cov / var_x


# ---------------------------------------------------------------------------
# Per-ticker state
# ---------------------------------------------------------------------------

_PRICE_WINDOW = 500


class _TickerFeatureState:
    """Rolling price/volume history for feature computation."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        self.prices: Deque[float] = deque(maxlen=_PRICE_WINDOW)
        self.volumes: Deque[float] = deque(maxlen=_PRICE_WINDOW)
        self.highs: Deque[float] = deque(maxlen=_PRICE_WINDOW)
        self.lows: Deque[float] = deque(maxlen=_PRICE_WINDOW)
        self.timestamps: Deque[datetime] = deque(maxlen=_PRICE_WINDOW)

    def update(self, price: float, volume: float,
               high: Optional[float] = None,
               low: Optional[float] = None) -> None:
        """Append a new OHLCV observation."""
        self.prices.append(price)
        self.volumes.append(volume)
        self.highs.append(high if high is not None else price)
        self.lows.append(low if low is not None else price)
        self.timestamps.append(datetime.now(timezone.utc))

    def price_list(self, n: Optional[int] = None) -> List[float]:
        """Return price list (optionally trimmed to last n)."""
        p = list(self.prices)
        return p[-n:] if n else p

    def returns_list(self, n: Optional[int] = None) -> List[float]:
        """Return simple period returns list."""
        p = list(self.prices)
        rets = [(p[i] - p[i - 1]) / p[i - 1] for i in range(1, len(p)) if p[i - 1] != 0]
        return rets[-n:] if n else rets


# ---------------------------------------------------------------------------
# Feature Engine
# ---------------------------------------------------------------------------

class FeatureEngine:
    """Continuously computes 21 technical and statistical features.

    State is maintained per ticker as a rolling window of up to 500
    price/volume observations.  All computations are pure Python.
    """

    def __init__(self) -> None:
        self._states: Dict[str, _TickerFeatureState] = {}

    def _state(self, ticker: str) -> _TickerFeatureState:
        t = ticker.upper()
        if t not in self._states:
            self._states[t] = _TickerFeatureState(t)
        return self._states[t]

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def update(
        self,
        ticker: str,
        price: float,
        volume: float,
        high: Optional[float] = None,
        low: Optional[float] = None,
    ) -> None:
        """Add a new OHLCV observation for a ticker.

        Args:
            ticker: Instrument symbol.
            price: Close/last price.
            volume: Period volume.
            high: Period high (defaults to price).
            low: Period low (defaults to price).
        """
        self._state(ticker).update(price, volume, high, low)

    def get_tracked_tickers(self) -> List[str]:
        """Return all tickers with active feature state.

        Returns:
            List of ticker symbols.
        """
        return list(self._states.keys())

    # ------------------------------------------------------------------
    # Feature 1: Returns
    # ------------------------------------------------------------------

    def compute_returns(self, ticker: str, period: int = 1) -> List[float]:
        """Compute simple period returns for the past N periods.

        Args:
            ticker: Instrument symbol.
            period: Look-back (default 1 = 1-period return).

        Returns:
            List of return values.

        Raises:
            ValueError: If insufficient price history.
        """
        prices = self._state(ticker).price_list()
        if len(prices) < period + 1:
            raise ValueError(f"Need at least {period + 1} prices for {ticker!r}")
        return [(prices[i] - prices[i - period]) / prices[i - period]
                for i in range(period, len(prices))
                if prices[i - period] != 0]

    # ------------------------------------------------------------------
    # Feature 2: Rolling mean
    # ------------------------------------------------------------------

    def compute_rolling_mean(self, ticker: str, window: int) -> float:
        """Compute rolling mean of last `window` prices.

        Args:
            ticker: Instrument symbol.
            window: Look-back window.

        Returns:
            Mean price.

        Raises:
            ValueError: If insufficient data.
        """
        prices = self._state(ticker).price_list(window)
        if len(prices) < window:
            raise ValueError(f"Need {window} prices for {ticker!r}, have {len(prices)}")
        return _mean(prices)

    # ------------------------------------------------------------------
    # Feature 3: Rolling std
    # ------------------------------------------------------------------

    def compute_rolling_std(self, ticker: str, window: int) -> float:
        """Compute rolling standard deviation of last `window` prices.

        Args:
            ticker: Instrument symbol.
            window: Look-back window.

        Returns:
            Standard deviation of prices.

        Raises:
            ValueError: If insufficient data.
        """
        prices = self._state(ticker).price_list(window)
        if len(prices) < window:
            raise ValueError(f"Need {window} prices for {ticker!r}, have {len(prices)}")
        return _std(prices, ddof=1)

    # ------------------------------------------------------------------
    # Feature 4: ATR
    # ------------------------------------------------------------------

    def compute_atr(self, ticker: str, window: int = 14) -> float:
        """Compute Average True Range over `window` periods.

        ATR = EMA of True Range.
        True Range = max(high - low, |high - prev_close|, |low - prev_close|)

        Args:
            ticker: Instrument symbol.
            window: ATR period (default 14).

        Returns:
            ATR value.

        Raises:
            ValueError: If insufficient data.
        """
        st = self._state(ticker)
        if len(st.prices) < window + 1:
            raise ValueError(f"Need {window + 1} prices for ATR({window}) on {ticker!r}")
        highs = list(st.highs)
        lows = list(st.lows)
        closes = list(st.prices)
        trs = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)
        return _mean(trs[-window:])

    # ------------------------------------------------------------------
    # Feature 5: RSI
    # ------------------------------------------------------------------

    def compute_rsi(self, ticker: str, window: int = 14) -> float:
        """Compute Relative Strength Index.

        RSI = 100 - 100/(1 + RS) where RS = avg_gain / avg_loss.

        Args:
            ticker: Instrument symbol.
            window: RSI period (default 14).

        Returns:
            RSI value in [0, 100].

        Raises:
            ValueError: If insufficient data.
        """
        prices = self._state(ticker).price_list(window + 1)
        if len(prices) < window + 1:
            raise ValueError(f"Need {window + 1} prices for RSI({window}) on {ticker!r}")
        gains, losses = [], []
        for i in range(1, len(prices)):
            delta = prices[i] - prices[i - 1]
            gains.append(max(0.0, delta))
            losses.append(max(0.0, -delta))
        avg_gain = _mean(gains[-window:])
        avg_loss = _mean(losses[-window:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - 100.0 / (1.0 + rs)

    # ------------------------------------------------------------------
    # Feature 6: MACD
    # ------------------------------------------------------------------

    def compute_macd(
        self,
        ticker: str,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> MACDResult:
        """Compute MACD indicator.

        Args:
            ticker: Instrument symbol.
            fast: Fast EMA period (default 12).
            slow: Slow EMA period (default 26).
            signal: Signal EMA period (default 9).

        Returns:
            MACDResult with macd_line, signal_line, histogram.

        Raises:
            ValueError: If insufficient data.
        """
        prices = self._state(ticker).price_list()
        if len(prices) < slow + signal:
            raise ValueError(f"Need {slow + signal} prices for MACD on {ticker!r}")
        fast_ema_series = _ema_series(prices, fast)
        slow_ema_series = _ema_series(prices, slow)
        macd_series = [f - s for f, s in zip(fast_ema_series, slow_ema_series)]
        if len(macd_series) < signal:
            raise ValueError(f"Insufficient MACD series length for signal on {ticker!r}")
        signal_line = _ema(macd_series, signal)
        macd_line = macd_series[-1]
        return MACDResult(
            macd_line=macd_line,
            signal_line=signal_line,
            histogram=macd_line - signal_line,
            fast_period=fast,
            slow_period=slow,
            signal_period=signal,
        )

    # ------------------------------------------------------------------
    # Feature 7: VWAP
    # ------------------------------------------------------------------

    def compute_vwap(self, ticker: str) -> float:
        """Compute Volume-Weighted Average Price from full history.

        Args:
            ticker: Instrument symbol.

        Returns:
            VWAP value.

        Raises:
            ValueError: If no price data.
        """
        st = self._state(ticker)
        if not st.prices:
            raise ValueError(f"No price data for {ticker!r}")
        total_vol = sum(st.volumes)
        if total_vol == 0:
            return _mean(list(st.prices))
        return sum(p * v for p, v in zip(st.prices, st.volumes)) / total_vol

    # ------------------------------------------------------------------
    # Feature 8: TWAP
    # ------------------------------------------------------------------

    def compute_twap(self, ticker: str, window: Optional[int] = None) -> float:
        """Compute Time-Weighted Average Price.

        Args:
            ticker: Instrument symbol.
            window: Look-back window (None = all).

        Returns:
            TWAP value.

        Raises:
            ValueError: If no price data.
        """
        prices = self._state(ticker).price_list(window)
        if not prices:
            raise ValueError(f"No price data for {ticker!r}")
        return _mean(prices)

    # ------------------------------------------------------------------
    # Feature 9: Realized volatility
    # ------------------------------------------------------------------

    def compute_realized_volatility(
        self, ticker: str, window: int = 20, annualize: bool = True
    ) -> float:
        """Compute realised volatility (std dev of log returns, optionally annualised).

        Args:
            ticker: Instrument symbol.
            window: Look-back window in periods.
            annualize: If True, multiply by sqrt(252).

        Returns:
            Realised volatility.

        Raises:
            ValueError: If insufficient data.
        """
        prices = self._state(ticker).price_list(window + 1)
        if len(prices) < window + 1:
            raise ValueError(f"Need {window + 1} prices for RealVol on {ticker!r}")
        log_returns = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
            if prices[i - 1] > 0 and prices[i] > 0
        ]
        if not log_returns:
            return 0.0
        vol = _std(log_returns, ddof=1)
        return vol * math.sqrt(252) if annualize else vol

    # ------------------------------------------------------------------
    # Feature 10: Beta
    # ------------------------------------------------------------------

    def compute_beta(
        self, ticker: str, benchmark_ticker: str, window: int = 60
    ) -> float:
        """Compute rolling beta of ticker against benchmark.

        Args:
            ticker: Subject instrument.
            benchmark_ticker: Benchmark instrument.
            window: Look-back window.

        Returns:
            Beta coefficient.

        Raises:
            ValueError: If insufficient aligned history.
        """
        t_rets = self._state(ticker).returns_list(window)
        b_rets = self._state(benchmark_ticker).returns_list(window)
        n = min(len(t_rets), len(b_rets))
        if n < 2:
            raise ValueError(f"Insufficient return history for beta of {ticker!r} vs {benchmark_ticker!r}")
        t_rets = t_rets[-n:]
        b_rets = b_rets[-n:]
        return _ols_slope(b_rets, t_rets)

    # ------------------------------------------------------------------
    # Feature 11: Correlation
    # ------------------------------------------------------------------

    def compute_correlation(
        self, ticker1: str, ticker2: str, window: int = 60
    ) -> float:
        """Compute rolling Pearson correlation between two tickers.

        Args:
            ticker1: First instrument.
            ticker2: Second instrument.
            window: Look-back window.

        Returns:
            Pearson correlation in [-1, 1].

        Raises:
            ValueError: If insufficient aligned history.
        """
        r1 = self._state(ticker1).returns_list(window)
        r2 = self._state(ticker2).returns_list(window)
        n = min(len(r1), len(r2))
        if n < 2:
            raise ValueError(f"Insufficient history for correlation of {ticker1!r} vs {ticker2!r}")
        return _pearson_r(r1[-n:], r2[-n:])

    # ------------------------------------------------------------------
    # Feature 12: Cointegration
    # ------------------------------------------------------------------

    def compute_cointegration(
        self, ticker1: str, ticker2: str, window: int = 60
    ) -> CointegrationResult:
        """Compute a simplified cointegration test (Engle-Granger heuristic).

        Estimates the OLS hedge ratio, then checks whether the spread
        is stationary using the Z-score.

        Args:
            ticker1: First instrument.
            ticker2: Second instrument.
            window: Look-back window.

        Returns:
            CointegrationResult.

        Raises:
            ValueError: If insufficient aligned price history.
        """
        p1 = self._state(ticker1).price_list(window)
        p2 = self._state(ticker2).price_list(window)
        n = min(len(p1), len(p2))
        if n < 10:
            raise ValueError(f"Need at least 10 prices for cointegration of {ticker1!r}/{ticker2!r}")
        p1 = p1[-n:]
        p2 = p2[-n:]
        hedge_ratio = _ols_slope(p2, p1)
        spread = [p1[i] - hedge_ratio * p2[i] for i in range(n)]
        s_mean = _mean(spread)
        s_std = _std(spread, ddof=1)
        current = spread[-1]
        z_score = (current - s_mean) / s_std if s_std > 0 else 0.0
        return CointegrationResult(
            ticker1=ticker1.upper(),
            ticker2=ticker2.upper(),
            hedge_ratio=hedge_ratio,
            spread_mean=s_mean,
            spread_std=s_std,
            current_spread=current,
            z_score=z_score,
            is_cointegrated=abs(z_score) < 3.0,
        )

    # ------------------------------------------------------------------
    # Feature 13: PCA
    # ------------------------------------------------------------------

    def compute_pca(
        self, tickers: List[str], n_components: int = 3, window: int = 60
    ) -> PCAResult:
        """Compute PCA on the return matrix for a group of tickers.

        Uses power-iteration to find principal components (pure Python).

        Args:
            tickers: List of instrument symbols.
            n_components: Number of components to extract.
            window: Look-back window for returns.

        Returns:
            PCAResult.

        Raises:
            ValueError: If fewer than 2 tickers or insufficient data.
        """
        if len(tickers) < 2:
            raise ValueError("PCA requires at least 2 tickers")
        series = [self._state(t).returns_list(window) for t in tickers]
        min_len = min(len(s) for s in series)
        if min_len < 2:
            raise ValueError("Insufficient return history for PCA")
        series = [s[-min_len:] for s in series]
        n_obs = min_len
        n_feat = len(tickers)
        means = [_mean(s) for s in series]
        centered = [[series[j][i] - means[j] for i in range(n_obs)] for j in range(n_feat)]
        cov = [[_covariance(centered[i], centered[j]) for j in range(n_feat)] for i in range(n_feat)]
        n_comp = min(n_components, n_feat)
        loadings: List[List[float]] = []
        explained: List[float] = []
        total_var = sum(cov[i][i] for i in range(n_feat))
        residual = [row[:] for row in cov]
        for _ in range(n_comp):
            vec = [1.0 / math.sqrt(n_feat)] * n_feat
            for _iter in range(50):
                new_vec = [sum(residual[i][j] * vec[j] for j in range(n_feat)) for i in range(n_feat)]
                norm = math.sqrt(sum(x ** 2 for x in new_vec))
                if norm < 1e-12:
                    break
                vec = [x / norm for x in new_vec]
            eigenvalue = sum(
                vec[i] * sum(residual[i][j] * vec[j] for j in range(n_feat))
                for i in range(n_feat)
            )
            loadings.append([round(v, 6) for v in vec])
            explained.append(eigenvalue / total_var if total_var > 0 else 0.0)
            for i in range(n_feat):
                for j in range(n_feat):
                    residual[i][j] -= eigenvalue * vec[i] * vec[j]
        return PCAResult(
            tickers=[t.upper() for t in tickers],
            n_components=n_comp,
            explained_variance_ratio=[round(e, 6) for e in explained],
            loadings=loadings,
            total_explained=round(sum(explained), 6),
        )

    # ------------------------------------------------------------------
    # Feature 14: Rolling Sharpe
    # ------------------------------------------------------------------

    def compute_rolling_sharpe(
        self, ticker: str, window: int = 252, risk_free: float = 0.0
    ) -> float:
        """Compute rolling Sharpe ratio (annualised).

        Args:
            ticker: Instrument symbol.
            window: Look-back window.
            risk_free: Risk-free rate per period.

        Returns:
            Annualised Sharpe ratio.

        Raises:
            ValueError: If insufficient data.
        """
        rets = self._state(ticker).returns_list(window)
        if len(rets) < 2:
            raise ValueError(f"Need at least 2 returns for Sharpe on {ticker!r}")
        excess = [r - risk_free for r in rets]
        mean_e = _mean(excess)
        std_e = _std(excess, ddof=1)
        if std_e == 0:
            return 0.0
        return (mean_e / std_e) * math.sqrt(252)

    # ------------------------------------------------------------------
    # Feature 15: Rolling Sortino
    # ------------------------------------------------------------------

    def compute_rolling_sortino(
        self, ticker: str, window: int = 252, risk_free: float = 0.0
    ) -> float:
        """Compute rolling Sortino ratio (annualised).

        Args:
            ticker: Instrument symbol.
            window: Look-back window.
            risk_free: Minimum acceptable return per period.

        Returns:
            Annualised Sortino ratio.

        Raises:
            ValueError: If insufficient data.
        """
        rets = self._state(ticker).returns_list(window)
        if len(rets) < 2:
            raise ValueError(f"Need at least 2 returns for Sortino on {ticker!r}")
        excess = [r - risk_free for r in rets]
        mean_e = _mean(excess)
        downside = [min(0.0, r) for r in excess]
        downside_std = _std(downside, ddof=1)
        if downside_std == 0:
            return 0.0 if mean_e <= 0 else float("inf")
        return (mean_e / downside_std) * math.sqrt(252)

    # ------------------------------------------------------------------
    # Feature 16: Rolling drawdown
    # ------------------------------------------------------------------

    def compute_rolling_drawdown(
        self, ticker: str, window: int = 252
    ) -> DrawdownResult:
        """Compute rolling maximum drawdown and current drawdown.

        Args:
            ticker: Instrument symbol.
            window: Look-back window.

        Returns:
            DrawdownResult.

        Raises:
            ValueError: If insufficient data.
        """
        prices = self._state(ticker).price_list(window)
        if len(prices) < 2:
            raise ValueError(f"Need at least 2 prices for drawdown on {ticker!r}")
        peak = prices[0]
        trough = prices[0]
        max_dd = 0.0
        dd_start = 0
        dd_duration = 0
        current_dd_start = 0
        for i, p in enumerate(prices):
            if p > peak:
                peak = p
                current_dd_start = i
            dd = (p - peak) / peak
            if dd < max_dd:
                max_dd = dd
                trough = p
        current_peak = max(prices)
        current_price = prices[-1]
        current_dd = (current_price - current_peak) / current_peak if current_peak > 0 else 0.0
        duration = len(prices) - 1 - current_dd_start
        return DrawdownResult(
            current_drawdown=current_dd,
            max_drawdown=max_dd,
            drawdown_duration=max(0, duration),
            peak_value=current_peak,
            trough_value=trough,
        )

    # ------------------------------------------------------------------
    # Feature 17: Rolling VaR
    # ------------------------------------------------------------------

    def compute_rolling_var(
        self, ticker: str, window: int = 252, confidence: float = 0.95
    ) -> float:
        """Compute historical Value-at-Risk at given confidence level.

        Args:
            ticker: Instrument symbol.
            window: Look-back window.
            confidence: Confidence level (default 0.95).

        Returns:
            VaR as a positive loss value (fraction of portfolio).

        Raises:
            ValueError: If insufficient data.
        """
        rets = self._state(ticker).returns_list(window)
        if len(rets) < 10:
            raise ValueError(f"Need at least 10 returns for VaR on {ticker!r}")
        pct = (1.0 - confidence) * 100.0
        return abs(_percentile(rets, pct))

    # ------------------------------------------------------------------
    # Feature 18: Expected Shortfall
    # ------------------------------------------------------------------

    def compute_expected_shortfall(
        self, ticker: str, window: int = 252, confidence: float = 0.95
    ) -> float:
        """Compute Expected Shortfall (CVaR) at given confidence level.

        ES = mean of losses beyond the VaR threshold.

        Args:
            ticker: Instrument symbol.
            window: Look-back window.
            confidence: Confidence level.

        Returns:
            ES as a positive loss value.

        Raises:
            ValueError: If insufficient data.
        """
        rets = self._state(ticker).returns_list(window)
        if len(rets) < 10:
            raise ValueError(f"Need at least 10 returns for ES on {ticker!r}")
        sorted_rets = sorted(rets)
        cutoff_idx = max(1, int((1 - confidence) * len(sorted_rets)))
        tail = sorted_rets[:cutoff_idx]
        return abs(_mean(tail)) if tail else 0.0

    # ------------------------------------------------------------------
    # Feature 19: Kelly fraction
    # ------------------------------------------------------------------

    def compute_kelly(self, ticker: str, window: int = 252) -> float:
        """Compute Kelly criterion optimal fraction.

        Kelly = mean_return / variance_of_returns.

        Args:
            ticker: Instrument symbol.
            window: Look-back window.

        Returns:
            Kelly fraction (capped at 1.0).

        Raises:
            ValueError: If insufficient data.
        """
        rets = self._state(ticker).returns_list(window)
        if len(rets) < 10:
            return 0.0
        mean_r = _mean(rets)
        var_r = _std(rets, ddof=1) ** 2
        if var_r == 0:
            return 0.0
        kelly = mean_r / var_r
        return max(-1.0, min(1.0, kelly))

    # ------------------------------------------------------------------
    # Feature 20: Information Ratio
    # ------------------------------------------------------------------

    def compute_information_ratio(
        self, ticker: str, benchmark_ticker: str, window: int = 252
    ) -> float:
        """Compute rolling Information Ratio (annualised).

        IR = mean(active_return) / tracking_error * sqrt(252)

        Args:
            ticker: Subject instrument.
            benchmark_ticker: Benchmark instrument.
            window: Look-back window.

        Returns:
            Annualised Information Ratio.

        Raises:
            ValueError: If insufficient aligned history.
        """
        t_rets = self._state(ticker).returns_list(window)
        b_rets = self._state(benchmark_ticker).returns_list(window)
        n = min(len(t_rets), len(b_rets))
        if n < 2:
            raise ValueError(f"Insufficient history for IR of {ticker!r} vs {benchmark_ticker!r}")
        active = [t - b for t, b in zip(t_rets[-n:], b_rets[-n:])]
        mean_a = _mean(active)
        te = _std(active, ddof=1)
        if te == 0:
            return 0.0
        return (mean_a / te) * math.sqrt(252)

    # ------------------------------------------------------------------
    # Feature 21: Full snapshot
    # ------------------------------------------------------------------

    def get_feature_snapshot(self, ticker: str) -> FeatureSnapshot:
        """Compute all available features for a ticker.

        Best-effort: features that require more data than available are
        skipped (set to 0.0 or None).

        Args:
            ticker: Instrument symbol.

        Returns:
            FeatureSnapshot with all computed features.

        Raises:
            ValueError: If ticker has no price data at all.
        """
        st = self._state(ticker)
        if not st.prices:
            raise ValueError(f"No price data for {ticker!r}")
        price = list(st.prices)[-1]
        def _safe(fn, *args, default=0.0, **kwargs):  # type: ignore[no-untyped-def]
            try:
                return fn(*args, **kwargs)
            except (ValueError, ZeroDivisionError):
                return default
        returns_list = st.returns_list()
        returns_1 = returns_list[-1] if returns_list else 0.0
        return FeatureSnapshot(
            ticker=ticker.upper(),
            timestamp=datetime.now(timezone.utc),
            price=price,
            returns_1=returns_1,
            rolling_mean_20=_safe(self.compute_rolling_mean, ticker, 20),
            rolling_std_20=_safe(self.compute_rolling_std, ticker, 20),
            atr_14=_safe(self.compute_atr, ticker, 14),
            rsi_14=_safe(self.compute_rsi, ticker, 14),
            macd=_safe(self.compute_macd, ticker, default=None),
            vwap=_safe(self.compute_vwap, ticker),
            twap=_safe(self.compute_twap, ticker),
            realized_vol_20=_safe(self.compute_realized_volatility, ticker, 20),
            rolling_sharpe_60=_safe(self.compute_rolling_sharpe, ticker, 60),
            rolling_sortino_60=_safe(self.compute_rolling_sortino, ticker, 60),
            rolling_drawdown=_safe(self.compute_rolling_drawdown, ticker, 60, default=None),
            var_95_20=_safe(self.compute_rolling_var, ticker, 20),
            es_95_20=_safe(self.compute_expected_shortfall, ticker, 20),
            kelly=_safe(self.compute_kelly, ticker, 20),
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[FeatureEngine] = None


def get_feature_engine() -> FeatureEngine:
    """Return the singleton FeatureEngine.

    Returns:
        Shared FeatureEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = FeatureEngine()
    return _default_engine
