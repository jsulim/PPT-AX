from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

FORM_START_RE = re.compile(r"(붙임|별지|서식|입찰참가신청서|제안서\s*표지|확약서|서약서)")


@dataclass(frozen=True)
class HwpxParagraph:
    xml_path: str
    paragraph_index: int
    text: str
    is_form_start: bool


@dataclass(frozen=True)
class HwpxCell:
    xml_path: str
    table_index: int
    row_index: int
    col_index: int
    text: str

    @property
    def ref(self) -> str:
        return f"{self.xml_path}:tbl{self.table_index}:r{self.row_index}:c{self.col_index}"


@dataclass(frozen=True)
class HwpxTable:
    xml_path: str
    table_index: int
    rows: list[list[HwpxCell]]


@dataclass(frozen=True)
class HwpxDocument:
    paragraphs: list[HwpxParagraph]
    tables: list[HwpxTable]

    @property
    def text(self) -> str:
        parts = [paragraph.text for paragraph in self.paragraphs if paragraph.text]
        for table in self.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row if cell.text)
        return "\n".join(parts)


def read_hwpx(path: Path) -> HwpxDocument:
    paragraphs: list[HwpxParagraph] = []
    tables: list[HwpxTable] = []

    with zipfile.ZipFile(path) as archive:
        for xml_path in _section_paths(archive):
            root = ET.fromstring(archive.read(xml_path))
            paragraphs.extend(_extract_paragraphs(xml_path, root))
            tables.extend(_extract_tables(xml_path, root))

    return HwpxDocument(paragraphs=paragraphs, tables=tables)


def form_text(document: HwpxDocument) -> str:
    lines = document.text.splitlines()
    for index, line in enumerate(lines):
        if FORM_START_RE.search(line):
            return "\n".join(lines[index:])
    return document.text


def _section_paths(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.startswith("Contents/section") and name.endswith(".xml")
    )


def _extract_paragraphs(xml_path: str, root: ET.Element) -> list[HwpxParagraph]:
    paragraphs: list[HwpxParagraph] = []
    for paragraph in _iter_local(root, "p"):
        text = _text_of(paragraph)
        if not text:
            continue
        paragraphs.append(
            HwpxParagraph(
                xml_path=xml_path,
                paragraph_index=len(paragraphs),
                text=text,
                is_form_start=bool(FORM_START_RE.search(text)),
            )
        )
    return paragraphs


def _extract_tables(xml_path: str, root: ET.Element) -> list[HwpxTable]:
    tables: list[HwpxTable] = []
    for table_index, table_el in enumerate(_iter_local(root, "tbl")):
        rows: list[list[HwpxCell]] = []
        for row_index, row_el in enumerate(_children_local(table_el, "tr")):
            row: list[HwpxCell] = []
            for col_index, cell_el in enumerate(_children_local(row_el, "tc")):
                row.append(
                    HwpxCell(
                        xml_path=xml_path,
                        table_index=table_index,
                        row_index=row_index,
                        col_index=col_index,
                        text=_text_of(cell_el),
                    )
                )
            rows.append(row)
        tables.append(HwpxTable(xml_path=xml_path, table_index=table_index, rows=rows))
    return tables


def _iter_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _children_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in list(root) if _local_name(element.tag) == name]


def _text_of(root: ET.Element) -> str:
    texts = [element.text or "" for element in root.iter() if _local_name(element.tag) == "t"]
    return "\n".join(text.strip() for text in texts if text and text.strip()).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
