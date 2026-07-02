"""Tests for execution algorithms — pure math, no DB, no network."""
from __future__ import annotations

from decimal import Decimal

import pytest

from services.execution_algorithms import (
    compute_adaptive,
    compute_arrival_price,
    compute_iceberg,
    compute_pov,
    compute_twap,
    compute_vwap,
    run_algorithm,
)


# ---------------------------------------------------------------------------
# TestTWAP
# ---------------------------------------------------------------------------


class TestTWAP:
    def test_total_quantity_preserved(self):
        result = compute_twap("AAPL", Decimal("1000"), duration_minutes=60, n_slices=12)
        total = sum(s["quantity"] for s in result["schedule"])
        assert total == Decimal("1000")

    def test_slice_count(self):
        result = compute_twap("AAPL", Decimal("1000"), duration_minutes=60, n_slices=10)
        assert len(result["schedule"]) == 10

    def test_equal_slices_within_rounding(self):
        result = compute_twap("AAPL", Decimal("100"), duration_minutes=60, n_slices=4)
        qtys = [s["quantity"] for s in result["schedule"]]
        assert max(qtys) - min(qtys) <= Decimal("0.000001") * 2

    def test_delay_monotonic(self):
        result = compute_twap("AAPL", Decimal("100"), duration_minutes=60, n_slices=12)
        delays = [s["delay_minutes"] for s in result["schedule"]]
        assert delays == sorted(delays)

    def test_first_slice_zero_delay(self):
        result = compute_twap("AAPL", Decimal("100"), duration_minutes=60, n_slices=6)
        assert result["schedule"][0]["delay_minutes"] == 0.0

    def test_invalid_n_slices_raises(self):
        with pytest.raises(ValueError):
            compute_twap("AAPL", Decimal("100"), n_slices=1)

    def test_algo_label(self):
        result = compute_twap("AAPL", Decimal("100"), n_slices=3)
        assert result["algo"] == "TWAP"
        assert result["ticker"] == "AAPL"

    def test_returns_correct_keys(self):
        result = compute_twap("AAPL", Decimal("100"))
        for key in ("algo", "ticker", "total_quantity", "total_slices", "schedule", "params"):
            assert key in result


# ---------------------------------------------------------------------------
# TestVWAP
# ---------------------------------------------------------------------------


class TestVWAP:
    def test_total_quantity_preserved(self):
        profile = [0.2, 0.3, 0.25, 0.25]
        result = compute_vwap("AAPL", Decimal("1000"), volume_profile=profile)
        total = sum(s["quantity"] for s in result["schedule"])
        assert abs(total - Decimal("1000")) <= Decimal("0.001")

    def test_slice_proportions(self):
        profile = [1.0, 3.0]  # 25%/75%
        result = compute_vwap("AAPL", Decimal("1000"), volume_profile=profile)
        s = result["schedule"]
        # First slice ~250, second ~750
        assert s[0]["quantity"] < s[1]["quantity"]

    def test_min_profile_length(self):
        with pytest.raises(ValueError):
            compute_vwap("AAPL", Decimal("100"), volume_profile=[1.0])

    def test_zero_weights_raises(self):
        with pytest.raises(ValueError):
            compute_vwap("AAPL", Decimal("100"), volume_profile=[0.0, 0.0])

    def test_algo_label(self):
        result = compute_vwap("AAPL", Decimal("100"), volume_profile=[0.5, 0.5])
        assert result["algo"] == "VWAP"


# ---------------------------------------------------------------------------
# TestPOV
# ---------------------------------------------------------------------------


class TestPOV:
    def test_total_quantity_preserved(self):
        result = compute_pov("AAPL", Decimal("1000"), participation_rate=0.10, avg_volume_per_minute=5000)
        total = sum(s["quantity"] for s in result["schedule"])
        assert abs(total - Decimal("1000")) <= Decimal("0.001")

    def test_participation_rate_reflected(self):
        result = compute_pov("AAPL", Decimal("1000"), participation_rate=0.10, avg_volume_per_minute=1000)
        # At 10% of 1000/min, each slice should be ~100
        first_qty = result["schedule"][0]["quantity"]
        assert abs(first_qty - Decimal("100")) < Decimal("1")

    def test_invalid_participation_rate(self):
        with pytest.raises(ValueError):
            compute_pov("AAPL", Decimal("100"), participation_rate=0.0, avg_volume_per_minute=1000)

    def test_invalid_rate_above_50(self):
        with pytest.raises(ValueError):
            compute_pov("AAPL", Decimal("100"), participation_rate=0.51, avg_volume_per_minute=1000)

    def test_algo_label(self):
        result = compute_pov("AAPL", Decimal("100"), participation_rate=0.10, avg_volume_per_minute=1000)
        assert result["algo"] == "POV"


# ---------------------------------------------------------------------------
# TestIceberg
# ---------------------------------------------------------------------------


