"""Tests for the Enterprise Auth & RBAC service (M7)."""
from __future__ import annotations

import uuid

import pytest

import services.auth_service as svc
from models.auth import AuditLog, Team, TeamMember, User


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        h = svc.hash_password("securepass123")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_verify_correct_password(self):
        h = svc.hash_password("correctpassword")
        assert svc.verify_password("correctpassword", h) is True

    def test_reject_wrong_password(self):
        h = svc.hash_password("rightpassword")
        assert svc.verify_password("wrongpassword", h) is False

    def test_different_passwords_different_hashes(self):
        h1 = svc.hash_password("pass1")
        h2 = svc.hash_password("pass1")
        # Different salts → different hashes even for same password
        assert h1 != h2

    def test_verify_malformed_hash_returns_false(self):
        assert svc.verify_password("pass", "not:a:valid:hash") is False


# ---------------------------------------------------------------------------
# JWT token
# ---------------------------------------------------------------------------

class TestJWT:
    def test_create_token_returns_string(self):
        token = svc.create_access_token("user-id", "test@example.com", "ANALYST")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_decode_valid_token(self):
        token = svc.create_access_token("user-id", "test@example.com", "ANALYST")
        payload = svc.decode_token(token)
        assert payload is not None
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "ANALYST"

    def test_decode_invalid_token_returns_none(self):
        result = svc.decode_token("not.a.valid.token")
        assert result is None

    def test_decode_empty_token_returns_none(self):
        result = svc.decode_token("")
        assert result is None

    def test_decode_tampered_token_returns_none(self):
        token = svc.create_access_token("u1", "x@y.com", "ADMIN")
        parts = token.split(".")
        # Tamper with the payload
        tampered = parts[0] + ".tampered123." + parts[2]
        result = svc.decode_token(tampered)
        assert result is None

    def test_token_contains_user_id(self):
        token = svc.create_access_token("my-user-id", "u@u.com", "QUANT")
        payload = svc.decode_token(token)
        assert payload["sub"] == "my-user-id"


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

