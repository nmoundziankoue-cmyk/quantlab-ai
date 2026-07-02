"""M9 Phase 10 — OAuth2 provider framework.

Supports: Google, GitHub, Microsoft, Apple (stubs — no external API keys required
for the framework to load; actual OAuth flows require env vars).

Provides:
- ``OAuthProvider`` ABC
- 4 concrete stubs
- ``get_authorization_url`` — redirect URL builder
- ``exchange_code`` — mock token exchange
- ``get_user_info`` — mock user profile fetch
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import urllib.parse
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class OAuthUserInfo:
    provider: str
    provider_user_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    raw: Optional[dict] = None


@dataclass
class OAuthTokens:
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class OAuthProvider(ABC):
    name: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str]

    def get_client_id(self) -> Optional[str]:
        return os.environ.get(f"{self.name.upper()}_CLIENT_ID")

    def get_client_secret(self) -> Optional[str]:
        return os.environ.get(f"{self.name.upper()}_CLIENT_SECRET")

    def is_configured(self) -> bool:
        return bool(self.get_client_id() and self.get_client_secret())

    def build_authorization_url(self, redirect_uri: str, state: str, **extra) -> str:
        params = {
            "client_id": self.get_client_id() or "demo_client_id",
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            **extra,
        }
        return f"{self.authorization_url}?{urllib.parse.urlencode(params)}"

    @abstractmethod
    def mock_user_info(self, code: str) -> OAuthUserInfo:
        """Return a deterministic mock user for testing."""

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange auth code for tokens (mock implementation)."""
        return OAuthTokens(
            access_token=f"mock_access_{hashlib.sha256(code.encode()).hexdigest()[:16]}",
            refresh_token=f"mock_refresh_{secrets.token_hex(8)}",
            scope=" ".join(self.scopes),
        )

    def get_user_info(self, access_token: str) -> OAuthUserInfo:
        return self.mock_user_info(access_token)


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

class GoogleOAuthProvider(OAuthProvider):
    name = "google"
    authorization_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    scopes = ["openid", "email", "profile"]

    def build_authorization_url(self, redirect_uri: str, state: str, **extra) -> str:
        return super().build_authorization_url(redirect_uri, state, access_type="offline", prompt="consent")

    def mock_user_info(self, code: str) -> OAuthUserInfo:
        uid = hashlib.md5(code.encode()).hexdigest()[:8]
        return OAuthUserInfo(
            provider="google",
            provider_user_id=f"google_{uid}",
            email=f"user_{uid}@gmail.com",
            name=f"Google User {uid[:4]}",
            avatar_url=f"https://lh3.googleusercontent.com/a/{uid}",
        )


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

class GitHubOAuthProvider(OAuthProvider):
    name = "github"
    authorization_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    userinfo_url = "https://api.github.com/user"
    scopes = ["read:user", "user:email"]

    def mock_user_info(self, code: str) -> OAuthUserInfo:
        uid = abs(hash(code)) % 100000
        return OAuthUserInfo(
            provider="github",
            provider_user_id=str(uid),
            email=f"user{uid}@users.noreply.github.com",
            name=f"github_user_{uid}",
            avatar_url=f"https://avatars.githubusercontent.com/u/{uid}",
        )


# ---------------------------------------------------------------------------
# Microsoft
# ---------------------------------------------------------------------------

class MicrosoftOAuthProvider(OAuthProvider):
    name = "microsoft"
    authorization_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    userinfo_url = "https://graph.microsoft.com/v1.0/me"
    scopes = ["openid", "email", "profile", "User.Read"]

    def mock_user_info(self, code: str) -> OAuthUserInfo:
        uid = hashlib.sha1(code.encode()).hexdigest()[:8]
        return OAuthUserInfo(
            provider="microsoft",
            provider_user_id=str(uuid.UUID(uid.ljust(32, "0"))),
            email=f"{uid}@outlook.com",
            name=f"MS User {uid[:4]}",
        )


# ---------------------------------------------------------------------------
# Apple
# ---------------------------------------------------------------------------

class AppleOAuthProvider(OAuthProvider):
    name = "apple"
    authorization_url = "https://appleid.apple.com/auth/authorize"
    token_url = "https://appleid.apple.com/auth/token"
    userinfo_url = ""  # Apple returns user info in JWT id_token only
    scopes = ["name", "email"]

    def build_authorization_url(self, redirect_uri: str, state: str, **extra) -> str:
        return super().build_authorization_url(redirect_uri, state, response_mode="form_post")

    def mock_user_info(self, code: str) -> OAuthUserInfo:
        uid = hashlib.md5(code.encode()).hexdigest()[:8]
        return OAuthUserInfo(
            provider="apple",
            provider_user_id=f"000{uid}.apple.id",
            email=f"{uid}@privaterelay.appleid.com",
            name=f"Apple User",
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PROVIDERS: Dict[str, OAuthProvider] = {
    "google": GoogleOAuthProvider(),
    "github": GitHubOAuthProvider(),
    "microsoft": MicrosoftOAuthProvider(),
    "apple": AppleOAuthProvider(),
}


def get_provider(name: str) -> Optional[OAuthProvider]:
    return _PROVIDERS.get(name.lower())


def list_providers() -> List[dict]:
    return [
        {
            "name": p.name,
            "configured": p.is_configured(),
            "scopes": p.scopes,
            "authorization_url": p.authorization_url,
        }
        for p in _PROVIDERS.values()
    ]


def generate_state() -> str:
    return secrets.token_urlsafe(32)
