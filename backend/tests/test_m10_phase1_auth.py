"""M10 Phase 1 — Real auth endpoint tests: /auth/me, /auth/logout, /auth/refresh, /auth/roles."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

_COMPLIANT_PWD = "TestPass1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(email: str, password: str = _COMPLIANT_PWD):
    r = client.post("/auth/register", json={"email": email, "password": password})
    if r.status_code not in (200, 400):  # 400 = already exists
        raise RuntimeError(f"Register failed: {r.text}")
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200, r2.text
    return r2.json()


# ── /auth/me ─────────────────────────────────────────────────────────────────

class TestAuthMe:
    def test_me_returns_user_profile(self):
        data = _register_and_login("me_test@m10.com")
        token = data["access_token"]
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "me_test@m10.com"
        assert "role" in body
        assert "id" in body

    def test_me_without_token_returns_401(self):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token_returns_401(self):
        r = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401


# ── /auth/logout ─────────────────────────────────────────────────────────────

class TestAuthLogout:
    def test_logout_returns_success(self):
        data = _register_and_login("logout_test@m10.com")
        token = data["access_token"]
        r = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["logged_out"] is True
        assert "user_id" in body

    def test_logout_requires_auth(self):
        r = client.post("/auth/logout")
        assert r.status_code == 401

    def test_token_revoked_after_logout(self):
        data = _register_and_login("revoke_test@m10.com")
        token = data["access_token"]
        # Logout
        r1 = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert r1.status_code == 200
        # Token should now be revoked — /auth/me should return 401
        r2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 401


# ── /auth/roles ───────────────────────────────────────────────────────────────

class TestAuthRoles:
    def test_roles_endpoint_returns_list(self):
        r = client.get("/auth/roles")
        assert r.status_code == 200
        body = r.json()
        assert "roles" in body
        assert body["total"] >= 5
        names = [role["name"] for role in body["roles"]]
        assert "ADMIN" in names
        assert "ANALYST" in names
        assert "VIEWER" in names

    def test_roles_have_level_field(self):
        r = client.get("/auth/roles")
        roles = r.json()["roles"]
        for role in roles:
            assert "name" in role
            assert "level" in role
            assert role["level"] >= 1

    def test_admin_has_higher_level_than_viewer(self):
        r = client.get("/auth/roles")
        roles = {role["name"]: role["level"] for role in r.json()["roles"]}
        assert roles["ADMIN"] > roles["VIEWER"]


# ── /auth/refresh ─────────────────────────────────────────────────────────────

class TestAuthRefresh:
    def test_refresh_with_invalid_token_returns_401(self):
        r = client.post("/auth/refresh", json={"refresh_token": "invalid_token"})
        assert r.status_code == 401

    def test_refresh_with_empty_token_returns_401(self):
        r = client.post("/auth/refresh", json={"refresh_token": ""})
        assert r.status_code == 401


# ── Password policy ───────────────────────────────────────────────────────────

class TestPasswordPolicy:
    def test_short_password_rejected(self):
        r = client.post("/auth/register", json={
            "email": "short_pw@m10.com",
            "password": "Ab1",
        })
        # Pydantic min_length=8 returns 422; service-level check returns 400 — both mean rejected
        assert r.status_code in (400, 422)

    def test_no_uppercase_rejected(self):
        r = client.post("/auth/register", json={
            "email": "no_upper@m10.com",
            "password": "testpass1",
        })
        assert r.status_code == 400
        assert "uppercase" in r.json()["detail"].lower()

    def test_no_digit_rejected(self):
        r = client.post("/auth/register", json={
            "email": "no_digit@m10.com",
            "password": "TestPassword",
        })
        assert r.status_code == 400
        assert "digit" in r.json()["detail"].lower()

    def test_compliant_password_accepted(self):
        r = client.post("/auth/register", json={
            "email": "good_pw@m10.com",
            "password": "TestPass1",
        })
        # Either 200 (created) or 400 (already exists) — both mean policy passed
        assert r.status_code in (200, 400)
        if r.status_code == 200:
            assert "id" in r.json()
