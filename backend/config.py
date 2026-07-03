"""Application settings loaded from environment variables or .env file."""
from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the QuantLab backend.

    Values are read from the environment first, then from a ``.env`` file in
    the backend directory, then the defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    database_url: str = (
        "postgresql+psycopg2://apex:apex@localhost:5432/apexquant"
    )

    # ------------------------------------------------------------------ #
    # Market data                                                          #
    # ------------------------------------------------------------------ #
    price_cache_ttl_seconds: int = 60
    sector_cache_ttl_seconds: int = 86_400  # 24 h

    # ------------------------------------------------------------------ #
    # Performance engine                                                   #
    # ------------------------------------------------------------------ #
    default_benchmark: str = "SPY"
    risk_free_rate_annual: float = 0.02  # used for Sharpe / Sortino

    # ------------------------------------------------------------------ #
    # M2 — Cache (Redis optional; falls back to in-memory if not set)     #
    # ------------------------------------------------------------------ #
    redis_url: str = ""           # e.g. "redis://localhost:6379/0"
    quote_cache_ttl_seconds: int = 30
    ohlcv_cache_ttl_seconds: int = 300
    news_cache_ttl_seconds: int = 600  # 10 min
    watchlist_cache_ttl_seconds: int = 30

    # ------------------------------------------------------------------ #
    # Security & Auth                                                      #
    # ------------------------------------------------------------------ #
    jwt_secret_key: str = "CHANGE_ME_run_python_-c_import_secrets_print_secrets_token_hex_32"
    access_token_expire_hours: int = 24
    refresh_token_expire_days: int = 30

    # Comma-separated allowed CORS origins for production.
    # Empty string = dev mode (allow all localhost ports via regex).
    # Example: "https://app.example.com,https://admin.example.com"
    cors_origins: str = ""

    # ------------------------------------------------------------------ #
    # Environment                                                          #
    # ------------------------------------------------------------------ #
    environment: str = "development"  # "production" enables strict security

    # ------------------------------------------------------------------ #
    # API                                                                  #
    # ------------------------------------------------------------------ #
    api_title: str = "QuantLab AI — Portfolio Engine"
    api_version: str = "2.0.0"


    @model_validator(mode="after")
    def _require_jwt_secret(self) -> "Settings":
        if self.jwt_secret_key.startswith("CHANGE_ME"):
            raise ValueError(
                "JWT_SECRET_KEY is not configured.\n"
                "Generate a secure key and add it to backend/.env:\n"
                '  python -c "import secrets; print(secrets.token_hex(32))"\n'
                "Then set: JWT_SECRET_KEY=<generated_value>"
            )
        return self


settings = Settings()
