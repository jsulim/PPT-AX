from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.templates import (
    ProjectCreate,
    ProjectRead,
    TemplateDetail,
    TemplateRead,
    TemplateSlotRead,
    TemplateSlotUpdate,
)
from app.services.templates import create_template_record, store_uploaded_pptx
from app.settings import Settings, get_settings
from db.models import Project, Template, TemplateTextSlot
from worker.tasks.templates import analyze_template_task

router = APIRouter(tags=["templates"])


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Annotated[Session, Depends(get_db)]) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db: Annotated[Session, Depends(get_db)]) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())


@router.post("/templates", response_model=TemplateRead, status_code=201)
def upload_template(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
    project_id: uuid.UUID | None = None,
) -> Template:
    try:
        stored_path, digest = store_uploaded_pptx(file, settings)
        template = create_template_record(
            db,
            filename=file.filename or "template.pptx",
            stored_path=stored_path,
            sha256=digest,
            project_id=project_id,
        )
        db.commit()
        db.refresh(template)
        analyze_template_task.delay(str(template.id))
        return template
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/templates", response_model=list[TemplateRead])
def list_templates(db: Annotated[Session, Depends(get_db)]) -> list[Template]:
    return list(db.scalars(select(Template).order_by(Template.created_at.desc())).all())


@router.get("/templates/{template_id}", response_model=TemplateDetail)
def get_template(template_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> TemplateDetail:
    template = db.get(Template, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    slots = list(
        db.scalars(
            select(TemplateTextSlot)
            .where(TemplateTextSlot.template_id == template_id)
            .order_by(TemplateTextSlot.slide_index, TemplateTextSlot.shape_id)
        ).all()
    )
    data = TemplateRead.model_validate(template).model_dump()
    return TemplateDetail(**data, slots=[TemplateSlotRead.model_validate(slot) for slot in slots])


@router.get("/templates/{template_id}/slots", response_model=list[TemplateSlotRead])
def list_template_slots(
    template_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[TemplateTextSlot]:
    if db.get(Template, template_id) is None:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    return list(
        db.scalars(
            select(TemplateTextSlot)
            .where(TemplateTextSlot.template_id == template_id)
            .order_by(TemplateTextSlot.slide_index, TemplateTextSlot.shape_id)
        ).all()
    )


@router.get("/templates/{template_id}/slides/{slide_index}/{image_kind}")
def get_template_slide_image(
    template_id: uuid.UUID,
    slide_index: int,
    image_kind: str,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    if image_kind not in {"thumb", "preview"}:
        raise HTTPException(status_code=400, detail="thumb 또는 preview만 요청할 수 있습니다.")
    if db.get(Template, template_id) is None:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    image_path = (
        settings.thumbs_dir / "templates" / str(template_id) / f"{image_kind}-{slide_index}.png"
    )
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="미리보기 이미지를 찾을 수 없습니다.")
    return FileResponse(image_path)


@router.patch("/template-slots/{slot_id}", response_model=TemplateSlotRead)
def update_template_slot(
    slot_id: uuid.UUID,
    payload: TemplateSlotUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TemplateTextSlot:
    slot = db.get(TemplateTextSlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="슬롯을 찾을 수 없습니다.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(slot, key, value)
    db.commit()
    db.refresh(slot)
    return slot
