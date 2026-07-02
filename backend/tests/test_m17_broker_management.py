"""Tests for M17 Broker Management Engine."""
import pytest
from services.broker_management import (
    BrokerManagementEngine, CommissionType, BrokerStatus, AssetClass,
    RoutingStrategy, CommissionSchedule, BrokerRecord, RoutingRule,
)


def _eng():
    return BrokerManagementEngine()


def _register(e, name="Goldman Sachs", assets=None, exchanges=None):
    return e.register_broker(
        name=name,
        supported_asset_classes=assets or [AssetClass.EQUITY],
        supported_exchanges=exchanges or ["NYSE", "NASDAQ"],
    )


# ---------------------------------------------------------------------------
# register_broker
# ---------------------------------------------------------------------------

class TestRegisterBroker:
    def test_register_returns_broker_record(self):
        e = _eng()
        b = _register(e)
        assert isinstance(b, BrokerRecord)

    def test_register_assigns_unique_id(self):
        e = _eng()
        b1 = _register(e, name="GS")
        b2 = _register(e, name="JPM")
        assert b1.broker_id != b2.broker_id

    def test_register_status_active(self):
        e = _eng()
        b = _register(e)
        assert b.status == BrokerStatus.ACTIVE

    def test_register_stores_asset_classes(self):
        e = _eng()
        b = _register(e, assets=[AssetClass.EQUITY, AssetClass.OPTIONS])
        assert AssetClass.EQUITY in b.supported_asset_classes

    def test_register_empty_name_raises(self):
        e = _eng()
        with pytest.raises(ValueError):
            e.register_broker("")

    def test_all_brokers_returns_registered(self):
        e = _eng()
        _register(e, name="GS")
        _register(e, name="JPM")
        assert len(e.all_brokers()) == 2


# ---------------------------------------------------------------------------
# deactivate / suspend
# ---------------------------------------------------------------------------

class TestBrokerStatus:
    def test_deactivate_broker(self):
        e = _eng()
        b = _register(e)
        e.deactivate_broker(b.broker_id)
        updated = e.all_brokers()[0]
        assert updated.status == BrokerStatus.INACTIVE

    def test_suspend_broker(self):
        e = _eng()
        b = _register(e)
        e.suspend_broker(b.broker_id)
        updated = e.all_brokers()[0]
        assert updated.status == BrokerStatus.SUSPENDED

    def test_deactivate_nonexistent_raises(self):
        e = _eng()
        with pytest.raises((KeyError, ValueError)):
            e.deactivate_broker("does-not-exist")


# ---------------------------------------------------------------------------
# commission schedules
# ---------------------------------------------------------------------------

class TestCommissionSchedules:
    def test_add_commission_schedule(self):
        e = _eng()
        b = _register(e)
        e.add_commission_schedule(b.broker_id, AssetClass.EQUITY, CommissionType.PER_SHARE, base_rate=0.005, minimum_per_trade=1.0)
        brokers = e.all_brokers()
        assert len(brokers[0].commission_schedules) == 1

    def test_compute_commission_per_share(self):
        e = _eng()
        b = _register(e)
        e.add_commission_schedule(b.broker_id, AssetClass.EQUITY, CommissionType.PER_SHARE, base_rate=0.005, minimum_per_trade=1.0)
        comm = e.compute_commission(b.broker_id, AssetClass.EQUITY, 1000, 175.0)
        assert comm == pytest.approx(max(1000 * 0.005, 1.0), rel=1e-5)

    def test_compute_commission_flat(self):
        e = _eng()
        b = _register(e)
        e.add_commission_schedule(b.broker_id, AssetClass.EQUITY, CommissionType.FLAT, base_rate=10.0, minimum_per_trade=0.0)
        comm = e.compute_commission(b.broker_id, AssetClass.EQUITY, 1000, 175.0)
        assert comm == pytest.approx(10.0, rel=1e-5)

    def test_compute_commission_percent(self):
        e = _eng()
        b = _register(e)
        e.add_commission_schedule(b.broker_id, AssetClass.EQUITY, CommissionType.PERCENT, base_rate=0.001, minimum_per_trade=0.0)
        comm = e.compute_commission(b.broker_id, AssetClass.EQUITY, 100, 175.0)
        assert comm == pytest.approx(100 * 175.0 * 0.001, rel=1e-5)

    def test_compute_commission_minimum_enforced(self):
        e = _eng()
        b = _register(e)
        e.add_commission_schedule(b.broker_id, AssetClass.EQUITY, CommissionType.PER_SHARE, base_rate=0.001, minimum_per_trade=5.0)
        comm = e.compute_commission(b.broker_id, AssetClass.EQUITY, 1, 175.0)
        assert comm == pytest.approx(5.0, rel=1e-5)

    def test_compute_commission_no_schedule_raises(self):
        e = _eng()
        b = _register(e)
        with pytest.raises((KeyError, ValueError)):
            e.compute_commission(b.broker_id, AssetClass.OPTIONS, 100, 5.0)


