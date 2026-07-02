"""M16 tests — Futures Analytics Engine."""
import math
import pytest
from services.futures_engine import (
    FuturesEngine, FuturesContract, TermStructure, RollYield,
    FuturesBasis, CarryScore, MarketStructure, AssetClass, get_futures_engine,
)

ENG = FuturesEngine()

CL1 = FuturesContract("CL", "CLZ24", 0.0833, 80.0, open_interest=50000, volume=30000, asset_class=AssetClass.ENERGY)
CL2 = FuturesContract("CL", "CLF25", 0.1667, 81.5, open_interest=30000, volume=20000, asset_class=AssetClass.ENERGY)
CL3 = FuturesContract("CL", "CLG25", 0.2500, 82.5, open_interest=15000, volume=10000, asset_class=AssetClass.ENERGY)

ES1 = FuturesContract("ES", "ESM24", 0.0833, 5000.0, open_interest=100000, asset_class=AssetClass.EQUITY_INDEX)
ES2 = FuturesContract("ES", "ESU24", 0.3333, 4980.0, open_interest=60000, asset_class=AssetClass.EQUITY_INDEX)

CONTRACTS_CONTANGO = [CL1, CL2, CL3]
CONTRACTS_BACKW    = [
    FuturesContract("GC", "GCZ24", 0.0833, 1950.0, asset_class=AssetClass.METALS),
    FuturesContract("GC", "GCG25", 0.3333, 1920.0, asset_class=AssetClass.METALS),
]


class TestTermStructure:
    def test_returns_term_structure(self):
        ts = ENG.term_structure(CONTRACTS_CONTANGO)
        assert isinstance(ts, TermStructure)

    def test_sorted_by_expiry(self):
        ts = ENG.term_structure([CL3, CL1, CL2])  # unsorted input
        expiries = [c.expiry_years for c in ts.contracts]
        assert expiries == sorted(expiries)

    def test_contango_detected(self):
        ts = ENG.term_structure(CONTRACTS_CONTANGO)
        assert ts.structure == MarketStructure.CONTANGO

    def test_backwardation_detected(self):
        ts = ENG.term_structure(CONTRACTS_BACKW)
        assert ts.structure == MarketStructure.BACKWARDATION

    def test_flat_detected(self):
        c1 = FuturesContract("XX", "XXA", 0.1, 100.0)
        c2 = FuturesContract("XX", "XXB", 0.2, 100.0)
        ts = ENG.term_structure([c1, c2])
        assert ts.structure == MarketStructure.FLAT

    def test_front_back_prices(self):
        ts = ENG.term_structure(CONTRACTS_CONTANGO)
        assert ts.front_price == CL1.price
        assert ts.back_price == CL3.price

    def test_curve_points_length(self):
        ts = ENG.term_structure(CONTRACTS_CONTANGO)
        assert len(ts.curve_points) == len(CONTRACTS_CONTANGO)

    def test_single_contract_flat(self):
        ts = ENG.term_structure([CL1])
        assert ts.structure == MarketStructure.FLAT

    def test_empty_contracts_raises(self):
        with pytest.raises((ValueError, Exception)):
            ENG.term_structure([])

    def test_to_dict(self):
        d = ENG.term_structure(CONTRACTS_CONTANGO).to_dict()
        assert "structure" in d and "slope_percent" in d


class TestRollYield:
    def test_returns_roll_yield(self):
        ry = ENG.roll_yield(CL1, CL2)
        assert isinstance(ry, RollYield)

    def test_near_far_contracts(self):
        ry = ENG.roll_yield(CL1, CL2)
        assert ry.near_contract == CL1.contract_code
        assert ry.far_contract == CL2.contract_code

    def test_contango_negative_roll(self):
        # Far price > near price => contango => negative roll yield
        ry = ENG.roll_yield(CL1, CL2)
        assert ry.structure == MarketStructure.CONTANGO
        assert ry.roll_yield_annualised < 0

    def test_backwardation_positive_roll(self):
        near = FuturesContract("GC", "GCZ24", 0.0833, 1950.0, asset_class=AssetClass.METALS)
        far  = FuturesContract("GC", "GCG25", 0.3333, 1920.0, asset_class=AssetClass.METALS)
        ry = ENG.roll_yield(near, far)
        assert ry.structure == MarketStructure.BACKWARDATION
        assert ry.roll_yield_annualised > 0

    def test_to_dict(self):
        d = ENG.roll_yield(CL1, CL2).to_dict()
        assert "roll_yield_annualised" in d and "structure" in d

    def test_roll_yield_curve_length(self):
        ts = ENG.term_structure(CONTRACTS_CONTANGO)
        ryc = ENG.roll_yield_curve(ts)
        assert len(ryc) == len(CONTRACTS_CONTANGO) - 1


