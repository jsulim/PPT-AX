from __future__ import annotations

import re
import zipfile
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import cast
from xml.etree import ElementTree as ET

from core.hwpx.mapping import FieldMapping
from core.hwpx.read import HwpxDocument, HwpxTable

CELL_REF_RE = re.compile(r"^(?P<xml>.+):tbl(?P<table>\d+):r(?P<row>\d+):c(?P<col>\d+)$")


@dataclass(frozen=True)
class CellFill:
    cell_ref: str
    field_key: str
    value: str


@dataclass(frozen=True)
class TableRowFill:
    xml_path: str
    table_index: int
    template_row_index: int
    rows: list[dict[int, tuple[str, str]]]


@dataclass(frozen=True)
class RepeatedTableFill:
    xml_path: str
    table_index: int
    rows: list[dict[str, str]]


@dataclass(frozen=True)
class HwpxFillReport:
    filled: list[str] = field(default_factory=list)
    missing: list[dict[str, str]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


def fill_hwpx_cells(
    input_path: Path,
    output_path: Path,
    fills: list[CellFill],
    table_rows: list[TableRowFill] | None = None,
    repeated_tables: list[RepeatedTableFill] | None = None,
) -> HwpxFillReport:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fills_by_xml: dict[str, list[CellFill]] = {}
    for fill in fills:
        parsed = _parse_cell_ref(fill.cell_ref)
        if parsed is None:
            continue
        fills_by_xml.setdefault(parsed["xml"], []).append(fill)
    table_rows_by_xml: dict[str, list[TableRowFill]] = {}
    for row_fill in table_rows or []:
        table_rows_by_xml.setdefault(row_fill.xml_path, []).append(row_fill)
    repeated_tables_by_xml: dict[str, list[RepeatedTableFill]] = {}
    for repeat_fill in repeated_tables or []:
        repeated_tables_by_xml.setdefault(repeat_fill.xml_path, []).append(repeat_fill)

    filled: list[str] = []
    skipped: list[dict[str, str]] = []

    with zipfile.ZipFile(input_path, "r") as source:
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if (
                    info.filename in fills_by_xml
                    or info.filename in table_rows_by_xml
                    or info.filename in repeated_tables_by_xml
                ):
                    data, xml_filled, xml_skipped = _fill_xml(
                        data,
                        fills_by_xml.get(info.filename, []),
                        table_rows_by_xml.get(info.filename, []),
                        repeated_tables_by_xml.get(info.filename, []),
                    )
                    filled.extend(xml_filled)
                    skipped.extend(xml_skipped)
                target.writestr(info, data)

    return HwpxFillReport(filled=filled, skipped=skipped)


def build_cell_fills(
    mappings: list[FieldMapping],
    values: dict[str, object],
) -> tuple[list[CellFill], list[dict[str, str]]]:
    fills: list[CellFill] = []
    missing: list[dict[str, str]] = []
    for mapping in mappings:
        field_key = mapping.field_key
        cell_ref = mapping.cell_ref
        value = _resolve_value(values, field_key)
        if value in {None, ""}:
            missing.append(
                {
                    "field_key": field_key,
                    "cell_ref": cell_ref,
                    "message": "채울 데이터가 없습니다.",
                }
            )
            fills.append(
                CellFill(
                    cell_ref=cell_ref,
                    field_key=field_key,
                    value=f"[확인 필요: {field_key}]",
                )
            )
            continue
        fills.append(CellFill(cell_ref=cell_ref, field_key=field_key, value=str(value)))
    return fills, missing


def build_repeating_fills(
    document: HwpxDocument,
    values: dict[str, object],
) -> tuple[list[TableRowFill], list[RepeatedTableFill], list[dict[str, str]]]:
    table_rows: list[TableRowFill] = []
    repeated_tables: list[RepeatedTableFill] = []
    missing: list[dict[str, str]] = []
    track_records = _list_value(values, "track_records") or _list_value(
        values, "selectedTrackRecords"
    )
    personnel = _list_value(values, "personnel") or _list_value(values, "selectedPersonnel")

    for table in document.tables:
        table_kind, header_row_index, column_fields = _detect_repeating_table(table)
        is_consent_table = _is_personnel_consent_table(table)
        row_fill: TableRowFill | None
        row_missing: list[dict[str, str]]
        if is_consent_table:
            row_fill, row_missing = None, []
        elif not _has_blank_template_row(table, header_row_index):
            row_fill, row_missing = None, []
        elif table_kind == "track_records":
            row_fill, row_missing = _build_table_row_fill(
                table,
                header_row_index,
                column_fields,
                track_records,
                "track_records",
            )
        elif table_kind == "personnel":
            row_fill, row_missing = _build_table_row_fill(
                table,
                header_row_index,
                column_fields,
                personnel,
                "personnel",
            )
        else:
            row_fill, row_missing = None, []
        if row_fill is not None:
            table_rows.append(row_fill)
            missing.extend(row_missing)

        if personnel and is_consent_table:
            repeated_tables.append(
                RepeatedTableFill(
                    xml_path=table.xml_path,
                    table_index=table.table_index,
                    rows=[_personnel_consent_values(item) for item in personnel],
                )
            )

    return table_rows, repeated_tables, missing


def _fill_xml(
    data: bytes,
    fills: list[CellFill],
    table_rows: list[TableRowFill],
    repeated_tables: list[RepeatedTableFill],
) -> tuple[bytes, list[str], list[dict[str, str]]]:
    _register_namespaces(data)
    root = ET.fromstring(data)
    tables = _iter_local(root, "tbl")
    filled: list[str] = []
    skipped: list[dict[str, str]] = []

    for repeat_fill in sorted(repeated_tables, key=lambda item: item.table_index, reverse=True):
        table_filled, table_skipped = _apply_repeated_table(root, tables, repeat_fill)
        filled.extend(table_filled)
        skipped.extend(table_skipped)

    for row_fill in sorted(table_rows, key=lambda item: item.table_index, reverse=True):
        table_filled, table_skipped = _apply_table_rows(tables, row_fill)
        filled.extend(table_filled)
        skipped.extend(table_skipped)

    for fill in fills:
        parsed = _parse_cell_ref(fill.cell_ref)
        if parsed is None:
            skipped.append({"cell_ref": fill.cell_ref, "reason": "invalid_ref"})
            continue
        try:
            table = tables[int(parsed["table"])]
            row = _children_local(table, "tr")[int(parsed["row"])]
            cell = _children_local(row, "tc")[int(parsed["col"])]
        except (IndexError, ValueError):
            skipped.append({"cell_ref": fill.cell_ref, "reason": "cell_not_found"})
            continue
        _replace_text(cell, fill.value)
        filled.append(f"{fill.field_key}@{fill.cell_ref}")

    return _serialize_hwpx_xml(root), filled, skipped


def _apply_table_rows(
    tables: list[ET.Element],
    table_fill: TableRowFill,
) -> tuple[list[str], list[dict[str, str]]]:
    filled: list[str] = []
    skipped: list[dict[str, str]] = []
    try:
        table = tables[table_fill.table_index]
        rows = _children_local(table, "tr")
        template_row = rows[table_fill.template_row_index]
    except IndexError:
        return [], [{"table": str(table_fill.table_index), "reason": "template_row_not_found"}]

    insert_at = list(table).index(template_row)
    table.remove(template_row)
    for item_index, row_values in enumerate(table_fill.rows):
        row = deepcopy(template_row)
        cells = _children_local(row, "tc")
        for col_index, (field_key, value) in row_values.items():
            if col_index >= len(cells):
                skipped.append(
                    {
                        "table": str(table_fill.table_index),
                        "row": str(item_index),
                        "field_key": field_key,
                        "reason": "cell_not_found",
                    }
                )
                continue
            _replace_text(cells[col_index], value)
            filled.append(
                f"{field_key}@{table_fill.xml_path}:tbl{table_fill.table_index}:row{item_index}"
            )
        table.insert(insert_at + item_index, row)

    return filled, skipped


def _apply_repeated_table(
    root: ET.Element,
    tables: list[ET.Element],
    table_fill: RepeatedTableFill,
) -> tuple[list[str], list[dict[str, str]]]:
    if not table_fill.rows:
        return [], []
    try:
        template_table = tables[table_fill.table_index]
    except IndexError:
        return [], [{"table": str(table_fill.table_index), "reason": "repeat_table_not_found"}]

    parent = _find_parent(root, template_table)
    if parent is None:
        return [], [{"table": str(table_fill.table_index), "reason": "parent_not_found"}]

    insert_at = list(parent).index(template_table)
    filled: list[str] = []
    for item_index, values in enumerate(table_fill.rows):
        table = template_table if item_index == 0 else deepcopy(template_table)
        _fill_label_value_table(table, values)
        filled.append(
            f"personnel.repeat@{table_fill.xml_path}:tbl{table_fill.table_index}:repeat{item_index}"
        )
        if item_index > 0:
            parent.insert(insert_at + item_index, table)
    return filled, []


def _fill_label_value_table(table: ET.Element, values: dict[str, str]) -> None:
    for row in _children_local(table, "tr"):
        cells = _children_local(row, "tc")
        for index, cell in enumerate(cells):
            field_key = _consent_field_key(_text_of(cell))
            if field_key is None:
                continue
            target = _target_cell(cells, index)
            if target is not None:
                _replace_text(
                    target,
                    values.get(field_key) or f"[확인 필요: personnel.{field_key}]",
                )


def _replace_text(root: ET.Element, value: str) -> None:
    text_nodes = [element for element in root.iter() if _local_name(element.tag) == "t"]
    if not text_nodes:
        return
    text_nodes[0].text = value
    for node in text_nodes[1:]:
        node.text = ""


def _resolve_value(values: dict[str, object], path: str) -> object | None:
    current: object = values
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _build_table_row_fill(
    table: HwpxTable,
    header_row_index: int,
    column_fields: dict[int, str],
    items: list[dict[str, object]],
    list_key: str,
) -> tuple[TableRowFill | None, list[dict[str, str]]]:
    if not items:
        return None, []
    template_row_index = header_row_index + 1
    if template_row_index >= len(table.rows):
        return None, [
            {
                "field_key": list_key,
                "cell_ref": f"{table.xml_path}:tbl{table.table_index}",
                "message": "반복 표의 예시 행을 찾지 못했습니다.",
            }
        ]

    missing: list[dict[str, str]] = []
    rows: list[dict[int, tuple[str, str]]] = []
    for item_index, item in enumerate(items):
        row_values: dict[int, tuple[str, str]] = {}
        for col_index, field_key in column_fields.items():
            value = _record_value(item, field_key, item_index)
            output_value = (
                str(value) if value not in {None, ""} else f"[확인 필요: {list_key}.{field_key}]"
            )
            if value in {None, ""} and field_key not in {"no"}:
                missing.append(
                    {
                        "field_key": f"{list_key}.{field_key}",
                        "cell_ref": (
                            f"{table.xml_path}:tbl{table.table_index}:"
                            f"r{template_row_index}:c{col_index}"
                        ),
                        "message": "반복 표에 채울 데이터가 없습니다.",
                    }
                )
            row_values[col_index] = (f"{list_key}.{field_key}", output_value)
        rows.append(row_values)

    return (
        TableRowFill(
            xml_path=table.xml_path,
            table_index=table.table_index,
            template_row_index=template_row_index,
            rows=rows,
        ),
        missing,
    )


def _detect_repeating_table(table: HwpxTable) -> tuple[str | None, int, dict[int, str]]:
    best_kind: str | None = None
    best_row_index = -1
    best_fields: dict[int, str] = {}
    best_score = 0
    for row_index, row in enumerate(table.rows):
        personnel_fields = _match_header_fields(row, PERSONNEL_HEADER_FIELDS)
        track_fields = _match_header_fields(row, TRACK_RECORD_HEADER_FIELDS)
        personnel_score = len(set(personnel_fields.values()) - {"no"})
        track_score = len(set(track_fields.values()) - {"no"})
        if (
            personnel_score > best_score
            and personnel_score >= 3
            and "name" in personnel_fields.values()
        ):
            best_kind = "personnel"
            best_row_index = row_index
            best_fields = personnel_fields
            best_score = personnel_score
        if (
            track_score > best_score
            and track_score >= 3
            and "taskName" in track_fields.values()
            and bool({"org", "amount", "contractPeriod"} & set(track_fields.values()))
        ):
            best_kind = "track_records"
            best_row_index = row_index
            best_fields = track_fields
            best_score = track_score
    return best_kind, best_row_index, best_fields


def _has_blank_template_row(table: HwpxTable, header_row_index: int) -> bool:
    template_row_index = header_row_index + 1
    if header_row_index < 0 or template_row_index >= len(table.rows):
        return False
    row = table.rows[template_row_index]
    if not row:
        return False
    blank_count = 0
    for cell in row:
        text = _normalize(cell.text)
        if not text or text in {"년개월", "년", "개월"}:
            blank_count += 1
    return blank_count / len(row) >= 0.6


def _match_header_fields(
    row: Sequence[object],
    header_fields: dict[str, tuple[str, ...]],
) -> dict[int, str]:
    matched: dict[int, str] = {}
    for col_index, cell in enumerate(row):
        normalized = _normalize(_cell_text(cell))
        for field_key, aliases in header_fields.items():
            if any(_is_label_match(normalized, _normalize(alias)) for alias in aliases):
                matched[col_index] = field_key
                break
    return matched


def _is_personnel_consent_table(table: HwpxTable) -> bool:
    text = _normalize(" ".join(cell.text for row in table.rows for cell in row))
    if not any(_is_label_match(text, _normalize(keyword)) for keyword in CONSENT_KEYWORDS):
        return False
    fields = {
        field
        for row in table.rows
        for cell in row
        if (field := _consent_field_key(cell.text)) is not None
    }
    return "name" in fields and len(fields) >= 2


def _consent_field_key(label: str) -> str | None:
    normalized = _normalize(label)
    for field_key, aliases in CONSENT_LABEL_FIELDS.items():
        if any(_is_label_match(normalized, _normalize(alias)) for alias in aliases):
            return field_key
    return None


def _personnel_consent_values(item: dict[str, object]) -> dict[str, str]:
    return {
        "name": str(_record_value(item, "name", 0) or ""),
        "dept": str(_record_value(item, "dept", 0) or ""),
        "position": str(_record_value(item, "position", 0) or ""),
        "birth": str(_record_value(item, "birth", 0) or ""),
        "phone": str(_record_value(item, "phone", 0) or ""),
        "email": str(_record_value(item, "email", 0) or ""),
    }


def _record_value(item: dict[str, object], field_key: str, index: int) -> object | None:
    if field_key == "no":
        return index + 1
    aliases = RECORD_FIELD_ALIASES.get(field_key, (field_key,))
    for alias in aliases:
        value = item.get(alias)
        if value not in {None, ""}:
            if field_key == "amount":
                return _format_amount(value)
            return value
    return None


def _format_amount(value: object) -> str:
    if isinstance(value, int | float) and value:
        return f"{int(value):,}"
    return str(value)


def _list_value(values: dict[str, object], key: str) -> list[dict[str, object]]:
    value = values.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _target_cell(cells: list[ET.Element], label_index: int) -> ET.Element | None:
    for candidate in cells[label_index + 1 :]:
        text = _text_of(candidate)
        if not text.strip() or re.fullmatch(r"[\[\]().:·\-\s_]+", text):
            return candidate
    if label_index + 1 < len(cells):
        return cells[label_index + 1]
    return None


def _cell_text(cell: object) -> str:
    return str(getattr(cell, "text", ""))


def _text_of(root: ET.Element) -> str:
    texts = [element.text or "" for element in root.iter() if _local_name(element.tag) == "t"]
    return "\n".join(text.strip() for text in texts if text and text.strip()).strip()


def _find_parent(root: ET.Element, target: ET.Element) -> ET.Element | None:
    for parent in root.iter():
        if target in list(parent):
            return parent
    return None


def _normalize(value: str) -> str:
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


def _register_namespaces(data: bytes) -> None:
    for _, (prefix, uri) in ET.iterparse(BytesIO(data), events=("start-ns",)):
        ET.register_namespace(prefix, uri)


def _serialize_hwpx_xml(root: ET.Element) -> bytes:
    body = cast(bytes, ET.tostring(root, encoding="utf-8", xml_declaration=False))
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>' + body


def _parse_cell_ref(cell_ref: str) -> dict[str, str] | None:
    match = CELL_REF_RE.match(cell_ref)
    return match.groupdict() if match else None


def _iter_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _children_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in list(root) if _local_name(element.tag) == name]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


