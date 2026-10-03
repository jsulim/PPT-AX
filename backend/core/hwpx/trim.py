from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, cast

from lxml import etree as LET

FORM_START_RE = re.compile(
    r"(입찰\s*및\s*제안서\s*관련\s*서식|별지\s*제\s*\d+\s*호\s*서식|입찰\s*참가\s*신청서|제안서\s*표지)"
)


def trim_hwpx_to_form_start(path: Path) -> bool:
    temp_path = path.with_suffix(".trimmed.hwpx")
    found = False

    with zipfile.ZipFile(path, "r") as source:
        section_paths = _section_paths(source)
        found_section: str | None = None
        trimmed_sections: dict[str, bytes] = {}

        for section_path in section_paths:
            data = source.read(section_path)
            if found_section is not None:
                continue

            root = _parse_xml(data)
            start_index = _find_form_start_index(root)
            if start_index is None:
                trimmed_sections[section_path] = _empty_section(root)
                continue

            found = True
            found_section = section_path
            trimmed_sections[section_path] = _trim_section_before(root, start_index)

        if not found:
            return False

        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                output_data = trimmed_sections.get(info.filename)
                if output_data is None:
                    output_data = source.read(info.filename)
                target.writestr(info, output_data)

    temp_path.replace(path)
    return True


def _section_paths(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.startswith("Contents/section") and name.endswith(".xml")
    )


def _parse_xml(data: bytes) -> Any:
    parser = LET.XMLParser(remove_blank_text=False, resolve_entities=False, huge_tree=True)
    return LET.fromstring(data, parser=parser)


def _find_form_start_index(root: Any) -> int | None:
    for index, child in enumerate(list(root)):
        if _is_form_start_text(_text_of(child)):
            return index
    return None


def _is_form_start_text(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text)
    if "입찰및제안서관련서식" in normalized:
        return True
    return len(normalized) <= 80 and FORM_START_RE.search(text) is not None


def _empty_section(root: Any) -> bytes:
    for child in list(root):
        root.remove(child)
    return _serialize_xml(root)


def _trim_section_before(root: Any, start_index: int) -> bytes:
    for child in list(root)[:start_index]:
        root.remove(child)
    return _serialize_xml(root)


def _text_of(root: Any) -> str:
    texts = [element.text or "" for element in root.iter() if _local_name(element.tag) == "t"]
    return "\n".join(text.strip() for text in texts if text and text.strip()).strip()


def _serialize_xml(root: Any) -> bytes:
    body = cast(bytes, LET.tostring(root, encoding="UTF-8", xml_declaration=False))
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>' + body


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
