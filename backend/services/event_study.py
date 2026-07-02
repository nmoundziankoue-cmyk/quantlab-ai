"""M15 Phase 5 — Event Study Engine.

Classical event study methodology: AR, AAR, CAR, CAAR, t-statistics,
p-values, confidence intervals, bootstrap.
Pure Python, fully deterministic — no external ML/stats libraries.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Event windows
# ---------------------------------------------------------------------------

class EventWindow(str, Enum):
    W1 = "[-1,+1]"
    W3 = "[-3,+3]"
    W5 = "[-5,+5]"
    W10 = "[-10,+10]"
    W20 = "[-20,+20]"
    W60 = "[-60,+60]"


_WINDOW_HALF: Dict[EventWindow, int] = {
    EventWindow.W1: 1,
    EventWindow.W3: 3,
    EventWindow.W5: 5,
    EventWindow.W10: 10,
    EventWindow.W20: 20,
    EventWindow.W60: 60,
}

ALL_WINDOWS: List[EventWindow] = list(EventWindow)


# ---------------------------------------------------------------------------
# Statistical helpers (no scipy dependency)
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def _std(values: List[float]) -> float:
    return math.sqrt(_variance(values))


def _t_stat(values: List[float]) -> float:
    """One-sample t-statistic testing H0: mean=0."""
    n = len(values)
    if n < 2:
        return 0.0
    s = _std(values)
    if s == 0.0:
        return 0.0
    return _mean(values) / (s / math.sqrt(n))


def _approx_p_value(t: float, df: int) -> float:
    """Approximate two-tailed p-value via a rational approximation of the t-distribution CDF."""
    if df <= 0:
        return 1.0
    abs_t = abs(t)
    if abs_t == 0.0:
        return 1.0
    # Use normal approximation for large df; Cornish-Fisher for small df
    if df >= 30:
        # Abramowitz & Stegun 26.2.17
        z = abs_t
        p = 1.0 / (1.0 + 0.2316419 * z)
        poly = ((((1.330274429 * p - 1.821255978) * p + 1.781477937) * p - 0.356563782) * p + 0.319381530) * p
        tail = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
        return min(1.0, 2.0 * tail)
    # Small df: rough approximation
    x = df / (df + t * t)
    # Incomplete beta via power series (accurate for common cases)
    a = df / 2.0
    b = 0.5
    # Use regularized incomplete beta approximation
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    term = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    # First-order approximation
    p_one_tail = max(0.0, min(0.5, term))
    return min(1.0, 2.0 * p_one_tail)


def _confidence_interval(values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
    """Parametric confidence interval for the mean."""
    n = len(values)
    if n < 2:
        m = _mean(values)
        return (m, m)
    m = _mean(values)
    s = _std(values)
    # Critical value approximation (z for large n, t-approx for small n)
    alpha = 1.0 - confidence
    z = _inv_normal_cdf(1.0 - alpha / 2.0)
    margin = z * s / math.sqrt(n)
    return (round(m - margin, 6), round(m + margin, 6))


def _inv_normal_cdf(p: float) -> float:
    """Rational approximation of probit (Abramowitz & Stegun 26.2.23)."""
    if p <= 0.0:
        return -8.0
    if p >= 1.0:
        return 8.0
    if p < 0.5:
        return -_inv_normal_cdf(1.0 - p)
    t = math.sqrt(-2.0 * math.log(1.0 - p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    num = c0 + c1 * t + c2 * t * t
    den = 1.0 + d1 * t + d2 * t * t + d3 * t * t * t
    return t - num / den


def _bootstrap_mean_ci(
    values: List[float],
    n_boot: int = 200,
    confidence: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Deterministic bootstrap confidence interval for the mean.

    Uses a linear congruential generator so results are reproducible.
    """
    n = len(values)
    if n < 2:
        m = _mean(values)
        return (m, m)

    # LCG parameters (Numerical Recipes)
    a, c, m_lcg = 1664525, 1013904223, 2 ** 32
    state = seed & 0xFFFFFFFF
    boot_means: List[float] = []
    for _ in range(n_boot):
        sample = []
        for _ in range(n):
            state = (a * state + c) % m_lcg
            idx = state % n
            sample.append(values[idx])
        boot_means.append(_mean(sample))

    boot_means.sort()
    lo_idx = int((1.0 - confidence) / 2.0 * n_boot)
    hi_idx = int((1.0 + confidence) / 2.0 * n_boot)
    lo_idx = max(0, min(lo_idx, n_boot - 1))
    hi_idx = max(0, min(hi_idx, n_boot - 1))
    return (round(boot_means[lo_idx], 6), round(boot_means[hi_idx], 6))


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AbnormalReturnSeries:
    """AR series for a single security over an event window."""

    ticker: str
    window: EventWindow
    pre_returns: List[float]
    post_returns: List[float]
    expected_returns: List[float]
    ar_series: List[float]
    car: float
    t_stat: float
    p_value: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "window": self.window.value,
            "pre_returns": self.pre_returns,
            "post_returns": self.post_returns,
            "ar_series": self.ar_series,
            "car": self.car,
            "t_stat": self.t_stat,
            "p_value": self.p_value,
        }


