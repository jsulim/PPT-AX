from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.templates import ProjectRead


class WorkProveBid(BaseModel):
    no: str | None = None
    ord: str | None = None
    name: str = Field(min_length=1)
    notice_org: str | None = Field(default=None, alias="noticeOrg")
    demand_org: str | None = Field(default=None, alias="demandOrg")
    method: str | None = None
    bid_method: str | None = Field(default=None, alias="bidMethod")
    notice_dt: str | None = Field(default=None, alias="noticeDt")
    close_dt: str | None = Field(default=None, alias="closeDt")
    open_dt: str | None = Field(default=None, alias="openDt")
    budget: int | float | None = None
    estimate: int | float | None = None
    keywords: str | None = None
    url: str | None = None
    attachments: list[dict[str, object]] = Field(default_factory=list)


class WorkProveNotice(BaseModel):
    raw_text: str = Field(default="", alias="rawText")
    body_text: str = Field(default="", alias="bodyText")
    requirements: list[dict[str, object]] = Field(default_factory=list)
    scoring_items: list[dict[str, object]] = Field(default_factory=list, alias="scoringItems")
    forms: list[dict[str, object]] = Field(default_factory=list)
    qualifications: list[dict[str, object]] = Field(default_factory=list)


class WorkProveImportRequest(BaseModel):
    bid: WorkProveBid
    notice: WorkProveNotice = Field(default_factory=WorkProveNotice)
    company: dict[str, object] = Field(default_factory=dict)
    personnel: list[dict[str, object]] = Field(default_factory=list)
    track_records: list[dict[str, object]] = Field(default_factory=list, alias="trackRecords")
    selected_personnel: list[dict[str, object]] = Field(
        default_factory=list,
        alias="selectedPersonnel",
    )
    selected_track_records: list[dict[str, object]] = Field(
        default_factory=list,
        alias="selectedTrackRecords",
    )
    outline_items: list[dict[str, object]] = Field(default_factory=list, alias="outlineItems")
    user_email: str | None = Field(default=None, alias="userEmail")


class WorkProveImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project: ProjectRead
    notice_context_id: UUID
    bid_context_id: UUID
    outline_id: UUID


class CompanyDataSyncRequest(BaseModel):
    source: str = Field(default="work_prove", max_length=80)
    company: dict[str, object] = Field(default_factory=dict)
    personnel: list[dict[str, object]] = Field(default_factory=list)
    personnel_careers: list[dict[str, object]] = Field(
        default_factory=list,
        alias="personnelCareers",
    )
    track_records: list[dict[str, object]] = Field(default_factory=list, alias="trackRecords")
    user_email: str | None = Field(default=None, alias="userEmail")


class CompanyDataSyncResponse(BaseModel):
    company_profile: int
    personnel: int
    personnel_careers: int
    track_records: int


class CompanyDataSnapshot(BaseModel):
    company: dict[str, object] = Field(default_factory=dict)
    personnel: list[dict[str, object]] = Field(default_factory=list)
    personnel_careers: list[dict[str, object]] = Field(default_factory=list)
    track_records: list[dict[str, object]] = Field(default_factory=list)
