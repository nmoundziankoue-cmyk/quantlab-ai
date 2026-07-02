"""Enterprise Auth & RBAC service — JWT (HMAC-SHA256), RBAC, teams, audit logs (M7).

Uses Python stdlib only (hashlib, hmac, base64, secrets) — no external JWT library.
Token format: base64url(header).base64url(payload).HMAC-SHA256-signature
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models.auth import AuditLog, Team, TeamMember, User

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"
_TOKEN_EXPIRY_HOURS = 24
_PBKDF2_ITERATIONS = 100_000
_ROLES = {"ADMIN", "ANALYST", "VIEWER", "QUANT", "TRADER"}

# Role hierarchy (higher value = more permissions)
_ROLE_LEVEL = {"VIEWER": 1, "ANALYST": 2, "TRADER": 3, "QUANT": 4, "ADMIN": 5}


# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS)
    return f"pbkdf2:{salt}:{dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash."""
    try:
        _, salt, stored_dk = hashed.split(":")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS)
        return hmac.compare_digest(dk.hex(), stored_dk)
    except (ValueError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# JWT-like token (HMAC-SHA256)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_hours: int = _TOKEN_EXPIRY_HOURS,
) -> str:
    """Create a signed HMAC-SHA256 access token."""
    header = {"alg": _ALGORITHM, "typ": "JWT"}
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "jti": secrets.token_hex(16),  # unique token ID for blacklisting
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_hours)).timestamp()),
    }
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{h}.{p}".encode()
    sig = hmac.new(settings.jwt_secret_key.encode(), message, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a token. Returns payload dict or None on failure."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h, p, sig = parts
        message = f"{h}.{p}".encode()
        expected_sig = hmac.new(settings.jwt_secret_key.encode(), message, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(sig), expected_sig):
            return None
        payload = json.loads(_b64url_decode(p))
        now = int(datetime.now(timezone.utc).timestamp())
        if payload.get("exp", 0) < now:
            return None  # expired
        # Check token blacklist (logout / revocation)
        jti = payload.get("jti")
        if jti:
            from services.cache import cache
            if cache.is_token_revoked(jti):
                return None
        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def validate_password_policy(password: str) -> Optional[str]:
    """Return an error message if the password does not meet policy requirements, else None."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one digit"
    return None


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "ANALYST",
) -> Dict[str, Any]:
    """Create a new user. Returns error dict if email already exists."""
    existing = db.execute(select(User).where(User.email == email)).scalars().first()
    if existing:
        return {"error": f"User with email {email!r} already exists"}
    if role.upper() not in _ROLES:
        return {"error": f"Invalid role {role!r}. Must be one of {sorted(_ROLES)}"}
    pw_error = validate_password_policy(password)
    if pw_error:
        return {"error": pw_error}

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role.upper(),
    )
    db.add(user)
    db.flush()
    return _user_to_dict(user)


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> Dict[str, Any]:
    """Authenticate a user. Returns token dict or error dict."""
    user = db.execute(select(User).where(User.email == email)).scalars().first()
    if not user:
        return {"error": "Invalid credentials"}
    if not verify_password(password, user.hashed_password):
        return {"error": "Invalid credentials"}
    if not user.is_active:
        return {"error": "Account is deactivated"}

    user.last_login = datetime.now(timezone.utc)
    db.flush()

    token = create_access_token(str(user.id), user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_to_dict(user),
    }


def get_user(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.execute(select(User).where(User.email == email)).scalars().first()


def list_users(
    db: Session,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    if role:
        stmt = stmt.where(User.role == role.upper())
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    users = list(db.execute(stmt).scalars())
    return [_user_to_dict(u) for u in users]


def update_user(
    db: Session,
    user_id: uuid.UUID,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    user = db.get(User, user_id)
    if not user:
        return None
    if "password" in kwargs:
        user.hashed_password = hash_password(kwargs.pop("password"))
    for k, v in kwargs.items():
        if hasattr(user, k):
            setattr(user, k, v)
    db.flush()
    return _user_to_dict(user)


def deactivate_user(db: Session, user_id: uuid.UUID) -> bool:
    user = db.get(User, user_id)
    if not user:
        return False
    user.is_active = False
    db.flush()
    return True


def check_permission(user_role: str, required_role: str) -> bool:
    """Check if user_role has at least required_role permissions."""
    return _ROLE_LEVEL.get(user_role.upper(), 0) >= _ROLE_LEVEL.get(required_role.upper(), 999)


# ---------------------------------------------------------------------------
# Team management
# ---------------------------------------------------------------------------

def create_team(
    db: Session,
    name: str,
    description: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    existing = db.execute(select(Team).where(Team.name == name)).scalars().first()
    if existing:
        return {"error": f"Team {name!r} already exists"}
    team = Team(name=name, description=description, settings=settings)
    db.add(team)
    db.flush()
    return _team_to_dict(team)


def get_team(db: Session, team_id: uuid.UUID) -> Optional[Team]:
    return db.get(Team, team_id)


def list_teams(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    teams = list(db.execute(select(Team).order_by(Team.name).limit(limit)).scalars())
    return [_team_to_dict(t) for t in teams]


def delete_team(db: Session, team_id: uuid.UUID) -> bool:
    team = db.get(Team, team_id)
    if not team:
        return False
    db.delete(team)
    db.flush()
    return True


def add_team_member(
    db: Session,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "MEMBER",
) -> Dict[str, Any]:
    team = db.get(Team, team_id)
    if not team:
        return {"error": "Team not found"}
    user = db.get(User, user_id)
    if not user:
        return {"error": "User not found"}

    existing = db.execute(
        select(TeamMember)
        .where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).scalars().first()
    if existing:
        return {"error": "User is already a member"}

    member = TeamMember(team_id=team_id, user_id=user_id, role=role)
    db.add(member)
    db.flush()
    return {
        "id": str(member.id),
        "team_id": str(team_id),
        "user_id": str(user_id),
        "role": member.role,
    }


def remove_team_member(
    db: Session, team_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    member = db.execute(
        select(TeamMember)
        .where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).scalars().first()
    if not member:
        return False
    db.delete(member)
    db.flush()
    return True


def get_team_members(db: Session, team_id: uuid.UUID) -> List[Dict[str, Any]]:
    members = list(
        db.execute(
            select(TeamMember).where(TeamMember.team_id == team_id)
        ).scalars()
    )
    return [
        {"id": str(m.id), "team_id": str(m.team_id), "user_id": str(m.user_id), "role": m.role}
        for m in members
    ]


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def create_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    user_id: Optional[uuid.UUID] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None,
    response_status: Optional[int] = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_data=request_data,
        response_status=response_status,
    )
    db.add(log)
    db.flush()
    return log


def list_audit_logs(
    db: Session,
    user_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    logs = list(db.execute(stmt).scalars())
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "response_status": log.response_status,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _user_to_dict(u: User) -> Dict[str, Any]:
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "is_verified": u.is_verified,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _team_to_dict(t: Team) -> Dict[str, Any]:
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
