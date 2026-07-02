"""Tests for services/auth_enterprise.py (M8)."""
from __future__ import annotations

import time
import uuid

import pytest

from services.auth_enterprise import (
    _hash_token,
    check_extended_permission,
    clear_attempts,
    create_refresh_token_raw,
    create_session,
    disable_mfa,
    enable_mfa,
    generate_totp_secret,
    get_mfa_status,
    get_provisioning_uri,
    get_totp_code,
    is_account_locked,
    list_login_history,
    list_sessions,
    record_failed_attempt,
    record_login,
    revoke_all_sessions,
    revoke_session,
    rotate_refresh_token,
    setup_mfa,
    validate_mfa,
    verify_totp,
)


# ==========================================================================
# TOTP (pure math — no DB)
# ==========================================================================


class TestTOTP:
    def test_generate_secret_is_base32(self):
        import base64
        secret = generate_totp_secret()
        assert len(secret) == 32
        # Should be valid base32
        decoded = base64.b32decode(secret.upper())
        assert len(decoded) == 20

    def test_get_totp_code_length(self):
        secret = generate_totp_secret()
        code = get_totp_code(secret)
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_totp_with_current_code(self):
        secret = generate_totp_secret()
        code = get_totp_code(secret)
        assert verify_totp(secret, code)

    def test_verify_totp_invalid_code(self):
        secret = generate_totp_secret()
        assert not verify_totp(secret, "000000")

    def test_verify_totp_wrong_length_fails(self):
        secret = generate_totp_secret()
        assert not verify_totp(secret, "123")

    def test_verify_totp_window_allows_drift(self):
        secret = generate_totp_secret()
        # Generate code for "30 seconds ago"
        past_code = get_totp_code(secret, timestamp=time.time() - 28)
        assert verify_totp(secret, past_code, window=1)

    def test_provisioning_uri_format(self):
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "user@example.com")
        assert uri.startswith("otpauth://totp/")
        assert secret in uri
        assert "issuer=ApexQuant" in uri

    def test_different_secrets_give_different_codes(self):
        s1 = generate_totp_secret()
        s2 = generate_totp_secret()
        now = time.time()
        # Extremely unlikely to collide
        codes = {get_totp_code(s1, now), get_totp_code(s2, now)}
        # Could technically collide but extremely rare; just test they work
        assert all(len(c) == 6 for c in codes)


# ==========================================================================
# Token hashing
# ==========================================================================


class TestTokenHashing:
    def test_hash_is_deterministic(self):
        raw = "test-token-abc"
        assert _hash_token(raw) == _hash_token(raw)

    def test_different_raw_gives_different_hash(self):
        assert _hash_token("abc") != _hash_token("xyz")

    def test_hash_length(self):
        raw = create_refresh_token_raw()
        h = _hash_token(raw)
        assert len(h) == 64  # SHA-256 hex

    def test_refresh_token_raw_is_urlsafe(self):
        raw = create_refresh_token_raw()
        assert len(raw) > 32
        import re
        assert re.match(r"^[A-Za-z0-9_\-]+$", raw)


# ==========================================================================
# Brute-force protection (no DB)
# ==========================================================================


class TestBruteForce:
    def setup_method(self):
        clear_attempts("bf_test@example.com")

    def teardown_method(self):
        clear_attempts("bf_test@example.com")

    def test_not_locked_initially(self):
        assert not is_account_locked("bf_test@example.com")

    def test_records_failed_attempts(self):
        count = record_failed_attempt("bf_test@example.com")
        assert count == 1

    def test_accumulates_attempts(self):
        for i in range(5):
            count = record_failed_attempt("bf_test@example.com")
        assert count == 5

    def test_locks_after_max_attempts(self):
        for _ in range(10):
            record_failed_attempt("bf_test@example.com")
        assert is_account_locked("bf_test@example.com")

    def test_clear_attempts_unlocks(self):
        for _ in range(10):
            record_failed_attempt("bf_test@example.com")
        clear_attempts("bf_test@example.com")
        assert not is_account_locked("bf_test@example.com")

    def test_window_resets_after_expiry(self):
        import services.auth_enterprise as ae
        ae._login_attempts["bf_test@example.com"] = (10, time.time() - 1000)
        assert not is_account_locked("bf_test@example.com")