TRACK_RECORD_HEADER_FIELDS: dict[str, tuple[str, ...]] = {
    "no": ("연번", "번호", "순번"),
    "taskName": ("사업명", "용역명", "과업명", "계약명", "프로젝트명", "수행사업명"),
    "org": ("발주처", "발주기관", "수요기관", "기관명", "기관"),
    "amount": ("계약금액", "금액", "용역금액", "사업비", "수행금액"),
    "contractPeriod": ("계약기간", "수행기간", "기간"),
    "year": ("연도", "수행연도"),
    "field": ("분야", "사업분야"),
    "desc": ("개요", "주요내용", "용역개요", "수행내용", "사업내용"),
}

PERSONNEL_HEADER_FIELDS: dict[str, tuple[str, ...]] = {
    "no": ("연번", "번호", "순번"),
    "name": ("성명", "이름", "참여인력", "투입인력", "참여자", "담당자"),
    "dept": ("소속", "부서"),
    "position": ("직위", "직책", "역할", "담당업무", "책임"),
    "career": ("경력", "경력기간", "실무경력"),
    "joinDate": ("입사일", "입사"),
    "eduSchool": ("학교", "최종학교"),
    "eduMajor": ("전공", "학과"),
    "eduDegree": ("학위", "최종학력", "학력"),
}

