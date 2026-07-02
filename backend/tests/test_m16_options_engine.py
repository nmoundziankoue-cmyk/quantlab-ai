"""M16 tests — Options Analytics Engine (pure Python BS)."""
import math
import pytest
from services.options_engine import (
    OptionsEngine, OptionSpec, OptionType, OptionStyle, Greeks,
    OptionAnalytics, MaxPainResult, GammaExposure, IVSurface,
    get_options_engine,
)

ENG = OptionsEngine()

CALL = OptionSpec("SPY", OptionType.CALL, 450.0, 0.25, open_interest=1000, volume=500)
PUT  = OptionSpec("SPY", OptionType.PUT,  450.0, 0.25, open_interest=800,  volume=400)
S = 450.0
K = 450.0
T = 0.25
R = 0.05
IV = 0.20


class TestNormCDF:
    def test_cdf_half(self):
        from services.options_engine import _norm_cdf
        assert abs(_norm_cdf(0.0) - 0.5) < 1e-4

    def test_cdf_positive(self):
        from services.options_engine import _norm_cdf
        assert _norm_cdf(1.96) > 0.97

    def test_cdf_symmetry(self):
        from services.options_engine import _norm_cdf
        assert abs(_norm_cdf(1.0) + _norm_cdf(-1.0) - 1.0) < 1e-6

    def test_cdf_large_pos(self):
        from services.options_engine import _norm_cdf
        assert _norm_cdf(5.0) > 0.999

    def test_cdf_large_neg(self):
        from services.options_engine import _norm_cdf
        assert _norm_cdf(-5.0) < 0.001


class TestBSPrice:
    def test_call_positive(self):
        p = ENG.bs_price(S, K, T, R, IV, OptionType.CALL)
        assert p > 0

    def test_put_positive(self):
        p = ENG.bs_price(S, K, T, R, IV, OptionType.PUT)
        assert p > 0

    def test_put_call_parity(self):
        c = ENG.bs_price(S, K, T, R, IV, OptionType.CALL)
        p = ENG.bs_price(S, K, T, R, IV, OptionType.PUT)
        disc = math.exp(-R * T)
        lhs = c - p
        rhs = S - K * disc
        assert abs(lhs - rhs) < 0.01

    def test_call_atm_intrinsic_le_price(self):
        p = ENG.bs_price(S, K, T, R, IV, OptionType.CALL)
        intrinsic = max(0.0, S - K)
        assert p >= intrinsic

    def test_deep_itm_call_higher_than_otm(self):
        itm = ENG.bs_price(S, K - 50, T, R, IV, OptionType.CALL)
        otm = ENG.bs_price(S, K + 50, T, R, IV, OptionType.CALL)
        assert itm > otm

    def test_zero_expiry_call_returns_intrinsic(self):
        p = ENG.bs_price(500.0, 450.0, 0.0, R, IV, OptionType.CALL)
        assert abs(p - 50.0) < 1e-6

    def test_zero_expiry_put_otm_returns_zero(self):
        p = ENG.bs_price(S, K - 20, 0.0, R, IV, OptionType.PUT)
        assert p == 0.0


class TestBSGreeks:
    def test_call_delta_in_range(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.CALL)
        assert 0.0 <= g.delta <= 1.0

    def test_put_delta_in_range(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.PUT)
        assert -1.0 <= g.delta <= 0.0

    def test_gamma_positive(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.CALL)
        assert g.gamma > 0

    def test_call_put_gamma_equal(self):
        gc = ENG.bs_greeks(S, K, T, R, IV, OptionType.CALL)
        gp = ENG.bs_greeks(S, K, T, R, IV, OptionType.PUT)
        assert abs(gc.gamma - gp.gamma) < 1e-6

    def test_theta_negative_for_call(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.CALL)
        assert g.theta < 0

    def test_vega_positive(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.CALL)
        assert g.vega > 0

    def test_call_rho_positive(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.CALL)
        assert g.rho > 0

    def test_put_rho_negative(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.PUT)
        assert g.rho < 0

    def test_to_dict(self):
        g = ENG.bs_greeks(S, K, T, R, IV, OptionType.CALL)
        d = g.to_dict()
        assert all(k in d for k in ("delta", "gamma", "theta", "vega", "rho", "vanna", "charm"))


class TestImpliedVolatility:
    def test_iv_recovers_price(self):
        market_price = ENG.bs_price(S, K, T, R, 0.25, OptionType.CALL)
        iv = ENG.implied_volatility(market_price, S, K, T, R, OptionType.CALL)
        assert abs(iv - 0.25) < 1e-3

    def test_iv_recovers_put_price(self):
        market_price = ENG.bs_price(S, K, T, R, 0.30, OptionType.PUT)
        iv = ENG.implied_volatility(market_price, S, K, T, R, OptionType.PUT)
        assert abs(iv - 0.30) < 1e-3

    def test_higher_price_higher_iv(self):
        iv1 = ENG.implied_volatility(15.0, S, K, T, R, OptionType.CALL)
        iv2 = ENG.implied_volatility(25.0, S, K, T, R, OptionType.CALL)
        assert iv2 > iv1