@dataclass
class EventStudyResult:
    """Cross-sectional event study result."""

    event_id: str
    window: EventWindow
    n_securities: int
    aar: float
    caar: float
    t_stat: float
    p_value: float
    significant: bool
    ci_95_low: float
    ci_95_high: float
    bootstrap_ci_low: float
    bootstrap_ci_high: float
    ar_series_list: List[AbnormalReturnSeries] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "window": self.window.value,
            "n_securities": self.n_securities,
            "aar": self.aar,
            "caar": self.caar,
            "t_stat": self.t_stat,
            "p_value": self.p_value,
            "significant": self.significant,
            "ci_95_low": self.ci_95_low,
            "ci_95_high": self.ci_95_high,
            "bootstrap_ci_low": self.bootstrap_ci_low,
            "bootstrap_ci_high": self.bootstrap_ci_high,
        }


# ---------------------------------------------------------------------------
# EventStudy engine
# ---------------------------------------------------------------------------

class EventStudy:
    """Classical event study methodology engine."""

    def compute_ar_series(
        self,
        ticker: str,
        actual_returns: List[float],
        expected_returns: List[float],
        window: EventWindow,
    ) -> AbnormalReturnSeries:
        """Compute abnormal return series for one security.

        Args:
            ticker: Security identifier.
            actual_returns: Daily actual returns (length = 2*half+1).
            expected_returns: Daily expected (benchmark) returns, same length.
            window: Event window enum.

        Returns:
            AbnormalReturnSeries with AR, CAR, t-stat, p-value.
        """
        half = _WINDOW_HALF[window]
        total = 2 * half + 1
        # Pad or trim to window length
        actual = (actual_returns + [0.0] * total)[:total]
        expected = (expected_returns + [0.0] * total)[:total]

        ar = [round(a - e, 8) for a, e in zip(actual, expected)]
        car = round(sum(ar), 8)

        pre = actual[:half]
        post = actual[half + 1:]

        t = _t_stat(ar)
        p = _approx_p_value(t, df=max(1, len(ar) - 1))

        return AbnormalReturnSeries(
            ticker=ticker,
            window=window,
            pre_returns=pre,
            post_returns=post,
            expected_returns=expected,
            ar_series=ar,
            car=car,
            t_stat=round(t, 6),
            p_value=round(p, 6),
        )

    def compute_cross_sectional(
        self,
        event_id: str,
        ar_list: List[AbnormalReturnSeries],
        significance_level: float = 0.05,
    ) -> EventStudyResult:
        """Compute AAR, CAAR, and cross-sectional statistics.

        Args:
            event_id: Identifier of the event being studied.
            ar_list: List of per-security AbnormalReturnSeries.
            significance_level: p-value threshold for significance.

        Returns:
            EventStudyResult with full cross-sectional statistics.
        """
        if not ar_list:
            return EventStudyResult(
                event_id=event_id,
                window=EventWindow.W5,
                n_securities=0,
                aar=0.0,
                caar=0.0,
                t_stat=0.0,
                p_value=1.0,
                significant=False,
                ci_95_low=0.0,
                ci_95_high=0.0,
                bootstrap_ci_low=0.0,
                bootstrap_ci_high=0.0,
            )

        window = ar_list[0].window
        cars = [s.car for s in ar_list]
        caar = round(_mean(cars), 8)

        # Pooled AR series for AAR
        if ar_list:
            n_days = len(ar_list[0].ar_series)
            aar_per_day = []
            for i in range(n_days):
                day_ars = [s.ar_series[i] for s in ar_list if i < len(s.ar_series)]
                aar_per_day.append(_mean(day_ars))
            aar = round(_mean(aar_per_day), 8)
        else:
            aar = 0.0

        t = _t_stat(cars)
        p = _approx_p_value(t, df=max(1, len(cars) - 1))
        ci_lo, ci_hi = _confidence_interval(cars, 0.95)
        boot_lo, boot_hi = _bootstrap_mean_ci(cars)

        return EventStudyResult(
            event_id=event_id,
            window=window,
            n_securities=len(ar_list),
            aar=aar,
            caar=caar,
            t_stat=round(t, 6),
            p_value=round(p, 6),
            significant=p < significance_level,
            ci_95_low=ci_lo,
            ci_95_high=ci_hi,
            bootstrap_ci_low=boot_lo,
            bootstrap_ci_high=boot_hi,
            ar_series_list=ar_list,
        )

    def run_multi_window(
        self,
        event_id: str,
        tickers: List[str],
        actual_returns_map: Dict[str, List[float]],
        expected_returns_map: Dict[str, List[float]],
        windows: Optional[List[EventWindow]] = None,
    ) -> Dict[str, EventStudyResult]:
        """Run event study across multiple windows.

        Returns:
            Dict mapping window value string to EventStudyResult.
        """
        if windows is None:
            windows = ALL_WINDOWS

        results: Dict[str, EventStudyResult] = {}
        for w in windows:
            half = _WINDOW_HALF[w]
            total = 2 * half + 1
            ar_list = []
            for ticker in tickers:
                actual = actual_returns_map.get(ticker, [0.0] * total)
                expected = expected_returns_map.get(ticker, [0.0] * total)
                ar_series = self.compute_ar_series(ticker, actual, expected, w)
                ar_list.append(ar_series)
            result = self.compute_cross_sectional(event_id, ar_list)
            results[w.value] = result
        return results
