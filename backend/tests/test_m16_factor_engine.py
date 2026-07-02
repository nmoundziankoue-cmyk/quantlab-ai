"""M16 tests — Factor Engine."""
import math
import pytest
from services.factor_engine import (
    FactorEngine, FactorType, FactorExposure, FactorReturn,
    FactorAttribution, FactorCluster, get_factor_engine,
)

ENG = FactorEngine()

RETS = [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01,
        0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01]
MKT = [0.008, -0.015, 0.025, 0.008, -0.008, 0.016, 0.008, -0.008, 0.016, 0.008,
       0.008, -0.008, 0.016, 0.008, -0.008, 0.016, 0.008, -0.008, 0.016, 0.008]
FACTOR_RETS_MAP = {
    FactorType.MARKET: MKT,
    FactorType.MOMENTUM: RETS,
    FactorType.VALUE: [v * -0.5 for v in RETS],
}


class TestFactorScores:
    def test_market_exposure_float(self):
        b = ENG.compute_market_exposure(RETS, MKT)
        assert isinstance(b, float)

    def test_market_exposure_positive(self):
        b = ENG.compute_market_exposure(RETS, MKT)
        assert b > 0

    def test_size_score_float(self):
        score = ENG.compute_size_score(5000.0, [1000.0, 5000.0, 20000.0])
        assert isinstance(score, float)

    def test_size_score_small_cap_positive(self):
        score = ENG.compute_size_score(500.0, [500.0, 5000.0, 50000.0])
        assert score > 0  # small cap = positive SMB exposure

    def test_size_score_large_cap_negative(self):
        score = ENG.compute_size_score(50000.0, [500.0, 5000.0, 50000.0])
        assert score < 0

    def test_value_score_float(self):
        score = ENG.compute_value_score(2.5, [0.5, 1.0, 1.5, 2.0, 2.5])
        assert isinstance(score, float)

    def test_momentum_score_float(self):
        rets = [0.01] * 14
        score = ENG.compute_momentum_score(rets, lookback=12)
        assert isinstance(score, float)

    def test_quality_score_float(self):
        score = ENG.compute_quality_score(roe=0.2, debt_to_equity=0.3, earnings_stability=0.9)
        assert isinstance(score, float)

    def test_low_vol_score_negative_for_high_vol(self):
        high_vol = [0.1, -0.1, 0.15, -0.15, 0.2, -0.2] * 3
        score = ENG.compute_low_vol_score(high_vol)
        assert score < 0

    def test_growth_score_float(self):
        score = ENG.compute_growth_score(0.15, 0.20)
        assert isinstance(score, float)

    def test_profitability_score_equals_input(self):
        score = ENG.compute_profitability_score(0.35)
        assert abs(score - 0.35) < 1e-9

    def test_investment_score_negative_of_growth(self):
        score = ENG.compute_investment_score(0.12)
        assert abs(score - (-0.12)) < 1e-9

    def test_dividend_yield_score_float(self):
        score = ENG.compute_dividend_yield_score(0.03, [0.01, 0.02, 0.03, 0.04])
        assert isinstance(score, float)


class TestFactorExposures:
    def test_returns_factor_exposure(self):
        scores = {FactorType.MARKET: 1.2, FactorType.MOMENTUM: 0.8, FactorType.VALUE: -0.5}
        fe = ENG.compute_exposures("NVDA", scores)
        assert isinstance(fe, FactorExposure)

    def test_dominant_factor_highest_abs(self):
        scores = {FactorType.MARKET: 1.2, FactorType.VALUE: -2.0}
        fe = ENG.compute_exposures("TSLA", scores)
        assert fe.dominant_factor == FactorType.VALUE

    def test_ticker_stored(self):
        fe = ENG.compute_exposures("AAPL", {FactorType.QUALITY: 0.9})
        assert fe.ticker == "AAPL"

    def test_to_dict(self):
        fe = ENG.compute_exposures("X", {FactorType.MARKET: 1.0})
        d = fe.to_dict()
        assert "ticker" in d and "exposures" in d and "dominant_factor" in d

    def test_empty_scores_dominant_is_market(self):
        fe = ENG.compute_exposures("Y", {})
        assert fe.dominant_factor == FactorType.MARKET


