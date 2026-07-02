"""Tests for M19 FactorModelEngine service."""

import math
import pytest
from services.m19_factor_models import (
    FactorModelEngine,
    FactorReturn,
    FactorExposure,
    FactorAttribution,
    FactorCorrelation,
    FactorType,
    _mat_T,
    _mat_mul,
    _mat_inv,
    _ols,
    _pearson,
)


def synthetic_factor_returns(n=100, seed=0) -> list:
    import random
    rng = random.Random(seed)
    dates = [f"2024-01-{(i % 28) + 1:02d}" if i < 28
             else f"2024-02-{(i % 25) + 1:02d}" if i < 53
             else f"2024-03-{(i % 22) + 1:02d}"
             for i in range(min(n, 75))]
    dates = [f"2024-{1 + i // 25:02d}-{(i % 25) + 1:02d}" for i in range(n)]
    returns = []
    for d in dates:
        for fac in FactorType:
            returns.append(FactorReturn(date=d, factor=fac, return_value=rng.gauss(0.0, 0.01)))
    return dates, returns


def synthetic_security_returns(dates, factor_rets, betas, alpha=0.0001, seed=1) -> dict:
    import random
    rng = random.Random(seed)
    date_to_factors = {}
    for fr in factor_rets:
        date_to_factors.setdefault(fr.date, {})[fr.factor.value] = fr.return_value
    sec_rets = {}
    for d in dates:
        fac = date_to_factors.get(d, {})
        r = alpha + sum(betas.get(f, 0.0) * fac.get(f, 0.0) for f in betas) + rng.gauss(0.0, 0.005)
        sec_rets[d] = r
    return sec_rets


class TestLinearAlgebraHelpers:
    def test_transpose_square(self):
        A = [[1.0, 2.0], [3.0, 4.0]]
        T = _mat_T(A)
        assert T[0][0] == 1.0 and T[0][1] == 3.0
        assert T[1][0] == 2.0 and T[1][1] == 4.0

    def test_transpose_non_square(self):
        A = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        T = _mat_T(A)
        assert len(T) == 3 and len(T[0]) == 2

    def test_mat_mul_identity(self):
        I = [[1.0, 0.0], [0.0, 1.0]]
        A = [[2.0, 3.0], [4.0, 5.0]]
        result = _mat_mul(A, I)
        assert result[0][0] == 2.0 and result[1][1] == 5.0

    def test_mat_mul_correct(self):
        A = [[1.0, 2.0], [3.0, 4.0]]
        B = [[5.0, 6.0], [7.0, 8.0]]
        C = _mat_mul(A, B)
        assert C[0][0] == 19.0 and C[0][1] == 22.0

    def test_mat_inv_identity(self):
        I = [[1.0, 0.0], [0.0, 1.0]]
        inv = _mat_inv(I)
        assert abs(inv[0][0] - 1.0) < 1e-6
        assert abs(inv[1][1] - 1.0) < 1e-6
        assert abs(inv[0][1]) < 1e-6

    def test_mat_inv_2x2(self):
        A = [[2.0, 1.0], [1.0, 1.0]]
        inv = _mat_inv(A)
        result = _mat_mul(A, inv)
        assert abs(result[0][0] - 1.0) < 1e-6
        assert abs(result[0][1]) < 1e-6

    def test_ols_perfect_fit(self):
        X = [[1.0, i] for i in range(10)]
        y = [[2.0 * i + 1.0] for i in range(10)]
        beta, se, r2, adj_r2 = _ols(X, y)
        assert abs(beta[1] - 2.0) < 0.01
        assert r2 > 0.99

    def test_pearson_perfect_correlation(self):
        x = [float(i) for i in range(10)]
        y = [2.0 * xi + 1.0 for xi in x]
        assert abs(_pearson(x, y) - 1.0) < 1e-6

    def test_pearson_negative_correlation(self):
        x = [float(i) for i in range(10)]
        y = [-xi for xi in x]
        assert abs(_pearson(x, y) + 1.0) < 1e-6

    def test_pearson_zero_std(self):
        x = [1.0] * 10
        y = [float(i) for i in range(10)]
        assert _pearson(x, y) == 0.0