class TestIceberg:
    def test_total_quantity_preserved(self):
        result = compute_iceberg("AAPL", Decimal("500"), Decimal("100"), Decimal("150"))
        total = sum(s["quantity"] for s in result["schedule"])
        assert total == Decimal("500")

    def test_display_size_respected(self):
        result = compute_iceberg("AAPL", Decimal("500"), Decimal("100"), Decimal("150"))
        for s in result["schedule"][:-1]:
            assert s["quantity"] == Decimal("100")

    def test_limit_price_in_schedule(self):
        result = compute_iceberg("AAPL", Decimal("500"), Decimal("100"), Decimal("150"))
        for s in result["schedule"]:
            assert s["target_price"] == Decimal("150")

    def test_display_ge_total_raises(self):
        with pytest.raises(ValueError):
            compute_iceberg("AAPL", Decimal("100"), Decimal("200"), Decimal("150"))

    def test_display_zero_raises(self):
        with pytest.raises(ValueError):
            compute_iceberg("AAPL", Decimal("100"), Decimal("0"), Decimal("150"))

    def test_refill_delay_reflected(self):
        result = compute_iceberg("AAPL", Decimal("300"), Decimal("100"), Decimal("150"), refill_delay_minutes=2.0)
        assert result["schedule"][1]["delay_minutes"] == pytest.approx(2.0)

    def test_algo_label(self):
        result = compute_iceberg("AAPL", Decimal("300"), Decimal("100"), Decimal("150"))
        assert result["algo"] == "ICEBERG"


# ---------------------------------------------------------------------------
# TestAdaptive
# ---------------------------------------------------------------------------


class TestAdaptive:
    def test_total_quantity_preserved(self):
        result = compute_adaptive("AAPL", Decimal("1000"), duration_minutes=60, urgency=0.5)
        total = sum(s["quantity"] for s in result["schedule"])
        assert abs(total - Decimal("1000")) <= Decimal("0.001")

    def test_high_urgency_front_loaded(self):
        result_high = compute_adaptive("AAPL", Decimal("1000"), duration_minutes=60, urgency=1.0)
        result_low = compute_adaptive("AAPL", Decimal("1000"), duration_minutes=60, urgency=0.0)
        # High urgency: first slice should be larger than low urgency
        assert result_high["schedule"][0]["quantity"] > result_low["schedule"][0]["quantity"]

    def test_invalid_urgency_raises(self):
        with pytest.raises(ValueError):
            compute_adaptive("AAPL", Decimal("100"), urgency=1.5)

    def test_algo_label(self):
        result = compute_adaptive("AAPL", Decimal("100"))
        assert result["algo"] == "ADAPTIVE"


# ---------------------------------------------------------------------------
# TestArrivalPrice
# ---------------------------------------------------------------------------


class TestArrivalPrice:
    def test_total_quantity_preserved(self):
        result = compute_arrival_price("AAPL", Decimal("1000"), Decimal("150"), duration_minutes=30)
        total = sum(s["quantity"] for s in result["schedule"])
        assert abs(total - Decimal("1000")) <= Decimal("0.001")

    def test_arrival_price_in_target(self):
        result = compute_arrival_price("AAPL", Decimal("100"), Decimal("150"))
        for s in result["schedule"]:
            assert s["target_price"] == Decimal("150")

    def test_high_vol_front_loads_more(self):
        result_high_vol = compute_arrival_price("AAPL", Decimal("1000"), Decimal("150"), volatility_daily=0.10)
        result_low_vol = compute_arrival_price("AAPL", Decimal("1000"), Decimal("150"), volatility_daily=0.01)
        # Higher vol → more front-loading → first slice bigger
        assert result_high_vol["schedule"][0]["quantity"] >= result_low_vol["schedule"][0]["quantity"]

    def test_algo_label(self):
        result = compute_arrival_price("AAPL", Decimal("100"), Decimal("150"))
        assert result["algo"] == "ARRIVAL_PRICE"


# ---------------------------------------------------------------------------
# TestDispatcher
# ---------------------------------------------------------------------------


class TestDispatcher:
    def test_twap_dispatches(self):
        result = run_algorithm("TWAP", {
            "ticker": "AAPL",
            "total_quantity": Decimal("100"),
            "duration_minutes": 30,
            "n_slices": 6,
            "current_price": Decimal("150"),
        })
        assert result["algo"] == "TWAP"

    def test_unknown_algo_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            run_algorithm("UNKNOWN_ALGO", {})

    @pytest.mark.parametrize("algo", ["TWAP", "ADAPTIVE"])
    def test_all_standard_algos_produce_schedule(self, algo):
        params = {
            "ticker": "TEST",
            "total_quantity": Decimal("1000"),
            "duration_minutes": 60,
        }
        if algo == "TWAP":
            params["n_slices"] = 10
            params["current_price"] = Decimal("100")
        elif algo == "ADAPTIVE":
            params["urgency"] = 0.5
            params["current_price"] = Decimal("100")
        result = run_algorithm(algo, params)
        assert len(result["schedule"]) > 0
