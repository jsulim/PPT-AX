from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.integrations import CompanyDataSyncRequest
from db.models import (
    CompanyProfile,
    Personnel,
    PersonnelCareer,
    TrackRecord,
    UsageEvent,
)


@dataclass(frozen=True)
class CompanySyncCounts:
    company_profile: int = 0
    personnel: int = 0
    personnel_careers: int = 0
    track_records: int = 0


COMPANY_FIELD_ALIASES = {
    "name": ("name", "companyName", "상호", "법인명", "회사명", "업체명"),
    "business_no": ("businessNo", "business_no", "사업자등록번호", "사업자번호"),
    "corporate_no": ("corporateNo", "corporate_no", "법인등록번호"),
    "ceo_name": ("ceoName", "ceo_name", "대표자", "대표자명"),
    "phone": ("phone", "tel", "telephone", "연락처", "전화", "대표전화"),
    "email": ("email", "이메일", "전자우편"),
    "address": ("address", "주소", "소재지"),
}

PERSONNEL_FIELD_ALIASES = {
    "name": ("name", "personName", "성명", "이름"),
    "department": ("department", "dept", "소속", "부서"),
    "position": ("position", "rank", "직위", "직급"),
    "role": ("role", "task", "담당업무", "참여업무", "본용역참여업무"),
    "phone": ("phone", "tel", "연락처", "전화"),
    "email": ("email", "이메일", "전자우편"),
}

CAREER_FIELD_ALIASES = {
    "personnel_source_key": (
        "personnelSourceKey",
        "personnel_source_key",
        "personId",
        "personnelId",
    ),
    "personnel_name": ("personnelName", "personName", "성명", "이름"),
    "project_name": ("projectName", "taskName", "businessName", "사업명", "용역명", "과업명"),
    "client_name": ("clientName", "agency", "organization", "발주처", "발주기관", "근무처"),
    "period": ("period", "contractPeriod", "participationPeriod", "참여기간", "수행기간", "기간"),
    "role": ("role", "task", "담당업무", "역할"),
}

TRACK_RECORD_FIELD_ALIASES = {
    "project_name": ("projectName", "taskName", "businessName", "사업명", "용역명", "과업명"),
    "client_name": ("clientName", "agency", "organization", "발주처", "발주기관", "수요기관"),
    "period": ("period", "contractPeriod", "수행기간", "계약기간", "기간"),
    "amount_krw": ("amountKrw", "amount", "contractAmount", "계약금액", "금액"),
    "domain": ("domain", "category", "field", "분야", "구분"),
}


def sync_company_data(
    db: Session,
    payload: CompanyDataSyncRequest,
    *,
    commit: bool = True,
) -> CompanySyncCounts:
    source = payload.source or "work_prove"
    company_count = _sync_company_profile(db, source, payload.company)
    personnel_by_source_key = _sync_personnel(db, source, payload.personnel)
    db.flush()
    career_rows = _merged_personnel_career_rows(
        source,
        payload.personnel,
        payload.personnel_careers,
    )
    career_count = _sync_personnel_careers(db, source, career_rows, personnel_by_source_key)
    track_record_count = _sync_track_records(db, source, payload.track_records)

    db.add(
        UsageEvent(
            user_email=payload.user_email,
            event="sync_company_data",
            payload={
                "source": source,
                "company_profile": company_count,
                "personnel": len(personnel_by_source_key),
                "personnel_careers": career_count,
                "track_records": track_record_count,
            },
        )
    )

    if commit:
        db.commit()

    return CompanySyncCounts(
        company_profile=company_count,
        personnel=len(personnel_by_source_key),
        personnel_careers=career_count,
        track_records=track_record_count,
    )


def company_data_snapshot(db: Session) -> dict[str, object]:
    company = db.scalar(select(CompanyProfile).order_by(CompanyProfile.updated_at.desc()))
    personnel = db.scalars(
        select(Personnel).where(Personnel.active.is_(True)).order_by(Personnel.name)
    ).all()
    careers = db.scalars(select(PersonnelCareer).order_by(PersonnelCareer.personnel_name)).all()
    track_records = db.scalars(select(TrackRecord).order_by(TrackRecord.project_name)).all()
    return {
        "company": _model_payload(company) if company else {},
        "personnel": [_model_payload(row) for row in personnel],
        "personnel_careers": [_model_payload(row) for row in careers],
        "track_records": [_model_payload(row) for row in track_records],
    }


