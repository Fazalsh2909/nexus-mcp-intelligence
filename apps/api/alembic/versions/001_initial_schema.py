"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-13
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("integration_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), default="disconnected"),
        sa.Column("encrypted_credentials", sa.Text, nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("last_synced_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chat_session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tool_calls_json", sa.JSON, nullable=True),
        sa.Column("sources_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "tool_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("messages.id"),
            nullable=False,
        ),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("arguments_json", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("result_json", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "tool_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tool_call_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tool_calls.id"),
            nullable=False,
        ),
        sa.Column("data_json", sa.JSON, nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_title", sa.String(500), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("details_json", sa.JSON, nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "usage_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer, default=0),
        sa.Column("output_tokens", sa.Integer, default=0),
        sa.Column("estimated_cost", sa.Float, default=0.0),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), default="running"),
        sa.Column("total_scenarios", sa.Integer, default=0),
        sa.Column("completed_scenarios", sa.Integer, default=0),
        sa.Column("tool_selection_accuracy", sa.Float, nullable=True),
        sa.Column("answer_correctness", sa.Float, nullable=True),
        sa.Column("citation_accuracy", sa.Float, nullable=True),
        sa.Column("avg_latency_ms", sa.Float, nullable=True),
        sa.Column("avg_cost", sa.Float, nullable=True),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
            nullable=False,
        ),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("expected_tools", sa.JSON, nullable=True),
        sa.Column("actual_tools", sa.JSON, nullable=True),
        sa.Column("expected_answer_contains", sa.JSON, nullable=True),
        sa.Column("actual_answer", sa.Text, nullable=True),
        sa.Column("tool_selection_correct", sa.Boolean, nullable=True),
        sa.Column("answer_correct", sa.Boolean, nullable=True),
        sa.Column("citation_present", sa.Boolean, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("cost", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("usage_events")
    op.drop_table("audit_logs")
    op.drop_table("tool_results")
    op.drop_table("tool_calls")
    op.drop_table("messages")
    op.drop_table("chat_sessions")
    op.drop_table("connections")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("organizations")
