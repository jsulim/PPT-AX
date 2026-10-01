from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


@dataclass(frozen=True)
class TextSlot:
    slide_index: int
    shape_id: str
    kind: str
    original_text: str
    char_count: int
    max_char_count: int
    bounds: dict[str, int | None]
    style_ref: dict[str, str | int | None]
    role_key: str = "unknown"
    slot_name: str | None = None
    value_type: str = "unknown"
    field_binding: str | None = None
    locked: bool = False


@dataclass(frozen=True)
class TemplateSlots:
    slide_count: int
    slots: list[TextSlot]


def extract_text_slots(pptx_path: str) -> TemplateSlots:
    presentation = Presentation(pptx_path)
    slots: list[TextSlot] = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        for shape in slide.shapes:
            slots.extend(_extract_shape_slots(shape, slide_number, parent_id=None))
        notes_text = _extract_notes_text(slide)
        if notes_text:
            slots.append(
                _make_slot(
                    slide_index=slide_number,
                    shape_id=f"slide-{slide_number}:notes",
                    kind="notes",
                    text=notes_text,
                    shape=None,
                )
            )

    return TemplateSlots(slide_count=len(presentation.slides), slots=slots)


def _extract_shape_slots(shape: Any, slide_index: int, parent_id: str | None) -> list[TextSlot]:
    shape_id = _shape_id(shape, parent_id)

    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        slots: list[TextSlot] = []
        for child in shape.shapes:
            slots.extend(_extract_shape_slots(child, slide_index, shape_id))
        return slots

    if getattr(shape, "has_table", False):
        return _extract_table_slots(shape, slide_index, shape_id)

    if not getattr(shape, "has_text_frame", False):
        return []

    text = _normalize_text(shape.text_frame.text)
    if not text:
        return []

    kind = "placeholder" if getattr(shape, "is_placeholder", False) else "text_box"
    return [_make_slot(slide_index, shape_id, kind, text, shape)]


def _extract_table_slots(shape: Any, slide_index: int, shape_id: str) -> list[TextSlot]:
    slots: list[TextSlot] = []
    for row_index, row in enumerate(shape.table.rows):
        for col_index, cell in enumerate(row.cells):
            text = _normalize_text(cell.text)
            if not text:
                continue
            slots.append(
                _make_slot(
                    slide_index=slide_index,
                    shape_id=f"{shape_id}:r{row_index}:c{col_index}",
                    kind="table_cell",
                    text=text,
                    shape=shape,
                )
            )
    return slots


def _make_slot(
    slide_index: int,
    shape_id: str,
    kind: str,
    text: str,
    shape: Any | None,
) -> TextSlot:
    char_count = len(text)
    locked = _looks_fixed(text, shape)
    return TextSlot(
        slide_index=slide_index,
        shape_id=shape_id,
        kind=kind,
        original_text=text,
        char_count=char_count,
        max_char_count=max(char_count, int(char_count * 1.3), 20),
        bounds=_bounds(shape),
        style_ref=_style_ref(shape),
        value_type="fixed" if locked else "unknown",
        locked=locked,
    )


def _shape_id(shape: Any, parent_id: str | None) -> str:
    current = str(getattr(shape, "shape_id", "unknown"))
    return f"{parent_id}/{current}" if parent_id else current


def _bounds(shape: Any | None) -> dict[str, int | None]:
    if shape is None:
        return {"x": None, "y": None, "w": None, "h": None}
    return {
        "x": int(shape.left),
        "y": int(shape.top),
        "w": int(shape.width),
        "h": int(shape.height),
    }


def _style_ref(shape: Any | None) -> dict[str, str | int | None]:
    if shape is None or not getattr(shape, "has_text_frame", False):
        return {}

    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            font = run.font
            return {
                "font_name": font.name,
                "font_size": int(font.size) if font.size else None,
                "bold": str(font.bold) if font.bold is not None else None,
                "italic": str(font.italic) if font.italic is not None else None,
            }
    return {}


def _extract_notes_text(slide: Any) -> str:
    try:
        notes_slide = slide.notes_slide
    except (AttributeError, KeyError):
        return ""
    text_frame = getattr(notes_slide, "notes_text_frame", None)
    if text_frame is None:
        return ""
    return _normalize_text(text_frame.text)


def _normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r", "\n").split("\n")).strip()


def _looks_fixed(text: str, shape: Any | None) -> bool:
    compact = text.strip()
    lowered = compact.lower()
    if not compact:
        return True
    if compact.isdigit() and len(compact) <= 3:
        return True
    if lowered in {"page", "footer"}:
        return True
    if "copyright" in lowered or "confidential" in lowered:
        return True
    if shape is not None and getattr(shape, "top", 0) > 6_500_000 and len(compact) <= 20:
        return True
    return False
