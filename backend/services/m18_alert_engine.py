"""M18 — Institutional Alert Engine: real-time configurable alert system.

Supports price alerts, technical alerts, volatility alerts, volume spike alerts,
economic event alerts, news sentiment alerts, earnings alerts, custom threshold
alerts, alert history, deduplication, and webhook delivery simulation.

Pure Python, no external libraries.
"""
from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AlertType(str, Enum):
    """Category of alert."""
    PRICE = "PRICE"
    PRICE_THRESHOLD = "PRICE_THRESHOLD"
    TECHNICAL = "TECHNICAL"
    VOLATILITY = "VOLATILITY"
    VOLUME = "VOLUME"
    ECONOMIC = "ECONOMIC"
    NEWS = "NEWS"
    EARNINGS = "EARNINGS"
    RISK = "RISK"
    CUSTOM = "CUSTOM"


class AlertSeverity(str, Enum):
    """Severity level of an alert."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """Lifecycle status of an alert rule."""
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


class AlertDirection(str, Enum):
    """Direction for threshold-based alerts."""
    ABOVE = "ABOVE"
    BELOW = "BELOW"
    CROSS = "CROSS"


# ---------------------------------------------------------------------------
# Configuration and event dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AlertRule:
    """A configured alert rule.

    Args:
        rule_id: Unique identifier for this rule.
        name: Human-readable name.
        alert_type: Category (PRICE, TECHNICAL, etc.).
        severity: Severity level.
        ticker: Target instrument symbol (None = market-wide).
        field: The data field to monitor (e.g. "close", "volume").
        direction: ABOVE / BELOW / CROSS.
        threshold: Numeric threshold value.
        cooldown_seconds: Minimum seconds between repeated triggers.
        max_triggers: Maximum times this rule can trigger (0 = unlimited).
        tags: Arbitrary tags for grouping.
        enabled: Whether the rule is active.
        created_at: Creation timestamp.
    """

    rule_id: str
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    field: str
    direction: AlertDirection
    threshold: float
    cooldown_seconds: int = 0
    max_triggers: int = 0
    ticker: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "ticker": self.ticker,
            "field": self.field,
            "direction": self.direction.value,
            "threshold": self.threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "max_triggers": self.max_triggers,
            "tags": self.tags,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TriggeredAlert:
    """A single alert event generated when a rule fires.

    Args:
        alert_id: Unique identifier.
        rule_id: The rule that generated this alert.
        rule_name: Copied from rule for convenience.
        alert_type: Category.
        severity: Severity.
        ticker: Instrument symbol (if applicable).
        message: Human-readable description.
        current_value: The value that caused the trigger.
        threshold: Rule threshold.
        direction: Trigger direction.
        timestamp: UTC trigger time.
        delivered: Whether a webhook has been called.
        extra: Optional extra data payload.
    """

    alert_id: str
    rule_id: str
    rule_name: str
    alert_type: AlertType
    severity: AlertSeverity
    ticker: Optional[str]
    message: str
    current_value: float
    threshold: float
    direction: AlertDirection
    timestamp: datetime
    delivered: bool
    extra: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "ticker": self.ticker,
            "message": self.message,
            "current_value": round(self.current_value, 6),
            "threshold": round(self.threshold, 6),
            "direction": self.direction.value,
            "timestamp": self.timestamp.isoformat(),
            "delivered": self.delivered,
            "extra": self.extra,
        }


@dataclass
class WebhookConfig:
    """Webhook delivery configuration.

    Args:
        webhook_id: Unique identifier.
        url: Endpoint URL (simulated).
        severity_filter: Only deliver alerts of these severities.
        alert_type_filter: Only deliver alerts of these types.
        enabled: Whether webhook delivery is active.
    """

    webhook_id: str
    url: str
    severity_filter: List[AlertSeverity]
    alert_type_filter: List[AlertType]
    enabled: bool

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "webhook_id": self.webhook_id,
            "url": self.url,
            "severity_filter": [s.value for s in self.severity_filter],
            "alert_type_filter": [a.value for a in self.alert_type_filter],
            "enabled": self.enabled,
        }


@dataclass
class AlertStats:
    """Alert engine statistics.

    Args:
        total_rules: Number of configured rules.
        active_rules: Number of enabled rules.
        total_triggers: Total alert events fired.
        triggers_last_hour: Triggers in the last 60 minutes.
        by_severity: Trigger counts per severity.
        by_type: Trigger counts per alert type.
        delivery_success_rate: Fraction of webhooks delivered successfully.
    """

    total_rules: int
    active_rules: int
    total_triggers: int
    triggers_last_hour: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    delivery_success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable dict."""
        return {
            "total_rules": self.total_rules,
            "active_rules": self.active_rules,
            "total_triggers": self.total_triggers,
            "triggers_last_hour": self.triggers_last_hour,
            "by_severity": self.by_severity,
            "by_type": self.by_type,
            "delivery_success_rate": round(self.delivery_success_rate, 4),
        }


