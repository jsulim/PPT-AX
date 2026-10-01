from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.integrations import WorkProveImportRequest, WorkProveImportResponse
from app.schemas.templates import ProjectRead
from app.services.work_prove import import_work_prove_payload

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/work-prove/import", response_model=WorkProveImportResponse, status_code=201)
def import_work_prove(
    payload: WorkProveImportRequest,
    db: Annotated[Session, Depends(get_db)],
) -> WorkProveImportResponse:
    project, notice_context, bid_context, outline = import_work_prove_payload(db, payload)
    return WorkProveImportResponse(
        project=ProjectRead.model_validate(project),
        notice_context_id=notice_context.id,
        bid_context_id=bid_context.id,
        outline_id=outline.id,
    )
