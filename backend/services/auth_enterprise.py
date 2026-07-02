"""Production auth extensions: refresh tokens, sessions, MFA/TOTP, brute-force protection.

This module extends M7's ``services/auth_service.py`` without modifying it.
All new tables live in ``models/sessions.py``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import struct
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config import settings
from models.sessions import LoginHistory, MFAConfig, RefreshToken, UserSession
from services.auth_service import create_access_token, decode_token, get_user, _ROLE_LEVEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extended role hierarchy (superset of M7's 5-tier)
# ---------------------------------------------------------------------------

_EXTENDED_ROLE_LEVEL: Dict[str, int] = {
    **_ROLE_LEVEL,
    "RISK_MANAGER": 5,
    "PORTFOLIO_MANAGER": 6,
    "SUPER_ADMIN": 8,
}
# Normalise existing levels so ADMIN stays >= RISK_MANAGER/PM
_EXTENDED_ROLE_LEVEL["ADMIN"] = max(_EXTENDED_ROLE_LEVEL.get("ADMIN", 5), 7)

# Brute-force protection: in-memory attempt counter {email -> (count, window_start)}
_login_attempts: Dict[str, tuple[int, float]] = {}
_LOCKOUT_WINDOW_S = 900  # 15 minutes
_MAX_ATTEMPTS = 10

# ---------------------------------------------------------------------------
# TOTP (RFC 6238) — pure stdlib implementation
# ---------------------------------------------------------------------------

TOTP_PERIOD = 30
TOTP_DIGITS = 6


def generate_totp_secret() -> str:
    """Generate a cryptographically random base32 TOTP secret."""
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8")


def _hotp(secret_b32: str, counter: int) -> int:
    key = base64.b32decode(secret_b32.upper().strip("=") + "=" * ((-len(secret_b32)) % 8))
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return code % (10 ** TOTP_DIGITS)


def get_totp_code(secret_b32: str, timestamp: Optional[float] = None) -> str:
    ts = timestamp if timestamp is not None else time.time()
    counter = int(ts // TOTP_PERIOD)
    return f"{_hotp(secret_b32, counter):0{TOTP_DIGITS}d}"


def verify_totp(secret_b32: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code allowing ±window steps for clock drift."""
    counter = int(time.time() // TOTP_PERIOD)
    for step in range(-window, window + 1):
        expected = f"{_hotp(secret_b32, counter + step):0{TOTP_DIGITS}d}"
        if hmac.compare_digest(expected.encode(), code.encode()):
            return True
    return False


def get_provisioning_uri(secret_b32: str, email: str, issuer: str = "ApexQuant") -> str:
    from urllib.parse import quote
    label = f"{issuer}:{email}"
    return (
        f"otpauth://totp/{quote(label)}"
        f"?secret={secret_b32}"
        f"&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD}"
    )


# ---------------------------------------------------------------------------
# Refresh-token helpers
# ---------------------------------------------------------------------------

_REFRESH_BYTES = 48
_REFRESH_TTL_S = 7 * 24 * 3600  # 7 days


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token_raw() -> str:
    return secrets.token_urlsafe(_REFRESH_BYTES)


# ---------------------------------------------------------------------------
# Brute-force protection
# ---------------------------------------------------------------------------

def is_account_locked(email: str) -> bool:
    entry = _login_attempts.get(email)
    if entry is None:
        return False
    count, window_start = entry
    if time.time() - window_start > _LOCKOUT_WINDOW_S:
        del _login_attempts[email]
        return False
    return count >= _MAX_ATTEMPTS


def record_failed_attempt(email: str) -> int:
    now = time.time()
    entry = _login_attempts.get(email)
    if entry is None or now - entry[1] > _LOCKOUT_WINDOW_S:
        _login_attempts[email] = (1, now)
        return 1
    count = entry[0] + 1
    _login_attempts[email] = (count, entry[1])
    return count


def clear_attempts(email: str) -> None:
    _login_attempts.pop(email, None)


def get_remaining_lockout(email: str) -> float:
    entry = _login_attempts.get(email)
    if entry is None:
        return 0.0
    count, window_start = entry
    if count < _MAX_ATTEMPTS:
        return 0.0
    remaining = _LOCKOUT_WINDOW_S - (time.time() - window_start)
    return max(0.0, remaining)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def create_session(
    db: Session,
    user_id: uuid.UUID,
    *,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    device_name: Optional[str] = None,
) -> tuple[UserSession, str, str]:
    """Create a session + initial refresh token.

    Returns (session, access_token, refresh_token_raw).
    """
    from models.auth import User
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")

    fingerprint = hashlib.sha256(
        f"{ip_address}:{user_agent}".encode()
    ).hexdigest()[:32]

    expires_at = datetime.fromtimestamp(
        time.time() + _REFRESH_TTL_S, tz=timezone.utc
    )

    session = UserSession(
        user_id=user_id,
        device_fingerprint=fingerprint,
        device_name=device_name or "unknown",
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        last_used_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()

    raw = create_refresh_token_raw()
    rt = RefreshToken(
        session_id=session.id,
        token_hash=_hash_token(raw),
        expires_at=expires_at,
    )
    db.add(rt)
    db.flush()

    access_token = create_access_token(
        str(user.id), user.email, user.role, expires_hours=1
    )
    return session, access_token, raw


def rotate_refresh_token(
    db: Session, refresh_token_raw: str
) -> tuple[str, str]:
    """Validate old refresh token, issue new access + refresh tokens.

    Returns (new_access_token, new_refresh_token_raw).
    Raises ValueError on invalid / revoked / expired token.
    """
    token_hash = _hash_token(refresh_token_raw)
    rt: Optional[RefreshToken] = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    if rt is None or rt.is_revoked:
        raise ValueError("Invalid or revoked refresh token")
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ValueError("Refresh token expired")

    session: Optional[UserSession] = db.get(UserSession, rt.session_id)
    if session is None or not session.is_active:
        raise ValueError("Session inactive or not found")

    from models.auth import User
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise ValueError("User not found or inactive")

    # Revoke old refresh token
    rt.is_revoked = True

    # Issue new refresh token
    raw_new = create_refresh_token_raw()
    new_rt = RefreshToken(
        session_id=session.id,
        token_hash=_hash_token(raw_new),
        expires_at=datetime.fromtimestamp(
            time.time() + _REFRESH_TTL_S, tz=timezone.utc
        ),
    )
    db.add(new_rt)

    # Touch session
    session.last_used_at = datetime.now(timezone.utc)
    db.flush()

    access_token = create_access_token(str(user.id), user.email, user.role, expires_hours=1)
    return access_token, raw_new


def revoke_session(db: Session, session_id: uuid.UUID) -> bool:
    session = db.get(UserSession, session_id)
    if session is None:
        return False
    session.is_active = False
    for rt in session.refresh_tokens:
        rt.is_revoked = True
    db.flush()
    return True


def list_sessions(db: Session, user_id: uuid.UUID) -> List[dict]:
    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.is_active.is_(True))
        .order_by(UserSession.created_at.desc())
        .all()
    )
    return [_session_to_dict(s) for s in sessions]


