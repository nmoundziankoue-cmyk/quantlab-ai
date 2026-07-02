"""M18 — Earnings Intelligence: earnings data management, surprise analysis, and forecasting.

Stores earnings releases, computes surprise scores, tracks estimate revision
momentum, models post-earnings drift, generates earnings-event trading signals,
and maintains an earnings calendar.

Pure Python, no external libraries.
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EarningsBeatMiss(str, Enum):
    """Whether the reported figure beat, met, or missed consensus."""
    LARGE_BEAT = "LARGE_BEAT"
    BEAT = "BEAT"
    IN_LINE = "IN_LINE"
    MISS = "MISS"
    LARGE_MISS = "LARGE_MISS"


class EarningsSignal(str, Enum):
    """Trading signal generated from an earnings event."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class GuidanceDirection(str, Enum):
    """Direction of management earnings guidance."""
    RAISED = "RAISED"
    MAINTAINED = "MAINTAINED"
    LOWERED = "LOWERED"
    WITHDRAWN = "WITHDRAWN"
    NOT_PROVIDED = "NOT_PROVIDED"


# ---------------------------------------------------------------------------
# Helper math
# ---------------------------------------------------------------------------

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mu = _mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / (n - 1))


def _classify_surprise(pct: float) -> EarningsBeatMiss:
    if pct >= 0.10:
        return EarningsBeatMiss.LARGE_BEAT
    if pct >= 0.02:
        return EarningsBeatMiss.BEAT
    if pct <= -0.10:
        return EarningsBeatMiss.LARGE_MISS
    if pct <= -0.02:
        return EarningsBeatMiss.MISS
    return EarningsBeatMiss.IN_LINE


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EarningsRelease:
    """A single quarterly earnings release.

    Args:
        release_id: Unique identifier.
        ticker: Instrument symbol.
        fiscal_quarter: Quarter label (e.g. "Q1 2026").
        reported_eps: Reported EPS.
        consensus_eps: Analyst consensus EPS.
        reported_revenue: Reported revenue (USD millions).
        consensus_revenue: Analyst consensus revenue.
        gross_margin: Gross margin fraction.
        operating_margin: Operating margin fraction.
        net_income_usd_m: Net income in USD millions.
        eps_surprise_pct: (reported - consensus) / |consensus|.
        revenue_surprise_pct: (reported - consensus) / |consensus|.
        eps_beat_miss: Beat/miss classification.
        revenue_beat_miss: Beat/miss classification.
        guidance_direction: Management guidance update.
        guidance_eps_low: Low end of EPS guidance range.
        guidance_eps_high: High end of EPS guidance range.
        post_earnings_drift_1d: Observed 1-day stock return after release.
        release_time: UTC timestamp of release.
    """

    release_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    fiscal_quarter: str = ""
    reported_eps: float = 0.0
    consensus_eps: float = 0.0
    reported_revenue: float = 0.0
    consensus_revenue: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_income_usd_m: float = 0.0
    eps_surprise_pct: float = 0.0
    revenue_surprise_pct: float = 0.0
    eps_beat_miss: EarningsBeatMiss = EarningsBeatMiss.IN_LINE
    revenue_beat_miss: EarningsBeatMiss = EarningsBeatMiss.IN_LINE
    guidance_direction: GuidanceDirection = GuidanceDirection.NOT_PROVIDED
    guidance_eps_low: float = 0.0
    guidance_eps_high: float = 0.0
    post_earnings_drift_1d: float = 0.0
    release_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.consensus_eps != 0.0:
            self.eps_surprise_pct = (
                (self.reported_eps - self.consensus_eps) / abs(self.consensus_eps)
            )
        if self.consensus_revenue != 0.0:
            self.revenue_surprise_pct = (
                (self.reported_revenue - self.consensus_revenue)
                / abs(self.consensus_revenue)
            )
        self.eps_beat_miss = _classify_surprise(self.eps_surprise_pct)
        self.revenue_beat_miss = _classify_surprise(self.revenue_surprise_pct)

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "release_id": self.release_id,
            "ticker": self.ticker,
            "fiscal_quarter": self.fiscal_quarter,
            "reported_eps": round(self.reported_eps, 4),
            "consensus_eps": round(self.consensus_eps, 4),
            "reported_revenue": round(self.reported_revenue, 2),
            "consensus_revenue": round(self.consensus_revenue, 2),
            "gross_margin": round(self.gross_margin, 4),
            "operating_margin": round(self.operating_margin, 4),
            "net_income_usd_m": round(self.net_income_usd_m, 2),
            "eps_surprise_pct": round(self.eps_surprise_pct, 6),
            "revenue_surprise_pct": round(self.revenue_surprise_pct, 6),
            "eps_beat_miss": self.eps_beat_miss.value,
            "revenue_beat_miss": self.revenue_beat_miss.value,
            "guidance_direction": self.guidance_direction.value,
            "guidance_eps_low": round(self.guidance_eps_low, 4),
            "guidance_eps_high": round(self.guidance_eps_high, 4),
            "post_earnings_drift_1d": round(self.post_earnings_drift_1d, 6),
            "release_time": self.release_time.isoformat(),
        }


