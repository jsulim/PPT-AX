from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from core.hwpx.mapping import FieldMapping

CELL_REF_RE = re.compile(r"^(?P<xml>.+):tbl(?P<table>\d+):r(?P<row>\d+):c(?P<col>\d+)$")


@dataclass(frozen=True)
class CellFill:
    cell_ref: str
    field_key: str
    value: str


@dataclass(frozen=True)
class HwpxFillReport:
    filled: list[str] = field(default_factory=list)
    missing: list[dict[str, str]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


def fill_hwpx_cells(input_path: Path, output_path: Path, fills: list[CellFill]) -> HwpxFillReport:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fills_by_xml: dict[str, list[CellFill]] = {}
    for fill in fills:
        parsed = _parse_cell_ref(fill.cell_ref)
        if parsed is None:
            continue
        fills_by_xml.setdefault(parsed["xml"], []).append(fill)

    filled: list[str] = []
    skipped: list[dict[str, str]] = []

    with zipfile.ZipFile(input_path, "r") as source:
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename in fills_by_xml:
                    data, xml_filled, xml_skipped = _fill_xml(data, fills_by_xml[info.filename])
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


def _fill_xml(data: bytes, fills: list[CellFill]) -> tuple[bytes, list[str], list[dict[str, str]]]:
    ET.register_namespace("hp", "http://www.hancom.co.kr/hwpml/2011/paragraph")
    root = ET.fromstring(data)
    tables = _iter_local(root, "tbl")
    filled: list[str] = []
    skipped: list[dict[str, str]] = []

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
        filled.append(fill.cell_ref)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True), filled, skipped


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


def _parse_cell_ref(cell_ref: str) -> dict[str, str] | None:
    match = CELL_REF_RE.match(cell_ref)
    return match.groupdict() if match else None


def _iter_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _children_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in list(root) if _local_name(element.tag) == name]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
