"""OAuth state, pending write actions, and tool-call argument hashes

Revision ID: 002
Revises: 001
Create Date: 2026-08-14
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("state_hash", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "pending_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("arguments_json", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime, nullable=True),
    )

    op.add_column(
        "tool_calls", sa.Column("arguments_hash", sa.String(64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("tool_calls", "arguments_hash")
    op.drop_table("pending_actions")
    op.drop_table("oauth_states")
