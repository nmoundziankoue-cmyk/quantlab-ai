"""Tests for M17 Performance Attribution Engine (BHB, Brinson-Fachler, factor)."""
import pytest
from services.performance_attribution import (
    PerformanceAttributionEngine, AttributionModel,
    Holding, FactorExposure, BrinsonResult, FactorAttributionResult,
    FullAttributionReport,
)


def _eng():
    return PerformanceAttributionEngine()


def _holdings():
    return [
        Holding(category="Technology",  portfolio_weight=0.45, benchmark_weight=0.38, portfolio_return=0.08, benchmark_return=0.05),
        Holding(category="Financials",  portfolio_weight=0.15, benchmark_weight=0.10, portfolio_return=0.03, benchmark_return=0.04),
        Holding(category="Energy",      portfolio_weight=0.10, benchmark_weight=0.08, portfolio_return=-0.02, benchmark_return=0.01),
        Holding(category="Cash",        portfolio_weight=0.30, benchmark_weight=0.44, portfolio_return=0.005, benchmark_return=0.005),
    ]


def _bench_return():
    return sum(h.benchmark_weight * h.benchmark_return for h in _holdings())


def _factors():
    return [
        FactorExposure(factor_name="Market",   portfolio_exposure=1.05, benchmark_exposure=1.00, factor_return=0.04),
        FactorExposure(factor_name="Momentum", portfolio_exposure=0.30, benchmark_exposure=0.00, factor_return=0.02),
        FactorExposure(factor_name="Value",    portfolio_exposure=-0.10, benchmark_exposure=0.00, factor_return=0.01),
    ]


# ---------------------------------------------------------------------------
# brinson_attribution — BHB
# ---------------------------------------------------------------------------