def build_company_sync_request_from_work_prove(
    *,
    company: dict[str, object],
    personnel: list[dict[str, object]],
    track_records: list[dict[str, object]],
    selected_personnel: list[dict[str, object]],
    selected_track_records: list[dict[str, object]],
    user_email: str | None,
) -> CompanyDataSyncRequest:
    personnel_rows = personnel or selected_personnel
    track_record_rows = track_records or selected_track_records
    return CompanyDataSyncRequest(
        source="work_prove",
        company=company,
        personnel=personnel_rows,
        trackRecords=track_record_rows,
        userEmail=user_email,
    )


def _sync_company_profile(db: Session, source: str, row: dict[str, object]) -> int:
    if not row:
        return 0
    source_key = _source_key(source, "company", row, 0, fallback="default")
    normalized = _normalize_row(row, COMPANY_FIELD_ALIASES)
    profile = db.scalar(select(CompanyProfile).where(CompanyProfile.source_key == source_key))
    if profile is None:
        profile = CompanyProfile(source=source, source_key=source_key)
        db.add(profile)
    profile.source_row_id = _row_id(row)
    profile.name = normalized.get("name")
    profile.business_no = normalized.get("business_no")
    profile.corporate_no = normalized.get("corporate_no")
    profile.ceo_name = normalized.get("ceo_name")
    profile.phone = normalized.get("phone")
    profile.email = normalized.get("email")
    profile.address = normalized.get("address")
    profile.data = row
    return 1


def _sync_personnel(
    db: Session,
    source: str,
    rows: list[dict[str, object]],
) -> dict[str, Personnel]:
    synced: dict[str, Personnel] = {}
    for index, row in enumerate(rows):
        normalized = _normalize_row(row, PERSONNEL_FIELD_ALIASES)
        name = normalized.get("name")
        if not name:
            continue
        source_key = _source_key(source, "personnel", row, index, fallback=name)
        personnel = db.scalar(select(Personnel).where(Personnel.source_key == source_key))
        if personnel is None:
            personnel = Personnel(source=source, source_key=source_key, name=name)
            db.add(personnel)
        personnel.source_row_id = _row_id(row)
        personnel.name = name
        personnel.department = normalized.get("department")
        personnel.position = normalized.get("position")
        personnel.role = normalized.get("role")
        personnel.phone = normalized.get("phone")
        personnel.email = normalized.get("email")
        personnel.data = row
        personnel.active = _bool_value(row.get("active"), default=True)
        synced[source_key] = personnel
    return synced


def _sync_personnel_careers(
    db: Session,
    source: str,
    rows: list[dict[str, object]],
    personnel_by_source_key: dict[str, Personnel],
) -> int:
    count = 0
    for index, row in enumerate(rows):
        normalized = _normalize_row(row, CAREER_FIELD_ALIASES)
        project_name = normalized.get("project_name")
        if not project_name:
            continue
        personnel_source_key = normalized.get("personnel_source_key")
        personnel_name = normalized.get("personnel_name")
        fallback = f"{personnel_name or 'unknown'}:{project_name}:{index}"
        source_key = _source_key(source, "personnel_career", row, index, fallback=fallback)
        career = db.scalar(select(PersonnelCareer).where(PersonnelCareer.source_key == source_key))
        if career is None:
            career = PersonnelCareer(source=source, source_key=source_key)
            db.add(career)
        career.source_row_id = _row_id(row)
        career.personnel_source_key = personnel_source_key
        career.personnel_id = _linked_personnel_id(personnel_by_source_key, personnel_source_key)
        career.personnel_name = personnel_name
        career.project_name = project_name
        career.client_name = normalized.get("client_name")
        career.period = normalized.get("period")
        career.role = normalized.get("role")
        career.data = row
        count += 1
    return count


