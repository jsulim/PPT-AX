"""create company data tables

Revision ID: 202610030001
Revises: 202610020001
Create Date: 2026-10-03 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202610030001"
down_revision: str | None = "202610020001"
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
        "company_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_row_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("business_no", sa.String(length=80), nullable=True),
        sa.Column("corporate_no", sa.String(length=80), nullable=True),
        sa.Column("ceo_name", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index("ix_company_profile_name", "company_profile", ["name"])
    op.create_index("ix_company_profile_source", "company_profile", ["source"])
    op.create_index("ix_company_profile_source_key", "company_profile", ["source_key"])

    op.create_table(
        "personnel",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_row_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("position", sa.String(length=120), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index("ix_personnel_active", "personnel", ["active"])
    op.create_index("ix_personnel_name", "personnel", ["name"])
    op.create_index("ix_personnel_source", "personnel", ["source"])
    op.create_index("ix_personnel_source_key", "personnel", ["source_key"])

    op.create_table(
        "personnel_careers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("personnel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_row_id", sa.String(length=255), nullable=True),
        sa.Column("personnel_source_key", sa.String(length=255), nullable=True),
        sa.Column("personnel_name", sa.String(length=120), nullable=True),
        sa.Column("project_name", sa.String(length=500), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("period", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["personnel_id"], ["personnel.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index("ix_personnel_careers_personnel_id", "personnel_careers", ["personnel_id"])
    op.create_index(
        "ix_personnel_careers_personnel_name",
        "personnel_careers",
        ["personnel_name"],
    )
    op.create_index(
        "ix_personnel_careers_personnel_source_key",
        "personnel_careers",
        ["personnel_source_key"],
    )
    op.create_index("ix_personnel_careers_project_name", "personnel_careers", ["project_name"])
    op.create_index("ix_personnel_careers_source", "personnel_careers", ["source"])
    op.create_index("ix_personnel_careers_source_key", "personnel_careers", ["source_key"])

    op.create_table(
        "track_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_row_id", sa.String(length=255), nullable=True),
        sa.Column("project_name", sa.String(length=500), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("period", sa.String(length=255), nullable=True),
        sa.Column("amount_krw", sa.BigInteger(), nullable=True),
        sa.Column("domain", sa.String(length=120), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index("ix_track_records_client_name", "track_records", ["client_name"])
    op.create_index("ix_track_records_domain", "track_records", ["domain"])
    op.create_index("ix_track_records_project_name", "track_records", ["project_name"])
    op.create_index("ix_track_records_source", "track_records", ["source"])
    op.create_index("ix_track_records_source_key", "track_records", ["source_key"])


def downgrade() -> None:
    op.drop_index("ix_track_records_source_key", table_name="track_records")
    op.drop_index("ix_track_records_source", table_name="track_records")
    op.drop_index("ix_track_records_project_name", table_name="track_records")
    op.drop_index("ix_track_records_domain", table_name="track_records")
    op.drop_index("ix_track_records_client_name", table_name="track_records")
    op.drop_table("track_records")
    op.drop_index("ix_personnel_careers_source_key", table_name="personnel_careers")
    op.drop_index("ix_personnel_careers_source", table_name="personnel_careers")
    op.drop_index("ix_personnel_careers_project_name", table_name="personnel_careers")
    op.drop_index("ix_personnel_careers_personnel_source_key", table_name="personnel_careers")
    op.drop_index("ix_personnel_careers_personnel_name", table_name="personnel_careers")
    op.drop_index("ix_personnel_careers_personnel_id", table_name="personnel_careers")
    op.drop_table("personnel_careers")
    op.drop_index("ix_personnel_source_key", table_name="personnel")
    op.drop_index("ix_personnel_source", table_name="personnel")
    op.drop_index("ix_personnel_name", table_name="personnel")
    op.drop_index("ix_personnel_active", table_name="personnel")
    op.drop_table("personnel")
    op.drop_index("ix_company_profile_source_key", table_name="company_profile")
    op.drop_index("ix_company_profile_source", table_name="company_profile")
    op.drop_index("ix_company_profile_name", table_name="company_profile")
    op.drop_table("company_profile")
