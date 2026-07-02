"""Enterprise Auth & RBAC router (M7) — users, teams, JWT, audit logs."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import services.auth_service as svc
from middleware.rbac import get_current_user_payload
from schemas.auth import (
    AddTeamMemberRequest,
    CreateTeamRequest,
    LoginRequest,
    RegisterRequest,
    UpdateUserRequest,
)

_ROLES = ["VIEWER", "ANALYST", "TRADER", "QUANT", "RISK_MANAGER", "PORTFOLIO_MANAGER", "ADMIN", "SUPER_ADMIN"]


class RefreshRequest(BaseModel):
    refresh_token: str

router = APIRouter(prefix="/auth", tags=["Auth & Enterprise"])


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@router.post("/register", response_model=Dict[str, Any])
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    result = svc.create_user(
        db=db,
        email=req.email,
        password=req.password,
        full_name=req.full_name,
        role=req.role,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/login", response_model=Dict[str, Any])
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a JWT access token."""
    result = svc.authenticate_user(db=db, email=req.email, password=req.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.post("/verify-token", response_model=Dict[str, Any])
def verify_token(body: Dict[str, Any]):
    """Decode and verify a JWT token."""
    token = body.get("token", "")
    payload = svc.decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {**payload, "valid": True}


@router.get("/me", response_model=Dict[str, Any])
def get_me(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Return the current authenticated user's profile."""
    user = svc.get_user(db, uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return svc._user_to_dict(user)


@router.post("/logout", response_model=Dict[str, Any])
def logout(payload: dict = Depends(get_current_user_payload)):
    """Revoke the current access token so it can no longer be used."""
    from services.cache import cache
    jti = payload.get("jti")
    if jti:
        # Blacklist until the token's natural expiry
        exp = payload.get("exp", 0)
        now_ts = int(__import__("time").time())
        ttl = max(1, exp - now_ts)
        cache.revoke_token(jti, ttl)
    return {"logged_out": True, "user_id": payload.get("sub")}


@router.post("/refresh", response_model=Dict[str, Any])
def refresh_tokens(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for new access + refresh tokens."""
    from services.auth_enterprise import rotate_refresh_token
    try:
        access_token, refresh_token = rotate_refresh_token(db, body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/roles", response_model=Dict[str, Any])
def list_roles():
    """List all available roles and their permission levels."""
    role_levels = {
        "VIEWER": 1, "ANALYST": 2, "TRADER": 3, "QUANT": 4,
        "RISK_MANAGER": 5, "PORTFOLIO_MANAGER": 6, "ADMIN": 7, "SUPER_ADMIN": 8,
    }
    return {
        "roles": [{"name": r, "level": role_levels.get(r, 0)} for r in _ROLES],
        "total": len(_ROLES),
    }


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@router.get("/users", response_model=List[Dict[str, Any]])
def list_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all users with optional filters."""
    return svc.list_users(db, role=role, is_active=is_active, limit=limit)


@router.get("/users/{user_id}", response_model=Dict[str, Any])
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific user by ID."""
    user = svc.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return svc._user_to_dict(user)


@router.put("/users/{user_id}", response_model=Dict[str, Any])
def update_user(
    user_id: uuid.UUID,
    req: UpdateUserRequest,
    db: Session = Depends(get_db),
):
    """Update user attributes."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    result = svc.update_user(db, user_id, **update_data)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.post("/users/{user_id}/deactivate", response_model=Dict[str, Any])
def deactivate_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Deactivate a user account."""
    ok = svc.deactivate_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deactivated": str(user_id)}


@router.post("/check-permission", response_model=Dict[str, Any])
def check_permission(body: Dict[str, Any]):
    """Check if a given role has the required permission level."""
    user_role = body.get("user_role", "VIEWER")
    required_role = body.get("required_role", "ANALYST")
    has_permission = svc.check_permission(user_role, required_role)
    return {
        "user_role": user_role,
        "required_role": required_role,
        "has_permission": has_permission,
    }


# ---------------------------------------------------------------------------
# Team management
# ---------------------------------------------------------------------------

@router.post("/teams", response_model=Dict[str, Any])
def create_team(req: CreateTeamRequest, db: Session = Depends(get_db)):
    """Create a new team."""
    result = svc.create_team(db, req.name, req.description, req.settings)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/teams", response_model=List[Dict[str, Any]])
def list_teams(limit: int = 50, db: Session = Depends(get_db)):
    """List all teams."""
    return svc.list_teams(db, limit=limit)


@router.get("/teams/{team_id}", response_model=Dict[str, Any])
def get_team(team_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a team and its members."""
    team = svc.get_team(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = svc.get_team_members(db, team_id)
    return {**svc._team_to_dict(team), "members": members}


@router.delete("/teams/{team_id}", response_model=Dict[str, Any])
def delete_team(team_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a team."""
    ok = svc.delete_team(db, team_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"deleted": str(team_id)}


@router.post("/teams/{team_id}/members", response_model=Dict[str, Any])
def add_team_member(
    team_id: uuid.UUID,
    req: AddTeamMemberRequest,
    db: Session = Depends(get_db),
):
    """Add a user to a team."""
    result = svc.add_team_member(db, team_id, req.user_id, req.role)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/teams/{team_id}/members/{user_id}", response_model=Dict[str, Any])
def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Remove a user from a team."""
    ok = svc.remove_team_member(db, team_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"removed": str(user_id)}


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

@router.get("/audit-logs", response_model=List[Dict[str, Any]])
def list_audit_logs(
    user_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List audit log entries."""
    return svc.list_audit_logs(
        db, user_id=user_id, action=action, resource_type=resource_type, limit=limit
    )


@router.post("/audit-logs", response_model=Dict[str, Any])
def create_audit_log(body: Dict[str, Any], db: Session = Depends(get_db)):
    """Create an audit log entry."""
    log = svc.create_audit_log(
        db=db,
        action=body.get("action", "UNKNOWN"),
        resource_type=body.get("resource_type", "UNKNOWN"),
        user_id=uuid.UUID(body["user_id"]) if body.get("user_id") else None,
        resource_id=body.get("resource_id"),
        ip_address=body.get("ip_address"),
        response_status=body.get("response_status"),
    )
    return {
        "id": str(log.id),
        "action": log.action,
        "resource_type": log.resource_type,
        "created_at": log.created_at.isoformat(),
    }
