"""Tests for M9 Phase 3/4 — options strategies and binomial tree."""
import math
import pytest
from services.options_strategies import (
    bs_call, bs_put, bs_greeks, binomial_tree, build_strategy, list_strategies,
    _norm_cdf, _norm_pdf, _erf,
)


# ---------------------------------------------------------------------------
# Black-Scholes helpers
# ---------------------------------------------------------------------------

class TestBlackScholesHelpers:
    def test_norm_cdf_zero(self):
        assert _norm_cdf(0) == pytest.approx(0.5, abs=0.001)

    def test_norm_cdf_large_positive(self):
        assert _norm_cdf(10) > 0.999

    def test_norm_cdf_large_negative(self):
        assert _norm_cdf(-10) < 0.001

    def test_norm_pdf_peak(self):
        assert _norm_pdf(0) == pytest.approx(1 / math.sqrt(2 * math.pi), rel=0.001)

    def test_erf_zero(self):
        assert _erf(0) == pytest.approx(0.0, abs=1e-6)

    def test_erf_symmetry(self):
        assert _erf(1.0) == pytest.approx(-_erf(-1.0), abs=0.001)


# ---------------------------------------------------------------------------
# Black-Scholes pricing
# ---------------------------------------------------------------------------

class TestBlackScholes:
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20

    def test_call_positive(self):
        assert bs_call(self.S, self.K, self.T, self.r, self.sigma) > 0

    def test_put_positive(self):
        assert bs_put(self.S, self.K, self.T, self.r, self.sigma) > 0

    def test_put_call_parity(self):
        c = bs_call(self.S, self.K, self.T, self.r, self.sigma)
        p = bs_put(self.S, self.K, self.T, self.r, self.sigma)
        # C - P = S - K*e^(-rT)
        expected = self.S - self.K * math.exp(-self.r * self.T)
        assert abs(c - p - expected) < 0.01

    def test_call_deep_itm(self):
        c = bs_call(200.0, 100.0, 1.0, 0.05, 0.20)
        assert c > 90.0

    def test_put_deep_itm(self):
        p = bs_put(50.0, 100.0, 1.0, 0.05, 0.20)
        assert p > 40.0

    def test_zero_expiry_call(self):
        assert bs_call(110.0, 100.0, 0.0, 0.05, 0.20) == pytest.approx(10.0)

    def test_zero_expiry_put_otm(self):
        assert bs_put(110.0, 100.0, 0.0, 0.05, 0.20) == pytest.approx(0.0)

    def test_zero_expiry_call_otm(self):
        assert bs_call(90.0, 100.0, 0.0, 0.05, 0.20) == pytest.approx(0.0)

    def test_higher_vol_higher_price(self):
        c1 = bs_call(self.S, self.K, self.T, self.r, 0.10)
        c2 = bs_call(self.S, self.K, self.T, self.r, 0.40)
        assert c2 > c1


# ---------------------------------------------------------------------------
# Greeks
# ---------------------------------------------------------------------------

class TestGreeks:
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20

    def test_call_delta_range(self):
        g = bs_greeks(self.S, self.K, self.T, self.r, self.sigma, "call")
        assert 0 < g["delta"] < 1

    def test_put_delta_negative(self):
        g = bs_greeks(self.S, self.K, self.T, self.r, self.sigma, "put")
        assert -1 < g["delta"] < 0

    def test_atm_call_delta_near_half(self):
        g = bs_greeks(self.S, self.K, self.T, self.r, self.sigma, "call")
        assert 0.4 < g["delta"] < 0.7

    def test_gamma_positive(self):
        g = bs_greeks(self.S, self.K, self.T, self.r, self.sigma, "call")
        assert g["gamma"] > 0

    def test_vega_positive(self):
        g = bs_greeks(self.S, self.K, self.T, self.r, self.sigma, "call")
        assert g["vega"] > 0

    def test_call_theta_negative(self):
        g = bs_greeks(self.S, self.K, self.T, self.r, self.sigma, "call")
        assert g["theta"] < 0

    def test_put_rho_negative(self):
        g = bs_greeks(self.S, self.K, self.T, self.r, self.sigma, "put")
        assert g["rho"] < 0

    def test_zero_expiry_greeks(self):
        g = bs_greeks(self.S, self.K, 0.0, self.r, self.sigma, "call")
        assert g["gamma"] == 0.0


# ---------------------------------------------------------------------------
# Binomial tree
# ---------------------------------------------------------------------------

class TestBinomialTree:
    def test_call_price_close_to_bs(self):
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.20
        bt = binomial_tree(S, K, T, r, sigma, "call", steps=200)
        bs = bs_call(S, K, T, r, sigma)
        assert abs(bt - bs) < 0.5

    def test_put_price_close_to_bs(self):
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.20
        bt = binomial_tree(S, K, T, r, sigma, "put", steps=200)
        bs = bs_put(S, K, T, r, sigma)
        assert abs(bt - bs) < 0.5

    def test_american_put_ge_european(self):
        S, K, T, r, sigma = 100, 110, 1.0, 0.05, 0.20
        american = binomial_tree(S, K, T, r, sigma, "put", american=True)
        european = binomial_tree(S, K, T, r, sigma, "put", american=False)
        assert american >= european - 0.01

    def test_zero_expiry_itm_call(self):
        p = binomial_tree(110, 100, 0, 0.05, 0.20, "call")
        assert p == pytest.approx(10.0)

    def test_zero_expiry_otm_call(self):
        p = binomial_tree(90, 100, 0, 0.05, 0.20, "call")
        assert p == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Strategy builder
# ---------------------------------------------------------------------------

class TestStrategyBuilder:
    def test_list_strategies(self):
        strategies = list_strategies()
        assert len(strategies) == 8
        assert "straddle" in strategies
        assert "iron_condor" in strategies

    def test_straddle_structure(self):
        r = build_strategy("straddle", 100, 100, 0.25, 0.05, 0.20)
        assert r["strategy"] == "straddle"
        assert len(r["legs"]) == 2
        assert "payoff_curve" in r
        assert "greeks" in r

    def test_straddle_payoff_curve_length(self):
        r = build_strategy("straddle", 100, 100, 0.25, 0.05, 0.20)
        assert len(r["payoff_curve"]) > 5

    def test_covered_call_two_legs(self):
        r = build_strategy("covered_call", 100, 105, 0.25, 0.05, 0.20)
        assert len(r["legs"]) == 2

    def test_iron_condor_four_legs(self):
        r = build_strategy("iron_condor", 100, 100, 0.25, 0.05, 0.20)
        assert len(r["legs"]) == 4

    def test_butterfly_three_legs(self):
        r = build_strategy("butterfly", 100, 100, 0.25, 0.05, 0.20)
        assert len(r["legs"]) == 3

    def test_bull_call_spread_net_debit(self):
        r = build_strategy("bull_call_spread", 100, 100, 0.25, 0.05, 0.20)
        assert r["net_cost"] > 0  # buying lower, selling higher -> net debit

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            build_strategy("nonexistent", 100, 100, 0.25, 0.05, 0.20)

    def test_greeks_keys(self):
        r = build_strategy("straddle", 100, 100, 0.25, 0.05, 0.20)
        for key in ("delta", "gamma", "theta", "vega", "rho"):
            assert key in r["greeks"]

    def test_straddle_near_zero_delta(self):
        r = build_strategy("straddle", 100, 100, 0.5, 0.05, 0.20)
        assert abs(r["greeks"]["delta"]) < 0.2  # symmetric strategy
