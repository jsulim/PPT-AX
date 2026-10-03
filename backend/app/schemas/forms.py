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
    job_id: str
    output_filename: str
    download_url: str
    filled: list[str]
    missing: list[dict[str, str]]
    skipped: list[dict[str, str]]


class HwpxFormJobSummary(BaseModel):
    job_id: str
    created_at: str
    source_filename: str
    original_filename: str
    output_filename: str
    download_url: str
    filled_count: int
    missing_count: int
    skipped_count: int
    trim_applied: bool


class HwpxFormJobDetail(HwpxFormJobSummary):
    filled: list[str]
    missing: list[dict[str, str]]
    skipped: list[dict[str, str]]
    mappings: list[dict[str, object]]