class TestBasis:
    def test_returns_futures_basis(self):
        b = ENG.basis("CL", 79.5, CL1)
        assert isinstance(b, FuturesBasis)

    def test_basis_calculation(self):
        b = ENG.basis("CL", 79.5, CL1)
        assert abs(b.basis - (79.5 - CL1.price)) < 1e-5

    def test_basis_percent(self):
        b = ENG.basis("CL", 79.5, CL1)
        expected = (79.5 - CL1.price) / 79.5
        assert abs(b.basis_percent - expected) < 1e-5

    def test_convergence_days_positive(self):
        b = ENG.basis("CL", 79.5, CL1)
        assert b.convergence_days > 0

    def test_to_dict(self):
        d = ENG.basis("CL", 79.5, CL1).to_dict()
        assert "basis" in d and "cost_of_carry" in d


class TestFairValue:
    def test_fair_value_above_spot_with_positive_carry(self):
        fv = ENG.fair_value(100.0, risk_free_rate=0.05, dividend_yield=0.0,
                            storage_cost=0.0, convenience_yield=0.0, expiry_years=1.0)
        expected = 100.0 * math.exp(0.05)
        assert abs(fv - expected) < 0.001

    def test_fair_value_below_spot_with_high_convenience(self):
        fv = ENG.fair_value(100.0, risk_free_rate=0.02, dividend_yield=0.0,
                            storage_cost=0.0, convenience_yield=0.10, expiry_years=1.0)
        assert fv < 100.0

    def test_fair_value_at_spot_when_carry_zero(self):
        fv = ENG.fair_value(100.0, risk_free_rate=0.0, dividend_yield=0.0,
                            storage_cost=0.0, convenience_yield=0.0, expiry_years=1.0)
        assert abs(fv - 100.0) < 1e-6


class TestCarryScores:
    def setup_method(self):
        self.carry_map = {
            "CL": 0.08, "GC": -0.02, "ES": 0.03, "ZB": -0.05, "BTC": 0.15
        }

    def test_returns_list(self):
        scores = ENG.carry_scores(self.carry_map)
        assert isinstance(scores, list)

    def test_length_matches(self):
        scores = ENG.carry_scores(self.carry_map)
        assert len(scores) == len(self.carry_map)

    def test_sorted_descending(self):
        scores = ENG.carry_scores(self.carry_map)
        carries = [s.carry for s in scores]
        assert carries == sorted(carries, reverse=True)

    def test_rank_one_is_highest(self):
        scores = ENG.carry_scores(self.carry_map)
        assert scores[0].rank == 1
        assert scores[0].signal == "long"

    def test_lowest_carry_is_short(self):
        scores = ENG.carry_scores(self.carry_map)
        lowest = min(scores, key=lambda s: s.carry)
        assert lowest.signal == "short"

    def test_to_dict(self):
        scores = ENG.carry_scores(self.carry_map)
        d = scores[0].to_dict()
        assert "carry" in d and "carry_zscore" in d and "signal" in d

    def test_empty_returns_empty(self):
        assert ENG.carry_scores({}) == []


class TestOpenInterest:
    def test_returns_dict(self):
        oi = ENG.open_interest_summary(CONTRACTS_CONTANGO)
        assert isinstance(oi, dict)

    def test_total_oi_sum(self):
        oi = ENG.open_interest_summary(CONTRACTS_CONTANGO)
        expected = sum(c.open_interest for c in CONTRACTS_CONTANGO)
        assert oi["total_oi"] == expected

    def test_dominant_contract(self):
        oi = ENG.open_interest_summary(CONTRACTS_CONTANGO)
        assert oi["dominant_contract"] == CL1.contract_code  # highest OI

    def test_empty_contracts(self):
        oi = ENG.open_interest_summary([])
        assert oi["total_oi"] == 0


class TestSeasonality:
    def test_winter(self):
        assert ENG.seasonality_bucket(1) == "winter"
        assert ENG.seasonality_bucket(12) == "winter"

    def test_spring(self):
        assert ENG.seasonality_bucket(4) == "spring"

    def test_summer(self):
        assert ENG.seasonality_bucket(7) == "summer"

    def test_autumn(self):
        assert ENG.seasonality_bucket(10) == "autumn"


class TestSingleton:
    def test_singleton(self):
        a = get_futures_engine()
        b = get_futures_engine()
        assert a is b
