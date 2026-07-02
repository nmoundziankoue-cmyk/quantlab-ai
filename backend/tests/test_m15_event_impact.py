"""Tests for M15 EventImpactEngine."""
import pytest
from services.event_impact import EventImpact, EventImpactEngine


def _pre_returns():
    return [0.001, -0.001, 0.002, 0.001, 0.0]


def _post_returns():
    return [0.015, 0.010, 0.005, 0.003, -0.001]


def _market_returns():
    return [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001]


def _pre_volumes():
    return [1_000_000, 1_200_000, 900_000, 1_100_000, 1_050_000]


def _post_volumes():
    return [3_000_000, 2_500_000, 1_800_000, 1_400_000, 1_200_000]


def _compute_basic(engine: EventImpactEngine) -> EventImpact:
    return engine.compute(
        event_id="evt-001",
        ticker="AAPL",
        pre_returns=_pre_returns(),
        post_returns=_post_returns(),
        market_returns=_market_returns(),
        pre_volumes=_pre_volumes(),
        post_volumes=_post_volumes(),
        gap_return=0.02,
        expected_daily_return=0.001,
        metadata={},
    )


class TestEventImpactEngine:
    def setup_method(self):
        self.engine = EventImpactEngine()

    def test_compute_returns_event_impact(self):
        result = _compute_basic(self.engine)
        assert isinstance(result, EventImpact)

    def test_event_id_stored(self):
        result = _compute_basic(self.engine)
        assert result.event_id == "evt-001"

    def test_ticker_stored(self):
        result = _compute_basic(self.engine)
        assert result.ticker == "AAPL"

    def test_pre_return_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.pre_return, float)

    def test_post_return_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.post_return, float)

    def test_post_return_positive_for_positive_post(self):
        result = _compute_basic(self.engine)
        assert result.post_return > 0

    def test_gap_pct_stored(self):
        result = _compute_basic(self.engine)
        assert result.gap_pct == pytest.approx(0.02)

    def test_volume_spike_computed(self):
        result = _compute_basic(self.engine)
        assert result.volume_spike is not None
        assert result.volume_spike > 1.0

    def test_volatility_spike_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.volatility_spike, float)
        assert result.volatility_spike >= 0.0

    def test_abnormal_return_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.abnormal_return, float)

    def test_abnormal_return_post_minus_expected(self):
        result = _compute_basic(self.engine)
        expected_ar = result.post_return - 0.001 * len(_post_returns())
        assert abs(result.abnormal_return - expected_ar) < 1e-9

    def test_max_drawdown_non_positive(self):
        result = _compute_basic(self.engine)
        assert result.max_drawdown <= 0.0

    def test_relative_return_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.relative_return, float)

    def test_liquidity_change_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.liquidity_change, float)

    def test_recovery_days_non_negative(self):
        result = _compute_basic(self.engine)
        assert result.recovery_days >= 0

    def test_momentum_persistence_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.momentum_persistence, float)

    def test_risk_contribution_is_float(self):
        result = _compute_basic(self.engine)
        assert isinstance(result.risk_contribution, float)

    def test_metadata_stored(self):
        result = self.engine.compute(
            event_id="evt-001", ticker="AAPL",
            pre_returns=_pre_returns(), post_returns=_post_returns(),
            market_returns=_market_returns(),
            pre_volumes=_pre_volumes(), post_volumes=_post_volumes(),
            gap_return=0.02, expected_daily_return=0.001,
            metadata={"custom": "value"},
        )
        assert result.metadata["custom"] == "value"

    def test_batch_compute_returns_list(self):
        inputs = [
            {
                "event_id": "evt-001", "ticker": "AAPL",
                "pre_returns": _pre_returns(), "post_returns": _post_returns(),
                "market_returns": _market_returns(),
                "pre_volumes": _pre_volumes(), "post_volumes": _post_volumes(),
                "gap_return": 0.02, "expected_daily_return": 0.001, "metadata": {},
            },
            {
                "event_id": "evt-001", "ticker": "MSFT",
                "pre_returns": _pre_returns(), "post_returns": _post_returns(),
                "market_returns": _market_returns(),
                "pre_volumes": _pre_volumes(), "post_volumes": _post_volumes(),
                "gap_return": -0.01, "expected_daily_return": 0.001, "metadata": {},
            },
        ]
        results = self.engine.batch_compute("evt-001", inputs)
        assert len(results) == 2
        assert all(isinstance(r, EventImpact) for r in results)

    def test_summary_stats_structure(self):
        impacts = [_compute_basic(self.engine), _compute_basic(self.engine)]
        stats = self.engine.summary_stats(impacts)
        assert "post_return_mean" in stats
        assert "abnormal_return_mean" in stats
        assert "count" in stats

    def test_summary_stats_n(self):
        impacts = [_compute_basic(self.engine), _compute_basic(self.engine)]
        stats = self.engine.summary_stats(impacts)
        assert stats["count"] == 2

    def test_summary_stats_mean_post_return(self):
        i1 = _compute_basic(self.engine)
        i2 = _compute_basic(self.engine)
        stats = self.engine.summary_stats([i1, i2])
        expected = (i1.post_return + i2.post_return) / 2
        assert abs(stats["post_return_mean"] - expected) < 1e-4

    def test_negative_gap_return_stored(self):
        result = self.engine.compute(
            event_id="evt-002", ticker="GM",
            pre_returns=_pre_returns(), post_returns=[-0.02, -0.01, 0.0, -0.005, -0.003],
            market_returns=_market_returns(),
            pre_volumes=_pre_volumes(), post_volumes=_post_volumes(),
            gap_return=-0.05, expected_daily_return=0.001, metadata={},
        )
        assert result.gap_pct == pytest.approx(-0.05)

    def test_zero_pre_volume_no_error(self):
        result = self.engine.compute(
            event_id="evt-003", ticker="XYZ",
            pre_returns=_pre_returns(), post_returns=_post_returns(),
            market_returns=_market_returns(),
            pre_volumes=[0, 0, 0, 0, 0], post_volumes=_post_volumes(),
            gap_return=0.0, expected_daily_return=0.001, metadata={},
        )
        assert isinstance(result, EventImpact)
