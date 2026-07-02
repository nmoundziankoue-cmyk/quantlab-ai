"""Tests for M15 EventStudy — abnormal returns, CAR, CAAR, t-stat, bootstrap CI."""
import pytest
from services.event_study import (
    AbnormalReturnSeries,
    EventStudy,
    EventStudyResult,
    EventWindow,
    _mean,
    _std,
    _t_stat,
    _approx_p_value,
    _bootstrap_mean_ci,
    _confidence_interval,
)


class TestStatsPrimitives:
    def test_mean_basic(self):
        assert _mean([1.0, 2.0, 3.0]) == 2.0

    def test_mean_single(self):
        assert _mean([5.0]) == 5.0

    def test_mean_empty_returns_zero(self):
        assert _mean([]) == 0.0

    def test_std_known(self):
        # Sample std of [2,4,4,4,5,5,7,9] ≈ 2.138 (n-1 Bessel correction)
        result = _std([2, 4, 4, 4, 5, 5, 7, 9])
        assert abs(result - 2.138) < 0.01

    def test_std_zero_for_constant(self):
        assert _std([3.0, 3.0, 3.0]) == 0.0

    def test_t_stat_nonzero(self):
        values = [0.01, 0.02, 0.015, 0.018, 0.012]
        ts = _t_stat(values)
        assert ts > 0

    def test_t_stat_zero_std_returns_zero(self):
        assert _t_stat([1.0, 1.0, 1.0]) == 0.0

    def test_approx_p_value_large_t(self):
        p = _approx_p_value(10.0, df=100)
        assert p < 0.05

    def test_approx_p_value_zero_t(self):
        p = _approx_p_value(0.0, df=10)
        assert p == 1.0

    def test_approx_p_value_between_0_1(self):
        p = _approx_p_value(2.5, df=20)
        assert 0.0 <= p <= 1.0

    def test_bootstrap_mean_ci_returns_tuple(self):
        lo, hi = _bootstrap_mean_ci([0.01, 0.02, 0.015, 0.018, -0.002], seed=42)
        assert isinstance(lo, float)
        assert isinstance(hi, float)

    def test_bootstrap_mean_ci_lo_le_hi(self):
        lo, hi = _bootstrap_mean_ci([0.01, 0.02, 0.015], seed=42)
        assert lo <= hi

    def test_bootstrap_deterministic(self):
        vals = [0.01, 0.02, -0.01, 0.005, 0.03]
        a = _bootstrap_mean_ci(vals, seed=42)
        b = _bootstrap_mean_ci(vals, seed=42)
        assert a == b

    def test_bootstrap_different_seeds_differ(self):
        vals = [0.01, 0.02, -0.01, 0.005, 0.03]
        a = _bootstrap_mean_ci(vals, seed=42)
        b = _bootstrap_mean_ci(vals, seed=99)
        assert a != b

    def test_confidence_interval_returns_tuple(self):
        lo, hi = _confidence_interval([0.01, 0.02, 0.015, 0.018, 0.022])
        assert lo <= hi


class TestEventStudy:
    def setup_method(self):
        self.study = EventStudy()

    def _actual(self):
        # 7-element window for W3 (half=3, total=7)
        return [0.001, -0.002, 0.003, 0.015, 0.010, 0.008, 0.005]

    def _expected(self):
        return [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001]

    def test_compute_ar_series_returns_dataclass(self):
        result = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        assert isinstance(result, AbnormalReturnSeries)

    def test_ar_series_ticker(self):
        result = self.study.compute_ar_series("MSFT", self._actual(), self._expected(), EventWindow.W3)
        assert result.ticker == "MSFT"

    def test_ar_series_car_positive_for_positive_returns(self):
        actual = [0.01] * 7
        expected = [0.001] * 7
        result = self.study.compute_ar_series("AAPL", actual, expected, EventWindow.W3)
        assert result.car > 0

    def test_ar_series_window_stored(self):
        result = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W10)
        assert result.window == EventWindow.W10

    def test_ar_series_has_ar_series(self):
        result = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        assert isinstance(result.ar_series, list)
        assert len(result.ar_series) > 0

    def test_ar_series_t_stat_present(self):
        result = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        assert result.t_stat is not None

    def test_ar_series_p_value_between_0_1(self):
        result = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        assert 0.0 <= result.p_value <= 1.0

    def test_compute_cross_sectional_returns_result(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        ar2 = self.study.compute_ar_series("MSFT", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1, ar2])
        assert isinstance(result, EventStudyResult)

    def test_cross_sectional_n_securities(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        ar2 = self.study.compute_ar_series("MSFT", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1, ar2])
        assert result.n_securities == 2

    def test_cross_sectional_aar_is_float(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1])
        assert isinstance(result.aar, float)

    def test_cross_sectional_caar_is_float(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1])
        assert isinstance(result.caar, float)

    def test_cross_sectional_ci_bounds(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1])
        assert result.ci_95_low <= result.ci_95_high

    def test_cross_sectional_bootstrap_ci(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        ar2 = self.study.compute_ar_series("GOOG", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1, ar2])
        assert result.bootstrap_ci_low <= result.bootstrap_ci_high

    def test_cross_sectional_significant_field_is_bool(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1])
        assert isinstance(result.significant, bool)

    def test_run_multi_window_returns_dict(self):
        actual = [0.005] * 21  # enough for W10
        expected = [0.001] * 21
        result = self.study.run_multi_window(
            event_id="evt-001",
            tickers=["AAPL", "MSFT"],
            actual_returns_map={"AAPL": actual, "MSFT": actual},
            expected_returns_map={"AAPL": expected, "MSFT": expected},
            windows=[EventWindow.W3, EventWindow.W5],
        )
        assert isinstance(result, dict)

    def test_run_multi_window_keys_are_windows(self):
        actual = [0.005] * 11
        expected = [0.001] * 11
        result = self.study.run_multi_window(
            event_id="evt-001",
            tickers=["AAPL"],
            actual_returns_map={"AAPL": actual},
            expected_returns_map={"AAPL": expected},
            windows=[EventWindow.W1, EventWindow.W3],
        )
        assert EventWindow.W1 in result or str(EventWindow.W1) in result or EventWindow.W1.value in result

    def test_event_window_enum_values(self):
        assert EventWindow.W1.value == "[-1,+1]"
        assert EventWindow.W3.value == "[-3,+3]"
        assert EventWindow.W5.value == "[-5,+5]"
        assert EventWindow.W10.value == "[-10,+10]"

    def test_cross_sectional_p_value_range(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1])
        assert 0.0 <= result.p_value <= 1.0

    def test_cross_sectional_stores_ar_list(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-001", [ar1])
        assert len(result.ar_series_list) == 1

    def test_cross_sectional_event_id_stored(self):
        ar1 = self.study.compute_ar_series("AAPL", self._actual(), self._expected(), EventWindow.W3)
        result = self.study.compute_cross_sectional("evt-custom", [ar1])
        assert result.event_id == "evt-custom"
