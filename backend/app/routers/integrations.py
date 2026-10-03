from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.integrations import (
    CompanyDataSnapshot,
    CompanyDataSyncRequest,
    CompanyDataSyncResponse,
    WorkProveImportRequest,
    WorkProveImportResponse,
)
from app.schemas.templates import ProjectRead
from app.services.company_sync import company_data_snapshot, sync_company_data
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


@router.post("/work-prove/company-sync", response_model=CompanyDataSyncResponse)
def sync_work_prove_company_data(
    payload: CompanyDataSyncRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CompanyDataSyncResponse:
    counts = sync_company_data(db, payload)
    return CompanyDataSyncResponse(**counts.__dict__)


@router.get("/company/snapshot", response_model=CompanyDataSnapshot)
def read_company_data_snapshot(
    db: Annotated[Session, Depends(get_db)],
) -> CompanyDataSnapshot:
    snapshot = company_data_snapshot(db)
    return CompanyDataSnapshot(
        company=cast(dict[str, object], snapshot["company"]),
        personnel=cast(list[dict[str, object]], snapshot["personnel"]),
        personnel_careers=cast(list[dict[str, object]], snapshot["personnel_careers"]),
        track_records=cast(list[dict[str, object]], snapshot["track_records"]),
    )
