"""Add M10 enterprise tables: strategies, agent_sessions, agent_messages, websocket_events, background_jobs, provider_health_snapshots.

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a7
Create Date: 2026-06-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c1d2e3f4a5b6"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── trading_strategies ──────────────────────────────────────────────────
    op.create_table(
        "trading_strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trading_strategies_user_id", "trading_strategies", ["user_id"])
    op.create_index("ix_trading_strategies_strategy_type", "trading_strategies", ["strategy_type"])

    # ── trading_strategy_runs ───────────────────────────────────────────────
    op.create_table(
        "trading_strategy_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trading_strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("parameters_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trading_strategy_runs_strategy_id", "trading_strategy_runs", ["strategy_id"])
    op.create_index("ix_trading_strategy_runs_status", "trading_strategy_runs", ["status"])

    # ── agent_sessions ──────────────────────────────────────────────────────
    op.create_table(
        "agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("session_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("context", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_sessions_user_id", "agent_sessions", ["user_id"])
    op.create_index("ix_agent_sessions_agent_type", "agent_sessions", ["agent_type"])
    op.create_index("ix_agent_sessions_status", "agent_sessions", ["status"])

    # ── agent_messages ──────────────────────────────────────────────────────
    op.create_table(
        "agent_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True),
        sa.Column("token_usage", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_messages_session_id", "agent_messages", ["session_id"])

    # ── websocket_events ────────────────────────────────────────────────────
    op.create_table(
        "websocket_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conn_id", sa.String(100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(200), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("seq", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_websocket_events_conn_id", "websocket_events", ["conn_id"])
    op.create_index("ix_websocket_events_user_id", "websocket_events", ["user_id"])
    op.create_index("ix_websocket_events_event_type", "websocket_events", ["event_type"])
    op.create_index("ix_websocket_events_created_at", "websocket_events", ["created_at"])

    # ── background_jobs ─────────────────────────────────────────────────────
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="5"),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("progress_pct", sa.Integer, nullable=True),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_background_jobs_user_id", "background_jobs", ["user_id"])
    op.create_index("ix_background_jobs_job_type", "background_jobs", ["job_type"])
    op.create_index("ix_background_jobs_status", "background_jobs", ["status"])

    # ── provider_health_snapshots ───────────────────────────────────────────
    op.create_table(
        "provider_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_name", sa.String(100), nullable=False),
        sa.Column("health_score", sa.Float, nullable=True),
        sa.Column("latency_ms_p50", sa.Float, nullable=True),
        sa.Column("latency_ms_p95", sa.Float, nullable=True),
        sa.Column("error_rate", sa.Float, nullable=True),
        sa.Column("quota_used", sa.Integer, nullable=True),
        sa.Column("quota_limit", sa.Integer, nullable=True),
        sa.Column("is_healthy", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_provider_health_snapshots_provider_name", "provider_health_snapshots", ["provider_name"])
    op.create_index("ix_provider_health_snapshots_snapshot_at", "provider_health_snapshots", ["snapshot_at"])


def downgrade() -> None:
    op.drop_table("provider_health_snapshots")
    op.drop_table("background_jobs")
    op.drop_table("websocket_events")
    op.drop_table("agent_messages")
    op.drop_table("agent_sessions")
    op.drop_table("trading_strategy_runs")
    op.drop_table("trading_strategies")
