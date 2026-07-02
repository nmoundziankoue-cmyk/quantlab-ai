"""Add M8 production tables: sessions, refresh tokens, login history, MFA, notifications.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # user_sessions
    # ------------------------------------------------------------------
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_fingerprint", sa.String(255), nullable=True),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_is_active", "user_sessions", ["is_active"])

    # ------------------------------------------------------------------
    # refresh_tokens
    # ------------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("is_revoked", sa.Boolean, default=False, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    # ------------------------------------------------------------------
    # login_history
    # ------------------------------------------------------------------
    op.create_table(
        "login_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email_attempted", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("failure_reason", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_login_history_user_id", "login_history", ["user_id"])

    # ------------------------------------------------------------------
    # mfa_configs
    # ------------------------------------------------------------------
    op.create_table(
        "mfa_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("totp_secret", sa.String(255), nullable=True),
        sa.Column("is_enabled", sa.Boolean, default=False, nullable=False),
        sa.Column("backup_codes", postgresql.JSONB, nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_mfa_configs_user_id", "mfa_configs", ["user_id"])

    # ------------------------------------------------------------------
    # notification_templates
    # ------------------------------------------------------------------
    op.create_table(
        "notification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("subject_template", sa.Text, nullable=True),
        sa.Column("body_template", sa.Text, nullable=False),
        sa.Column("variables", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_notification_templates_name", "notification_templates", ["name"])
    op.create_index("ix_notification_templates_channel", "notification_templates", ["channel"])

    # ------------------------------------------------------------------
    # notification_logs
    # ------------------------------------------------------------------
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), default="PENDING", nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, default=0, nullable=False),
        sa.Column("priority", sa.Integer, default=5, nullable=False),
        sa.Column("metadata_", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_logs_user_id", "notification_logs", ["user_id"])
    op.create_index("ix_notification_logs_channel", "notification_logs", ["channel"])
    op.create_index("ix_notification_logs_status", "notification_logs", ["status"])


def downgrade() -> None:
    op.drop_table("notification_logs")
    op.drop_table("notification_templates")
    op.drop_table("mfa_configs")
    op.drop_table("login_history")
    op.drop_table("refresh_tokens")
    op.drop_table("user_sessions")