def revoke_all_sessions(db: Session, user_id: uuid.UUID, except_session: Optional[uuid.UUID] = None) -> int:
    q = db.query(UserSession).filter(
        UserSession.user_id == user_id, UserSession.is_active.is_(True)
    )
    if except_session:
        q = q.filter(UserSession.id != except_session)
    sessions = q.all()
    for s in sessions:
        s.is_active = False
        for rt in s.refresh_tokens:
            rt.is_revoked = True
    db.flush()
    return len(sessions)


# ---------------------------------------------------------------------------
# Login history
# ---------------------------------------------------------------------------

def record_login(
    db: Session,
    *,
    user_id: Optional[uuid.UUID],
    email_attempted: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str],
    success: bool,
    failure_reason: Optional[str] = None,
) -> LoginHistory:
    entry = LoginHistory(
        user_id=user_id,
        email_attempted=email_attempted,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        failure_reason=failure_reason,
    )
    db.add(entry)
    db.flush()
    return entry


def list_login_history(
    db: Session, user_id: uuid.UUID, limit: int = 50
) -> List[dict]:
    rows = (
        db.query(LoginHistory)
        .filter(LoginHistory.user_id == user_id)
        .order_by(LoginHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "ip_address": r.ip_address,
            "user_agent": r.user_agent,
            "success": r.success,
            "failure_reason": r.failure_reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# MFA management
# ---------------------------------------------------------------------------

def setup_mfa(db: Session, user_id: uuid.UUID) -> dict:
    """Create (or replace) a TOTP secret for the user. Returns secret + provisioning URI."""
    from models.auth import User
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")

    existing = db.query(MFAConfig).filter(MFAConfig.user_id == user_id).first()
    secret = generate_totp_secret()
    if existing:
        existing.totp_secret = secret
        existing.is_enabled = False
        existing.backup_codes = None
    else:
        existing = MFAConfig(user_id=user_id, totp_secret=secret, is_enabled=False)
        db.add(existing)
    db.flush()

    return {
        "secret": secret,
        "provisioning_uri": get_provisioning_uri(secret, user.email),
        "backup_codes": [],
    }


def enable_mfa(db: Session, user_id: uuid.UUID, totp_code: str) -> List[str]:
    """Verify TOTP code and enable MFA. Returns backup codes."""
    config = db.query(MFAConfig).filter(MFAConfig.user_id == user_id).first()
    if config is None or config.totp_secret is None:
        raise ValueError("MFA not set up. Call setup_mfa first.")
    if not verify_totp(config.totp_secret, totp_code):
        raise ValueError("Invalid TOTP code")

    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    config.is_enabled = True
    config.backup_codes = {"codes": backup_codes, "used": []}
    db.flush()
    return backup_codes


def disable_mfa(db: Session, user_id: uuid.UUID, totp_code: str) -> bool:
    config = db.query(MFAConfig).filter(MFAConfig.user_id == user_id).first()
    if config is None or not config.is_enabled:
        raise ValueError("MFA is not enabled")
    if not verify_totp(config.totp_secret, totp_code):
        raise ValueError("Invalid TOTP code")
    config.is_enabled = False
    config.totp_secret = None
    config.backup_codes = None
    db.flush()
    return True


def validate_mfa(db: Session, user_id: uuid.UUID, code: str) -> bool:
    """Validate TOTP or backup code. Returns True on success."""
    config = db.query(MFAConfig).filter(MFAConfig.user_id == user_id).first()
    if config is None or not config.is_enabled:
        return True  # MFA not required

    if verify_totp(config.totp_secret, code):
        config.last_used_at = datetime.now(timezone.utc)
        db.flush()
        return True

    # Try backup code
    if config.backup_codes and code.upper() in config.backup_codes.get("codes", []):
        if code.upper() not in config.backup_codes.get("used", []):
            used = list(config.backup_codes.get("used", []))
            used.append(code.upper())
            config.backup_codes = {**config.backup_codes, "used": used}
            config.last_used_at = datetime.now(timezone.utc)
            db.flush()
            return True
    return False


def get_mfa_status(db: Session, user_id: uuid.UUID) -> dict:
    config = db.query(MFAConfig).filter(MFAConfig.user_id == user_id).first()
    if config is None:
        return {"enabled": False, "configured": False}
    return {
        "enabled": config.is_enabled,
        "configured": config.totp_secret is not None,
        "last_used_at": config.last_used_at.isoformat() if config.last_used_at else None,
    }


# ---------------------------------------------------------------------------
# RBAC dependency factories
# ---------------------------------------------------------------------------

def check_extended_permission(user_role: str, required_role: str) -> bool:
    user_level = _EXTENDED_ROLE_LEVEL.get(user_role, 0)
    req_level = _EXTENDED_ROLE_LEVEL.get(required_role, 0)
    return user_level >= req_level


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _session_to_dict(s: UserSession) -> dict:
    return {
        "id": str(s.id),
        "device_name": s.device_name,
        "device_fingerprint": s.device_fingerprint,
        "ip_address": s.ip_address,
        "user_agent": s.user_agent,
        "is_active": s.is_active,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
