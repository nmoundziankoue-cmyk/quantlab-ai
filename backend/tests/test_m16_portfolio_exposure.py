"""M16 tests — Portfolio Exposure Engine."""
import pytest
from services.portfolio_exposure import (
    PortfolioExposureEngine, Holding, ExposureBreakdown,
    FactorExposureReport, ConcentrationMetrics, RiskExposure,
    get_portfolio_exposure_engine,
)

ENG = PortfolioExposureEngine()

PORTFOLIO = [
    Holding("AAPL", 0.15, sector="Information Technology", country="US", currency="USD",
            asset_class="equity", market_cap_bucket="large", beta=1.2,
            factor_exposures={"momentum": 0.8, "quality": 0.5}),
    Holding("MSFT", 0.12, sector="Information Technology", country="US", currency="USD",
            asset_class="equity", market_cap_bucket="large", beta=1.1,
            factor_exposures={"momentum": 0.6, "value": -0.3}),
    Holding("JPM",  0.10, sector="Financials", country="US", currency="USD",
            asset_class="equity", market_cap_bucket="large", beta=1.4,
            factor_exposures={"value": 0.7}),
    Holding("NESN", 0.08, sector="Consumer Staples", country="CH", currency="CHF",
            asset_class="equity", market_cap_bucket="large", beta=0.6,
            factor_exposures={"quality": 0.9}),
    Holding("UST10Y", 0.20, sector="Government Bond", country="US", currency="USD",
            asset_class="bond", duration=8.5, beta=0.0),
    Holding("GLD",  0.10, sector="Commodities", country="US", currency="USD",
            asset_class="commodity", beta=0.2),
    Holding("BTC",  0.05, sector="Crypto", country="US", currency="USD",
            asset_class="crypto", beta=1.8),
    Holding("CASH", 0.20, sector="Cash", country="US", currency="USD",
            asset_class="cash", beta=0.0),
]


class TestSectorExposure:
    def test_returns_exposure_breakdown(self):
        result = ENG.sector_exposure(PORTFOLIO)
        assert isinstance(result, ExposureBreakdown)

    def test_dimension_is_sector(self):
        result = ENG.sector_exposure(PORTFOLIO)
        assert result.dimension == "sector"

    def test_it_sector_present(self):
        result = ENG.sector_exposure(PORTFOLIO)
        assert "Information Technology" in result.breakdown

    def test_top_category_is_highest(self):
        result = ENG.sector_exposure(PORTFOLIO)
        top_w = result.breakdown[result.top_category]
        for w in result.breakdown.values():
            assert top_w >= w

    def test_hhi_positive(self):
        result = ENG.sector_exposure(PORTFOLIO)
        assert result.herfindahl_index > 0

    def test_n_categories(self):
        result = ENG.sector_exposure(PORTFOLIO)
        assert result.n_categories == len(result.breakdown)

    def test_to_dict(self):
        d = ENG.sector_exposure(PORTFOLIO).to_dict()
        assert "breakdown" in d and "top_category" in d


class TestCountryExposure:
    def test_returns_exposure_breakdown(self):
        result = ENG.country_exposure(PORTFOLIO)
        assert isinstance(result, ExposureBreakdown)

    def test_us_present(self):
        result = ENG.country_exposure(PORTFOLIO)
        assert "US" in result.breakdown

    def test_ch_present(self):
        result = ENG.country_exposure(PORTFOLIO)
        assert "CH" in result.breakdown

    def test_to_dict(self):
        d = ENG.country_exposure(PORTFOLIO).to_dict()
        assert "dimension" in d and d["dimension"] == "country"


class TestCurrencyExposure:
    def test_returns_exposure_breakdown(self):
        result = ENG.currency_exposure(PORTFOLIO)
        assert isinstance(result, ExposureBreakdown)

    def test_usd_dominant(self):
        result = ENG.currency_exposure(PORTFOLIO)
        assert result.top_category == "USD"

    def test_chf_present(self):
        result = ENG.currency_exposure(PORTFOLIO)
        assert "CHF" in result.breakdown


