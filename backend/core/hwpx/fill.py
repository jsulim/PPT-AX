from __future__ import annotations

import re
import zipfile
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, cast

from lxml import etree as LET

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
class PersonnelProfileFill:
    xml_path: str
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
    personnel_profiles: list[PersonnelProfileFill] | None = None,
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
    personnel_profiles_by_xml: dict[str, list[PersonnelProfileFill]] = {}
    for profile_fill in personnel_profiles or []:
        personnel_profiles_by_xml.setdefault(profile_fill.xml_path, []).append(profile_fill)

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
                    or info.filename in personnel_profiles_by_xml
                ):
                    data, xml_filled, xml_skipped = _fill_xml(
                        data,
                        fills_by_xml.get(info.filename, []),
                        table_rows_by_xml.get(info.filename, []),
                        repeated_tables_by_xml.get(info.filename, []),
                        personnel_profiles_by_xml.get(info.filename, []),
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


def build_personnel_profile_fills(
    document: HwpxDocument,
    values: dict[str, object],
) -> tuple[list[PersonnelProfileFill], list[dict[str, str]]]:
    personnel = _list_value(values, "personnel") or _list_value(values, "selectedPersonnel")
    if not personnel:
        return [], []

    xml_path = _find_personnel_profile_xml_path(document)
    if xml_path is None:
        return [], [
            {
                "field_key": "personnel.profiles",
                "cell_ref": "",
                "message": "참여인력 이력사항 서식을 찾지 못했습니다.",
            }
        ]

    rows = [_personnel_profile_values(item, values) for item in personnel]
    missing: list[dict[str, str]] = []
    for index, item in enumerate(personnel):
        for field_key in ("name", "dept", "position", "career"):
            if _record_value(item, field_key, index) in {None, ""}:
                missing.append(
                    {
                        "field_key": f"personnel.{field_key}",
                        "cell_ref": f"{xml_path}:personnel_profile:{index}",
                        "message": "참여인력 이력사항에 채울 데이터가 없습니다.",
                    }
                )
    return [PersonnelProfileFill(xml_path=xml_path, rows=rows)], missing


def _fill_xml(
    data: bytes,
    fills: list[CellFill],
    table_rows: list[TableRowFill],
    repeated_tables: list[RepeatedTableFill],
    personnel_profiles: list[PersonnelProfileFill],
) -> tuple[bytes, list[str], list[dict[str, str]]]:
    parser = LET.XMLParser(remove_blank_text=False, resolve_entities=False, huge_tree=True)
    root = LET.fromstring(data, parser=parser)
    tables = _iter_local(root, "tbl")
    filled: list[str] = []
    skipped: list[dict[str, str]] = []

    for repeat_fill in sorted(repeated_tables, key=lambda item: item.table_index, reverse=True):
        table_filled, table_skipped = _apply_repeated_table(root, tables, repeat_fill)
        filled.extend(table_filled)
        skipped.extend(table_skipped)

    for profile_fill in personnel_profiles:
        profile_filled, profile_skipped = _apply_personnel_profiles(root, profile_fill)
        filled.extend(profile_filled)
        skipped.extend(profile_skipped)
        tables = _iter_local(root, "tbl")

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
        if _replace_text(cell, fill.value):
            filled.append(f"{fill.field_key}@{fill.cell_ref}")
        else:
            skipped.append({"cell_ref": fill.cell_ref, "reason": "text_node_not_found"})

    return _serialize_hwpx_xml(root), filled, skipped


def _apply_table_rows(
    tables: list[Any],
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

    rows = _ensure_table_data_rows(table, rows, template_row, table_fill)
    for item_index, row_values in enumerate(table_fill.rows):
        row_index = table_fill.template_row_index + item_index
        if row_index >= len(rows):
            skipped.append(
                {
                    "table": str(table_fill.table_index),
                    "row": str(item_index),
                    "reason": "not_enough_blank_rows",
                }
            )
            continue
        row = rows[row_index]
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
            if _replace_text(cells[col_index], value):
                filled.append(
                    f"{field_key}@{table_fill.xml_path}:tbl{table_fill.table_index}:row{item_index}"
                )
            else:
                skipped.append(
                    {
                        "table": str(table_fill.table_index),
                        "row": str(item_index),
                        "field_key": field_key,
                        "reason": "text_node_not_found",
                    }
                )

    return filled, skipped


def _ensure_table_data_rows(
    table: Any,
    rows: list[Any],
    template_row: Any,
    table_fill: TableRowFill,
) -> list[Any]:
    required_rows = len(table_fill.rows)
    blank_rows = 0
    expected_cells = len(_children_local(template_row, "tc"))
    for row in rows[table_fill.template_row_index :]:
        if not _is_blank_repeating_row(row, expected_cells):
            break
        blank_rows += 1
    if blank_rows == 0:
        return rows

    insert_at = list(table).index(rows[table_fill.template_row_index + blank_rows - 1]) + 1
    for _index in range(max(0, required_rows - blank_rows)):
        clone = deepcopy(template_row)
        _clear_row_text(clone)
        table.insert(insert_at, clone)
        insert_at += 1

    updated_rows = _children_local(table, "tr")
    _renumber_table_rows(table, updated_rows)
    return updated_rows


def _is_blank_repeating_row(row: Any, expected_cells: int) -> bool:
    cells = _children_local(row, "tc")
    if expected_cells == 0:
        return False
    if len(cells) != expected_cells:
        return False
    row_text = _normalize(_text_of(row))
    if any(keyword in row_text for keyword in ("누계", "합계", "소계")):
        return False
    blank_count = 0
    for cell in cells:
        text = _normalize(_text_of(cell))
        if not text or text in {"년개월", "개월", "년"}:
            blank_count += 1
    return blank_count / len(cells) >= 0.6


def _clear_row_text(row: Any) -> None:
    for cell in _children_local(row, "tc"):
        _replace_text(cell, "")


def _renumber_table_rows(table: Any, rows: list[Any]) -> None:
    table.set("rowCnt", str(len(rows)))
    for row_index, row in enumerate(rows):
        for col_index, cell in enumerate(_children_local(row, "tc")):
            for child in list(cell):
                if _local_name(child.tag) == "cellAddr":
                    child.set("rowAddr", str(row_index))
                    child.set("colAddr", str(col_index))
                    break


def _apply_repeated_table(
    root: Any,
    tables: list[Any],
    table_fill: RepeatedTableFill,
) -> tuple[list[str], list[dict[str, str]]]:
    if not table_fill.rows:
        return [], []
    try:
        template_table = tables[table_fill.table_index]
    except IndexError:
        return [], [{"table": str(table_fill.table_index), "reason": "repeat_table_not_found"}]

    filled: list[str] = []
    header_row_index, column_fields = _detect_consent_header(template_table)
    if header_row_index >= 0 and column_fields:
        rows = _ensure_repeated_table_rows(
            template_table,
            header_row_index + 1,
            len(table_fill.rows),
        )
        for item_index, values in enumerate(table_fill.rows):
            row_index = header_row_index + 1 + item_index
            if row_index >= len(rows):
                return filled, [
                    {
                        "table": str(table_fill.table_index),
                        "row": str(item_index),
                        "reason": "not_enough_blank_rows",
                    }
                ]
            cells = _children_local(rows[row_index], "tc")
            for col_index, field_key in column_fields.items():
                if col_index >= len(cells):
                    continue
                if _replace_text(
                    cells[col_index],
                    values.get(field_key) or f"[확인 필요: personnel.{field_key}]",
                ):
                    filled.append(
                        f"personnel.{field_key}@{table_fill.xml_path}:"
                        f"tbl{table_fill.table_index}:repeat{item_index}"
                    )
        return filled, []

    if table_fill.rows:
        _fill_label_value_table(template_table, table_fill.rows[0])
        filled.append(
            f"personnel.repeat@{table_fill.xml_path}:tbl{table_fill.table_index}:repeat0"
        )
    return filled, []


def _ensure_repeated_table_rows(
    table: Any,
    template_row_index: int,
    required_rows: int,
) -> list[Any]:
    rows = _children_local(table, "tr")
    if template_row_index >= len(rows):
        return rows
    template_row = rows[template_row_index]
    expected_cells = len(_children_local(template_row, "tc"))
    blank_rows = 0
    for row in rows[template_row_index:]:
        if not _is_blank_repeating_row(row, expected_cells):
            break
        blank_rows += 1
    if blank_rows == 0:
        return rows

    insert_at = list(table).index(rows[template_row_index + blank_rows - 1]) + 1
    for _index in range(max(0, required_rows - blank_rows)):
        clone = deepcopy(template_row)
        _clear_row_text(clone)
        table.insert(insert_at, clone)
        insert_at += 1
    updated_rows = _children_local(table, "tr")
    _renumber_table_rows(table, updated_rows)
    return updated_rows


def _apply_personnel_profiles(
    root: Any,
    profile_fill: PersonnelProfileFill,
) -> tuple[list[str], list[dict[str, str]]]:
    if not profile_fill.rows:
        return [], []

    block_range = _find_personnel_profile_block(root)
    if block_range is None:
        return [], [{"field_key": "personnel.profiles", "reason": "profile_block_not_found"}]

    start, end = block_range
    children = list(root)
    template_block = children[start:end]
    if not template_block:
        return [], [{"field_key": "personnel.profiles", "reason": "profile_block_empty"}]

    insert_at = end
    blocks: list[list[Any]] = [template_block]
    for _item_index in range(1, len(profile_fill.rows)):
        block = [deepcopy(element) for element in template_block]
        for offset, element in enumerate(block):
            root.insert(insert_at + offset, element)
        insert_at += len(block)
        blocks.append(block)

    filled: list[str] = []
    skipped: list[dict[str, str]] = []
    for item_index, values in enumerate(profile_fill.rows):
        block_filled, block_skipped = _fill_personnel_profile_block(
            blocks[item_index],
            values,
            item_index,
        )
        filled.extend(block_filled)
        skipped.extend(block_skipped)
    return filled, skipped


def _fill_personnel_profile_block(
    block: list[Any],
    values: dict[str, str],
    item_index: int,
) -> tuple[list[str], list[dict[str, str]]]:
    tables = [element for element in _iter_block_local(block, "tbl")]
    table = next(
        (candidate for candidate in tables if _is_personnel_profile_table(candidate)),
        None,
    )
    if table is None:
        return [], [{"field_key": "personnel.profile", "reason": "profile_table_not_found"}]

    filled: list[str] = []
    skipped: list[dict[str, str]] = []

    def put(row_index: int, col_index: int, field_key: str) -> None:
        try:
            row = _children_local(table, "tr")[row_index]
            cell = _children_local(row, "tc")[col_index]
        except IndexError:
            skipped.append(
                {
                    "field_key": f"personnel.{field_key}",
                    "row": str(row_index),
                    "col": str(col_index),
                    "reason": "cell_not_found",
                }
            )
            return
        value = values.get(field_key)
        if not value and field_key in PERSONNEL_PROFILE_REQUIRED_FIELDS:
            value = f"[확인 필요: personnel.{field_key}]"
        elif not value:
            value = ""
        if _replace_text(cell, value):
            filled.append(f"personnel.{field_key}@profile:{item_index}:r{row_index}:c{col_index}")
        else:
            skipped.append(
                {
                    "field_key": f"personnel.{field_key}",
                    "row": str(row_index),
                    "col": str(col_index),
                    "reason": "text_node_not_found",
                }
            )

    put(0, 1, "name")
    put(0, 3, "dept")
    put(1, 1, "age")
    put(1, 3, "position")
    put(2, 1, "eduSchool")
    put(2, 2, "eduMajor")
    put(2, 4, "career")
    put(3, 1, "gradSchool")
    put(3, 2, "gradMajor")
    put(3, 3, "certifications")
    put(4, 1, "role")
    put(4, 3, "period")
    put(4, 5, "participationRate")

    career_rows = values.get("careerRows")
    if career_rows:
        _replace_text(_children_local(_children_local(table, "tr")[8], "tc")[0], career_rows)
        filled.append(f"personnel.careerRows@profile:{item_index}:r8")

    company_name = values.get("companyName")
    if company_name:
        signature = next(
            (
                element
                for element in block
                if "상호 또는 법인명" in _text_of(element)
            ),
            None,
        )
        if signature is not None:
            _replace_text(signature, f"상호 또는 법인명 : {company_name}                 (인)")
            filled.append(f"personnel.companyName@profile:{item_index}:signature")

    return filled, skipped


def _find_personnel_profile_block(root: Any) -> tuple[int, int] | None:
    children = list(root)
    start: int | None = None
    for index, child in enumerate(children):
        text = _text_of(child)
        if _is_personnel_profile_title(text):
            start = index
            break
    if start is None:
        for index, child in enumerate(children):
            text = _text_of(child)
            if text.strip() == "참여인력 이력사항":
                start = index
                break
    if start is None:
        return None

    end = len(children)
    for index in range(start + 1, len(children)):
        text = _text_of(children[index])
        if re.search(r"별지\s*제\s*12\s*호", text) or "행정처분 확인서" in text:
            end = index
            break
    while end > start and not _text_of(children[end - 1]).strip():
        end -= 1
    return start, end


def _is_personnel_profile_title(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text)
    return (
        len(normalized) <= 80
        and "별지제11호" in normalized
        and "참여인력이력사항" in normalized
    )


def _is_personnel_profile_table(table: Any) -> bool:
    text = _normalize(_text_of(table))
    return all(
        keyword in text
        for keyword in (
            _normalize("성 명"),
            _normalize("소 속"),
            _normalize("경력사항"),
            _normalize("참여 업무"),
        )
    )


def _fill_label_value_table(table: Any, values: dict[str, str]) -> None:
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


def _replace_text(root: Any, value: str) -> bool:
    text_nodes = [element for element in root.iter() if _local_name(element.tag) == "t"]
    if not text_nodes:
        run = next((element for element in root.iter() if _local_name(element.tag) == "run"), None)
        if run is None:
            return False
        namespace = run.tag.rsplit("}", 1)[0].lstrip("{") if "}" in run.tag else ""
        tag = f"{{{namespace}}}t" if namespace else "t"
        text_node = LET.Element(tag)
        run.insert(0, text_node)
        text_nodes = [text_node]
    text_nodes[0].text = value
    for node in text_nodes[1:]:
        node.text = ""
    return True


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


def _detect_consent_header(table: Any) -> tuple[int, dict[int, str]]:
    best_row_index = -1
    best_fields: dict[int, str] = {}
    for row_index, row in enumerate(_children_local(table, "tr")):
        fields: dict[int, str] = {}
        for col_index, cell in enumerate(_children_local(row, "tc")):
            field_key = _consent_field_key(_text_of(cell))
            if field_key is not None:
                fields[col_index] = field_key
        if len(fields) > len(best_fields):
            best_row_index = row_index
            best_fields = fields
    if "name" not in best_fields.values() or len(best_fields) < 2:
        return -1, {}
    return best_row_index, best_fields


def _personnel_consent_values(item: dict[str, object]) -> dict[str, str]:
    return {
        "name": str(_record_value(item, "name", 0) or ""),
        "dept": str(_record_value(item, "dept", 0) or ""),
        "position": str(_record_value(item, "position", 0) or ""),
        "birth": str(_record_value(item, "birth", 0) or ""),
        "phone": str(_record_value(item, "phone", 0) or ""),
        "email": str(_record_value(item, "email", 0) or ""),
    }


def _personnel_profile_values(
    item: dict[str, object],
    values: dict[str, object],
) -> dict[str, str]:
    company = values.get("company")
    company_name = ""
    if isinstance(company, dict):
        company_name = str(company.get("name") or "")
    return {
        "name": str(_record_value(item, "name", 0) or ""),
        "dept": str(_record_value(item, "dept", 0) or ""),
        "age": str(_record_value(item, "age", 0) or ""),
        "position": str(_record_value(item, "position", 0) or ""),
        "eduSchool": str(_record_value(item, "eduSchool", 0) or ""),
        "eduMajor": str(_record_value(item, "eduMajor", 0) or ""),
        "career": str(_record_value(item, "career", 0) or ""),
        "gradSchool": str(_record_value(item, "gradSchool", 0) or ""),
        "gradMajor": str(_record_value(item, "gradMajor", 0) or ""),
        "certifications": str(_record_value(item, "certifications", 0) or ""),
        "role": str(_record_value(item, "role", 0) or _record_value(item, "position", 0) or ""),
        "period": str(_record_value(item, "participationPeriod", 0) or ""),
        "participationRate": str(_record_value(item, "participationRate", 0) or ""),
        "careerRows": _personnel_career_rows(item),
        "companyName": company_name,
    }


def _personnel_career_rows(item: dict[str, object]) -> str:
    careers = item.get("careers") or item.get("careerRows") or item.get("projects")
    if not isinstance(careers, list):
        return ""
    lines: list[str] = []
    for career in careers:
        if not isinstance(career, dict):
            continue
        parts = [
            str(career.get("taskName") or career.get("projectName") or career.get("name") or ""),
            str(career.get("period") or career.get("participationPeriod") or ""),
            str(career.get("role") or career.get("task") or ""),
            str(career.get("org") or career.get("client") or career.get("workplace") or ""),
            str(career.get("note") or ""),
        ]
        line = " / ".join(part for part in parts if part)
        if line:
            lines.append(line)
    return "\n".join(lines)


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


def _target_cell(cells: list[Any], label_index: int) -> Any | None:
    for candidate in cells[label_index + 1 :]:
        text = _text_of(candidate)
        if not text.strip() or re.fullmatch(r"[\[\]().:·\-\s_]+", text):
            return candidate
    if label_index + 1 < len(cells):
        return cells[label_index + 1]
    return None


def _cell_text(cell: object) -> str:
    return str(getattr(cell, "text", ""))


def _text_of(root: Any) -> str:
    texts = [element.text or "" for element in root.iter() if _local_name(element.tag) == "t"]
    return "\n".join(text.strip() for text in texts if text and text.strip()).strip()


def _iter_block_local(block: Sequence[Any], name: str) -> list[Any]:
    return [
        element
        for root in block
        for element in root.iter()
        if _local_name(element.tag) == name
    ]


def _find_personnel_profile_xml_path(document: HwpxDocument) -> str | None:
    for table in document.tables:
        text = "\n".join(cell.text for row in table.rows for cell in row)
        if all(keyword in text for keyword in ("성 명", "소 속", "경    력    사    항")):
            return table.xml_path
    return None


def _find_parent(root: Any, target: Any) -> Any | None:
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


def _serialize_hwpx_xml(root: Any) -> bytes:
    body = cast(bytes, LET.tostring(root, encoding="UTF-8", xml_declaration=False))
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>' + body


def _parse_cell_ref(cell_ref: str) -> dict[str, str] | None:
    match = CELL_REF_RE.match(cell_ref)
    return match.groupdict() if match else None


def _iter_local(root: Any, name: str) -> list[Any]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _children_local(root: Any, name: str) -> list[Any]:
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

PERSONNEL_PROFILE_REQUIRED_FIELDS: set[str] = {
    "name",
    "dept",
    "position",
    "career",
    "role",
    "period",
    "participationRate",
}

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
    "position": ("position", "role", "title"),
    "age": ("age",),
    "career": ("career", "careerPeriod"),
    "joinDate": ("joinDate",),
    "eduSchool": ("eduSchool", "school"),
    "eduMajor": ("eduMajor", "major"),
    "eduDegree": ("eduDegree", "degree", "education"),
    "gradSchool": ("gradSchool", "graduateSchool"),
    "gradMajor": ("gradMajor", "graduateMajor"),
    "certifications": ("certifications", "certificate", "certificates", "license"),
    "role": ("role", "task", "assignedTask", "duty"),
    "participationPeriod": ("participationPeriod", "period"),
    "participationRate": ("participationRate", "rate"),
    "birth": ("birth", "birthDate", "birthday"),
    "phone": ("phone", "mobile"),
    "email": ("email",),
}