def _sync_track_records(db: Session, source: str, rows: list[dict[str, object]]) -> int:
    count = 0
    for index, row in enumerate(rows):
        normalized = _normalize_row(row, TRACK_RECORD_FIELD_ALIASES)
        project_name = normalized.get("project_name")
        if not project_name:
            continue
        source_key = _source_key(source, "track_record", row, index, fallback=project_name)
        track_record = db.scalar(select(TrackRecord).where(TrackRecord.source_key == source_key))
        if track_record is None:
            track_record = TrackRecord(
                source=source,
                source_key=source_key,
                project_name=project_name,
            )
            db.add(track_record)
        track_record.source_row_id = _row_id(row)
        track_record.project_name = project_name
        track_record.client_name = normalized.get("client_name")
        track_record.period = normalized.get("period")
        track_record.amount_krw = _int_value(normalized.get("amount_krw"))
        track_record.domain = normalized.get("domain")
        track_record.data = row
        count += 1
    return count


def _merged_personnel_career_rows(
    source: str,
    personnel_rows: list[dict[str, object]],
    explicit_career_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = list(explicit_career_rows)
    for personnel_index, personnel_row in enumerate(personnel_rows):
        personnel_source_key = _source_key(
            source,
            "personnel",
            personnel_row,
            personnel_index,
            fallback=(
                _string_value(_first_value(personnel_row, PERSONNEL_FIELD_ALIASES["name"]))
                or ""
            ),
        )
        personnel_name = _string_value(
            _first_value(personnel_row, PERSONNEL_FIELD_ALIASES["name"])
        )
        careers = personnel_row.get("careers") or personnel_row.get("careerRows") or []
        if not isinstance(careers, list):
            continue
        for career in careers:
            if not isinstance(career, dict):
                continue
            row = dict(career)
            row.setdefault("personnelSourceKey", personnel_source_key)
            row.setdefault("personnelName", personnel_name)
            rows.append(row)
    return rows


def _normalize_row(row: dict[str, object], aliases: dict[str, tuple[str, ...]]) -> dict[str, str]:
    return {
        field: value
        for field, alias_list in aliases.items()
        if (value := _string_value(_first_value(row, alias_list)))
    }


def _first_value(row: dict[str, object], keys: tuple[str, ...]) -> object | None:
    compact_row = {_compact_key(key): value for key, value in row.items()}
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
        compact_key = _compact_key(key)
        if compact_key in compact_row and compact_row[compact_key] not in (None, ""):
            return compact_row[compact_key]
    return None


def _source_key(
    source: str,
    table: str,
    row: dict[str, object],
    index: int,
    *,
    fallback: str,
) -> str:
    explicit = _first_value(row, ("sourceKey", "source_key", "id", "rowId", "rowNumber", "행번호"))
    if explicit:
        return f"{source}:{table}:{_string_value(explicit)}"
    if fallback:
        return f"{source}:{table}:{fallback}"
    return f"{source}:{table}:row-{index}"


def _row_id(row: dict[str, object]) -> str | None:
    return _string_value(_first_value(row, ("rowId", "rowNumber", "행번호")))


def _linked_personnel_id(
    personnel_by_source_key: dict[str, Personnel],
    personnel_source_key: str | None,
) -> Any:
    if not personnel_source_key:
        return None
    personnel = personnel_by_source_key.get(personnel_source_key)
    return personnel.id if personnel else None


def _model_payload(model: Any) -> dict[str, object]:
    data = dict(model.data or {})
    for key in (
        "name",
        "business_no",
        "corporate_no",
        "ceo_name",
        "phone",
        "email",
        "address",
        "department",
        "position",
        "role",
        "project_name",
        "client_name",
        "period",
        "amount_krw",
        "domain",
        "source_key",
    ):
        if hasattr(model, key) and (value := getattr(model, key)) not in (None, ""):
            data[key] = value
    return data


def _compact_key(value: str) -> str:
    return value.replace(" ", "").replace("_", "").replace("-", "").lower()


def _string_value(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _int_value(value: object | None) -> int | None:
    text = _string_value(value)
    if not text:
        return None
    digits = "".join(char for char in text if char.isdigit() or char == "-")
    if not digits or digits == "-":
        return None
    return int(digits)


def _bool_value(value: object | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return _string_value(value).lower() not in {"false", "0", "n", "no", "inactive", "퇴사"}