class TestAssetClassExposure:
    def test_returns_exposure_breakdown(self):
        result = ENG.asset_class_exposure(PORTFOLIO)
        assert isinstance(result, ExposureBreakdown)

    def test_equity_present(self):
        result = ENG.asset_class_exposure(PORTFOLIO)
        assert "equity" in result.breakdown

    def test_bond_present(self):
        result = ENG.asset_class_exposure(PORTFOLIO)
        assert "bond" in result.breakdown


class TestMarketCapExposure:
    def test_returns_exposure_breakdown(self):
        result = ENG.market_cap_exposure(PORTFOLIO)
        assert isinstance(result, ExposureBreakdown)

    def test_large_cap_present(self):
        result = ENG.market_cap_exposure(PORTFOLIO)
        assert "large" in result.breakdown


class TestFactorExposure:
    def test_returns_factor_exposure_report(self):
        result = ENG.factor_exposure(PORTFOLIO)
        assert isinstance(result, FactorExposureReport)

    def test_momentum_present(self):
        result = ENG.factor_exposure(PORTFOLIO)
        assert "momentum" in result.factor_exposures

    def test_weighted_momentum(self):
        simple = [
            Holding("A", 0.5, factor_exposures={"momentum": 1.0}),
            Holding("B", 0.5, factor_exposures={"momentum": 0.0}),
        ]
        result = ENG.factor_exposure(simple)
        assert abs(result.factor_exposures["momentum"] - 0.5) < 1e-6

    def test_dominant_factor_has_max_abs(self):
        result = ENG.factor_exposure(PORTFOLIO)
        dom = result.dominant_factor
        dom_abs = abs(result.factor_exposures[dom])
        for f, v in result.factor_exposures.items():
            assert dom_abs >= abs(v)

    def test_risk_contribution_sums_to_one(self):
        result = ENG.factor_exposure(PORTFOLIO)
        total = sum(result.factor_risk_contribution.values())
        assert abs(total - 1.0) < 1e-5

    def test_empty_factor_holdings(self):
        plain = [Holding("X", 0.5), Holding("Y", 0.5)]
        result = ENG.factor_exposure(plain)
        assert result.factor_exposures == {}

    def test_to_dict(self):
        d = ENG.factor_exposure(PORTFOLIO).to_dict()
        assert "factor_exposures" in d and "dominant_factor" in d


class TestConcentrationMetrics:
    def test_returns_concentration_metrics(self):
        result = ENG.concentration_metrics(PORTFOLIO)
        assert isinstance(result, ConcentrationMetrics)

    def test_hhi_positive(self):
        result = ENG.concentration_metrics(PORTFOLIO)
        assert result.hhi > 0

    def test_effective_n_positive(self):
        result = ENG.concentration_metrics(PORTFOLIO)
        assert result.effective_n > 0

    def test_equal_weight_max_effective_n(self):
        n = 5
        equal = [Holding(str(i), 1.0 / n) for i in range(n)]
        result = ENG.concentration_metrics(equal)
        assert abs(result.effective_n - n) < 0.1

    def test_gini_zero_for_equal(self):
        n = 4
        equal = [Holding(str(i), 0.25) for i in range(n)]
        result = ENG.concentration_metrics(equal)
        assert abs(result.gini_coefficient) < 0.01

    def test_top1_weight(self):
        result = ENG.concentration_metrics(PORTFOLIO)
        max_w = max(h.weight for h in PORTFOLIO)
        assert abs(result.top1_weight - max_w) < 1e-5

    def test_to_dict(self):
        d = ENG.concentration_metrics(PORTFOLIO).to_dict()
        assert "hhi" in d and "gini_coefficient" in d


