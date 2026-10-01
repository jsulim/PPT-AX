"""create context tables

Revision ID: 202610010003
Revises: 202610010002
Create Date: 2026-10-01 00:00:03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202610010003"
down_revision: str | None = "202610010002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "notice_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scoring_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notice_contexts_project_id", "notice_contexts", ["project_id"])
    op.create_index(
        "ix_notice_contexts_source_document_id",
        "notice_contexts",
        ["source_document_id"],
    )
    op.create_index("ix_notice_contexts_status", "notice_contexts", ["status"])

    op.create_table(
        "bid_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bid_contexts_project_id", "bid_contexts", ["project_id"])
    op.create_index("ix_bid_contexts_source_document_id", "bid_contexts", ["source_document_id"])
    op.create_index("ix_bid_contexts_status", "bid_contexts", ["status"])

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("event", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_event", "usage_events", ["event"])
    op.create_index("ix_usage_events_user_email", "usage_events", ["user_email"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_user_email", table_name="usage_events")
    op.drop_index("ix_usage_events_event", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index("ix_bid_contexts_status", table_name="bid_contexts")
    op.drop_index("ix_bid_contexts_source_document_id", table_name="bid_contexts")
    op.drop_index("ix_bid_contexts_project_id", table_name="bid_contexts")
    op.drop_table("bid_contexts")
    op.drop_index("ix_notice_contexts_status", table_name="notice_contexts")
    op.drop_index("ix_notice_contexts_source_document_id", table_name="notice_contexts")
    op.drop_index("ix_notice_contexts_project_id", table_name="notice_contexts")
    op.drop_table("notice_contexts")
