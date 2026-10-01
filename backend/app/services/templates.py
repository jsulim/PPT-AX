from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.settings import Settings
from core.pptx.fonts import compare_fonts
from core.pptx.render import render_pptx
from core.pptx.slots import extract_text_slots
from db.models import Document, Template, TemplateTextSlot


def store_uploaded_pptx(file: UploadFile, settings: Settings) -> tuple[Path, str]:
    suffix = Path(file.filename or "template.pptx").suffix.lower()
    if suffix != ".pptx":
        raise ValueError("PPTX 파일만 업로드할 수 있습니다.")

    settings.originals_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = settings.originals_dir / f"upload-{uuid.uuid4()}.pptx"
    with tmp_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    digest = _sha256_file(tmp_path)
    stored_path = settings.originals_dir / f"{digest}.pptx"
    if stored_path.exists():
        tmp_path.unlink()
    else:
        tmp_path.replace(stored_path)
    return stored_path, digest


def create_template_record(
    db: Session,
    *,
    filename: str,
    stored_path: Path,
    sha256: str,
    project_id: uuid.UUID | None = None,
) -> Template:
    document = db.scalar(select(Document).where(Document.sha256 == sha256))
    if document is None:
        document = Document(
            project_id=project_id,
            kind="proposal_pptx",
            filename=filename,
            stored_path=str(stored_path),
            sha256=sha256,
            status="pending",
        )
        db.add(document)
        db.flush()

    template = db.scalar(select(Template).where(Template.document_id == document.id))
    if template is None:
        template = Template(
            project_id=project_id,
            document_id=document.id,
            name=Path(filename).stem,
            status="pending",
        )
        db.add(template)
        db.flush()
    return template


def analyze_template(db: Session, template_id: uuid.UUID, settings: Settings) -> Template:
    template = db.get(Template, template_id)
    if template is None:
        raise ValueError("템플릿을 찾을 수 없습니다.")
    document = db.get(Document, template.document_id)
    if document is None:
        raise ValueError("템플릿 원본 문서를 찾을 수 없습니다.")

    try:
        extracted = extract_text_slots(document.stored_path)
        used_fonts, missing_fonts = compare_fonts(document.stored_path)
        render_dir = settings.thumbs_dir / "templates" / str(template.id)
        rendered = render_pptx(document.stored_path, render_dir)

        db.query(TemplateTextSlot).filter(TemplateTextSlot.template_id == template.id).delete()
        for slot in extracted.slots:
            db.add(
                TemplateTextSlot(
                    template_id=template.id,
                    slide_index=slot.slide_index,
                    shape_id=slot.shape_id,
                    kind=slot.kind,
                    role_key=slot.role_key,
                    slot_name=slot.slot_name,
                    value_type=slot.value_type,
                    field_binding=slot.field_binding,
                    original_text=slot.original_text,
                    char_count=slot.char_count,
                    max_char_count=slot.max_char_count,
                    bounds=slot.bounds,
                    style_ref=slot.style_ref,
                    locked=slot.locked,
                )
            )

        document.status = "ready"
        document.fonts_used = used_fonts
        document.fonts_missing = missing_fonts
        template.status = "analyzed"
        template.slide_count = extracted.slide_count
        template.preview_path = str(rendered[0].thumb_path) if rendered else None
        template.error = None
    except Exception as exc:
        document.status = "failed"
        document.error = str(exc)
        template.status = "failed"
        template.error = str(exc)
    db.commit()
    db.refresh(template)
    return template


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
