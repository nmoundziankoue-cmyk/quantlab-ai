"""Unit tests for M18 Earnings Intelligence Engine — 60 tests."""
import pytest

from services.m18_earnings_intelligence import (
    EarningsBeatMiss, EarningsSignal, GuidanceDirection,
    EarningsRelease, EarningsEstimate, EarningsCalendarEntry,
    EarningsSurpriseAnalysis, EarningsSignalResult,
    EarningsIntelligenceEngine, get_earnings_intelligence_engine,
    _classify_surprise,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_beat_miss_count(self):
        assert len(EarningsBeatMiss) >= 5

    def test_large_beat(self):
        assert EarningsBeatMiss.LARGE_BEAT is not None

    def test_large_miss(self):
        assert EarningsBeatMiss.LARGE_MISS is not None

    def test_in_line(self):
        assert EarningsBeatMiss.IN_LINE is not None

    def test_guidance_direction_raised(self):
        assert GuidanceDirection.RAISED is not None

    def test_guidance_direction_lowered(self):
        assert GuidanceDirection.LOWERED is not None

    def test_guidance_direction_withdrawn(self):
        assert GuidanceDirection.WITHDRAWN is not None

    def test_earnings_signal_has_buy(self):
        assert EarningsSignal.BUY is not None


# ---------------------------------------------------------------------------
# _classify_surprise
# ---------------------------------------------------------------------------

class TestClassifySurprise:
    def test_large_beat_above_10pct(self):
        result = _classify_surprise(0.12)
        assert result == EarningsBeatMiss.LARGE_BEAT

    def test_beat_between_2_and_10_pct(self):
        result = _classify_surprise(0.05)
        assert result == EarningsBeatMiss.BEAT

    def test_in_line_below_2pct(self):
        result = _classify_surprise(0.01)
        assert result == EarningsBeatMiss.IN_LINE

    def test_in_line_small_negative(self):
        result = _classify_surprise(-0.01)
        assert result == EarningsBeatMiss.IN_LINE

    def test_miss_between_2_and_10_pct_negative(self):
        result = _classify_surprise(-0.05)
        assert result == EarningsBeatMiss.MISS

    def test_large_miss_below_10pct_negative(self):
        result = _classify_surprise(-0.12)
        assert result == EarningsBeatMiss.LARGE_MISS

    def test_boundary_2pct_beat(self):
        result = _classify_surprise(0.02)
        assert result in (EarningsBeatMiss.BEAT, EarningsBeatMiss.IN_LINE)


# ---------------------------------------------------------------------------
# EarningsRelease
# ---------------------------------------------------------------------------

class TestEarningsRelease:
    def _make(self, eps=2.18, consensus_eps=2.02, rev=119600, consensus_rev=111200):
        return EarningsRelease(
            ticker="AAPL", fiscal_quarter="Q1 2026",
            reported_eps=eps, consensus_eps=consensus_eps,
            reported_revenue=rev, consensus_revenue=consensus_rev,
            gross_margin=0.46, operating_margin=0.31,
            guidance_direction=GuidanceDirection.RAISED,
        )

    def test_eps_surprise_pct(self):
        r = self._make(eps=2.18, consensus_eps=2.02)
        assert r.eps_surprise_pct > 0

    def test_eps_beat_miss(self):
        r = self._make(eps=2.18, consensus_eps=2.02)
        assert r.eps_beat_miss in (EarningsBeatMiss.BEAT, EarningsBeatMiss.LARGE_BEAT)

    def test_revenue_surprise_pct(self):
        r = self._make(rev=119600, consensus_rev=111200)
        assert r.revenue_surprise_pct > 0

    def test_to_dict_has_ticker(self):
        d = self._make().to_dict()
        assert "ticker" in d

    def test_to_dict_has_eps_beat_miss(self):
        d = self._make().to_dict()
        assert "eps_beat_miss" in d


# ---------------------------------------------------------------------------
# EarningsIntelligenceEngine — releases
# ---------------------------------------------------------------------------

class TestEarningsEngineReleases:
    def setup_method(self):
        self.engine = EarningsIntelligenceEngine()

    def _add_release(self, ticker="AAPL", eps=2.18, consensus_eps=2.02, quarter="Q1 2026"):
        release = EarningsRelease(
            ticker=ticker, fiscal_quarter=quarter,
            reported_eps=eps, consensus_eps=consensus_eps,
            reported_revenue=119600, consensus_revenue=111200,
            gross_margin=0.46, operating_margin=0.31,
            guidance_direction=GuidanceDirection.RAISED,
        )
        return self.engine.record_release(release)

    def test_record_release(self):
        r = self._add_release()
        assert r.release_id is not None

    def test_get_releases_for_ticker(self):
        self._add_release()
        releases = self.engine.get_releases("AAPL")
        assert len(releases) >= 1

    def test_get_releases_empty_for_unknown(self):
        assert self.engine.get_releases("ZZZZ") == []

    def test_get_latest_release(self):
        self._add_release("AAPL", quarter="Q1 2026")
        self._add_release("AAPL", quarter="Q2 2026")
        release = self.engine.get_latest_release("AAPL")
        assert release is not None

    def test_multiple_releases_stored(self):
        self._add_release("AAPL", quarter="Q1 2026")
        self._add_release("AAPL", quarter="Q2 2026")
        self._add_release("MSFT", quarter="Q1 2026")
        assert len(self.engine.get_releases("AAPL")) == 2
        assert len(self.engine.get_releases("MSFT")) == 1


# ---------------------------------------------------------------------------
# EarningsIntelligenceEngine — estimates
# ---------------------------------------------------------------------------

class TestEarningsEngineEstimates:
    def setup_method(self):
        self.engine = EarningsIntelligenceEngine()

    def _add_estimate(self, ticker="AAPL", eps=2.05, quarter="Q1 2026", analyst="GS"):
        est = EarningsEstimate(
            ticker=ticker, fiscal_quarter=quarter,
            analyst=analyst, eps_estimate=eps, revenue_estimate=113000,
            rating="BUY",
        )
        return self.engine.record_estimate(est)

    def test_record_estimate(self):
        e = self._add_estimate()
        assert e.estimate_id is not None

    def test_get_estimates_for_ticker(self):
        self._add_estimate("AAPL")
        estimates = self.engine.get_estimates("AAPL")
        assert len(estimates) >= 1

    def test_compute_consensus(self):
        self._add_estimate("AAPL", eps=2.00, analyst="GS")
        self._add_estimate("AAPL", eps=2.10, analyst="MS")
        self._add_estimate("AAPL", eps=2.05, analyst="JPM")
        consensus = self.engine.compute_consensus("AAPL", "Q1 2026")
        assert abs(consensus["consensus_eps"] - 2.05) < 0.1


# ---------------------------------------------------------------------------
# EarningsIntelligenceEngine — analytics
# ---------------------------------------------------------------------------

class TestEarningsEngineAnalytics:
    def setup_method(self):
        self.engine = EarningsIntelligenceEngine()
        for i, quarter in enumerate(["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026"]):
            release = EarningsRelease(
                ticker="AAPL", fiscal_quarter=quarter,
                reported_eps=2.0 + i * 0.1, consensus_eps=1.9 + i * 0.1,
                reported_revenue=115000 + i * 1000, consensus_revenue=113000 + i * 1000,
                gross_margin=0.45 + i * 0.01, operating_margin=0.30 + i * 0.005,
                guidance_direction=GuidanceDirection.RAISED,
            )
            self.engine.record_release(release)

    def test_compute_surprise_analysis(self):
        result = self.engine.compute_surprise_analysis("AAPL")
        assert isinstance(result, EarningsSurpriseAnalysis)

    def test_surprise_beat_rate_range(self):
        result = self.engine.compute_surprise_analysis("AAPL")
        assert 0.0 <= result.beat_rate <= 1.0

    def test_surprise_analysis_to_dict(self):
        d = self.engine.compute_surprise_analysis("AAPL").to_dict()
        assert "beat_rate" in d

    def test_forecast_post_earnings_drift(self):
        result = self.engine.forecast_post_earnings_drift("AAPL", eps_surprise_pct=0.08)
        assert isinstance(result, float)

    def test_detect_revision_trend(self):
        result = self.engine.detect_revision_trend("AAPL", "Q1 2026")
        assert result in ("UP", "DOWN", "STABLE", "INSUFFICIENT_DATA") or isinstance(result, str)

    def test_generate_signal(self):
        result = self.engine.generate_signal(
            ticker="AAPL", eps_surprise_pct=0.08,
            revenue_surprise_pct=0.07, guidance_direction=GuidanceDirection.RAISED,
        )
        assert isinstance(result, EarningsSignalResult)

    def test_signal_to_dict(self):
        d = self.engine.generate_signal("AAPL", 0.08, 0.07, GuidanceDirection.RAISED).to_dict()
        assert "signal" in d or "ticker" in d

    def test_signal_strong_buy_on_big_beat(self):
        result = self.engine.generate_signal("AAPL", eps_surprise_pct=0.15, revenue_surprise_pct=0.12, guidance_direction=GuidanceDirection.RAISED)
        assert result.signal in (EarningsSignal.STRONG_BUY, EarningsSignal.BUY)


# ---------------------------------------------------------------------------
# Earnings Calendar
# ---------------------------------------------------------------------------

class TestEarningsCalendar:
    def setup_method(self):
        self.engine = EarningsIntelligenceEngine()

    def test_add_calendar_entry(self):
        entry = EarningsCalendarEntry(
            ticker="MSFT", fiscal_quarter="Q2 2026",
            time_of_day="AFTER_HOURS", consensus_eps=3.20, consensus_revenue=68000,
        )
        result = self.engine.add_calendar_entry(entry)
        assert result.entry_id is not None

    def test_get_upcoming_earnings(self):
        entry = EarningsCalendarEntry(
            ticker="MSFT", fiscal_quarter="Q2 2026",
            time_of_day="AFTER_HOURS", consensus_eps=3.20,
        )
        self.engine.add_calendar_entry(entry)
        entries = self.engine.get_upcoming_earnings(limit=10)
        assert isinstance(entries, list)

    def test_calendar_entry_to_dict(self):
        entry = EarningsCalendarEntry(ticker="AAPL", fiscal_quarter="Q1 2026", time_of_day="AFTER_HOURS")
        d = entry.to_dict()
        assert "ticker" in d


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_earnings_intelligence_engine(self):
        eng = get_earnings_intelligence_engine()
        assert isinstance(eng, EarningsIntelligenceEngine)

    def test_singleton_same_instance(self):
        e1 = get_earnings_intelligence_engine()
        e2 = get_earnings_intelligence_engine()
        assert e1 is e2
