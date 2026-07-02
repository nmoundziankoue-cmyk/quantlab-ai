"""M16 tests — Bond Analytics Engine."""
import math
import pytest
from services.bond_engine import (
    BondEngine, BondSpec, BondType, BondAnalytics, YieldCurve, YieldCurvePoint,
    YieldBucket, CreditBucket, MaturityBucket, get_bond_engine,
)

ENG = BondEngine()

GOVT_BOND = BondSpec(
    isin="US912828T554", ticker="UST10Y", face_value=1000.0,
    coupon_rate=0.0425, coupon_frequency=2, maturity_years=10.0,
    bond_type=BondType.GOVERNMENT, credit_rating="AAA",
)

CORP_BOND = BondSpec(
    isin="US459200101", ticker="APPL4Y", face_value=1000.0,
    coupon_rate=0.055, coupon_frequency=2, maturity_years=4.0,
    bond_type=BondType.CORPORATE, credit_rating="AA",
)


class TestBondPricing:
    def test_price_at_ytm_is_par(self):
        # When YTM equals coupon rate, price ≈ par
        p = ENG.price(GOVT_BOND, GOVT_BOND.coupon_rate)
        assert abs(p - GOVT_BOND.face_value) < 1.0

    def test_price_decreases_with_yield(self):
        p1 = ENG.price(GOVT_BOND, 0.03)
        p2 = ENG.price(GOVT_BOND, 0.05)
        assert p1 > p2

    def test_price_increases_with_lower_yield(self):
        p1 = ENG.price(GOVT_BOND, 0.04)
        p2 = ENG.price(GOVT_BOND, 0.02)
        assert p2 > p1

    def test_ytm_recovers_price(self):
        target = 985.0
        y = ENG.ytm(GOVT_BOND, target)
        recovered = ENG.price(GOVT_BOND, y)
        assert abs(recovered - target) < 0.01

    def test_ytm_at_par(self):
        y = ENG.ytm(GOVT_BOND, GOVT_BOND.face_value)
        assert abs(y - GOVT_BOND.coupon_rate) < 1e-4


class TestDuration:
    def test_macaulay_duration_positive(self):
        y = 0.045
        d = ENG.macaulay_duration(GOVT_BOND, y)
        assert d > 0

    def test_macaulay_less_than_maturity(self):
        y = 0.045
        d = ENG.macaulay_duration(GOVT_BOND, y)
        assert d < GOVT_BOND.maturity_years

    def test_modified_less_than_macaulay(self):
        y = 0.045
        mac = ENG.macaulay_duration(GOVT_BOND, y)
        mod = ENG.modified_duration(GOVT_BOND, y)
        assert mod < mac

    def test_zero_coupon_duration_equals_maturity(self):
        zc = BondSpec("", "ZC", 1000.0, 0.0, 1, 5.0, BondType.GOVERNMENT)
        price = zc.face_value / ((1 + 0.04) ** 5)
        y = ENG.ytm(zc, price)
        d = ENG.macaulay_duration(zc, y)
        assert abs(d - 5.0) < 0.01


class TestConvexity:
    def test_convexity_positive(self):
        y = 0.045
        conv = ENG.convexity(GOVT_BOND, y)
        assert conv > 0

    def test_convexity_increases_lower_yield(self):
        c1 = ENG.convexity(GOVT_BOND, 0.06)
        c2 = ENG.convexity(GOVT_BOND, 0.03)
        assert c2 > c1


class TestDV01:
    def test_dv01_positive(self):
        y = 0.045
        dv = ENG.dv01(GOVT_BOND, y)
        assert dv > 0

    def test_dv01_long_bond_larger(self):
        long_b = BondSpec("", "L", 1000.0, 0.04, 2, 30.0, BondType.GOVERNMENT)
        short_b = BondSpec("", "S", 1000.0, 0.04, 2, 2.0, BondType.GOVERNMENT)
        dv_long = ENG.dv01(long_b, 0.04)
        dv_short = ENG.dv01(short_b, 0.04)
        assert dv_long > dv_short


class TestAccruedInterest:
    def test_zero_fraction(self):
        ai = ENG.accrued_interest(GOVT_BOND, 0.0)
        assert ai == 0.0

    def test_half_fraction(self):
        ai = ENG.accrued_interest(GOVT_BOND, 0.5)
        period_coupon = GOVT_BOND.face_value * GOVT_BOND.coupon_rate / GOVT_BOND.coupon_frequency
        assert abs(ai - period_coupon * 0.5) < 1e-9