# ---------------------------------------------------------------------------
# routing rules
# ---------------------------------------------------------------------------

class TestRoutingRules:
    def test_add_routing_rule(self):
        e = _eng()
        b = _register(e)
        e.add_routing_rule(b.broker_id, asset_class=AssetClass.EQUITY, routing_strategy=RoutingStrategy.BEST_EXECUTION, priority=1)
        b2 = next(x for x in e.all_brokers() if x.broker_id == b.broker_id)
        assert len(b2.routing_rules) == 1

    def test_route_order_returns_broker_record(self):
        e = _eng()
        b = _register(e, name="BestBroker", assets=[AssetClass.EQUITY])
        e.add_commission_schedule(b.broker_id, AssetClass.EQUITY, CommissionType.PER_SHARE, base_rate=0.005, minimum_per_trade=1.0)
        e.add_routing_rule(b.broker_id, asset_class=AssetClass.EQUITY, routing_strategy=RoutingStrategy.BEST_EXECUTION, priority=1)
        result = e.route_order(AssetClass.EQUITY, None, 17500.0)
        assert result is not None
        assert result.broker_id == b.broker_id

    def test_route_order_no_rule_returns_none(self):
        e = _eng()
        _register(e)
        result = e.route_order(AssetClass.OPTIONS, None, 500.0)
        assert result is None


# ---------------------------------------------------------------------------
# record_execution / quality score
# ---------------------------------------------------------------------------

class TestExecutionQuality:
    def test_record_execution(self):
        e = _eng()
        b = _register(e)
        e.record_execution(b.broker_id, "AAPL", 100, 175.0, 175.35)
        b_updated = next(x for x in e.all_brokers() if x.broker_id == b.broker_id)
        assert len(b_updated.execution_history) == 1

    def test_quality_score_updated_after_execution(self):
        e = _eng()
        b = _register(e)
        e.record_execution(b.broker_id, "AAPL", 100, 175.0, 175.10, 1.0)
        b_updated = next(x for x in e.all_brokers() if x.broker_id == b.broker_id)
        assert 0 <= b_updated.quality_score <= 100

    def test_rank_brokers(self):
        e = _eng()
        b1 = _register(e, name="GS")
        b2 = _register(e, name="JPM")
        e.record_execution(b1.broker_id, "AAPL", 100, 175.0, 175.01, 1.0)
        e.record_execution(b2.broker_id, "AAPL", 100, 175.0, 178.0, 0.8)
        ranked = e.rank_brokers()
        assert ranked[0][1].broker_id == b1.broker_id

    def test_statistics_total_count(self):
        e = _eng()
        _register(e, name="GS")
        _register(e, name="JPM")
        stats = e.statistics()
        assert stats["total"] == 2

    def test_statistics_by_status(self):
        e = _eng()
        b = _register(e, name="GS")
        _register(e, name="JPM")
        e.deactivate_broker(b.broker_id)
        stats = e.statistics()
        assert stats["by_status"].get("INACTIVE", 0) >= 1
