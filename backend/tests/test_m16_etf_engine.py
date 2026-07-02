"""M16 tests — ETF Intelligence Engine."""
import pytest
from services.etf_engine import (
    ETFEngine, ETFProfile, ETFHolding, SectorExposure, CountryExposure,
    ETFOverlap, TrackingDifference, TrackingQuality, FlowEstimate, FlowDirection,
    get_etf_engine,
)

ENG = ETFEngine()

HOLDINGS = [
    ETFHolding("AAPL", "Apple", 0.15, "Information Technology", "US", "large", "equity"),
    ETFHolding("MSFT", "Microsoft", 0.12, "Information Technology", "US", "large", "equity"),
    ETFHolding("JPM",  "JPMorgan", 0.08, "Financials", "US", "large", "equity"),
    ETFHolding("XOM",  "ExxonMobil", 0.06, "Energy", "US", "large", "equity"),
    ETFHolding("NESN", "Nestle", 0.05, "Consumer Staples", "CH", "large", "equity"),
]

SPY = ETFProfile("SPY", "SPDR S&P 500", 0.0009, 450000, "S&P 500", HOLDINGS, "1993-01-22", "SSGA")
QQQ = ETFProfile("QQQ", "Invesco QQQ", 0.0020, 200000, "NASDAQ-100", [
    ETFHolding("AAPL", "Apple", 0.10, "Information Technology", "US", "large", "equity"),
    ETFHolding("NVDA", "NVIDIA", 0.08, "Information Technology", "US", "large", "equity"),
    ETFHolding("AMZN", "Amazon", 0.06, "Consumer Discretionary", "US", "large", "equity"),
])

RETS_ETF = [0.01, -0.008, 0.012, 0.005, -0.006, 0.009, 0.007, -0.004, 0.011, 0.003]
RETS_BENCH = [0.009, -0.007, 0.011, 0.004, -0.005, 0.008, 0.006, -0.003, 0.010, 0.002]


class TestSectorExposure:
    def test_returns_sector_exposure(self):
        se = ENG.sector_exposure(SPY)
        assert isinstance(se, SectorExposure)

    def test_etf_ticker(self):
        se = ENG.sector_exposure(SPY)
        assert se.etf_ticker == "SPY"

    def test_sectors_dict_nonempty(self):
        se = ENG.sector_exposure(SPY)
        assert len(se.sectors) > 0

    def test_top_sector_is_it(self):
        se = ENG.sector_exposure(SPY)
        assert se.top_sector == "Information Technology"

    def test_weight_sums_close_to_total(self):
        se = ENG.sector_exposure(SPY)
        total_holding_weight = sum(h.weight for h in SPY.holdings)
        assert abs(sum(se.sectors.values()) - total_holding_weight) < 1e-6

    def test_concentration_ratio_positive(self):
        se = ENG.sector_exposure(SPY)
        assert se.concentration_ratio > 0

    def test_to_dict(self):
        d = ENG.sector_exposure(SPY).to_dict()
        assert "sectors" in d and "top_sector" in d


class TestCountryExposure:
    def test_returns_country_exposure(self):
        ce = ENG.country_exposure(SPY)
        assert isinstance(ce, CountryExposure)

    def test_us_is_top(self):
        ce = ENG.country_exposure(SPY)
        assert ce.top_country == "US"

    def test_domestic_weight_positive(self):
        ce = ENG.country_exposure(SPY)
        assert ce.domestic_weight > 0

    def test_to_dict(self):
        d = ENG.country_exposure(SPY).to_dict()
        assert "countries" in d and "top_country" in d


class TestMarketCapExposure:
    def test_returns_dict(self):
        cap = ENG.market_cap_exposure(SPY)
        assert isinstance(cap, dict)

    def test_large_bucket_present(self):
        cap = ENG.market_cap_exposure(SPY)
        assert "large" in cap