class TestRiskExposure:
    def test_returns_risk_exposure(self):
        result = ENG.risk_exposure(PORTFOLIO)
        assert isinstance(result, RiskExposure)

    def test_portfolio_beta_weighted(self):
        simple = [Holding("A", 0.5, beta=2.0), Holding("B", 0.5, beta=0.0)]
        result = ENG.risk_exposure(simple)
        assert abs(result.portfolio_beta - 1.0) < 1e-6

    def test_bond_duration_weighted(self):
        result = ENG.risk_exposure(PORTFOLIO)
        expected = sum(h.weight * h.duration for h in PORTFOLIO)
        assert abs(result.portfolio_duration - expected) < 1e-4

    def test_equity_share(self):
        result = ENG.risk_exposure(PORTFOLIO)
        equity_w = sum(h.weight for h in PORTFOLIO if h.asset_class == "equity")
        assert abs(result.equity_share - equity_w) < 1e-5

    def test_em_share_zero_all_us(self):
        us_only = [Holding("X", 0.5, country="US"), Holding("Y", 0.5, country="US")]
        result = ENG.risk_exposure(us_only)
        assert result.emerging_market_share == 0.0

    def test_em_share_positive(self):
        em_mix = [Holding("X", 0.6, country="CN"), Holding("Y", 0.4, country="US")]
        result = ENG.risk_exposure(em_mix)
        assert result.emerging_market_share > 0

    def test_to_dict(self):
        d = ENG.risk_exposure(PORTFOLIO).to_dict()
        assert "portfolio_beta" in d and "emerging_market_share" in d


class TestDriftFromTarget:
    def test_no_drift(self):
        cur = {"AAPL": 0.5, "MSFT": 0.5}
        tgt = {"AAPL": 0.5, "MSFT": 0.5}
        result = ENG.drift_from_target(cur, tgt)
        assert result["total_absolute_drift"] == 0.0
        assert not result["rebalance_needed"]

    def test_drift_detected(self):
        cur = {"AAPL": 0.6, "MSFT": 0.4}
        tgt = {"AAPL": 0.5, "MSFT": 0.5}
        result = ENG.drift_from_target(cur, tgt)
        assert abs(result["drifts"]["AAPL"] - 0.1) < 1e-5

    def test_rebalance_needed_when_large_drift(self):
        cur = {"AAPL": 0.9, "MSFT": 0.1}
        tgt = {"AAPL": 0.5, "MSFT": 0.5}
        result = ENG.drift_from_target(cur, tgt)
        assert result["rebalance_needed"]


class TestFullReport:
    def test_returns_dict(self):
        report = ENG.full_report(PORTFOLIO)
        assert isinstance(report, dict)

    def test_has_all_dimensions(self):
        report = ENG.full_report(PORTFOLIO)
        for key in ("sector", "country", "currency", "asset_class", "market_cap",
                    "factor", "concentration", "risk", "n_holdings"):
            assert key in report

    def test_n_holdings_correct(self):
        report = ENG.full_report(PORTFOLIO)
        assert report["n_holdings"] == len(PORTFOLIO)


class TestActiveWeights:
    def test_returns_dict(self):
        bench = [Holding("AAPL", 0.5), Holding("MSFT", 0.5)]
        port = [Holding("AAPL", 0.6), Holding("MSFT", 0.4)]
        result = ENG.active_weights(port, bench)
        assert isinstance(result, dict)

    def test_overweight_positive(self):
        bench = [Holding("AAPL", 0.4)]
        port = [Holding("AAPL", 0.6)]
        result = ENG.active_weights(port, bench)
        assert abs(result["AAPL"] - 0.2) < 1e-5

    def test_underweight_negative(self):
        bench = [Holding("MSFT", 0.5)]
        port = [Holding("MSFT", 0.3)]
        result = ENG.active_weights(port, bench)
        assert result["MSFT"] < 0

    def test_ticker_not_in_bench_is_full_weight(self):
        bench = [Holding("AAPL", 0.5)]
        port = [Holding("AAPL", 0.4), Holding("NVDA", 0.6)]
        result = ENG.active_weights(port, bench)
        assert abs(result["NVDA"] - 0.6) < 1e-5


class TestSingleton:
    def test_singleton(self):
        a = get_portfolio_exposure_engine()
        b = get_portfolio_exposure_engine()
        assert a is b