class TestUserManagement:
    def test_create_user(self, db):
        result = svc.create_user(db, email="alice@example.com", password="TestPass1")
        assert "id" in result
        assert result["email"] == "alice@example.com"
        assert result["role"] == "ANALYST"

    def test_create_user_duplicate_email_returns_error(self, db):
        svc.create_user(db, email="dup@example.com", password="TestPass1")
        result = svc.create_user(db, email="dup@example.com", password="TestPass1")
        assert "error" in result

    def test_create_user_invalid_role_returns_error(self, db):
        result = svc.create_user(db, email="bad@example.com", password="TestPass1", role="SUPERUSER")
        assert "error" in result

    def test_authenticate_user_success(self, db):
        svc.create_user(db, email="login@example.com", password="TestPass1")
        result = svc.authenticate_user(db, email="login@example.com", password="TestPass1")
        assert "access_token" in result
        assert result["token_type"] == "bearer"

    def test_authenticate_user_wrong_password(self, db):
        svc.create_user(db, email="wrongpass@example.com", password="TestPass1")
        result = svc.authenticate_user(db, email="wrongpass@example.com", password="wrongpass")
        assert "error" in result

    def test_authenticate_user_not_found(self, db):
        result = svc.authenticate_user(db, email="nobody@nowhere.com", password="x")
        assert "error" in result

    def test_authenticate_deactivated_user(self, db):
        svc.create_user(db, email="inactive@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "inactive@example.com")
        user.is_active = False
        db.flush()
        result = svc.authenticate_user(db, email="inactive@example.com", password="TestPass1")
        assert "error" in result

    def test_get_user_by_id(self, db):
        svc.create_user(db, email="byid@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "byid@example.com")
        fetched = svc.get_user(db, user.id)
        assert fetched is not None
        assert fetched.email == "byid@example.com"

    def test_get_user_not_found(self, db):
        result = svc.get_user(db, uuid.uuid4())
        assert result is None

    def test_list_users(self, db):
        svc.create_user(db, email="list1@example.com", password="TestPass1")
        users = svc.list_users(db, limit=100)
        assert isinstance(users, list)
        emails = [u["email"] for u in users]
        assert "list1@example.com" in emails

    def test_list_users_filter_by_role(self, db):
        svc.create_user(db, email="admin1@example.com", password="TestPass1", role="ADMIN")
        admins = svc.list_users(db, role="ADMIN", limit=50)
        assert all(u["role"] == "ADMIN" for u in admins)

    def test_update_user(self, db):
        svc.create_user(db, email="update@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "update@example.com")
        result = svc.update_user(db, user.id, full_name="Alice Smith")
        assert result is not None
        assert result["full_name"] == "Alice Smith"

    def test_deactivate_user(self, db):
        svc.create_user(db, email="deactivate@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "deactivate@example.com")
        ok = svc.deactivate_user(db, user.id)
        assert ok is True
        db.refresh(user)
        assert user.is_active is False

    def test_deactivate_user_not_found(self, db):
        ok = svc.deactivate_user(db, uuid.uuid4())
        assert ok is False


# ---------------------------------------------------------------------------
# RBAC permission check
# ---------------------------------------------------------------------------

class TestRBACPermissions:
    def test_admin_has_all_permissions(self):
        for role in ("VIEWER", "ANALYST", "TRADER", "QUANT", "ADMIN"):
            assert svc.check_permission("ADMIN", role) is True

    def test_viewer_limited_permissions(self):
        assert svc.check_permission("VIEWER", "VIEWER") is True
        assert svc.check_permission("VIEWER", "ANALYST") is False
        assert svc.check_permission("VIEWER", "ADMIN") is False

    def test_analyst_mid_level(self):
        assert svc.check_permission("ANALYST", "VIEWER") is True
        assert svc.check_permission("ANALYST", "ANALYST") is True
        assert svc.check_permission("ANALYST", "ADMIN") is False


# ---------------------------------------------------------------------------
# Team management
# ---------------------------------------------------------------------------

class TestTeamManagement:
    def test_create_team(self, db):
        result = svc.create_team(db, name="Quant Team A")
        assert "id" in result
        assert result["name"] == "Quant Team A"

    def test_create_team_duplicate_returns_error(self, db):
        svc.create_team(db, name="DupTeam")
        result = svc.create_team(db, name="DupTeam")
        assert "error" in result

    def test_list_teams(self, db):
        svc.create_team(db, name="List Team")
        teams = svc.list_teams(db, limit=50)
        assert isinstance(teams, list)
        names = [t["name"] for t in teams]
        assert "List Team" in names

    def test_delete_team(self, db):
        result = svc.create_team(db, name="Delete Team")
        team = svc.get_team(db, uuid.UUID(result["id"]))
        ok = svc.delete_team(db, team.id)
        assert ok is True

    def test_delete_team_not_found(self, db):
        ok = svc.delete_team(db, uuid.uuid4())
        assert ok is False

    def test_add_team_member(self, db):
        team_result = svc.create_team(db, name="Members Team")
        svc.create_user(db, email="member@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "member@example.com")
        team = svc.get_team(db, uuid.UUID(team_result["id"]))
        result = svc.add_team_member(db, team.id, user.id)
        assert "id" in result

    def test_add_same_member_twice_returns_error(self, db):
        team_result = svc.create_team(db, name="DupMember Team")
        svc.create_user(db, email="dupmember@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "dupmember@example.com")
        team = svc.get_team(db, uuid.UUID(team_result["id"]))
        svc.add_team_member(db, team.id, user.id)
        result = svc.add_team_member(db, team.id, user.id)
        assert "error" in result

    def test_remove_team_member(self, db):
        team_result = svc.create_team(db, name="Remove Member Team")
        svc.create_user(db, email="remove_member@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "remove_member@example.com")
        team = svc.get_team(db, uuid.UUID(team_result["id"]))
        svc.add_team_member(db, team.id, user.id)
        ok = svc.remove_team_member(db, team.id, user.id)
        assert ok is True

    def test_get_team_members(self, db):
        team_result = svc.create_team(db, name="GetMembers Team")
        svc.create_user(db, email="gmember@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "gmember@example.com")
        team = svc.get_team(db, uuid.UUID(team_result["id"]))
        svc.add_team_member(db, team.id, user.id)
        members = svc.get_team_members(db, team.id)
        assert isinstance(members, list)
        assert len(members) >= 1


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

class TestAuditLogs:
    def test_create_audit_log(self, db):
        log = svc.create_audit_log(
            db, action="LOGIN", resource_type="USER", ip_address="127.0.0.1"
        )
        assert log.id is not None
        assert log.action == "LOGIN"

    def test_list_audit_logs(self, db):
        svc.create_audit_log(db, action="LIST_TEST", resource_type="USER")
        logs = svc.list_audit_logs(db, limit=50)
        assert isinstance(logs, list)
        actions = [l["action"] for l in logs]
        assert "LIST_TEST" in actions

    def test_list_audit_logs_filter_by_action(self, db):
        svc.create_audit_log(db, action="FILTERED_ACTION", resource_type="PORTFOLIO")
        logs = svc.list_audit_logs(db, action="FILTERED_ACTION", limit=10)
        assert all(l["action"] == "FILTERED_ACTION" for l in logs)

    def test_audit_log_with_user(self, db):
        svc.create_user(db, email="audit_user@example.com", password="TestPass1")
        user = svc.get_user_by_email(db, "audit_user@example.com")
        log = svc.create_audit_log(
            db, action="TRADE", resource_type="ORDER", user_id=user.id
        )
        assert log.user_id == user.id
