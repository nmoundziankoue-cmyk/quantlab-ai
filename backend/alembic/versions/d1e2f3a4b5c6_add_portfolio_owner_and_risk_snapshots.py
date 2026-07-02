"""Add portfolio owner_id and portfolio_risk_snapshots table (M10 Phase 7).

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-06-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d1e2f3a4b5c6"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable owner_id to portfolios (existing rows keep NULL)
    op.add_column(
        "portfolios",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_portfolios_owner_id", "portfolios", ["owner_id"])

    # Portfolio risk snapshots table
    op.create_table(
        "portfolio_risk_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "taken_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("total_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_pnl", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_pnl_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("positions_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_portfolio_risk_snapshots_portfolio_taken",
        "portfolio_risk_snapshots",
        ["portfolio_id", "taken_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_risk_snapshots_portfolio_taken")
    op.drop_table("portfolio_risk_snapshots")
    op.drop_index("ix_portfolios_owner_id", table_name="portfolios")
    op.drop_column("portfolios", "owner_id")
