from __future__ import annotations

from pydantic import BaseModel


class HwpxMappingRead(BaseModel):
    field_key: str
    cell_ref: str
    label: str
    confidence: float


class HwpxAnalyzeResponse(BaseModel):
    mappings: list[HwpxMappingRead]
    form_text: str


class HwpxFillResponse(BaseModel):
    output_filename: str
    download_url: str
    filled: list[str]
    missing: list[dict[str, str]]
    skipped: list[dict[str, str]]