class TestIVRank:
    def test_iv_rank_at_high_end(self):
        history = [0.10, 0.15, 0.20, 0.25, 0.30]
        rank = ENG.iv_rank(0.30, history)
        assert abs(rank - 100.0) < 0.1

    def test_iv_rank_at_low_end(self):
        history = [0.10, 0.15, 0.20, 0.25, 0.30]
        rank = ENG.iv_rank(0.10, history)
        assert abs(rank - 0.0) < 0.1

    def test_iv_rank_midpoint(self):
        history = [0.10, 0.30]
        rank = ENG.iv_rank(0.20, history)
        assert abs(rank - 50.0) < 0.1

    def test_iv_percentile_fraction(self):
        history = [0.10, 0.15, 0.20, 0.25, 0.30]
        pct = ENG.iv_percentile(0.20, history)
        assert 0.0 <= pct <= 100.0

    def test_iv_rank_empty_history(self):
        rank = ENG.iv_rank(0.25, [])
        assert rank == 50.0


class TestAnalyze:
    def test_returns_option_analytics(self):
        result = ENG.analyze(CALL, S, IV, R)
        assert isinstance(result, OptionAnalytics)

    def test_is_itm_atm(self):
        result = ENG.analyze(CALL, S, IV, R)
        assert not result.is_itm  # ATM call with S == K => not ITM

    def test_itm_call(self):
        itm = OptionSpec("SPY", OptionType.CALL, 400.0, 0.25)
        result = ENG.analyze(itm, S, IV, R)
        assert result.is_itm

    def test_intrinsic_value_correct(self):
        itm = OptionSpec("SPY", OptionType.CALL, 430.0, 0.25)
        result = ENG.analyze(itm, S, IV, R)
        assert abs(result.intrinsic_value - 20.0) < 0.01

    def test_to_dict(self):
        d = ENG.analyze(CALL, S, IV, R).to_dict()
        assert "iv" in d and "greeks" in d and "moneyness" in d


class TestMaxPain:
    def setup_method(self):
        self.calls = [
            OptionSpec("SPY", OptionType.CALL, 440.0, 0.25, open_interest=500),
            OptionSpec("SPY", OptionType.CALL, 450.0, 0.25, open_interest=1000),
            OptionSpec("SPY", OptionType.CALL, 460.0, 0.25, open_interest=300),
        ]
        self.puts = [
            OptionSpec("SPY", OptionType.PUT, 440.0, 0.25, open_interest=400),
            OptionSpec("SPY", OptionType.PUT, 450.0, 0.25, open_interest=800),
            OptionSpec("SPY", OptionType.PUT, 460.0, 0.25, open_interest=200),
        ]

    def test_returns_max_pain_result(self):
        mp = ENG.max_pain("SPY", 0.25, self.calls, self.puts)
        assert isinstance(mp, MaxPainResult)

    def test_max_pain_strike_in_set(self):
        mp = ENG.max_pain("SPY", 0.25, self.calls, self.puts)
        all_strikes = {o.strike for o in self.calls + self.puts}
        assert mp.max_pain_strike in all_strikes

    def test_to_dict(self):
        mp = ENG.max_pain("SPY", 0.25, self.calls, self.puts)
        d = mp.to_dict()
        assert "max_pain_strike" in d and "total_pain_by_strike" in d


class TestGammaExposure:
    def setup_method(self):
        self.calls = [
            OptionSpec("SPY", OptionType.CALL, 440.0, 0.25, open_interest=1000),
            OptionSpec("SPY", OptionType.CALL, 450.0, 0.25, open_interest=500),
        ]
        self.puts = [
            OptionSpec("SPY", OptionType.PUT, 440.0, 0.25, open_interest=800),
            OptionSpec("SPY", OptionType.PUT, 450.0, 0.25, open_interest=600),
        ]
        self.iv_map = {440.0: 0.22, 450.0: 0.20}

    def test_returns_gamma_exposure(self):
        gex = ENG.gamma_exposure("SPY", S, self.calls, self.puts, self.iv_map)
        assert isinstance(gex, GammaExposure)

    def test_has_call_put_gamma(self):
        gex = ENG.gamma_exposure("SPY", S, self.calls, self.puts, self.iv_map)
        assert gex.call_gamma != 0.0 or gex.put_gamma != 0.0

    def test_per_strike_keys(self):
        gex = ENG.gamma_exposure("SPY", S, self.calls, self.puts, self.iv_map)
        assert 440.0 in gex.gamma_by_strike and 450.0 in gex.gamma_by_strike

    def test_to_dict(self):
        gex = ENG.gamma_exposure("SPY", S, self.calls, self.puts, self.iv_map)
        d = gex.to_dict()
        assert "net_gamma_exposure" in d and "flip_point" in d


class TestIVSurface:
    def test_build_iv_surface(self):
        market_prices = {
            (430.0, 0.25): (18.0, OptionType.CALL),
            (450.0, 0.25): (12.0, OptionType.CALL),
            (470.0, 0.25): (7.0,  OptionType.CALL),
            (430.0, 0.5):  (22.0, OptionType.CALL),
            (450.0, 0.5):  (17.0, OptionType.CALL),
            (470.0, 0.5):  (13.0, OptionType.CALL),
        }
        surf = ENG.build_iv_surface("SPY", market_prices, S, R)
        assert isinstance(surf, IVSurface)
        assert surf.ticker == "SPY"
        assert len(surf.strikes) > 0 and len(surf.expiries) > 0


class TestSingleton:
    def test_singleton(self):
        a = get_options_engine()
        b = get_options_engine()
        assert a is b
