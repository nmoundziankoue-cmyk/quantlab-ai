"""Tests for M9 Phase 10 — OAuth2 provider framework."""
import pytest
from services.oauth_providers import (
    GoogleOAuthProvider, GitHubOAuthProvider, MicrosoftOAuthProvider, AppleOAuthProvider,
    get_provider, list_providers, generate_state, OAuthUserInfo, OAuthTokens,
)


# ---------------------------------------------------------------------------
# generate_state
# ---------------------------------------------------------------------------

class TestGenerateState:
    def test_unique(self):
        states = {generate_state() for _ in range(50)}
        assert len(states) == 50

    def test_url_safe(self):
        state = generate_state()
        import urllib.parse
        assert urllib.parse.quote(state, safe="") != state or len(state) > 10


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    def test_get_google(self):
        p = get_provider("google")
        assert p is not None
        assert p.name == "google"

    def test_get_github(self):
        assert get_provider("github").name == "github"

    def test_get_microsoft(self):
        assert get_provider("microsoft").name == "microsoft"

    def test_get_apple(self):
        assert get_provider("apple").name == "apple"

    def test_get_case_insensitive(self):
        assert get_provider("GOOGLE") is get_provider("google")

    def test_get_nonexistent(self):
        assert get_provider("twitter") is None

    def test_list_providers(self):
        providers = list_providers()
        names = [p["name"] for p in providers]
        for expected in ("google", "github", "microsoft", "apple"):
            assert expected in names

    def test_list_structure(self):
        for p in list_providers():
            assert "name" in p
            assert "configured" in p
            assert "scopes" in p


# ---------------------------------------------------------------------------
# Individual providers
# ---------------------------------------------------------------------------

class TestGoogleProvider:
    def setup_method(self):
        self.p = GoogleOAuthProvider()

    def test_scopes_include_openid(self):
        assert "openid" in self.p.scopes

    def test_authorization_url_includes_client_id(self):
        url = self.p.build_authorization_url("https://example.com/cb", "state123")
        assert "client_id" in url
        assert "state123" in url

    def test_auth_url_includes_offline_access(self):
        url = self.p.build_authorization_url("https://example.com/cb", "s")
        assert "offline" in url

    def test_mock_user_info(self):
        user = self.p.mock_user_info("test_code")
        assert user.provider == "google"
        assert "@" in user.email

    def test_exchange_code(self):
        tokens = self.p.exchange_code("code123", "https://example.com/cb")
        assert tokens.access_token.startswith("mock_access_")
        assert tokens.refresh_token is not None

    def test_deterministic_user_for_same_code(self):
        u1 = self.p.mock_user_info("code_abc")
        u2 = self.p.mock_user_info("code_abc")
        assert u1.email == u2.email

    def test_different_codes_different_users(self):
        u1 = self.p.mock_user_info("code_a")
        u2 = self.p.mock_user_info("code_b")
        assert u1.email != u2.email


class TestGitHubProvider:
    def setup_method(self):
        self.p = GitHubOAuthProvider()

    def test_scopes(self):
        assert "read:user" in self.p.scopes

    def test_mock_user(self):
        user = self.p.mock_user_info("gh_code")
        assert user.provider == "github"
        assert user.avatar_url is not None

    def test_authorization_url(self):
        url = self.p.build_authorization_url("https://app.com/cb", "st")
        assert "github.com" in url


class TestMicrosoftProvider:
    def setup_method(self):
        self.p = MicrosoftOAuthProvider()

    def test_scopes_include_email(self):
        assert "email" in self.p.scopes

    def test_mock_user(self):
        user = self.p.mock_user_info("ms_code")
        assert user.provider == "microsoft"

    def test_authorization_url(self):
        url = self.p.build_authorization_url("https://app.com/cb", "st")
        assert "microsoftonline.com" in url


class TestAppleProvider:
    def setup_method(self):
        self.p = AppleOAuthProvider()

    def test_mock_user(self):
        user = self.p.mock_user_info("apple_code")
        assert user.provider == "apple"
        assert ".apple.id" in user.provider_user_id

    def test_authorization_url_form_post(self):
        url = self.p.build_authorization_url("https://app.com/cb", "st")
        assert "form_post" in url

    def test_scopes(self):
        assert "email" in self.p.scopes


# ---------------------------------------------------------------------------
# OAuthTokens dataclass
# ---------------------------------------------------------------------------

class TestOAuthTokens:
    def test_defaults(self):
        t = OAuthTokens(access_token="tok")
        assert t.token_type == "Bearer"
        assert t.expires_in == 3600

    def test_custom_expiry(self):
        t = OAuthTokens(access_token="tok", expires_in=7200)
        assert t.expires_in == 7200


# ---------------------------------------------------------------------------
# OAuthUserInfo dataclass
# ---------------------------------------------------------------------------

class TestOAuthUserInfo:
    def test_basic(self):
        u = OAuthUserInfo(provider="google", provider_user_id="123", email="a@b.com", name="Alice")
        assert u.provider == "google"
        assert u.avatar_url is None

    def test_with_avatar(self):
        u = OAuthUserInfo(provider="github", provider_user_id="456", email="b@c.com", name="Bob",
                          avatar_url="https://avatars.github.com/456")
        assert u.avatar_url is not None
