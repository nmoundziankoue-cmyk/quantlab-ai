"""Pydantic v2 schemas for the Enterprise Auth & RBAC system (M7)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: str = "ANALYST"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: "UserSchema"


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class TeamSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime


class AddTeamMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: str = "MEMBER"


class TeamMemberSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime


class AuditLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    response_status: Optional[int] = None
    created_at: datetime


class TokenDecodeResponse(BaseModel):
    sub: str
    email: str
    role: str
    iat: int
    exp: int
    valid: bool