@dataclass
class EarningsEstimate:
    """An analyst estimate for a future earnings period.

    Args:
        estimate_id: Unique identifier.
        ticker: Instrument symbol.
        fiscal_quarter: Target quarter.
        analyst: Analyst firm name.
        eps_estimate: EPS estimate.
        revenue_estimate: Revenue estimate (USD millions).
        price_target: 12-month price target.
        rating: Buy / Hold / Sell.
        estimate_date: Date estimate was published.
    """

    estimate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    fiscal_quarter: str = ""
    analyst: str = ""
    eps_estimate: float = 0.0
    revenue_estimate: float = 0.0
    price_target: float = 0.0
    rating: str = "HOLD"
    estimate_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def analyst_firm(self) -> str:
        """Alias for analyst."""
        return self.analyst

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "estimate_id": self.estimate_id,
            "ticker": self.ticker,
            "fiscal_quarter": self.fiscal_quarter,
            "analyst": self.analyst,
            "eps_estimate": round(self.eps_estimate, 4),
            "revenue_estimate": round(self.revenue_estimate, 2),
            "price_target": round(self.price_target, 2),
            "rating": self.rating,
            "estimate_date": self.estimate_date.isoformat(),
        }


@dataclass
class EarningsCalendarEntry:
    """A scheduled upcoming earnings release.

    Args:
        entry_id: Unique identifier.
        ticker: Instrument symbol.
        fiscal_quarter: Expected quarter.
        expected_date: Estimated release date.
        time_of_day: BMO (before-market-open) or AMC (after-market-close).
        consensus_eps: Current consensus EPS.
        consensus_revenue: Current consensus revenue.
        num_estimates: Number of analyst estimates in consensus.
    """

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    fiscal_quarter: str = ""
    expected_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    time_of_day: str = "AMC"
    consensus_eps: float = 0.0
    consensus_revenue: float = 0.0
    num_estimates: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "entry_id": self.entry_id,
            "ticker": self.ticker,
            "fiscal_quarter": self.fiscal_quarter,
            "expected_date": self.expected_date.isoformat(),
            "time_of_day": self.time_of_day,
            "consensus_eps": round(self.consensus_eps, 4),
            "consensus_revenue": round(self.consensus_revenue, 2),
            "num_estimates": self.num_estimates,
        }


