"""Extended auth endpoints: refresh tokens, sessions, MFA, login history (M8)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from middleware.rbac import get_current_user_payload
from services.auth_enterprise import (
    clear_attempts,
    create_session,
    disable_mfa,
    enable_mfa,
    get_mfa_status,
    get_remaining_lockout,
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
)
from services.auth_service import authenticate_user, get_user_by_email

router = APIRouter(prefix="/auth/enterprise", tags=["auth-enterprise"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str
    device_name: Optional[str] = None
    mfa_code: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class MFAVerifyRequest(BaseModel):
    code: str


class MFAValidateRequest(BaseModel):
    user_id: str
    code: str


# ---------------------------------------------------------------------------
# Login with session creation
# ---------------------------------------------------------------------------


@router.post("/login")
def enterprise_login(
    body: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Authenticate and return access + refresh tokens with session creation."""
    email = body.email.lower().strip()
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if is_account_locked(email):
        remaining = get_remaining_lockout(email)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked. Try again in {int(remaining)}s.",
        )

    result = authenticate_user(db, email, body.password)
    if result is None:
        count = record_failed_attempt(email)
        user = get_user_by_email(db, email)
        record_login(
            db,
            user_id=uuid.UUID(user["id"]) if user else None,
            email_attempted=email,
            ip_address=ip,
            user_agent=ua,
            success=False,
            failure_reason="invalid_credentials",
        )
        attempts_left = max(0, 10 - count)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials. {attempts_left} attempts remaining before lockout.",
        )

    user_dict = result["user"]
    user_id = uuid.UUID(user_dict["id"])

    # MFA check
    mfa_status = get_mfa_status(db, user_id)
    if mfa_status["enabled"]:
        if not body.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="MFA_REQUIRED",
            )
        if not validate_mfa(db, user_id, body.mfa_code):
            record_login(
                db,
                user_id=user_id,
                email_attempted=email,
                ip_address=ip,
                user_agent=ua,
                success=False,
                failure_reason="invalid_mfa",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code",
            )

    clear_attempts(email)
    session, access_token, refresh_token = create_session(
        db,
        user_id,
        ip_address=ip,
        user_agent=ua,
        device_name=body.device_name,
    )
    record_login(
        db,
        user_id=user_id,
        email_attempted=email,
        ip_address=ip,
        user_agent=ua,
        success=True,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "session_id": str(session.id),
        "user": user_dict,
    }


# ---------------------------------------------------------------------------
# Token rotation
# ---------------------------------------------------------------------------


@router.post("/refresh")
def refresh_tokens(body: RefreshRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Exchange a valid refresh token for new access + refresh tokens."""
    try:
        access_token, refresh_token = rotate_refresh_token(db, body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


@router.get("/sessions")
def get_sessions(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List active sessions for the current user."""
    user_id = uuid.UUID(payload["sub"])
    sessions = list_sessions(db, user_id)
    return {"sessions": sessions, "count": len(sessions)}


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Revoke a specific session."""
    sid = uuid.UUID(session_id)
    ok = revoke_session(db, sid)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"revoked": True, "session_id": session_id}


@router.delete("/sessions")
def delete_all_sessions(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Revoke all other sessions (logout everywhere)."""
    user_id = uuid.UUID(payload["sub"])
    count = revoke_all_sessions(db, user_id)
    return {"revoked_count": count}


# ---------------------------------------------------------------------------
# Login history
# ---------------------------------------------------------------------------


@router.get("/login-history")
def login_history(
    limit: int = 50,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user_id = uuid.UUID(payload["sub"])
    history = list_login_history(db, user_id, limit=limit)
    return {"history": history, "count": len(history)}


# ---------------------------------------------------------------------------
# MFA management
# ---------------------------------------------------------------------------


@router.post("/mfa/setup")
def mfa_setup(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generate TOTP secret and provisioning URI."""
    user_id = uuid.UUID(payload["sub"])
    try:
        result = setup_mfa(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/mfa/enable")
def mfa_enable(
    body: MFAVerifyRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Verify TOTP code and activate MFA. Returns backup codes."""
    user_id = uuid.UUID(payload["sub"])
    try:
        backup_codes = enable_mfa(db, user_id, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"enabled": True, "backup_codes": backup_codes}


@router.post("/mfa/disable")
def mfa_disable(
    body: MFAVerifyRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Disable MFA after TOTP verification."""
    user_id = uuid.UUID(payload["sub"])
    try:
        disable_mfa(db, user_id, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"enabled": False}


@router.get("/mfa/status")
def mfa_status(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user_id = uuid.UUID(payload["sub"])
    return get_mfa_status(db, user_id)


@router.post("/mfa/validate")
def mfa_validate(
    body: MFAValidateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Validate MFA code for a given user (used after password auth)."""
    try:
        user_id = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    valid = validate_mfa(db, user_id, body.code)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    return {"valid": True}
