from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


@dataclass(frozen=True)
class TextReplacement:
    slide_index: int
    shape_id: str
    text: str


@dataclass(frozen=True)
class ApplyTextReport:
    applied: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


def apply_text_replacements(
    template_path: Path,
    output_path: Path,
    replacements: list[TextReplacement],
) -> ApplyTextReport:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, output_path)

    presentation = Presentation(str(output_path))
    by_slide = _group_replacements(replacements)
    applied: list[str] = []
    skipped: list[dict[str, str]] = []

    for slide_index, slide_replacements in by_slide.items():
        if slide_index < 1 or slide_index > len(presentation.slides):
            for replacement in slide_replacements:
                skipped.append(
                    {
                        "shape_id": replacement.shape_id,
                        "reason": "slide_not_found",
                    }
                )
            continue

        slide = presentation.slides[slide_index - 1]
        for replacement in slide_replacements:
            if replacement.shape_id.endswith(":notes"):
                skipped.append({"shape_id": replacement.shape_id, "reason": "notes_not_supported"})
                continue

            target = _find_text_target(slide.shapes, replacement.shape_id)
            if target is None:
                skipped.append({"shape_id": replacement.shape_id, "reason": "shape_not_found"})
                continue

            _replace_text(target, replacement.text)
            applied.append(replacement.shape_id)

    presentation.save(str(output_path))
    return ApplyTextReport(applied=applied, skipped=skipped)


def _group_replacements(
    replacements: list[TextReplacement],
) -> dict[int, list[TextReplacement]]:
    grouped: dict[int, list[TextReplacement]] = {}
    for replacement in replacements:
        grouped.setdefault(replacement.slide_index, []).append(replacement)
    return grouped


def _find_text_target(shapes: Any, shape_id: str) -> Any | None:
    if ":r" in shape_id and ":c" in shape_id:
        shape_part, cell_part = shape_id.split(":r", 1)
        row_part, col_part = cell_part.split(":c", 1)
        shape = _find_shape(shapes, shape_part)
        if shape is None or not getattr(shape, "has_table", False):
            return None
        return shape.table.cell(int(row_part), int(col_part))
    return _find_shape(shapes, shape_id)


def _find_shape(shapes: Any, shape_id: str) -> Any | None:
    parts = shape_id.split("/")
    current_shapes = shapes
    current_shape: Any | None = None
    for part in parts:
        current_shape = None
        for shape in current_shapes:
            if str(getattr(shape, "shape_id", "")) == part:
                current_shape = shape
                break
        if current_shape is None:
            return None
        if part != parts[-1]:
            if current_shape.shape_type != MSO_SHAPE_TYPE.GROUP:
                return None
            current_shapes = current_shape.shapes
    return current_shape


def _replace_text(target: Any, text: str) -> None:
    text_frame = target.text_frame
    paragraphs = text_frame.paragraphs
    first_paragraph = paragraphs[0] if paragraphs else text_frame.add_paragraph()
    first_run = first_paragraph.runs[0] if first_paragraph.runs else first_paragraph.add_run()
    first_run.text = text

    for run in first_paragraph.runs[1:]:
        run.text = ""
    for paragraph in paragraphs[1:]:
        for run in paragraph.runs:
            run.text = ""