@dataclass
class EarningsSurpriseAnalysis:
    """Statistical analysis of a company's historical earnings surprises.

    Args:
        ticker: Instrument symbol.
        beat_rate: Fraction of quarters that beat EPS consensus.
        avg_eps_surprise_pct: Average EPS surprise percent.
        avg_revenue_surprise_pct: Average revenue surprise percent.
        consistency_score: 0-100 score for how consistently the company beats.
        post_earnings_drift_avg: Average 1-day post-earnings return.
        recent_quarters: List of (quarter, eps_surprise_pct) pairs.
    """

    ticker: str
    beat_rate: float
    avg_eps_surprise_pct: float
    avg_revenue_surprise_pct: float
    consistency_score: float
    post_earnings_drift_avg: float
    recent_quarters: List[Tuple[str, float]]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "ticker": self.ticker,
            "beat_rate": round(self.beat_rate, 4),
            "avg_eps_surprise_pct": round(self.avg_eps_surprise_pct, 4),
            "avg_revenue_surprise_pct": round(self.avg_revenue_surprise_pct, 4),
            "consistency_score": round(self.consistency_score, 2),
            "post_earnings_drift_avg": round(self.post_earnings_drift_avg, 4),
            "recent_quarters": [[q, round(s, 4)] for q, s in self.recent_quarters],
        }


@dataclass
class EarningsSignalResult:
    """A trading signal generated from earnings analytics.

    Args:
        signal_id: Unique identifier.
        ticker: Target symbol.
        signal: Trading signal.
        confidence: Model confidence (0-1).
        factors: Dict of factor name → contribution to signal.
        rationale: Plain-English explanation.
        generated_at: Signal time.
    """

    signal_id: str
    ticker: str
    signal: EarningsSignal
    confidence: float
    factors: Dict[str, float]
    rationale: str
    generated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "signal_id": self.signal_id,
            "ticker": self.ticker,
            "signal": self.signal.value,
            "confidence": round(self.confidence, 4),
            "factors": {k: round(v, 4) for k, v in self.factors.items()},
            "rationale": self.rationale,
            "generated_at": self.generated_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Earnings Intelligence Engine
# ---------------------------------------------------------------------------