CONSENT_LABEL_FIELDS: dict[str, tuple[str, ...]] = {
    "name": ("성명", "이름", "참여자", "동의자"),
    "dept": ("소속", "부서"),
    "position": ("직위", "직책"),
    "birth": ("생년월일", "생년", "주민등록번호"),
    "phone": ("전화", "연락처", "휴대전화"),
    "email": ("이메일", "전자우편", "e-mail"),
}

CONSENT_KEYWORDS: tuple[str, ...] = (
    "개인정보",
    "동의서",
    "개인정보수집",
    "개인정보제공",
    "보안서약",
    "청렴서약",
)

RECORD_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "no": ("no",),
    "taskName": ("taskName", "name", "projectName", "title"),
    "org": ("org", "client", "agency", "demandOrg", "noticeOrg"),
    "amount": ("amountRaw", "amount", "contractAmount"),
    "contractPeriod": ("contractPeriod", "period"),
    "year": ("year",),
    "field": ("field", "domain"),
    "desc": ("desc", "description", "summary"),
    "name": ("name",),
    "dept": ("dept", "department"),
    "position": ("position", "role"),
    "career": ("career", "careerPeriod"),
    "joinDate": ("joinDate",),
    "eduSchool": ("eduSchool", "school"),
    "eduMajor": ("eduMajor", "major"),
    "eduDegree": ("eduDegree", "degree", "education"),
    "birth": ("birth", "birthDate", "birthday"),
    "phone": ("phone", "mobile"),
    "email": ("email",),
}
