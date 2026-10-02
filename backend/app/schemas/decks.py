from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeckBuildRequest(BaseModel):
    template_id: UUID


class GeneratedDeckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    template_id: UUID
    outline_id: UUID | None
    title: str
    status: str
    output_path: str
    report: dict[str, object]
    created_at: datetime
    updated_at: datetime