class EarningsIntelligenceEngine:
    """Comprehensive earnings data management and analytics engine."""

    def __init__(self) -> None:
        self._releases: Dict[str, List[EarningsRelease]] = defaultdict(list)
        self._estimates: Dict[str, List[EarningsEstimate]] = defaultdict(list)
        self._calendar: List[EarningsCalendarEntry] = []

    # ------------------------------------------------------------------
    # Release management
    # ------------------------------------------------------------------

    def record_release(self, release: "EarningsRelease") -> "EarningsRelease":
        """Store an EarningsRelease.

        Args:
            release: Pre-built EarningsRelease instance.

        Returns:
            The stored release.
        """
        t = release.ticker.upper()
        release.ticker = t
        self._releases[t].append(release)
        return release

    def get_latest_release(self, ticker: str) -> Optional[EarningsRelease]:
        """Return the most recent release for a ticker.

        Args:
            ticker: Instrument symbol.

        Returns:
            EarningsRelease or None.
        """
        releases = self._releases.get(ticker.upper(), [])
        return releases[-1] if releases else None

    def get_releases(
        self, ticker: str, limit: int = 20
    ) -> List[EarningsRelease]:
        """Return historical earnings releases for a ticker (newest first).

        Args:
            ticker: Instrument symbol.
            limit: Maximum records.

        Returns:
            List of EarningsRelease.
        """
        t = ticker.upper()
        return list(reversed(self._releases.get(t, [])))[:limit]

    # ------------------------------------------------------------------
    # Estimates
    # ------------------------------------------------------------------

    def record_estimate(self, estimate: "EarningsEstimate") -> "EarningsEstimate":
        """Store an EarningsEstimate.

        Args:
            estimate: Pre-built EarningsEstimate instance.

        Returns:
            The stored estimate.
        """
        t = estimate.ticker.upper()
        estimate.ticker = t
        self._estimates[t].append(estimate)
        return estimate

    def add_estimate(
        self,
        ticker: str,
        fiscal_quarter: str,
        analyst_firm: str,
        eps_estimate: float,
        revenue_estimate: float,
        price_target: float = 0.0,
        rating: str = "HOLD",
    ) -> EarningsEstimate:
        """Add an analyst earnings estimate via keyword arguments.

        Args:
            ticker: Instrument symbol.
            fiscal_quarter: Target quarter.
            analyst_firm: Analyst firm name.
            eps_estimate: EPS estimate.
            revenue_estimate: Revenue estimate.
            price_target: 12-month price target.
            rating: Buy / Hold / Sell.

        Returns:
            EarningsEstimate.
        """
        t = ticker.upper()
        est = EarningsEstimate(
            ticker=t,
            fiscal_quarter=fiscal_quarter,
            analyst=analyst_firm,
            eps_estimate=eps_estimate,
            revenue_estimate=revenue_estimate,
            price_target=price_target,
            rating=rating,
        )
        self._estimates[t].append(est)
        return est

    def get_estimates(
        self, ticker: str, fiscal_quarter: Optional[str] = None
    ) -> List[EarningsEstimate]:
        """Return estimates for a ticker.

        Args:
            ticker: Instrument symbol.
            fiscal_quarter: Optional quarter filter.

        Returns:
            List of EarningsEstimate.
        """
        t = ticker.upper()
        ests = self._estimates.get(t, [])
        if fiscal_quarter:
            ests = [e for e in ests if e.fiscal_quarter == fiscal_quarter]
        return list(ests)

    def get_consensus(
        self, ticker: str, fiscal_quarter: str
    ) -> Dict[str, float]:
        """Compute consensus estimates for a ticker and quarter.

        Args:
            ticker: Instrument symbol.
            fiscal_quarter: Target quarter.

        Returns:
            Dict with consensus_eps, consensus_revenue, num_estimates.
        """
        t = ticker.upper()
        ests = [e for e in self._estimates.get(t, []) if e.fiscal_quarter == fiscal_quarter]
        if not ests:
            return {"consensus_eps": 0.0, "consensus_revenue": 0.0, "num_estimates": 0}
        avg_eps = _mean([e.eps_estimate for e in ests])
        avg_rev = _mean([e.revenue_estimate for e in ests])
        return {
            "consensus_eps": round(avg_eps, 4),
            "consensus_revenue": round(avg_rev, 2),
            "num_estimates": len(ests),
        }

    def compute_consensus(self, ticker: str, fiscal_quarter: str) -> Dict[str, float]:
        """Alias for get_consensus.

        Args:
            ticker: Instrument symbol.
            fiscal_quarter: Target quarter.

        Returns:
            Dict with consensus_eps, consensus_revenue, num_estimates.
        """
        return self.get_consensus(ticker, fiscal_quarter)

    def get_estimate_revision_trend(
        self, ticker: str, fiscal_quarter: str
    ) -> str:
        """Detect whether analyst estimates are being revised up, down, or flat.

        Args:
            ticker: Instrument symbol.
            fiscal_quarter: Target quarter.

        Returns:
            "UPWARD", "DOWNWARD", or "STABLE".
        """
        t = ticker.upper()
        ests = sorted(
            [e for e in self._estimates.get(t, []) if e.fiscal_quarter == fiscal_quarter],
            key=lambda e: e.estimate_date,
        )
        if len(ests) < 2:
            return "STABLE"
        eps_list = [e.eps_estimate for e in ests]
        first_half = _mean(eps_list[:len(eps_list)//2])
        second_half = _mean(eps_list[len(eps_list)//2:])
        if second_half > first_half * 1.01:
            return "UPWARD"
        if second_half < first_half * 0.99:
            return "DOWNWARD"
        return "STABLE"

    # ------------------------------------------------------------------
    # Surprise analysis
    # ------------------------------------------------------------------

    def compute_surprise_analysis(self, ticker: str) -> EarningsSurpriseAnalysis:
        """Alias for analyse_surprise_history.

        Args:
            ticker: Instrument symbol.

        Returns:
            EarningsSurpriseAnalysis.
        """
        return self.analyse_surprise_history(ticker)

    def detect_revision_trend(self, ticker: str, fiscal_quarter: str) -> str:
        """Alias for get_estimate_revision_trend.

        Args:
            ticker: Instrument symbol.
            fiscal_quarter: Target quarter.

        Returns:
            Trend string.
        """
        result = self.get_estimate_revision_trend(ticker, fiscal_quarter)
        if result == "STABLE" and not self._estimates.get(ticker.upper()):
            return "INSUFFICIENT_DATA"
        return result

    def analyse_surprise_history(self, ticker: str) -> EarningsSurpriseAnalysis:
        """Analyse a company's historical earnings surprise pattern.

        Args:
            ticker: Instrument symbol.

        Returns:
            EarningsSurpriseAnalysis.

        Raises:
            ValueError: If no releases found.
        """
        t = ticker.upper()
        releases = self._releases.get(t, [])
        if not releases:
            return EarningsSurpriseAnalysis(
                ticker=t, beat_rate=0.0, avg_eps_surprise_pct=0.0,
                avg_revenue_surprise_pct=0.0, post_earnings_drift_avg=0.0,
                consistency_score=0.0, recent_quarters=[],
            )
        beats = sum(1 for r in releases if r.eps_beat_miss in {
            EarningsBeatMiss.BEAT, EarningsBeatMiss.LARGE_BEAT})
        beat_rate = beats / len(releases)
        avg_eps_surprise = _mean([r.eps_surprise_pct for r in releases])
        avg_rev_surprise = _mean([r.revenue_surprise_pct for r in releases])
        avg_drift = _mean([r.post_earnings_drift_1d for r in releases])
        std_surprise = _std([r.eps_surprise_pct for r in releases])
        consistency = max(0.0, min(100.0, beat_rate * 70 + (1 / (1 + std_surprise * 10)) * 30))
        recent = sorted(releases, key=lambda r: r.release_time, reverse=True)[:8]
        recent_quarters = [(r.fiscal_quarter, r.eps_surprise_pct) for r in recent]
        return EarningsSurpriseAnalysis(
            ticker=t,
            beat_rate=beat_rate,
            avg_eps_surprise_pct=avg_eps_surprise,
            avg_revenue_surprise_pct=avg_rev_surprise,
            consistency_score=consistency,
            post_earnings_drift_avg=avg_drift,
            recent_quarters=recent_quarters,
        )

    # ------------------------------------------------------------------
    # Post-earnings drift forecast
    # ------------------------------------------------------------------

    def forecast_post_earnings_drift(
        self, ticker: str, eps_surprise_pct: float
    ) -> float:
        """Forecast expected 1-day return after an earnings release.

        Uses a linear regression over historical surprise vs drift pairs.

        Args:
            ticker: Instrument symbol.
            eps_surprise_pct: Expected EPS surprise percent.

        Returns:
            Predicted 1-day return as fraction.
        """
        t = ticker.upper()
        releases = self._releases.get(t, [])
        if len(releases) < 3:
            return eps_surprise_pct * 0.3
        xs = [r.eps_surprise_pct for r in releases]
        ys = [r.post_earnings_drift_1d for r in releases]
        n = len(xs)
        mu_x = _mean(xs)
        mu_y = _mean(ys)
        cov = sum((xs[i] - mu_x) * (ys[i] - mu_y) for i in range(n)) / n
        var_x = sum((x - mu_x) ** 2 for x in xs) / n
        slope = cov / var_x if var_x > 0 else 0.0
        intercept = mu_y - slope * mu_x
        return slope * eps_surprise_pct + intercept

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(
        self,
        ticker: str,
        eps_surprise_pct: float = 0.0,
        revenue_surprise_pct: float = 0.0,
        guidance_direction: GuidanceDirection = GuidanceDirection.NOT_PROVIDED,
    ) -> EarningsSignalResult:
        """Generate an earnings-event trading signal.

        Args:
            ticker: Instrument symbol.
            eps_surprise_pct: EPS surprise percent.
            revenue_surprise_pct: Revenue surprise percent.
            guidance_direction: Management guidance update.

        Returns:
            EarningsSignalResult.
        """
        t = ticker.upper()
        factors: Dict[str, float] = {
            "eps_surprise": eps_surprise_pct,
            "revenue_surprise": revenue_surprise_pct,
        }
        guidance_score = {
            GuidanceDirection.RAISED: 0.3,
            GuidanceDirection.MAINTAINED: 0.05,
            GuidanceDirection.LOWERED: -0.3,
            GuidanceDirection.WITHDRAWN: -0.2,
            GuidanceDirection.NOT_PROVIDED: 0.0,
        }[guidance_direction]
        factors["guidance"] = guidance_score
        composite = (eps_surprise_pct * 0.50 + revenue_surprise_pct * 0.25
                     + guidance_score * 0.25)
        if composite >= 0.10:
            signal = EarningsSignal.STRONG_BUY
        elif composite >= 0.03:
            signal = EarningsSignal.BUY
        elif composite <= -0.10:
            signal = EarningsSignal.STRONG_SELL
        elif composite <= -0.03:
            signal = EarningsSignal.SELL
        else:
            signal = EarningsSignal.HOLD
        confidence = min(0.95, 0.4 + abs(composite) * 2.0)
        rationale = (
            f"{t} earnings signal: EPS surprise={eps_surprise_pct:.2%}, "
            f"Revenue surprise={revenue_surprise_pct:.2%}, "
            f"Guidance={guidance_direction.value}. "
            f"Composite={composite:.3f}."
        )
        return EarningsSignalResult(
            signal_id=str(uuid.uuid4()),
            ticker=t,
            signal=signal,
            confidence=confidence,
            factors=factors,
            rationale=rationale,
            generated_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------

    def add_calendar_entry(self, entry: "EarningsCalendarEntry") -> "EarningsCalendarEntry":
        """Add a pre-built EarningsCalendarEntry to the calendar.

        Args:
            entry: Calendar entry to store.

        Returns:
            The stored entry.
        """
        self._calendar.append(entry)
        return entry

    def schedule_earnings(
        self,
        ticker: str,
        fiscal_quarter: str,
        expected_date: datetime,
        time_of_day: str = "AMC",
        consensus_eps: float = 0.0,
        consensus_revenue: float = 0.0,
        num_estimates: int = 0,
    ) -> EarningsCalendarEntry:
        """Add an earnings event to the calendar.

        Args:
            ticker: Instrument symbol.
            fiscal_quarter: Quarter label.
            expected_date: Estimated release date.
            time_of_day: BMO or AMC.
            consensus_eps: Consensus EPS.
            consensus_revenue: Consensus revenue.
            num_estimates: Number of analyst estimates.

        Returns:
            EarningsCalendarEntry.
        """
        entry = EarningsCalendarEntry(
            entry_id=str(uuid.uuid4()),
            ticker=ticker.upper(),
            fiscal_quarter=fiscal_quarter,
            expected_date=expected_date,
            time_of_day=time_of_day.upper(),
            consensus_eps=consensus_eps,
            consensus_revenue=consensus_revenue,
            num_estimates=num_estimates,
        )
        self._calendar.append(entry)
        return entry

    def get_upcoming_earnings(
        self, limit: int = 20, ticker: Optional[str] = None
    ) -> List[EarningsCalendarEntry]:
        """Return earnings calendar entries sorted by date.

        Args:
            limit: Maximum entries.
            ticker: Optional ticker filter.

        Returns:
            List of EarningsCalendarEntry.
        """
        events = list(self._calendar)
        if ticker:
            t = ticker.upper()
            events = [e for e in events if e.ticker == t]
        events.sort(key=lambda e: e.expected_date)
        return events[:limit]

    def get_earnings_calendar(self, limit: int = 50) -> List[EarningsCalendarEntry]:
        """Return all scheduled earnings events.

        Args:
            limit: Maximum entries.

        Returns:
            List sorted by date.
        """
        return sorted(self._calendar, key=lambda e: e.expected_date)[:limit]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[EarningsIntelligenceEngine] = None


def get_earnings_intelligence_engine() -> EarningsIntelligenceEngine:
    """Return the singleton EarningsIntelligenceEngine.

    Returns:
        Shared EarningsIntelligenceEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = EarningsIntelligenceEngine()
    return _default_engine