class TestETFOverlap:
    def test_returns_etf_overlap(self):
        ov = ENG.compute_overlap(SPY, QQQ)
        assert isinstance(ov, ETFOverlap)

    def test_common_tickers_includes_aapl(self):
        ov = ENG.compute_overlap(SPY, QQQ)
        assert "AAPL" in ov.common_tickers

    def test_jaccard_in_range(self):
        ov = ENG.compute_overlap(SPY, QQQ)
        assert 0.0 <= ov.jaccard_similarity <= 1.0

    def test_overlap_weight_positive(self):
        ov = ENG.compute_overlap(SPY, QQQ)
        assert ov.overlap_weight > 0

    def test_to_dict(self):
        d = ENG.compute_overlap(SPY, QQQ).to_dict()
        assert "common_tickers" in d and "n_common" in d

    def test_multi_fund_overlap(self):
        mat = ENG.multi_fund_overlap([SPY, QQQ])
        assert "tickers" in mat and "matrix" in mat

    def test_multi_fund_diagonal_one(self):
        mat = ENG.multi_fund_overlap([SPY, QQQ])
        assert mat["matrix"][0][0] == 1.0
        assert mat["matrix"][1][1] == 1.0


class TestTrackingDifference:
    def test_returns_tracking_difference(self):
        td = ENG.tracking_difference(SPY, RETS_ETF, RETS_BENCH)
        assert isinstance(td, TrackingDifference)

    def test_etf_ticker(self):
        td = ENG.tracking_difference(SPY, RETS_ETF, RETS_BENCH)
        assert td.etf_ticker == "SPY"

    def test_tracking_error_nonneg(self):
        td = ENG.tracking_difference(SPY, RETS_ETF, RETS_BENCH)
        assert td.tracking_error >= 0

    def test_quality_is_excellent_small_td(self):
        # Make very small tracking difference
        same = [0.01] * 10
        td = ENG.tracking_difference(SPY, same, same)
        assert td.quality == TrackingQuality.EXCELLENT

    def test_to_dict(self):
        d = ENG.tracking_difference(SPY, RETS_ETF, RETS_BENCH).to_dict()
        assert "tracking_difference" in d and "quality" in d


class TestFlowEstimate:
    def test_returns_flow_estimate(self):
        fe = ENG.estimate_flows(SPY, 100000, 103000, 0.01)
        assert isinstance(fe, FlowEstimate)

    def test_inflow_when_aum_grows_more_than_returns(self):
        fe = ENG.estimate_flows(SPY, 100000, 108000, 0.01)
        assert fe.direction == FlowDirection.INFLOW

    def test_outflow_when_aum_falls_despite_positive_return(self):
        fe = ENG.estimate_flows(SPY, 100000, 98000, 0.02)
        assert fe.direction == FlowDirection.OUTFLOW

    def test_to_dict(self):
        d = ENG.estimate_flows(SPY, 100000, 102000, 0.01).to_dict()
        assert "net_flow_usd" in d and "direction" in d


class TestConcentration:
    def test_hhi_nonneg(self):
        hhi = ENG.herfindahl_index(SPY)
        assert hhi > 0

    def test_effective_n_positive(self):
        eff_n = ENG.effective_number_of_holdings(SPY)
        assert eff_n > 0

    def test_top_n_holdings_count(self):
        top = ENG.top_n_holdings(SPY, n=3)
        assert len(top) == 3

    def test_top_holdings_sorted(self):
        top = ENG.top_n_holdings(SPY, n=len(SPY.holdings))
        weights = [h.weight for h in top]
        assert weights == sorted(weights, reverse=True)


class TestFundSummary:
    def test_returns_dict(self):
        s = ENG.fund_summary(SPY)
        assert isinstance(s, dict)

    def test_has_ticker(self):
        s = ENG.fund_summary(SPY)
        assert s["ticker"] == "SPY"

    def test_has_hhi(self):
        s = ENG.fund_summary(SPY)
        assert "hhi" in s


class TestSingleton:
    def test_singleton(self):
        a = get_etf_engine()
        b = get_etf_engine()
        assert a is b
