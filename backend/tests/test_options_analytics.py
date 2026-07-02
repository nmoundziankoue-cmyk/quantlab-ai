"""Tests for the Options Analytics Engine (M7)."""
from __future__ import annotations

import math
import pytest

from services.options_analytics import (
    black_scholes_price,
    calculate_greeks,
    expected_move,
    gamma_exposure,
    implied_volatility,
    iv_surface,
    max_pain,
    options_chain,
    volatility_skew,
)


# ---------------------------------------------------------------------------
# Black-Scholes price
# ---------------------------------------------------------------------------

class TestBlackScholesPrice:
    def test_call_price_positive(self):
        price = black_scholes_price(100, 100, 1.0, 0.2, "CALL")
        assert price > 0

    def test_put_price_positive(self):
        price = black_scholes_price(100, 100, 1.0, 0.2, "PUT")
        assert price > 0

    def test_itm_call_higher_than_otm_call(self):
        itm = black_scholes_price(110, 100, 1.0, 0.2, "CALL")
        otm = black_scholes_price(90, 100, 1.0, 0.2, "CALL")
        assert itm > otm

    def test_itm_put_higher_than_otm_put(self):
        itm = black_scholes_price(90, 100, 1.0, 0.2, "PUT")
        otm = black_scholes_price(110, 100, 1.0, 0.2, "PUT")
        assert itm > otm

    def test_put_call_parity(self):
        S, K, T, sigma, r = 100.0, 100.0, 1.0, 0.2, 0.05
        call = black_scholes_price(S, K, T, sigma, "CALL", r)
        put = black_scholes_price(S, K, T, sigma, "PUT", r)
        disc = math.exp(-r * T)
        # Put-call parity: C - P = S - K * e^(-rT)
        assert abs((call - put) - (S - K * disc)) < 1e-4

    def test_zero_time_call_returns_intrinsic(self):
        price = black_scholes_price(110, 100, 0, 0.2, "CALL")
        assert price == 10.0  # intrinsic = max(S-K, 0)

    def test_case_insensitive_option_type(self):
        price_upper = black_scholes_price(100, 100, 1.0, 0.2, "CALL")
        price_lower = black_scholes_price(100, 100, 1.0, 0.2, "call")
        assert abs(price_upper - price_lower) < 1e-10

    def test_higher_vol_higher_price(self):
        p_low = black_scholes_price(100, 100, 1.0, 0.1, "CALL")
        p_high = black_scholes_price(100, 100, 1.0, 0.5, "CALL")
        assert p_high > p_low

    def test_longer_expiry_higher_price(self):
        p_short = black_scholes_price(100, 100, 0.25, 0.2, "CALL")
        p_long = black_scholes_price(100, 100, 2.0, 0.2, "CALL")
        assert p_long > p_short


# ---------------------------------------------------------------------------
# Greeks
# ---------------------------------------------------------------------------

