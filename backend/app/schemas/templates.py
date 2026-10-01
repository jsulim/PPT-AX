from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    agency: str | None = Field(default=None, max_length=255)
    domain: str | None = Field(default=None, max_length=100)
    year: int | None = None
    notes: str | None = None


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stage: str
    created_at: datetime
    updated_at: datetime


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None
    document_id: UUID
    name: str
    status: str
    slide_count: int
    preview_path: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class TemplateSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    slide_index: int
    shape_id: str
    kind: str
    role_key: str
    slot_name: str | None
    value_type: str
    field_binding: str | None
    original_text: str
    char_count: int
    max_char_count: int
    bounds: dict[str, int | None]
    style_ref: dict[str, str | int | None]
    locked: bool


class TemplateSlotUpdate(BaseModel):
    role_key: str | None = Field(default=None, max_length=80)
    slot_name: str | None = Field(default=None, max_length=120)
    value_type: str | None = Field(default=None, max_length=30)
    field_binding: str | None = Field(default=None, max_length=255)
    locked: bool | None = None


class TemplateDetail(TemplateRead):
    slots: list[TemplateSlotRead]