class TestFactorModelEngineInit:
    def test_created(self):
        engine = FactorModelEngine()
        assert engine is not None

    def test_starts_empty(self):
        engine = FactorModelEngine()
        assert engine.list_tickers() == []

    def test_reset_clears_state(self):
        engine = FactorModelEngine()
        _, rets = synthetic_factor_returns(n=30)
        engine.add_factor_returns(rets)
        engine.reset()
        assert engine.list_tickers() == []
        assert engine._factor_returns == {}

    def test_get_nonexistent_exposure_none(self):
        engine = FactorModelEngine()
        assert engine.get_exposure("AAPL") is None


class TestAddFactorReturns:
    def setup_method(self):
        self.engine = FactorModelEngine()

    def test_add_factor_returns(self):
        _, rets = synthetic_factor_returns(n=30)
        self.engine.add_factor_returns(rets)
        assert len(self.engine._factor_returns) > 0

    def test_add_multiple_factors(self):
        dates, rets = synthetic_factor_returns(n=50)
        self.engine.add_factor_returns(rets)
        assert len(dates) > 0

    def test_factor_returns_stored_by_date(self):
        rets = [FactorReturn(date="2024-01-01", factor=FactorType.MARKET, return_value=0.01)]
        self.engine.add_factor_returns(rets)
        assert "2024-01-01" in self.engine._factor_returns
        assert self.engine._factor_returns["2024-01-01"]["MARKET"] == 0.01


