"""Tests for services/notifications.py (M8)."""
from __future__ import annotations

import uuid
from string import Template

import pytest

import services.notifications as notif_svc
from models.notifications import NotificationLog, NotificationTemplate


class TestNotificationTemplatesCRUD:
    def test_create_template(self, db):
        tpl = notif_svc.create_template(
            db,
            name=f"tpl_{uuid.uuid4().hex[:8]}",
            channel="CONSOLE",
            body_template="Hello $name",
            subject_template="Greetings",
        )
        assert tpl["id"]
        assert tpl["channel"] == "CONSOLE"

    def test_create_duplicate_name_raises(self, db):
        name = f"dup_{uuid.uuid4().hex[:8]}"
        notif_svc.create_template(db, name=name, channel="CONSOLE", body_template="x")
        with pytest.raises(ValueError, match="already exists"):
            notif_svc.create_template(db, name=name, channel="CONSOLE", body_template="y")

    def test_create_invalid_channel_raises(self, db):
        with pytest.raises(ValueError, match="Unknown channel"):
            notif_svc.create_template(db, name="bad", channel="FAX", body_template="x")

    def test_get_template_by_id(self, db):
        tpl = notif_svc.create_template(
            db, name=f"get_{uuid.uuid4().hex[:8]}", channel="CONSOLE", body_template="hi"
        )
        fetched = notif_svc.get_template(db, uuid.UUID(tpl["id"]))
        assert fetched["name"] == tpl["name"]

    def test_get_nonexistent_returns_none(self, db):
        assert notif_svc.get_template(db, uuid.uuid4()) is None

    def test_list_templates(self, db):
        n = f"list_{uuid.uuid4().hex[:8]}"
        notif_svc.create_template(db, name=n, channel="WEBHOOK", body_template="body")
        templates = notif_svc.list_templates(db, channel="WEBHOOK", active_only=False)
        names = [t["name"] for t in templates]
        assert n in names

    def test_update_template_body(self, db):
        tpl = notif_svc.create_template(
            db, name=f"upd_{uuid.uuid4().hex[:8]}", channel="CONSOLE", body_template="old"
        )
        updated = notif_svc.update_template(db, uuid.UUID(tpl["id"]), body_template="new")
        assert updated["body_template"] == "new"

    def test_update_nonexistent_returns_none(self, db):
        assert notif_svc.update_template(db, uuid.uuid4(), body_template="x") is None

    def test_delete_template(self, db):
        tpl = notif_svc.create_template(
            db, name=f"del_{uuid.uuid4().hex[:8]}", channel="CONSOLE", body_template="bye"
        )
        ok = notif_svc.delete_template(db, uuid.UUID(tpl["id"]))
        assert ok
        assert notif_svc.get_template(db, uuid.UUID(tpl["id"])) is None

    def test_delete_nonexistent_returns_false(self, db):
        assert not notif_svc.delete_template(db, uuid.uuid4())

    def test_list_active_only_filters_inactive(self, db):
        n = f"inactive_{uuid.uuid4().hex[:8]}"
        tpl = notif_svc.create_template(db, name=n, channel="CONSOLE", body_template="x")
        notif_svc.update_template(db, uuid.UUID(tpl["id"]), is_active=False)
        active = notif_svc.list_templates(db, active_only=True)
        names = [t["name"] for t in active]
        assert n not in names


