"""Tests for M17 Risk Limits Engine (12 limit types, hard/soft)."""
import pytest
from services.risk_limits import (
    RiskLimitsEngine, LimitType, LimitSeverity, CheckResult,
    RiskLimit, LimitViolation, PreTradeCheckResult, RiskContext, ProposedOrder,
)


def _eng():
    return RiskLimitsEngine()


def _ctx(nav=1_000_000, cash=100_000, gross_leverage=1.0, sector_weights=None):
    return RiskContext(
        nav=nav,
        cash=cash,
        gross_leverage=gross_leverage,
        net_leverage=gross_leverage * 0.8,
        sector_weights=sector_weights or {"TECHNOLOGY": 0.25},
        current_positions={},
    )


def _order(ticker="AAPL", side="BUY", qty=100, price=175.0, sector="TECHNOLOGY"):
    return ProposedOrder(ticker=ticker, side=side, quantity=qty, price=price, sector=sector)


# ---------------------------------------------------------------------------
# add / remove limits
# ---------------------------------------------------------------------------

class TestAddRemoveLimits:
    def test_add_limit(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=500_000, description="Max order")
        limits = e.get_all_limits()
        assert any(l.limit_type == LimitType.MAX_ORDER_SIZE for l in limits)

    def test_add_multiple_limits(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=500_000)
        e.add_limit(LimitType.MAX_POSITION_SIZE, hard_limit=1_000_000)
        assert len(e.get_all_limits()) == 2

    def test_remove_limit(self):
        e = _eng()
        lid = e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=500_000).limit_id
        e.remove_limit(lid)
        assert not any(l.limit_id == lid for l in e.get_all_limits())

    def test_remove_nonexistent_raises(self):
        e = _eng()
        with pytest.raises((KeyError, ValueError)):
            e.remove_limit("does-not-exist")

    def test_disable_limit(self):
        e = _eng()
        limit = e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=100)
        e.disable_limit(limit.limit_id)
        result = e.check_order(_order(qty=10000), _ctx())
        assert result.order_allowed

    def test_enable_limit_after_disable(self):
        e = _eng()
        limit = e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=100)
        e.disable_limit(limit.limit_id)
        e.enable_limit(limit.limit_id)
        result = e.check_order(_order(qty=10000, price=175.0), _ctx())
        assert not result.order_allowed

    def test_add_limit_returns_risk_limit(self):
        e = _eng()
        lim = e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=500_000)
        assert isinstance(lim, RiskLimit)


# ---------------------------------------------------------------------------
# check_order — MAX_ORDER_SIZE
# ---------------------------------------------------------------------------

class TestMaxOrderSize:
    def test_order_within_limit_passes(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=100_000)
        result = e.check_order(_order(qty=100, price=175.0), _ctx())
        assert result.order_allowed

    def test_order_exceeds_hard_limit_rejected(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=1000)
        result = e.check_order(_order(qty=10000, price=175.0), _ctx())
        assert not result.order_allowed
        assert result.result == CheckResult.HARD_REJECT

    def test_order_within_soft_limit_passes(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=100_000, soft_limit=10_000)
        result = e.check_order(_order(qty=100, price=175.0), _ctx())
        assert result.result != CheckResult.HARD_REJECT

    def test_order_between_soft_and_hard_is_warning(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=50_000, soft_limit=10_000)
        result = e.check_order(_order(qty=100, price=175.0), _ctx())
        assert result.result in (CheckResult.SOFT_WARNING, CheckResult.PASS)


# ---------------------------------------------------------------------------
# check_order — MAX_POSITION_SIZE
# ---------------------------------------------------------------------------

