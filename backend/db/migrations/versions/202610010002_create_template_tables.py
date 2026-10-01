"""create template tables

Revision ID: 202610010002
Revises: 202610010001
Create Date: 2026-10-01 00:00:02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202610010002"
down_revision: str | None = "202610010001"
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
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("agency", sa.String(length=255), nullable=True),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_agency", "projects", ["agency"])
    op.create_index("ix_projects_domain", "projects", ["domain"])
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_stage", "projects", ["stage"])
    op.create_index("ix_projects_year", "projects", ["year"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("fonts_used", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fonts_missing", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256"),
    )
    op.create_index("ix_documents_kind", "documents", ["kind"])
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("slide_count", sa.Integer(), nullable=False),
        sa.Column("preview_path", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_templates_document_id", "templates", ["document_id"])
    op.create_index("ix_templates_name", "templates", ["name"])
    op.create_index("ix_templates_project_id", "templates", ["project_id"])
    op.create_index("ix_templates_status", "templates", ["status"])

    op.create_table(
        "template_text_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slide_index", sa.Integer(), nullable=False),
        sa.Column("shape_id", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("role_key", sa.String(length=80), nullable=False),
        sa.Column("slot_name", sa.String(length=120), nullable=True),
        sa.Column("value_type", sa.String(length=30), nullable=False),
        sa.Column("field_binding", sa.String(length=255), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("max_char_count", sa.Integer(), nullable=False),
        sa.Column("bounds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("style_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_template_text_slots_role_key", "template_text_slots", ["role_key"])
    op.create_index("ix_template_text_slots_slide_index", "template_text_slots", ["slide_index"])
    op.create_index("ix_template_text_slots_template_id", "template_text_slots", ["template_id"])
    op.create_index("ix_template_text_slots_value_type", "template_text_slots", ["value_type"])

    op.create_table(
        "outlines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outlines_project_id", "outlines", ["project_id"])
    op.create_index("ix_outlines_status", "outlines", ["status"])
    op.create_index("ix_outlines_template_id", "outlines", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_outlines_template_id", table_name="outlines")
    op.drop_index("ix_outlines_status", table_name="outlines")
    op.drop_index("ix_outlines_project_id", table_name="outlines")
    op.drop_table("outlines")
    op.drop_index("ix_template_text_slots_value_type", table_name="template_text_slots")
    op.drop_index("ix_template_text_slots_template_id", table_name="template_text_slots")
    op.drop_index("ix_template_text_slots_slide_index", table_name="template_text_slots")
    op.drop_index("ix_template_text_slots_role_key", table_name="template_text_slots")
    op.drop_table("template_text_slots")
    op.drop_index("ix_templates_status", table_name="templates")
    op.drop_index("ix_templates_project_id", table_name="templates")
    op.drop_index("ix_templates_name", table_name="templates")
    op.drop_index("ix_templates_document_id", table_name="templates")
    op.drop_table("templates")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_index("ix_documents_kind", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_projects_year", table_name="projects")
    op.drop_index("ix_projects_stage", table_name="projects")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_index("ix_projects_domain", table_name="projects")
    op.drop_index("ix_projects_agency", table_name="projects")
    op.drop_table("projects")