class TestRegression:
    def setup_method(self):
        self.engine = FactorModelEngine()
        self.dates, self.rets = synthetic_factor_returns(n=100)
        self.engine.add_factor_returns(self.rets)

    def test_regress_returns_exposure(self):
        betas = {"MARKET": 1.0, "SIZE": 0.3}
        sec_rets = synthetic_security_returns(self.dates, self.rets, betas)
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET, FactorType.SIZE])
        assert exp is not None

    def test_exposure_has_ticker(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        assert exp.ticker == "AAPL"

    def test_exposure_has_betas(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        assert "MARKET" in exp.betas

    def test_exposure_has_r_squared(self):
        betas = {"MARKET": 1.0}
        sec_rets = synthetic_security_returns(self.dates, self.rets, betas)
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        assert 0.0 <= exp.r_squared <= 1.0

    def test_exposure_has_t_stats(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        assert "MARKET" in exp.t_stats

    def test_exposure_has_p_values(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        assert "MARKET" in exp.p_values

    def test_p_values_in_range(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        for p in exp.p_values.values():
            assert 0.0 <= p <= 1.0

    def test_exposure_cached(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        cached = self.engine.get_exposure("AAPL")
        assert cached is not None

    def test_high_beta_market_factor(self):
        betas = {"MARKET": 1.5}
        sec_rets = synthetic_security_returns(self.dates, self.rets, betas, alpha=0.0, seed=10)
        exp = self.engine.regress("HIGH_BETA", sec_rets, [FactorType.MARKET])
        assert exp.betas.get("MARKET", 0.0) > 0.5

    def test_insufficient_data_returns_zero_exposure(self):
        few_rets = {"2024-01-01": 0.01}
        exp = self.engine.regress("X", few_rets, [FactorType.MARKET])
        assert exp.r_squared == 0.0

    def test_exposure_to_dict(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        exp = self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        d = exp.to_dict()
        for key in ["ticker", "alpha", "betas", "r_squared"]:
            assert key in d

    def test_list_tickers_after_regress(self):
        sec_rets = synthetic_security_returns(self.dates, self.rets, {"MARKET": 1.0})
        self.engine.regress("AAPL", sec_rets, [FactorType.MARKET])
        assert "AAPL" in self.engine.list_tickers()


class TestAttribution:
    def setup_method(self):
        self.engine = FactorModelEngine()
        dates, rets = synthetic_factor_returns(n=100)
        self.engine.add_factor_returns(rets)
        sec_rets = synthetic_security_returns(dates, rets, {"MARKET": 1.0, "VALUE": 0.2})
        self.engine.regress("AAPL", sec_rets, [FactorType.MARKET, FactorType.VALUE])

    def test_attribution_returns_result(self):
        attr = self.engine.compute_attribution("AAPL", 0.10, {"MARKET": 0.08, "VALUE": 0.03})
        assert attr is not None

    def test_attribution_has_ticker(self):
        attr = self.engine.compute_attribution("AAPL", 0.10, {"MARKET": 0.08})
        assert attr.ticker == "AAPL"

    def test_attribution_has_factor_contributions(self):
        attr = self.engine.compute_attribution("AAPL", 0.10, {"MARKET": 0.08})
        assert isinstance(attr.factor_contributions, dict)

    def test_attribution_unknown_ticker_returns_residual(self):
        attr = self.engine.compute_attribution("UNKN", 0.10, {"MARKET": 0.08})
        assert attr.residual == 0.10

    def test_attribution_to_dict(self):
        attr = self.engine.compute_attribution("AAPL", 0.10, {"MARKET": 0.08})
        d = attr.to_dict()
        assert "total_return" in d and "factor_contributions" in d


class TestFactorCorrelations:
    def setup_method(self):
        self.engine = FactorModelEngine()
        _, rets = synthetic_factor_returns(n=50)
        self.engine.add_factor_returns(rets)

    def test_correlations_returned(self):
        corrs = self.engine.compute_factor_correlations([FactorType.MARKET, FactorType.SIZE, FactorType.VALUE])
        assert len(corrs) > 0

    def test_correlation_range(self):
        corrs = self.engine.compute_factor_correlations([FactorType.MARKET, FactorType.SIZE])
        for c in corrs:
            assert -1.0 <= c.correlation <= 1.0

    def test_correlation_to_dict(self):
        corrs = self.engine.compute_factor_correlations([FactorType.MARKET, FactorType.SIZE])
        if corrs:
            d = corrs[0].to_dict()
            assert "factor_a" in d and "correlation" in d

    def test_no_self_correlation(self):
        corrs = self.engine.compute_factor_correlations([FactorType.MARKET, FactorType.SIZE])
        for c in corrs:
            assert c.factor_a != c.factor_b


class TestPortfolioBeta:
    def setup_method(self):
        self.engine = FactorModelEngine()
        dates, rets = synthetic_factor_returns(n=100)
        self.engine.add_factor_returns(rets)
        for ticker, beta in [("AAPL", 1.0), ("MSFT", 1.5)]:
            sr = synthetic_security_returns(dates, rets, {"MARKET": beta})
            self.engine.regress(ticker, sr, [FactorType.MARKET])

    def test_portfolio_beta_computed(self):
        beta = self.engine.compute_portfolio_beta({"AAPL": 0.5, "MSFT": 0.5}, FactorType.MARKET)
        assert isinstance(beta, float)

    def test_equal_weight_beta_between_components(self):
        beta = self.engine.compute_portfolio_beta({"AAPL": 0.5, "MSFT": 0.5}, FactorType.MARKET)
        assert 0.5 < beta < 2.5

    def test_full_weight_single_asset(self):
        beta = self.engine.compute_portfolio_beta({"AAPL": 1.0}, FactorType.MARKET)
        aapl_beta = self.engine.get_exposure("AAPL").betas.get("MARKET", 0.0)
        assert abs(beta - aapl_beta) < 1e-9


class TestFactorSeries:
    def test_series_returned(self):
        engine = FactorModelEngine()
        rets = [FactorReturn(date="2024-01-01", factor=FactorType.MARKET, return_value=0.01),
                FactorReturn(date="2024-01-02", factor=FactorType.MARKET, return_value=-0.005)]
        engine.add_factor_returns(rets)
        series = engine.build_factor_return_series(FactorType.MARKET)
        assert len(series) == 2

    def test_series_sorted_by_date(self):
        engine = FactorModelEngine()
        rets = [FactorReturn(date="2024-01-03", factor=FactorType.MARKET, return_value=0.02),
                FactorReturn(date="2024-01-01", factor=FactorType.MARKET, return_value=0.01)]
        engine.add_factor_returns(rets)
        series = engine.build_factor_return_series(FactorType.MARKET)
        assert series[0]["date"] < series[1]["date"]