class TestFactorReturns:
    def test_returns_factor_return(self):
        fr = ENG.compute_factor_returns(FactorType.MOMENTUM, RETS, MKT)
        assert isinstance(fr, FactorReturn)

    def test_factor_field(self):
        fr = ENG.compute_factor_returns(FactorType.SIZE, RETS, MKT)
        assert fr.factor == FactorType.SIZE

    def test_hit_rate_in_range(self):
        fr = ENG.compute_factor_returns(FactorType.VALUE, RETS, MKT)
        assert 0.0 <= fr.hit_rate <= 1.0

    def test_volatility_nonneg(self):
        fr = ENG.compute_factor_returns(FactorType.QUALITY, RETS, MKT)
        assert fr.volatility >= 0

    def test_to_dict(self):
        fr = ENG.compute_factor_returns(FactorType.MARKET, RETS, MKT)
        d = fr.to_dict()
        assert "factor" in d and "sharpe" in d


class TestFactorAttribution:
    def test_returns_factor_attribution(self):
        exp = {FactorType.MARKET: 1.0, FactorType.MOMENTUM: 0.5}
        fa = ENG.attribute_returns("AAPL", RETS, FACTOR_RETS_MAP, exp)
        assert isinstance(fa, FactorAttribution)

    def test_r_squared_in_range(self):
        exp = {FactorType.MARKET: 1.0}
        fa = ENG.attribute_returns("AAPL", RETS, FACTOR_RETS_MAP, exp)
        assert 0.0 <= fa.r_squared <= 1.0

    def test_total_return_is_sum(self):
        exp = {FactorType.MARKET: 0.0}
        fa = ENG.attribute_returns("TEST", RETS, FACTOR_RETS_MAP, exp)
        assert abs(fa.total_return - sum(RETS)) < 1e-8

    def test_to_dict(self):
        fa = ENG.attribute_returns("X", RETS, {}, {})
        d = fa.to_dict()
        assert "total_return" in d and "idiosyncratic_return" in d


class TestFactorCorrelation:
    def test_returns_dict(self):
        corr = ENG.factor_correlation(FACTOR_RETS_MAP)
        assert "factors" in corr and "matrix" in corr

    def test_diagonal_ones(self):
        corr = ENG.factor_correlation(FACTOR_RETS_MAP)
        n = len(corr["factors"])
        for i in range(n):
            assert corr["matrix"][i][i] == 1.0

    def test_symmetric(self):
        corr = ENG.factor_correlation(FACTOR_RETS_MAP)
        n = len(corr["factors"])
        for i in range(n):
            for j in range(n):
                assert abs(corr["matrix"][i][j] - corr["matrix"][j][i]) < 1e-9


class TestFactorClustering:
    def test_returns_list_of_clusters(self):
        clusters = ENG.cluster_factors(FACTOR_RETS_MAP, n_clusters=2)
        assert isinstance(clusters, list)

    def test_cluster_count_correct(self):
        clusters = ENG.cluster_factors(FACTOR_RETS_MAP, n_clusters=2)
        assert len(clusters) == 2

    def test_each_factor_in_one_cluster(self):
        clusters = ENG.cluster_factors(FACTOR_RETS_MAP, n_clusters=2)
        all_factors = [f for c in clusters for f in c.factors]
        assert set(all_factors) == set(FACTOR_RETS_MAP.keys())

    def test_to_dict(self):
        clusters = ENG.cluster_factors(FACTOR_RETS_MAP, n_clusters=2)
        for c in clusters:
            d = c.to_dict()
            assert "cluster_id" in d and "factors" in d


class TestPortfolioFactorExposure:
    def test_returns_dict(self):
        holdings = {"AAPL": 0.6, "MSFT": 0.4}
        asset_exp = {
            "AAPL": {FactorType.MARKET: 1.2, FactorType.MOMENTUM: 0.8},
            "MSFT": {FactorType.MARKET: 0.9, FactorType.QUALITY: 0.5},
        }
        result = ENG.portfolio_factor_exposure(holdings, asset_exp)
        assert isinstance(result, dict)

    def test_weighted_market_exposure(self):
        holdings = {"A": 0.5, "B": 0.5}
        asset_exp = {"A": {FactorType.MARKET: 2.0}, "B": {FactorType.MARKET: 0.0}}
        result = ENG.portfolio_factor_exposure(holdings, asset_exp)
        assert abs(result[FactorType.MARKET] - 1.0) < 1e-9


class TestFactorStatistics:
    def test_returns_dict(self):
        stats = ENG.factor_statistics(FACTOR_RETS_MAP)
        assert isinstance(stats, dict)

    def test_has_each_factor(self):
        stats = ENG.factor_statistics(FACTOR_RETS_MAP)
        for f in FACTOR_RETS_MAP:
            assert f.value in stats

    def test_has_sharpe(self):
        stats = ENG.factor_statistics(FACTOR_RETS_MAP)
        for k, v in stats.items():
            assert "sharpe" in v


class TestSingleton:
    def test_singleton(self):
        a = get_factor_engine()
        b = get_factor_engine()
        assert a is b