class TestBuckets:
    def test_yield_bucket_very_low(self):
        assert ENG.yield_bucket(0.015) == YieldBucket.VERY_LOW

    def test_yield_bucket_low(self):
        assert ENG.yield_bucket(0.025) == YieldBucket.LOW

    def test_yield_bucket_moderate(self):
        assert ENG.yield_bucket(0.035) == YieldBucket.MODERATE

    def test_yield_bucket_high(self):
        assert ENG.yield_bucket(0.05) == YieldBucket.HIGH

    def test_yield_bucket_very_high(self):
        assert ENG.yield_bucket(0.08) == YieldBucket.VERY_HIGH

    def test_credit_bucket_aaa(self):
        assert ENG.credit_bucket("AAA") == CreditBucket.AAA

    def test_credit_bucket_aa(self):
        assert ENG.credit_bucket("AA+") == CreditBucket.AA

    def test_credit_bucket_bbb(self):
        assert ENG.credit_bucket("BBB-") == CreditBucket.BBB

    def test_credit_bucket_not_rated(self):
        assert ENG.credit_bucket("NR") == CreditBucket.NOT_RATED

    def test_credit_bucket_ccc(self):
        assert ENG.credit_bucket("CCC+") == CreditBucket.CCC_AND_BELOW

    def test_maturity_short(self):
        assert ENG.maturity_bucket(1.5) == MaturityBucket.SHORT

    def test_maturity_medium(self):
        assert ENG.maturity_bucket(5.0) == MaturityBucket.MEDIUM

    def test_maturity_long(self):
        assert ENG.maturity_bucket(10.0) == MaturityBucket.LONG

    def test_maturity_ultra_long(self):
        assert ENG.maturity_bucket(30.0) == MaturityBucket.ULTRA_LONG


class TestAnalyze:
    def test_returns_bond_analytics(self):
        result = ENG.analyze(GOVT_BOND, 985.0, risk_free_rate=0.042)
        assert isinstance(result, BondAnalytics)

    def test_ytm_positive(self):
        result = ENG.analyze(GOVT_BOND, 985.0)
        assert result.ytm > 0

    def test_dirty_price_gte_clean(self):
        result = ENG.analyze(GOVT_BOND, 985.0, accrual_fraction=0.5)
        assert result.dirty_price >= result.price

    def test_to_dict(self):
        d = ENG.analyze(GOVT_BOND, 985.0).to_dict()
        assert "ytm" in d and "duration" in d and "convexity" in d


class TestYieldCurve:
    def setup_method(self):
        self.curve = YieldCurve("US Treasury", [
            YieldCurvePoint(0.25, 0.052, "3M"),
            YieldCurvePoint(1.0,  0.050, "1Y"),
            YieldCurvePoint(5.0,  0.045, "5Y"),
            YieldCurvePoint(10.0, 0.043, "10Y"),
            YieldCurvePoint(30.0, 0.044, "30Y"),
        ])

    def test_interpolate_within_range(self):
        y = self.curve.interpolate(2.5)
        assert 0.043 <= y <= 0.050

    def test_interpolate_below_min_returns_first(self):
        y = self.curve.interpolate(0.1)
        assert abs(y - 0.052) < 1e-9

    def test_interpolate_above_max_returns_last(self):
        y = self.curve.interpolate(40.0)
        assert abs(y - 0.044) < 1e-9

    def test_spread_negative_for_inverted(self):
        inv = YieldCurve("INV", [
            YieldCurvePoint(1.0, 0.055, "1Y"),
            YieldCurvePoint(10.0, 0.040, "10Y"),
        ])
        assert inv.is_inverted()

    def test_to_dict(self):
        d = self.curve.to_dict()
        assert "spread" in d and "inverted" in d


class TestPortfolioBondMetrics:
    def test_portfolio_duration_float(self):
        bonds = [GOVT_BOND, CORP_BOND]
        prices = [985.0, 1015.0]
        weights = [0.6, 0.4]
        dur = ENG.portfolio_duration(bonds, prices, weights)
        assert isinstance(dur, float) and dur > 0

    def test_yield_bucket_breakdown_dict(self):
        bonds = [GOVT_BOND, CORP_BOND]
        prices = [985.0, 1015.0]
        weights = [0.6, 0.4]
        bkts = ENG.yield_bucket_breakdown(bonds, prices, weights)
        assert isinstance(bkts, dict) and sum(bkts.values()) > 0

    def test_credit_bucket_breakdown_dict(self):
        bonds = [GOVT_BOND, CORP_BOND]
        weights = [0.6, 0.4]
        bkts = ENG.credit_bucket_breakdown(bonds, weights)
        assert isinstance(bkts, dict)


class TestSingleton:
    def test_singleton(self):
        a = get_bond_engine()
        b = get_bond_engine()
        assert a is b
