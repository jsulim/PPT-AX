from __future__ import annotations

import re
from dataclasses import dataclass

from core.hwpx.read import HwpxCell, HwpxDocument


@dataclass(frozen=True)
class FieldMapping:
    field_key: str
    cell_ref: str
    label: str
    confidence: float


FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "company.name": ("상호", "법인명", "업체명", "회사명"),
    "company.ceo_name": ("대표자", "대표자명", "성명"),
    "company.business_no": ("사업자등록번호", "사업자 번호", "등록번호"),
    "company.corporate_no": ("법인등록번호", "법인 번호"),
    "company.address": ("주소", "소재지", "본사"),
    "company.phone": ("전화", "연락처", "대표전화"),
    "company.email": ("이메일", "전자우편", "e-mail"),
    "bid.name": ("공고명", "사업명", "용역명", "건명"),
    "bid.no": ("공고번호", "입찰공고번호"),
    "bid.noticeOrg": ("발주기관", "공고기관"),
    "bid.demandOrg": ("수요기관", "기관명"),
    "bid.budget": ("예산", "사업예산", "추정금액", "기초금액"),
    "bid.closeDt": ("마감일", "마감일시", "제출기한"),
}


def infer_label_mappings(document: HwpxDocument) -> list[FieldMapping]:
    mappings: list[FieldMapping] = []
    seen: set[tuple[str, str]] = set()

    for table in document.tables:
        for row in table.rows:
            for index, cell in enumerate(row):
                field_key = match_field_key(cell.text)
                if field_key is None:
                    continue
                target = _target_cell(row, index)
                if target is None:
                    continue
                key = (field_key, target.ref)
                if key in seen:
                    continue
                seen.add(key)
                mappings.append(
                    FieldMapping(
                        field_key=field_key,
                        cell_ref=target.ref,
                        label=cell.text,
                        confidence=0.82,
                    )
                )

    return mappings


def match_field_key(label: str) -> str | None:
    normalized = _normalize_label(label)
    if not normalized:
        return None
    for field_key, aliases in FIELD_LABELS.items():
        for alias in aliases:
            if _normalize_label(alias) in normalized:
                return field_key
    return None


def _target_cell(row: list[HwpxCell], label_index: int) -> HwpxCell | None:
    for candidate in row[label_index + 1 :]:
        text = getattr(candidate, "text", "")
        if not str(text).strip() or re.fullmatch(r"[\[\]().:·\-\s_]+", str(text)):
            return candidate
    if label_index + 1 < len(row):
        return row[label_index + 1]
    return None


def _normalize_label(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", value).lower()
