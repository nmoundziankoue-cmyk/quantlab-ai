"""add_m7_institutional_tables

Revision ID: a1b2c3d4e5f6
Revises: c6d193858a6c
Create Date: 2026-06-28 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c6d193858a6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add M7 institutional tables: options, orchestrator, knowledge graph, economic calendar, auth."""

    # ------------------------------------------------------------------
    # Options Analytics
    # ------------------------------------------------------------------
    op.create_table(
        'options_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('underlying_price', sa.Float(), nullable=False),
        sa.Column('strike', sa.Float(), nullable=False),
        sa.Column('expiry_days', sa.Integer(), nullable=False),
        sa.Column('option_type', sa.String(length=10), nullable=True),
        sa.Column('implied_vol', sa.Float(), nullable=True),
        sa.Column('delta', sa.Float(), nullable=True),
        sa.Column('gamma', sa.Float(), nullable=True),
        sa.Column('theta', sa.Float(), nullable=True),
        sa.Column('vega', sa.Float(), nullable=True),
        sa.Column('rho', sa.Float(), nullable=True),
        sa.Column('theoretical_price', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_options_snapshots_ticker', 'options_snapshots', ['ticker'])

    # ------------------------------------------------------------------
    # Agent Orchestration
    # ------------------------------------------------------------------
    op.create_table(
        'agent_workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dag_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_workflows_status', 'agent_workflows', ['status'])

    op.create_table(
        'workflow_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('depends_on', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['agent_workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workflow_tasks_workflow_id', 'workflow_tasks', ['workflow_id'])

    # ------------------------------------------------------------------
    # Knowledge Graph
    # ------------------------------------------------------------------
    op.create_table(
        'knowledge_entities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('source_doc_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_entities_name', 'knowledge_entities', ['name'])
    op.create_index('ix_knowledge_entities_entity_type', 'knowledge_entities', ['entity_type'])

    op.create_table(
        'knowledge_edges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=100), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['knowledge_entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['knowledge_entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_edges_source_id', 'knowledge_edges', ['source_id'])
    op.create_index('ix_knowledge_edges_target_id', 'knowledge_edges', ['target_id'])
    op.create_index('ix_knowledge_edges_relationship_type', 'knowledge_edges', ['relationship_type'])

    # ------------------------------------------------------------------
    # Economic Calendar
    # ------------------------------------------------------------------
    op.create_table(
        'economic_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('country', sa.String(length=10), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('importance', sa.String(length=20), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('actual', sa.Float(), nullable=True),
        sa.Column('forecast', sa.Float(), nullable=True),
        sa.Column('previous', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('impact_score', sa.Float(), nullable=True),
        sa.Column('affected_assets', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_economic_events_name', 'economic_events', ['name'])
    op.create_index('ix_economic_events_country', 'economic_events', ['country'])
    op.create_index('ix_economic_events_importance', 'economic_events', ['importance'])
    op.create_index('ix_economic_events_category', 'economic_events', ['category'])
    op.create_index('ix_economic_events_release_date', 'economic_events', ['release_date'])

    # ------------------------------------------------------------------
    # Auth & Enterprise (users, teams, audit_logs)
    # ------------------------------------------------------------------
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])

    op.create_table(
        'teams',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'team_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('team_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('ix_team_members_user_id', 'team_members', ['user_id'])

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])


def downgrade() -> None:
    """Drop all M7 tables."""
    op.drop_table('audit_logs')
    op.drop_table('team_members')
    op.drop_table('teams')
    op.drop_table('users')
    op.drop_table('economic_events')
    op.drop_table('knowledge_edges')
    op.drop_table('knowledge_entities')
    op.drop_table('workflow_tasks')
    op.drop_table('agent_workflows')
    op.drop_table('options_snapshots')
