"""RBAC FastAPI dependency factories (M8).

Usage::

    from middleware.rbac import require_role, get_current_user_payload

    @router.get("/admin-only")
    def admin_endpoint(payload=Depends(require_role("ADMIN"))):
        return {"user": payload["email"]}
"""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import decode_token, check_permission

_bearer = HTTPBearer(auto_error=False)

# Extended role levels (superset of M7 5-tier)
_ROLE_LEVEL: Dict[str, int] = {
    "VIEWER": 1,
    "ANALYST": 2,
    "TRADER": 3,
    "QUANT": 4,
    "RISK_MANAGER": 5,
    "PORTFOLIO_MANAGER": 6,
    "ADMIN": 7,
    "SUPER_ADMIN": 8,
}


def _extract_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    # 1. Bearer header
    if credentials and credentials.credentials:
        return credentials.credentials
    # 2. Cookie fallback
    return request.cookies.get("access_token")


def get_current_user_payload(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """Decode JWT and return the payload. Raises 401 on failure."""
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_optional_user_payload(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[dict]:
    """Like get_current_user_payload but returns None instead of raising 401."""
    token = _extract_token(request, credentials)
    if not token:
        return None
    return decode_token(token)


def require_role(minimum_role: str):
    """Return a FastAPI dependency that enforces a minimum role level."""

    def dependency(
        payload: dict = Depends(get_current_user_payload),
    ) -> dict:
        user_role = payload.get("role", "VIEWER")
        user_level = _ROLE_LEVEL.get(user_role, 0)
        req_level = _ROLE_LEVEL.get(minimum_role, 0)
        if user_level < req_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {minimum_role}, current: {user_role}",
            )
        return payload

    return dependency


def require_any_role(*roles: str):
    """Return a dependency that passes if the user has any of the listed roles."""

    def dependency(
        payload: dict = Depends(get_current_user_payload),
    ) -> dict:
        user_role = payload.get("role", "VIEWER")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Allowed roles: {', '.join(roles)}",
            )
        return payload

    return dependency


# Convenience pre-built dependencies
AuthRequired = Depends(get_current_user_payload)
AdminRequired = Depends(require_role("ADMIN"))
SuperAdminRequired = Depends(require_role("SUPER_ADMIN"))
AnalystRequired = Depends(require_role("ANALYST"))
TraderRequired = Depends(require_role("TRADER"))
QuantRequired = Depends(require_role("QUANT"))
RiskManagerRequired = Depends(require_role("RISK_MANAGER"))
