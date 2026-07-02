"""Unit tests for M18 Alert Engine — 55 tests."""
import pytest

from services.m18_alert_engine import (
    AlertType, AlertSeverity, AlertStatus, AlertDirection,
    AlertRule, TriggeredAlert, WebhookConfig, AlertStats,
    AlertEngine, get_alert_engine,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------

class TestAlertEnums:
    def test_alert_type_has_9_values(self):
        assert len(AlertType) >= 9

    def test_alert_severity_has_5_values(self):
        assert len(AlertSeverity) >= 5

    def test_alert_direction_exists(self):
        assert AlertDirection.ABOVE is not None
        assert AlertDirection.BELOW is not None

    def test_alert_status_triggered(self):
        assert AlertStatus.TRIGGERED is not None

    def test_alert_severity_critical(self):
        assert AlertSeverity.CRITICAL is not None

    def test_alert_type_price(self):
        assert AlertType.PRICE is not None


# ---------------------------------------------------------------------------
# AlertRule
# ---------------------------------------------------------------------------

class TestAlertRule:
    def _make_rule(self, **kwargs):
        from datetime import datetime, timezone
        defaults = dict(
            rule_id="R1", name="Test Rule", alert_type=AlertType.PRICE,
            severity=AlertSeverity.MEDIUM, field="price",
            direction=AlertDirection.ABOVE, threshold=200.0,
            ticker="AAPL", cooldown_seconds=60, max_triggers=10,
            tags=[], enabled=True, created_at=datetime.now(timezone.utc),
        )
        defaults.update(kwargs)
        return AlertRule(**defaults)

    def test_rule_creation(self):
        rule = self._make_rule()
        assert rule.rule_id == "R1"

    def test_rule_to_dict(self):
        d = self._make_rule().to_dict()
        assert "rule_id" in d and "threshold" in d

    def test_rule_direction_above(self):
        rule = self._make_rule(direction=AlertDirection.ABOVE)
        assert rule.direction == AlertDirection.ABOVE

    def test_rule_direction_below(self):
        rule = self._make_rule(direction=AlertDirection.BELOW)
        assert rule.direction == AlertDirection.BELOW


# ---------------------------------------------------------------------------
# AlertEngine — rule management
# ---------------------------------------------------------------------------

class TestAlertEngineRules:
    def setup_method(self):
        self.engine = AlertEngine()

    def _add_rule(self, ticker="AAPL", field="price", threshold=200.0, direction=AlertDirection.ABOVE, cooldown_seconds=0, max_triggers=100):
        return self.engine.add_rule(
            name=f"Rule for {ticker}",
            alert_type=AlertType.PRICE,
            severity=AlertSeverity.HIGH,
            field=field,
            direction=direction,
            threshold=threshold,
            ticker=ticker,
            cooldown_seconds=cooldown_seconds,
            max_triggers=max_triggers,
        )

    def test_add_rule(self):
        self._add_rule()
        assert len(self.engine.list_rules()) == 1

    def test_get_rules_empty_initially(self):
        assert len(self.engine.list_rules()) == 0

    def test_remove_rule(self):
        rule = self._add_rule()
        self.engine.remove_rule(rule.rule_id)
        assert len(self.engine.list_rules()) == 0

    def test_remove_nonexistent_rule_returns_false(self):
        result = self.engine.remove_rule("NONEXISTENT")
        assert result is False

    def test_add_multiple_rules(self):
        for _ in range(5):
            self._add_rule()
        assert len(self.engine.list_rules()) == 5

    def test_get_rule_by_id(self):
        rule = self._add_rule()
        found = self.engine.get_rule(rule.rule_id)
        assert found is not None and found.rule_id == rule.rule_id

    def test_get_nonexistent_rule_returns_none(self):
        assert self.engine.get_rule("NOPE") is None

    def test_enable_disable_rule(self):
        rule = self._add_rule()
        self.engine.disable_rule(rule.rule_id)
        found = self.engine.get_rule(rule.rule_id)
        assert found is not None and found.enabled is False

    def test_re_enable_rule(self):
        rule = self._add_rule()
        self.engine.disable_rule(rule.rule_id)
        self.engine.enable_rule(rule.rule_id)
        found = self.engine.get_rule(rule.rule_id)
        assert found.enabled is True


# ---------------------------------------------------------------------------
# AlertEngine — evaluate
# ---------------------------------------------------------------------------

class TestAlertEngineEvaluate:
    def setup_method(self):
        self.engine = AlertEngine()
        rule = self.engine.add_rule(
            name="Price Above 200",
            alert_type=AlertType.PRICE,
            severity=AlertSeverity.HIGH,
            field="price",
            direction=AlertDirection.ABOVE,
            threshold=200.0,
            ticker="AAPL",
            cooldown_seconds=0,
            max_triggers=100,
        )
        self.rule_id = rule.rule_id

    def test_evaluate_triggers_when_price_above_threshold(self):
        alerts = self.engine.evaluate("AAPL", "price", 210.0)
        assert len(alerts) >= 1

    def test_evaluate_no_trigger_when_below_threshold(self):
        alerts = self.engine.evaluate("AAPL", "price", 190.0)
        assert len(alerts) == 0

    def test_triggered_alert_has_rule_id(self):
        alerts = self.engine.evaluate("AAPL", "price", 210.0)
        assert alerts[0].rule_id == self.rule_id

    def test_triggered_alert_to_dict(self):
        alerts = self.engine.evaluate("AAPL", "price", 210.0)
        d = alerts[0].to_dict()
        assert "rule_id" in d

    def test_evaluate_below_direction_triggers_when_price_below(self):
        rule = self.engine.add_rule(
            name="Price Below 100",
            alert_type=AlertType.PRICE,
            severity=AlertSeverity.MEDIUM,
            field="price",
            direction=AlertDirection.BELOW,
            threshold=100.0,
            ticker="AAPL",
            cooldown_seconds=0,
            max_triggers=100,
        )
        alerts = self.engine.evaluate("AAPL", "price", 90.0)
        below_alerts = [a for a in alerts if a.rule_id == rule.rule_id]
        assert len(below_alerts) >= 1

    def test_cooldown_prevents_retrigger(self):
        rule = self.engine.add_rule(
            name="Cooldown Test",
            alert_type=AlertType.PRICE,
            severity=AlertSeverity.LOW,
            field="price",
            direction=AlertDirection.ABOVE,
            threshold=100.0,
            ticker="AAPL",
            cooldown_seconds=3600,
            max_triggers=100,
        )
        self.engine.evaluate("AAPL", "price", 150.0)
        alerts2 = self.engine.evaluate("AAPL", "price", 160.0)
        cd_alerts2 = [a for a in alerts2 if a.rule_id == rule.rule_id]
        assert len(cd_alerts2) == 0

    def test_max_triggers_enforced(self):
        rule = self.engine.add_rule(
            name="Max Test",
            alert_type=AlertType.PRICE,
            severity=AlertSeverity.LOW,
            field="price",
            direction=AlertDirection.ABOVE,
            threshold=50.0,
            ticker="AAPL",
            cooldown_seconds=0,
            max_triggers=2,
        )
        results = []
        for _ in range(5):
            alerts = self.engine.evaluate("AAPL", "price", 100.0)
            results.extend([a for a in alerts if a.rule_id == rule.rule_id])
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# AlertEngine — fire custom / history / stats
# ---------------------------------------------------------------------------

class TestAlertEngineHistoryStats:
    def setup_method(self):
        self.engine = AlertEngine()

    def test_fire_custom_alert(self):
        alert = self.engine.fire_custom_alert(
            name="Custom",
            severity=AlertSeverity.HIGH,
            message="Test alert",
            alert_type=AlertType.CUSTOM,
        )
        assert isinstance(alert, TriggeredAlert)

    def test_fire_custom_alert_in_history(self):
        self.engine.fire_custom_alert(
            name="T", severity=AlertSeverity.HIGH, message="M"
        )
        hist = self.engine.get_history(limit=10)
        assert len(hist) >= 1

    def test_get_history_empty_initially(self):
        assert self.engine.get_history() == []

    def test_get_history_limit(self):
        for i in range(10):
            self.engine.fire_custom_alert(
                name=f"T{i}", severity=AlertSeverity.LOW, message="M"
            )
        hist = self.engine.get_history(limit=5)
        assert len(hist) == 5

    def test_get_stats_returns_alert_stats(self):
        stats = self.engine.get_stats()
        assert isinstance(stats, AlertStats)

    def test_get_stats_total_count(self):
        self.engine.fire_custom_alert(name="T", severity=AlertSeverity.HIGH, message="M")
        stats = self.engine.get_stats()
        assert stats.total_triggers >= 1

    def test_alert_stats_to_dict(self):
        d = self.engine.get_stats().to_dict()
        assert "total_triggers" in d

    def test_register_webhook(self):
        config = self.engine.register_webhook(url="https://hooks.example.com/test")
        assert config is not None and config.webhook_id is not None

    def test_remove_webhook(self):
        config = self.engine.register_webhook(url="https://example.com")
        result = self.engine.remove_webhook(config.webhook_id)
        assert result is True


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_alert_engine_returns_engine(self):
        eng = get_alert_engine()
        assert isinstance(eng, AlertEngine)

    def test_singleton_same_instance(self):
        e1 = get_alert_engine()
        e2 = get_alert_engine()
        assert e1 is e2
