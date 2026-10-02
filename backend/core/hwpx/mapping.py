from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from core.hwpx.read import HwpxCell, HwpxDocument


@dataclass(frozen=True)
class FieldMapping:
    field_key: str
    cell_ref: str
    label: str
    confidence: float


FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "company.name": ("상호", "법인명", "업체명", "회사명"),
    "company.corporate_no": ("법인등록번호", "법인 번호"),
    "company.business_no": ("사업자등록번호", "사업자 번호", "사업자번호"),
    "company.address": ("주소", "소재지", "본사"),
    "company.phone": ("전화", "연락처", "대표전화"),
    "company.email": ("이메일", "전자우편", "e-mail"),
    "company.ceo_name": ("대표자", "대표자명"),
    "bid.name": ("공고명", "사업명", "용역명", "건명", "프로젝트명"),
    "bid.no": ("공고번호", "입찰공고번호"),
    "bid.noticeOrg": ("발주기관", "공고기관"),
    "bid.demandOrg": ("수요기관", "기관명"),
    "bid.budget": ("예산", "사업예산", "추정금액", "기초금액"),
    "bid.closeDt": ("마감일", "마감일시", "제출기한"),
}


def infer_label_mappings(document: HwpxDocument) -> list[FieldMapping]:
    mappings: list[FieldMapping] = []
    seen: set[tuple[str, str]] = set()
    seen_cell_refs: set[str] = set()

    for table in document.tables:
        for row in table.rows:
            for index, cell in enumerate(row):
                field_key = match_field_key(cell.text)
                if field_key is None:
                    continue
                target = _target_cell(row, index)
                if target is None:
                    continue
                if target.ref in seen_cell_refs:
                    continue
                key = (field_key, target.ref)
                if key in seen:
                    continue
                seen.add(key)
                seen_cell_refs.add(target.ref)
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
    if not normalized or len(normalized) > 24:
        return None
    for field_key, aliases in FIELD_LABELS.items():
        if not _passes_field_guard(field_key, normalized):
            continue
        for alias in aliases:
            if _is_label_match(normalized, _normalize_label(alias)):
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


def _is_label_match(label: str, alias: str) -> bool:
    if not label or not alias:
        return False
    if alias in label:
        return True
    if len(label) >= 3 and label in alias:
        return True
    if len(label) < 3 or len(alias) < 3:
        return False
    return SequenceMatcher(None, label, alias).ratio() >= 0.72


def _passes_field_guard(field_key: str, label: str) -> bool:
    if field_key == "company.ceo_name" and any(
        token in label for token in ("전화", "연락처", "이메일", "email", "메일")
    ):
        return False
    if field_key == "company.business_no" and "주민" in label:
        return False
    if field_key == "bid.no" and "번호" not in label:
        return False
    if field_key == "bid.budget" and any(
        token in label for token in ("계획", "방안", "내용", "적절", "유무", "타당")
    ):
        return False
    return True
