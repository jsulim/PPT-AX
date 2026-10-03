from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.schemas.forms import (
    HwpxAnalyzeResponse,
    HwpxFillResponse,
    HwpxFormJobDetail,
    HwpxFormJobSummary,
    HwpxMappingRead,
)
from app.services.form_jobs import (
    HwpxFormJob,
    list_hwpx_form_jobs,
    now_iso,
    read_hwpx_form_job,
    write_hwpx_form_job,
)
from app.settings import Settings, get_settings
from core.hwpx.fill import (
    build_cell_fills,
    build_personnel_profile_fills,
    build_repeating_fills,
    fill_hwpx_cells,
)
from core.hwpx.mapping import infer_label_mappings
from core.hwpx.read import form_text, read_hwpx
from core.hwpx.trim import trim_hwpx_to_form_start

router = APIRouter(prefix="/forms", tags=["forms"])


@router.post("/hwpx/analyze", response_model=HwpxAnalyzeResponse)
def analyze_hwpx_form(
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
) -> HwpxAnalyzeResponse:
    try:
        stored_path = _store_uploaded_hwpx(file, settings)
        document = read_hwpx(stored_path)
        mappings = infer_label_mappings(document)
        return HwpxAnalyzeResponse(
            mappings=[HwpxMappingRead(**mapping.__dict__) for mapping in mappings],
            form_text=form_text(document),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/hwpx/fill", response_model=HwpxFillResponse)
def fill_hwpx_form(
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
    values_json: Annotated[str, Form()],
) -> HwpxFillResponse:
    try:
        values = json.loads(values_json)
        if not isinstance(values, dict):
            raise ValueError("values_json은 JSON 객체여야 합니다.")
        stored_path = _store_uploaded_hwpx(file, settings)
        document = read_hwpx(stored_path)
        mappings = infer_label_mappings(document)
        fills, missing = build_cell_fills(mappings, values)
        table_rows, repeated_tables, repeat_missing = build_repeating_fills(document, values)
        personnel_profiles, profile_missing = build_personnel_profile_fills(document, values)

        job_id = str(uuid.uuid4())
        output_filename = f"{job_id}.hwpx"
        output_path = settings.outputs_dir / "hwpx" / output_filename
        report = fill_hwpx_cells(
            stored_path,
            output_path,
            fills,
            table_rows=table_rows,
            repeated_tables=repeated_tables,
            personnel_profiles=personnel_profiles,
        )
        trim_applied = trim_hwpx_to_form_start(output_path)
        download_url = f"/forms/hwpx/outputs/{output_filename}"
        job = HwpxFormJob(
            job_id=job_id,
            created_at=now_iso(),
            source_filename=file.filename or "form.hwpx",
            original_filename=stored_path.name,
            output_filename=output_filename,
            download_url=download_url,
            filled=report.filled,
            missing=missing + repeat_missing + profile_missing,
            skipped=report.skipped,
            mappings=[mapping.__dict__ for mapping in mappings],
            trim_applied=trim_applied,
        )
        write_hwpx_form_job(settings.jobs_dir, job)
        return HwpxFillResponse(
            job_id=job_id,
            output_filename=output_filename,
            download_url=download_url,
            filled=report.filled,
            missing=missing + repeat_missing + profile_missing,
            skipped=report.skipped,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="values_json 형식이 올바르지 않습니다.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/hwpx/jobs", response_model=list[HwpxFormJobSummary])
def list_filled_hwpx_jobs(
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = 50,
) -> list[HwpxFormJobSummary]:
    safe_limit = min(max(limit, 1), 200)
    return [_job_summary(job) for job in list_hwpx_form_jobs(settings.jobs_dir, safe_limit)]


@router.get("/hwpx/jobs/{job_id}", response_model=HwpxFormJobDetail)
def read_filled_hwpx_job(
    job_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HwpxFormJobDetail:
    job = read_hwpx_form_job(settings.jobs_dir, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="생성 로그를 찾을 수 없습니다.")
    return HwpxFormJobDetail(
        **_job_summary(job).model_dump(),
        filled=job.filled,
        missing=job.missing,
        skipped=job.skipped,
        mappings=job.mappings,
    )


@router.get("/hwpx/outputs/{filename}")
def download_filled_hwpx(
    filename: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    if "/" in filename or "\\" in filename or not filename.endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="잘못된 파일 이름입니다.")
    output_path = settings.outputs_dir / "hwpx" / filename
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="출력 HWPX 파일을 찾을 수 없습니다.")
    return FileResponse(
        output_path,
        media_type="application/x-hwpml",
        filename=filename,
    )


def _store_uploaded_hwpx(file: UploadFile, settings: Settings) -> Path:
    suffix = Path(file.filename or "form.hwpx").suffix.lower()
    if suffix != ".hwpx":
        raise ValueError("HWPX 파일만 업로드할 수 있습니다.")

    settings.originals_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = settings.originals_dir / f"upload-{uuid.uuid4()}.hwpx"
    with tmp_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    digest = _sha256_file(tmp_path)
    stored_path = settings.originals_dir / f"{digest}.hwpx"
    if stored_path.exists():
        tmp_path.unlink()
    else:
        tmp_path.replace(stored_path)
    return stored_path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _job_summary(job: HwpxFormJob) -> HwpxFormJobSummary:
    return HwpxFormJobSummary(
        job_id=job.job_id,
        created_at=job.created_at,
        source_filename=job.source_filename,
        original_filename=job.original_filename,
        output_filename=job.output_filename,
        download_url=job.download_url,
        filled_count=job.filled_count,
        missing_count=job.missing_count,
        skipped_count=job.skipped_count,
        trim_applied=job.trim_applied,
    )