class TestSendNotification:
    def test_send_console_delivers(self, db):
        result = notif_svc.send_notification(
            db,
            channel="CONSOLE",
            recipient="test@example.com",
            subject="Test",
            body="Hello world",
        )
        assert result["status"] == "DELIVERED"
        assert result["channel"] == "CONSOLE"

    def test_send_creates_log(self, db):
        notif_svc.send_notification(
            db, channel="CONSOLE", recipient="r@r.com", body="log test"
        )
        logs = notif_svc.list_logs(db, limit=5)
        assert any(l["channel"] == "CONSOLE" for l in logs)

    def test_send_invalid_channel_raises(self, db):
        with pytest.raises(ValueError, match="Unknown channel"):
            notif_svc.send_notification(db, channel="SMS", recipient="x", body="y")

    def test_send_webhook_fails_gracefully(self, db):
        result = notif_svc.send_notification(
            db,
            channel="WEBHOOK",
            recipient="http://localhost:1/nonexistent",
            body="test",
        )
        # Should fail gracefully, not raise
        assert result["status"] == "FAILED"
        assert result["error_message"] is not None

    def test_send_slack_fails_gracefully(self, db):
        result = notif_svc.send_notification(
            db,
            channel="SLACK",
            recipient="http://localhost:1/fake-webhook",
            body="slack test",
        )
        assert result["status"] == "FAILED"

    def test_send_increments_attempts(self, db):
        result = notif_svc.send_notification(
            db, channel="CONSOLE", recipient="x@x.com", body="attempts test"
        )
        assert result["attempts"] == 1

    def test_send_with_user_id(self, db):
        from services.auth_service import create_user
        user = create_user(db, f"notif_{uuid.uuid4().hex[:8]}@test.com", "Pass123!")
        uid = uuid.UUID(user["id"])
        result = notif_svc.send_notification(
            db, channel="CONSOLE", recipient="x@x.com", body="user notif", user_id=uid
        )
        assert result["user_id"] == str(uid)


class TestSendFromTemplate:
    def test_send_from_template_substitutes_vars(self, db):
        n = f"tmpl_{uuid.uuid4().hex[:8]}"
        notif_svc.create_template(
            db,
            name=n,
            channel="CONSOLE",
            body_template="Hello $username, your balance is $balance",
            subject_template="Balance for $username",
        )
        result = notif_svc.send_from_template(
            db, n, "user@example.com", variables={"username": "Alice", "balance": "1000"}
        )
        assert "Alice" in result["body"]
        assert result["status"] == "DELIVERED"

    def test_send_nonexistent_template_raises(self, db):
        with pytest.raises(ValueError, match="not found"):
            notif_svc.send_from_template(db, "no-such-template", "x@x.com")

    def test_send_inactive_template_raises(self, db):
        n = f"inact_{uuid.uuid4().hex[:8]}"
        tpl = notif_svc.create_template(db, name=n, channel="CONSOLE", body_template="x")
        notif_svc.update_template(db, uuid.UUID(tpl["id"]), is_active=False)
        with pytest.raises(ValueError, match="not found"):
            notif_svc.send_from_template(db, n, "x@x.com")


class TestNotificationLogs:
    def test_list_logs_returns_list(self, db):
        notif_svc.send_notification(db, channel="CONSOLE", recipient="a@b.com", body="log")
        logs = notif_svc.list_logs(db, limit=10)
        assert isinstance(logs, list)
        assert len(logs) > 0

    def test_get_log_by_id(self, db):
        result = notif_svc.send_notification(db, channel="CONSOLE", recipient="a@b.com", body="get-log")
        log = notif_svc.get_log(db, uuid.UUID(result["id"]))
        assert log is not None
        assert log["channel"] == "CONSOLE"

    def test_get_nonexistent_log_returns_none(self, db):
        assert notif_svc.get_log(db, uuid.uuid4()) is None

    def test_list_logs_filter_by_channel(self, db):
        notif_svc.send_notification(db, channel="CONSOLE", recipient="f@f.com", body="filter-ch")
        logs = notif_svc.list_logs(db, channel="CONSOLE", limit=50)
        assert all(l["channel"] == "CONSOLE" for l in logs)

    def test_list_logs_filter_by_status(self, db):
        notif_svc.send_notification(db, channel="CONSOLE", recipient="s@s.com", body="status-test")
        logs = notif_svc.list_logs(db, status="DELIVERED", limit=50)
        assert all(l["status"] == "DELIVERED" for l in logs)

    def test_log_dict_has_required_fields(self, db):
        result = notif_svc.send_notification(db, channel="CONSOLE", recipient="x@x.com", body="fields")
        log = notif_svc.get_log(db, uuid.UUID(result["id"]))
        for key in ("id", "channel", "recipient", "body", "status", "attempts", "created_at"):
            assert key in log
