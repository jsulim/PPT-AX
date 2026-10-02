from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.schemas.forms import HwpxAnalyzeResponse, HwpxFillResponse, HwpxMappingRead
from app.settings import Settings, get_settings
from core.hwpx.fill import build_cell_fills, fill_hwpx_cells
from core.hwpx.mapping import infer_label_mappings
from core.hwpx.read import form_text, read_hwpx

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

        output_filename = f"{uuid.uuid4()}.hwpx"
        output_path = settings.outputs_dir / "hwpx" / output_filename
        report = fill_hwpx_cells(stored_path, output_path, fills)
        return HwpxFillResponse(
            output_filename=output_filename,
            download_url=f"/forms/hwpx/outputs/{output_filename}",
            filled=report.filled,
            missing=missing,
            skipped=report.skipped,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="values_json 형식이 올바르지 않습니다.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