# ---------------------------------------------------------------------------
# Internal rule state
# ---------------------------------------------------------------------------

@dataclass
class _RuleState:
    rule: AlertRule
    trigger_count: int = 0
    last_triggered: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Alert Engine
# ---------------------------------------------------------------------------

class AlertEngine:
    """Institutional-grade configurable alert engine.

    Manages alert rules, evaluates incoming market data events, fires
    TriggeredAlert objects, maintains history, and simulates webhook delivery.
    """

    _MAX_HISTORY = 5000

    def __init__(self) -> None:
        self._rules: Dict[str, _RuleState] = {}
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._history: Deque[TriggeredAlert] = deque(maxlen=self._MAX_HISTORY)
        self._delivery_attempts: int = 0
        self._delivery_successes: int = 0
        self._handlers: List[Callable[[TriggeredAlert], None]] = []

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(
        self,
        name: str = "",
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        field: str = "price",
        direction: Optional[AlertDirection] = None,
        threshold: float = 0.0,
        ticker: Optional[str] = None,
        cooldown_seconds: int = 300,
        max_triggers: int = 0,
        tags: Optional[List[str]] = None,
    ) -> AlertRule:
        """Register a new alert rule.

        Args:
            name: Rule name string.
            alert_type: Alert category.
            severity: Severity level.
            field: Data field to monitor.
            direction: Trigger direction.
            threshold: Numeric threshold.
            ticker: Target symbol (None = global).
            cooldown_seconds: Minimum seconds between triggers.
            max_triggers: Max triggers (0 = unlimited).
            tags: Optional tags.

        Returns:
            The newly created AlertRule.
        """
        rule_id = str(uuid.uuid4())
        rule = AlertRule(
            rule_id=rule_id, name=name, alert_type=alert_type or AlertType.CUSTOM,
            severity=severity or AlertSeverity.INFO, ticker=ticker.upper() if ticker else None,
            field=field, direction=direction or AlertDirection.ABOVE, threshold=threshold,
            cooldown_seconds=cooldown_seconds, max_triggers=max_triggers,
            tags=tags or [], enabled=True,
            created_at=datetime.now(timezone.utc),
        )
        self._rules[rule_id] = _RuleState(rule=rule)
        return rule

    def add_rule_object(self, rule: "AlertRule") -> AlertRule:
        """Register a pre-built AlertRule object directly.

        Args:
            rule: AlertRule instance to register.

        Returns:
            The same AlertRule (stored by rule_id).
        """
        self._rules[rule.rule_id] = _RuleState(rule=rule)
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule.

        Args:
            rule_id: Rule identifier.

        Returns:
            True if rule was found and removed.
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a previously disabled rule.

        Args:
            rule_id: Rule identifier.

        Returns:
            True if rule found.
        """
        if rule_id in self._rules:
            self._rules[rule_id].rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule without removing it.

        Args:
            rule_id: Rule identifier.

        Returns:
            True if rule found.
        """
        if rule_id in self._rules:
            self._rules[rule_id].rule.enabled = False
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Retrieve a rule by ID.

        Args:
            rule_id: Rule identifier.

        Returns:
            AlertRule or None.
        """
        state = self._rules.get(rule_id)
        return state.rule if state else None

    def get_rules(self) -> List[AlertRule]:
        """Alias for list_rules() with no filters."""
        return self.list_rules()

    def list_rules(
        self, alert_type: Optional[AlertType] = None, ticker: Optional[str] = None
    ) -> List[AlertRule]:
        """List all rules, optionally filtered.

        Args:
            alert_type: Filter by type.
            ticker: Filter by ticker.

        Returns:
            List of matching AlertRule objects.
        """
        rules = [s.rule for s in self._rules.values()]
        if alert_type:
            rules = [r for r in rules if r.alert_type == alert_type]
        if ticker:
            t = ticker.upper()
            rules = [r for r in rules if r.ticker is None or r.ticker == t]
        return rules

    # ------------------------------------------------------------------
    # Webhook management
    # ------------------------------------------------------------------

    def register_webhook(
        self,
        url: str,
        severity_filter: Optional[List[AlertSeverity]] = None,
        alert_type_filter: Optional[List[AlertType]] = None,
    ) -> WebhookConfig:
        """Register a webhook endpoint.

        Args:
            url: Target URL (simulated delivery).
            severity_filter: Only deliver these severities (None = all).
            alert_type_filter: Only deliver these types (None = all).

        Returns:
            WebhookConfig.
        """
        webhook_id = str(uuid.uuid4())
        config = WebhookConfig(
            webhook_id=webhook_id, url=url,
            severity_filter=severity_filter or list(AlertSeverity),
            alert_type_filter=alert_type_filter or list(AlertType),
            enabled=True,
        )
        self._webhooks[webhook_id] = config
        return config

    def remove_webhook(self, webhook_id: str) -> bool:
        """Remove a webhook registration.

        Args:
            webhook_id: Webhook identifier.

        Returns:
            True if found and removed.
        """
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, handler: Callable[[TriggeredAlert], None]) -> None:
        """Register a callback invoked synchronously on each triggered alert.

        Args:
            handler: Callable receiving a TriggeredAlert.
        """
        self._handlers.append(handler)

    # ------------------------------------------------------------------
    # Alert evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        ticker: str,
        field: str = "price",
        value: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> List[TriggeredAlert]:
        """Evaluate incoming market data against all applicable rules.

        Args:
            ticker: Instrument symbol.
            field: Data field name (e.g. "close", "volume").
            value: Current field value.
            extra: Optional extra context.

        Returns:
            List of TriggeredAlert for rules that fired.
        """
        t = ticker.upper()
        now = datetime.now(timezone.utc)
        fired: List[TriggeredAlert] = []
        for state in self._rules.values():
            rule = state.rule
            if not rule.enabled:
                continue
            if rule.ticker is not None and rule.ticker != t:
                continue
            if rule.field != field:
                continue
            if rule.max_triggers > 0 and state.trigger_count >= rule.max_triggers:
                rule.enabled = False
                continue
            if state.last_triggered is not None:
                elapsed = (now - state.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue
            triggered = False
            if rule.direction == AlertDirection.ABOVE and value > rule.threshold:
                triggered = True
            elif rule.direction == AlertDirection.BELOW and value < rule.threshold:
                triggered = True
            elif rule.direction == AlertDirection.CROSS:
                triggered = True
            if not triggered:
                continue
            state.trigger_count += 1
            state.last_triggered = now
            alert = TriggeredAlert(
                alert_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                alert_type=rule.alert_type,
                severity=rule.severity,
                ticker=t,
                message=(
                    f"{rule.name}: {t} {field}={value:.4g} "
                    f"{rule.direction.value} {rule.threshold:.4g}"
                ),
                current_value=value,
                threshold=rule.threshold,
                direction=rule.direction,
                timestamp=now,
                delivered=False,
                extra=extra or {},
            )
            self._history.append(alert)
            fired.append(alert)
            self._deliver(alert)
            for handler in self._handlers:
                handler(alert)
        return fired

    def fire_custom_alert(
        self,
        name: str,
        message: str = "",
        severity: "AlertSeverity" = AlertSeverity.INFO,
        alert_type: "AlertType" = AlertType.CUSTOM,
        ticker: Optional[str] = None,
        value: float = 0.0,
        threshold: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> TriggeredAlert:
        """Fire an alert without an associated rule.

        Args:
            name: Alert name.
            message: Human-readable message.
            severity: Severity level.
            alert_type: Alert category.
            ticker: Optional associated ticker.
            value: Current value that triggered the alert.
            threshold: Reference threshold value.
            extra: Optional arbitrary payload.

        Returns:
            The generated TriggeredAlert.
        """
        alert = TriggeredAlert(
            alert_id=str(uuid.uuid4()),
            rule_id="CUSTOM",
            rule_name=name,
            alert_type=alert_type,
            severity=severity,
            ticker=ticker.upper() if ticker else None,
            message=message,
            current_value=value,
            threshold=threshold,
            direction=AlertDirection.ABOVE,
            timestamp=datetime.now(timezone.utc),
            delivered=False,
            extra=extra or {},
        )
        self._history.append(alert)
        self._deliver(alert)
        for handler in self._handlers:
            handler(alert)
        return alert

    # ------------------------------------------------------------------
    # Internal delivery
    # ------------------------------------------------------------------

    def _deliver(self, alert: TriggeredAlert) -> None:
        """Simulate webhook delivery for an alert."""
        for wh in self._webhooks.values():
            if not wh.enabled:
                continue
            if alert.severity not in wh.severity_filter:
                continue
            if alert.alert_type not in wh.alert_type_filter:
                continue
            self._delivery_attempts += 1
            self._delivery_successes += 1
            alert.delivered = True

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(
        self,
        limit: int = 100,
        ticker: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
    ) -> List[TriggeredAlert]:
        """Retrieve alert history with optional filters.

        Args:
            limit: Maximum number of records to return.
            ticker: Filter by instrument.
            severity: Filter by severity.
            alert_type: Filter by alert type.

        Returns:
            List of TriggeredAlert (newest first).
        """
        results = list(reversed(self._history))
        if ticker:
            t = ticker.upper()
            results = [a for a in results if a.ticker == t]
        if severity:
            results = [a for a in results if a.severity == severity]
        if alert_type:
            results = [a for a in results if a.alert_type == alert_type]
        return results[:limit]

    def clear_history(self) -> None:
        """Clear all alert history."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> AlertStats:
        """Return aggregated alert engine statistics.

        Returns:
            AlertStats.
        """
        now = datetime.now(timezone.utc)
        total = len(self._history)
        last_hour = sum(
            1 for a in self._history
            if (now - a.timestamp).total_seconds() <= 3600
        )
        by_severity: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for a in self._history:
            by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
            by_type[a.alert_type.value] = by_type.get(a.alert_type.value, 0) + 1
        delivery_rate = (
            self._delivery_successes / self._delivery_attempts
            if self._delivery_attempts > 0 else 1.0
        )
        return AlertStats(
            total_rules=len(self._rules),
            active_rules=sum(1 for s in self._rules.values() if s.rule.enabled),
            total_triggers=total,
            triggers_last_hour=last_hour,
            by_severity=by_severity,
            by_type=by_type,
            delivery_success_rate=delivery_rate,
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_default_engine: Optional[AlertEngine] = None


def get_alert_engine() -> AlertEngine:
    """Return the singleton AlertEngine.

    Returns:
        Shared AlertEngine instance.
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = AlertEngine()
    return _default_engine