class TestBrinsonBHB:
    def test_returns_brinson_result(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        assert isinstance(r, BrinsonResult)

    def test_model_label(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        assert r.model == AttributionModel.BRINSON

    def test_active_return_equals_portfolio_minus_benchmark(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        port_return = sum(h.portfolio_weight * h.portfolio_return for h in _holdings())
        bench_return = _bench_return()
        assert r.active_return == pytest.approx(port_return - bench_return, abs=1e-8)

    def test_effects_sum_to_active_return(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        total = r.total_allocation + r.total_selection + r.total_interaction
        assert total == pytest.approx(r.active_return, abs=1e-8)

    def test_effects_count_equals_holdings(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        assert len(r.category_effects) == len(_holdings())

    def test_allocation_formula_bhb(self):
        e = _eng()
        bench_return = _bench_return()
        r = e.brinson_attribution(_holdings(), bench_return, AttributionModel.BRINSON)
        expected_total_alloc = sum(
            (h.portfolio_weight - h.benchmark_weight) * (h.benchmark_return - bench_return)
            for h in _holdings()
        )
        assert r.total_allocation == pytest.approx(expected_total_alloc, abs=1e-8)

    def test_selection_formula_bhb(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        expected_total_sel = sum(
            h.benchmark_weight * (h.portfolio_return - h.benchmark_return)
            for h in _holdings()
        )
        assert r.total_selection == pytest.approx(expected_total_sel, abs=1e-8)

    def test_interaction_formula_bhb(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        expected_total_inter = sum(
            (h.portfolio_weight - h.benchmark_weight) * (h.portfolio_return - h.benchmark_return)
            for h in _holdings()
        )
        assert r.total_interaction == pytest.approx(expected_total_inter, abs=1e-8)

    def test_empty_holdings_raises(self):
        e = _eng()
        with pytest.raises(ValueError):
            e.brinson_attribution([], 0.05, AttributionModel.BRINSON)


# ---------------------------------------------------------------------------
# brinson_attribution — Brinson-Fachler
# ---------------------------------------------------------------------------

class TestBrinsonFachler:
    def test_returns_brinson_result(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON_FACHLER)
        assert isinstance(r, BrinsonResult)

    def test_active_return_same_as_bhb(self):
        e = _eng()
        r_bhb = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON)
        r_bf = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON_FACHLER)
        assert r_bhb.active_return == pytest.approx(r_bf.active_return, abs=1e-8)

    def test_bf_interaction_zero(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON_FACHLER)
        assert r.total_interaction == pytest.approx(0.0, abs=1e-10)

    def test_bf_effects_sum_to_active_return(self):
        e = _eng()
        r = e.brinson_attribution(_holdings(), _bench_return(), AttributionModel.BRINSON_FACHLER)
        total = r.total_allocation + r.total_selection + r.total_interaction
        assert total == pytest.approx(r.active_return, abs=1e-8)


# ---------------------------------------------------------------------------
# factor_attribution
# ---------------------------------------------------------------------------

class TestFactorAttribution:
    def test_returns_list_of_results(self):
        e = _eng()
        results = e.factor_attribution(_factors())
        assert isinstance(results, list)
        assert len(results) == len(_factors())

    def test_attribution_direction(self):
        e = _eng()
        results = e.factor_attribution(_factors())
        market = next(r for r in results if r.factor_name == "Market")
        expected = (1.05 - 1.00) * 0.04
        assert market.attribution == pytest.approx(expected, abs=1e-8)

    def test_attribution_sorted_by_absolute_value(self):
        e = _eng()
        results = e.factor_attribution(_factors())
        abs_attrs = [abs(r.attribution) for r in results]
        assert abs_attrs == sorted(abs_attrs, reverse=True)

    def test_empty_factors_raises(self):
        e = _eng()
        with pytest.raises(ValueError):
            e.factor_attribution([])


# ---------------------------------------------------------------------------
# full_report
# ---------------------------------------------------------------------------

class TestFullReport:
    def test_returns_full_attribution_report(self):
        e = _eng()
        r = e.full_report(_holdings(), _bench_return())
        assert isinstance(r, FullAttributionReport)

    def test_portfolio_return_computed(self):
        e = _eng()
        r = e.full_report(_holdings(), _bench_return())
        expected = sum(h.portfolio_weight * h.portfolio_return for h in _holdings())
        assert r.portfolio_return == pytest.approx(expected, abs=1e-8)

    def test_benchmark_return_stored(self):
        e = _eng()
        br = _bench_return()
        r = e.full_report(_holdings(), br)
        assert r.benchmark_return == pytest.approx(br, abs=1e-8)

    def test_brinson_populated(self):
        e = _eng()
        r = e.full_report(_holdings(), _bench_return())
        assert r.brinson is not None
        assert isinstance(r.brinson, BrinsonResult)

    def test_active_return_consistent(self):
        e = _eng()
        r = e.full_report(_holdings(), _bench_return())
        assert r.active_return == pytest.approx(r.portfolio_return - r.benchmark_return, abs=1e-8)


# ---------------------------------------------------------------------------
# information_ratio / tracking_error
# ---------------------------------------------------------------------------

class TestInfoRatioTrackingError:
    def test_information_ratio_positive(self):
        e = _eng()
        active = [0.001, 0.002, -0.0005, 0.003, 0.001, -0.001, 0.002]
        ir = e.information_ratio(active)
        assert ir > 0

    def test_tracking_error_positive(self):
        e = _eng()
        active = [0.001, 0.002, -0.0005, 0.003, 0.001]
        te = e.tracking_error(active)
        assert te > 0

    def test_tracking_error_zero_for_constant(self):
        e = _eng()
        active = [0.001] * 20
        te = e.tracking_error(active)
        assert te == pytest.approx(0.0, abs=1e-10)

    def test_decompose_active_return(self):
        e = _eng()
        decomposed = e.decompose_active_return(_holdings(), _bench_return())
        assert "allocation_effect" in decomposed
        assert "selection_effect" in decomposed