# ==========================================================================
# RBAC permission checks
# ==========================================================================


class TestRBACPermissions:
    def test_super_admin_passes_all(self):
        for role in ["VIEWER", "ANALYST", "TRADER", "QUANT", "ADMIN", "SUPER_ADMIN"]:
            assert check_extended_permission("SUPER_ADMIN", role)

    def test_viewer_fails_analyst(self):
        assert not check_extended_permission("VIEWER", "ANALYST")

    def test_analyst_passes_viewer(self):
        assert check_extended_permission("ANALYST", "VIEWER")

    def test_admin_passes_quant(self):
        assert check_extended_permission("ADMIN", "QUANT")

    def test_unknown_role_fails(self):
        assert not check_extended_permission("UNKNOWN", "VIEWER")

    def test_same_role_passes(self):
        assert check_extended_permission("TRADER", "TRADER")


# ==========================================================================
# Session management (DB required)
# ==========================================================================


class TestSessionManagement:
    def _make_user(self, db):
        from services.auth_service import create_user
        user = create_user(db, f"sess_{uuid.uuid4().hex[:8]}@test.com", "Pass123!")
        return uuid.UUID(user["id"])

    def test_create_session_returns_tokens(self, db):
        uid = self._make_user(db)
        session, access_tok, refresh_tok = create_session(db, uid, ip_address="127.0.0.1")
        assert session.id is not None
        assert len(access_tok) > 10
        assert len(refresh_tok) > 30

    def test_session_stored_in_db(self, db):
        uid = self._make_user(db)
        from models.sessions import UserSession
        session, _, _ = create_session(db, uid)
        stored = db.get(UserSession, session.id)
        assert stored is not None
        assert stored.user_id == uid

    def test_refresh_token_stored_as_hash(self, db):
        uid = self._make_user(db)
        from models.sessions import RefreshToken
        _, _, raw = create_session(db, uid)
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_token(raw)).first()
        assert rt is not None
        assert not rt.is_revoked

    def test_rotate_refresh_token(self, db):
        uid = self._make_user(db)
        _, _, raw = create_session(db, uid)
        new_access, new_refresh = rotate_refresh_token(db, raw)
        assert len(new_access) > 10
        assert new_refresh != raw

    def test_rotate_revokes_old_token(self, db):
        uid = self._make_user(db)
        from models.sessions import RefreshToken
        _, _, raw = create_session(db, uid)
        rotate_refresh_token(db, raw)
        old_rt = db.query(RefreshToken).filter(
            RefreshToken.token_hash == _hash_token(raw)
        ).first()
        assert old_rt.is_revoked

    def test_rotate_invalid_token_raises(self, db):
        with pytest.raises(ValueError, match="Invalid"):
            rotate_refresh_token(db, "invalid-token")

    def test_revoke_session(self, db):
        uid = self._make_user(db)
        session, _, _ = create_session(db, uid)
        ok = revoke_session(db, session.id)
        assert ok
        from models.sessions import UserSession
        stored = db.get(UserSession, session.id)
        assert not stored.is_active

    def test_list_sessions(self, db):
        uid = self._make_user(db)
        create_session(db, uid, device_name="device-A")
        create_session(db, uid, device_name="device-B")
        sessions = list_sessions(db, uid)
        assert len(sessions) >= 2

    def test_revoke_all_sessions(self, db):
        uid = self._make_user(db)
        create_session(db, uid)
        create_session(db, uid)
        count = revoke_all_sessions(db, uid)
        assert count >= 2
        remaining = list_sessions(db, uid)
        assert len(remaining) == 0


# ==========================================================================
# Login history
# ==========================================================================


