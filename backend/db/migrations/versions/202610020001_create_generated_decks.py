"""create generated decks

Revision ID: 202610020001
Revises: 202610010003
Create Date: 2026-10-02 08:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202610020001"
down_revision: str | None = "202610010003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outline_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(["outline_id"], ["outlines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_decks_outline_id", "generated_decks", ["outline_id"])
    op.create_index("ix_generated_decks_project_id", "generated_decks", ["project_id"])
    op.create_index("ix_generated_decks_status", "generated_decks", ["status"])
    op.create_index("ix_generated_decks_template_id", "generated_decks", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_generated_decks_template_id", table_name="generated_decks")
    op.drop_index("ix_generated_decks_status", table_name="generated_decks")
    op.drop_index("ix_generated_decks_project_id", table_name="generated_decks")
    op.drop_index("ix_generated_decks_outline_id", table_name="generated_decks")
    op.drop_table("generated_decks")