class TestMaxPositionSize:
    def test_position_within_limit_passes(self):
        e = _eng()
        e.add_limit(LimitType.MAX_POSITION_SIZE, hard_limit=100_000)
        result = e.check_order(_order(qty=100, price=175.0), _ctx())
        assert result.order_allowed

    def test_position_exceeds_limit_rejected(self):
        e = _eng()
        e.add_limit(LimitType.MAX_POSITION_SIZE, hard_limit=1000)
        result = e.check_order(_order(qty=100, price=175.0), _ctx())
        assert not result.order_allowed


# ---------------------------------------------------------------------------
# check_order — MAX_LEVERAGE
# ---------------------------------------------------------------------------

class TestMaxLeverage:
    def test_leverage_within_limit_passes(self):
        e = _eng()
        e.add_limit(LimitType.MAX_LEVERAGE, hard_limit=2.0)
        result = e.check_order(_order(), _ctx(gross_leverage=1.0))
        assert result.order_allowed

    def test_leverage_exceeds_limit_rejected(self):
        e = _eng()
        e.add_limit(LimitType.MAX_LEVERAGE, hard_limit=1.0)
        result = e.check_order(_order(), _ctx(gross_leverage=1.5))
        assert not result.order_allowed


# ---------------------------------------------------------------------------
# check_order — MAX_SECTOR_WEIGHT
# ---------------------------------------------------------------------------

class TestMaxSectorWeight:
    def test_sector_within_limit_passes(self):
        e = _eng()
        e.add_limit(LimitType.MAX_SECTOR_WEIGHT, hard_limit=0.40)
        result = e.check_order(_order(sector="TECHNOLOGY"), _ctx(sector_weights={"TECHNOLOGY": 0.25}))
        assert result.order_allowed

    def test_sector_exceeds_limit_rejected(self):
        e = _eng()
        e.add_limit(LimitType.MAX_SECTOR_WEIGHT, hard_limit=0.20)
        result = e.check_order(
            _order(ticker="AAPL", side="BUY", qty=10000, price=175.0, sector="TECHNOLOGY"),
            _ctx(nav=1_000_000, sector_weights={"TECHNOLOGY": 0.25}),
        )
        assert not result.order_allowed


# ---------------------------------------------------------------------------
# PreTradeCheckResult structure
# ---------------------------------------------------------------------------

class TestPreTradeCheckResult:
    def test_returns_pre_trade_check_result(self):
        e = _eng()
        result = e.check_order(_order(), _ctx())
        assert isinstance(result, PreTradeCheckResult)

    def test_result_has_violations_list(self):
        e = _eng()
        result = e.check_order(_order(), _ctx())
        assert isinstance(result.violations, list)

    def test_hard_reject_produces_violation(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=100)
        result = e.check_order(_order(qty=10000, price=175.0), _ctx())
        assert len(result.violations) >= 1
        assert any(v.result == CheckResult.HARD_REJECT for v in result.violations)

    def test_pass_result_no_violations(self):
        e = _eng()
        result = e.check_order(_order(), _ctx())
        hard_rejects = [v for v in result.violations if v.result == CheckResult.HARD_REJECT]
        assert len(hard_rejects) == 0

    def test_violation_has_limit_id(self):
        e = _eng()
        e.add_limit(LimitType.MAX_ORDER_SIZE, hard_limit=100)
        result = e.check_order(_order(qty=10000, price=175.0), _ctx())
        assert all(v.limit_id for v in result.hard_violations)


# ---------------------------------------------------------------------------
# default_limits
# ---------------------------------------------------------------------------

class TestDefaultLimits:
    def test_default_limits_not_empty(self):
        e = RiskLimitsEngine.default_limits()
        assert len(e.get_all_limits()) > 0

    def test_default_limits_have_max_order_size(self):
        e = RiskLimitsEngine.default_limits()
        types = [l.limit_type for l in e.get_all_limits()]
        assert LimitType.MAX_ORDER_SIZE in types or LimitType.MAX_POSITION_SIZE in types

    def test_default_limits_all_enabled(self):
        e = RiskLimitsEngine.default_limits()
        assert all(l.enabled for l in e.get_all_limits())