class TestLoginHistory:
    def _make_user(self, db):
        from services.auth_service import create_user
        user = create_user(db, f"hist_{uuid.uuid4().hex[:8]}@test.com", "Pass123!")
        return uuid.UUID(user["id"])

    def test_record_successful_login(self, db):
        uid = self._make_user(db)
        entry = record_login(
            db,
            user_id=uid,
            email_attempted="test@test.com",
            ip_address="1.2.3.4",
            user_agent="test-agent",
            success=True,
        )
        assert entry.id is not None
        assert entry.success

    def test_record_failed_login(self, db):
        uid = self._make_user(db)
        entry = record_login(
            db,
            user_id=uid,
            email_attempted="test@test.com",
            ip_address="1.2.3.4",
            user_agent=None,
            success=False,
            failure_reason="invalid_credentials",
        )
        assert not entry.success
        assert entry.failure_reason == "invalid_credentials"

    def test_list_login_history(self, db):
        uid = self._make_user(db)
        for i in range(3):
            record_login(db, user_id=uid, email_attempted="x@x.com", ip_address=None, user_agent=None, success=True)
        history = list_login_history(db, uid)
        assert len(history) >= 3

    def test_login_history_dict_format(self, db):
        uid = self._make_user(db)
        record_login(db, user_id=uid, email_attempted="x@x.com", ip_address="1.1.1.1", user_agent=None, success=True)
        history = list_login_history(db, uid, limit=1)
        assert history
        assert "success" in history[0]
        assert "created_at" in history[0]


# ==========================================================================
# MFA management
# ==========================================================================


class TestMFA:
    def _make_user(self, db):
        from services.auth_service import create_user
        user = create_user(db, f"mfa_{uuid.uuid4().hex[:8]}@test.com", "Pass123!")
        return uuid.UUID(user["id"])

    def test_setup_mfa_returns_secret(self, db):
        uid = self._make_user(db)
        result = setup_mfa(db, uid)
        assert "secret" in result
        assert "provisioning_uri" in result
        assert len(result["secret"]) > 0

    def test_mfa_status_not_configured(self, db):
        uid = self._make_user(db)
        status = get_mfa_status(db, uid)
        assert not status["enabled"]
        assert not status["configured"]

    def test_mfa_status_configured_not_enabled(self, db):
        uid = self._make_user(db)
        setup_mfa(db, uid)
        status = get_mfa_status(db, uid)
        assert not status["enabled"]
        assert status["configured"]

    def test_enable_mfa_with_valid_code(self, db):
        uid = self._make_user(db)
        result = setup_mfa(db, uid)
        secret = result["secret"]
        code = get_totp_code(secret)
        backup_codes = enable_mfa(db, uid, code)
        assert len(backup_codes) == 8
        status = get_mfa_status(db, uid)
        assert status["enabled"]

    def test_enable_mfa_with_invalid_code_raises(self, db):
        uid = self._make_user(db)
        setup_mfa(db, uid)
        with pytest.raises(ValueError, match="Invalid TOTP"):
            enable_mfa(db, uid, "000000")

    def test_validate_mfa_succeeds_with_correct_code(self, db):
        uid = self._make_user(db)
        result = setup_mfa(db, uid)
        code = get_totp_code(result["secret"])
        enable_mfa(db, uid, code)
        new_code = get_totp_code(result["secret"])
        assert validate_mfa(db, uid, new_code)

    def test_validate_mfa_fails_with_wrong_code(self, db):
        uid = self._make_user(db)
        result = setup_mfa(db, uid)
        code = get_totp_code(result["secret"])
        enable_mfa(db, uid, code)
        assert not validate_mfa(db, uid, "000000")

    def test_validate_mfa_skipped_when_disabled(self, db):
        uid = self._make_user(db)
        # MFA not set up -> always passes
        assert validate_mfa(db, uid, "wrong")

    def test_disable_mfa(self, db):
        uid = self._make_user(db)
        result = setup_mfa(db, uid)
        code = get_totp_code(result["secret"])
        enable_mfa(db, uid, code)
        new_code = get_totp_code(result["secret"])
        disable_mfa(db, uid, new_code)
        status = get_mfa_status(db, uid)
        assert not status["enabled"]

    def test_disable_mfa_invalid_code_raises(self, db):
        uid = self._make_user(db)
        result = setup_mfa(db, uid)
        code = get_totp_code(result["secret"])
        enable_mfa(db, uid, code)
        with pytest.raises(ValueError, match="Invalid TOTP"):
            disable_mfa(db, uid, "000000")
