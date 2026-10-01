import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agency: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="preparing", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    fonts_used: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    fonts_missing: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)


class Template(TimestampMixin, Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    slide_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preview_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class TemplateTextSlot(TimestampMixin, Base):
    __tablename__ = "template_text_slots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slide_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    shape_id: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    role_key: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown", index=True)
    slot_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    value_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unknown",
        index=True,
    )
    field_binding: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bounds: Mapped[dict[str, int | None]] = mapped_column(JSONB, nullable=False)
    style_ref: Mapped[dict[str, str | int | None]] = mapped_column(JSONB, nullable=False)
    locked: Mapped[bool] = mapped_column(default=False, nullable=False)


class Outline(TimestampMixin, Base):
    __tablename__ = "outlines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    items: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