class TestGreeks:
    def test_returns_all_greeks(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "CALL")
        assert set(g.keys()) == {"delta", "gamma", "theta", "vega", "rho"}

    def test_call_delta_between_0_and_1(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "CALL")
        assert 0 < g["delta"] < 1

    def test_put_delta_between_minus1_and_0(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "PUT")
        assert -1 < g["delta"] < 0

    def test_gamma_positive(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "CALL")
        assert g["gamma"] > 0

    def test_vega_positive(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "CALL")
        assert g["vega"] > 0

    def test_call_theta_negative(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "CALL")
        assert g["theta"] < 0

    def test_call_rho_positive(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "CALL")
        assert g["rho"] > 0

    def test_put_rho_negative(self):
        g = calculate_greeks(100, 100, 1.0, 0.2, "PUT")
        assert g["rho"] < 0

    def test_zero_time_returns_zeros(self):
        g = calculate_greeks(100, 100, 0, 0.2, "CALL")
        assert g == {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    def test_deep_itm_call_delta_near_1(self):
        g = calculate_greeks(200, 100, 1.0, 0.2, "CALL")
        assert g["delta"] > 0.9

    def test_deep_otm_call_delta_near_0(self):
        g = calculate_greeks(50, 100, 1.0, 0.2, "CALL")
        assert g["delta"] < 0.1


# ---------------------------------------------------------------------------
# Implied volatility
# ---------------------------------------------------------------------------

class TestImpliedVolatility:
    def test_round_trip(self):
        S, K, T, sigma = 100.0, 100.0, 1.0, 0.25
        price = black_scholes_price(S, K, T, sigma, "CALL")
        iv = implied_volatility(price, S, K, T, "CALL")
        assert iv is not None
        assert abs(iv - sigma) < 1e-3

    def test_zero_price_returns_none(self):
        iv = implied_volatility(0.0, 100, 100, 1.0, "CALL")
        assert iv is None

    def test_zero_time_returns_none(self):
        iv = implied_volatility(10.0, 100, 100, 0, "CALL")
        assert iv is None

    def test_iv_positive(self):
        price = black_scholes_price(100, 100, 1.0, 0.3, "PUT")
        iv = implied_volatility(price, 100, 100, 1.0, "PUT")
        assert iv is not None
        assert iv > 0


# ---------------------------------------------------------------------------
# Options chain
# ---------------------------------------------------------------------------

class TestOptionsChain:
    def test_returns_expected_keys(self):
        result = options_chain("AAPL", 150.0)
        assert "ticker" in result
        assert "chain" in result
        assert "total_contracts" in result

    def test_chain_not_empty(self):
        result = options_chain("AAPL", 150.0)
        assert len(result["chain"]) > 0

    def test_chain_item_has_greeks(self):
        result = options_chain("AAPL", 150.0)
        item = result["chain"][0]
        assert "delta" in item
        assert "gamma" in item

    def test_chain_has_calls_and_puts(self):
        result = options_chain("AAPL", 150.0)
        types = {c["option_type"] for c in result["chain"]}
        assert "CALL" in types
        assert "PUT" in types

    def test_custom_strikes(self):
        result = options_chain("MSFT", 300.0, strikes=[280, 300, 320])
        strikes_in_chain = {c["strike"] for c in result["chain"]}
        assert 300.0 in strikes_in_chain

    def test_custom_expiries(self):
        result = options_chain("NVDA", 500.0, expiry_days_list=[7, 30])
        expiries = {c["expiry_days"] for c in result["chain"]}
        assert 7 in expiries and 30 in expiries


# ---------------------------------------------------------------------------
# IV Surface
# ---------------------------------------------------------------------------

class TestIVSurface:
    def test_returns_expected_keys(self):
        result = iv_surface("AAPL", 150.0)
        assert "surface" in result
        assert "strikes" in result
        assert "expiry_days" in result

    def test_surface_dimensions(self):
        result = iv_surface("AAPL", 150.0)
        assert len(result["surface"]) == len(result["expiry_days"])
        assert len(result["surface"][0]) == len(result["strikes"])

    def test_all_ivs_positive(self):
        result = iv_surface("AAPL", 150.0)
        for row in result["surface"]:
            assert all(v > 0 for v in row)


# ---------------------------------------------------------------------------
# Max Pain
# ---------------------------------------------------------------------------

class TestMaxPain:
    def test_returns_max_pain_strike(self):
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
        calls_oi = [500, 800, 1200, 600, 200]
        puts_oi = [200, 600, 1200, 800, 500]
        result = max_pain(strikes, calls_oi, puts_oi)
        assert result["max_pain_strike"] in strikes

    def test_pain_by_strike_length(self):
        strikes = [90.0, 100.0, 110.0]
        calls_oi = [500, 1000, 300]
        puts_oi = [300, 1000, 500]
        result = max_pain(strikes, calls_oi, puts_oi)
        assert len(result["pain_by_strike"]) == 3

    def test_mismatched_lists_returns_empty(self):
        result = max_pain([100.0], [100], [])
        assert result["max_pain_strike"] is None


# ---------------------------------------------------------------------------
# Expected move
# ---------------------------------------------------------------------------

class TestExpectedMove:
    def test_returns_all_fields(self):
        result = expected_move(100.0, 0.2, 30)
        assert "expected_move_1sigma" in result
        assert "upper_bound_1sigma" in result
        assert "lower_bound_1sigma" in result
        assert "pct_move_1sigma" in result

    def test_upper_minus_lower_equals_2sigma(self):
        result = expected_move(100.0, 0.2, 30)
        spread = result["upper_bound_1sigma"] - result["lower_bound_1sigma"]
        assert abs(spread - 2 * result["expected_move_1sigma"]) < 1e-6

    def test_higher_vol_larger_move(self):
        low = expected_move(100.0, 0.1, 30)
        high = expected_move(100.0, 0.5, 30)
        assert high["expected_move_1sigma"] > low["expected_move_1sigma"]


# ---------------------------------------------------------------------------
# Gamma exposure
# ---------------------------------------------------------------------------

class TestGammaExposure:
    def test_returns_expected_keys(self):
        chain = options_chain("AAPL", 150.0)["chain"]
        result = gamma_exposure(chain, 150.0)
        assert "total_gex" in result
        assert "gex_by_strike" in result

    def test_gex_by_strike_list(self):
        chain = options_chain("AAPL", 150.0)["chain"]
        result = gamma_exposure(chain, 150.0)
        assert isinstance(result["gex_by_strike"], list)
        assert len(result["gex_by_strike"]) > 0

    def test_empty_chain(self):
        result = gamma_exposure([], 150.0)
        assert result["total_gex"] == 0.0


# ---------------------------------------------------------------------------
# Volatility skew
# ---------------------------------------------------------------------------

class TestVolatilitySkew:
    def test_returns_expected_keys(self):
        result = volatility_skew(150.0)
        assert "put_25d_iv" in result
        assert "call_25d_iv" in result
        assert "risk_reversal_25d" in result

    def test_ivs_positive(self):
        result = volatility_skew(150.0)
        assert result["put_25d_iv"] > 0
        assert result["call_25d_iv"] > 0

    def test_risk_reversal_is_difference(self):
        result = volatility_skew(150.0)
        assert abs(result["risk_reversal_25d"] - (result["call_25d_iv"] - result["put_25d_iv"])) < 1e-6
