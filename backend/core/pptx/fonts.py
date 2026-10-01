from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pptx import Presentation


def extract_pptx_fonts(pptx_path: str | Path) -> list[str]:
    presentation = Presentation(str(pptx_path))
    fonts: set[str] = set()

    for slide in presentation.slides:
        for shape in _walk_shapes(slide.shapes):
            if not getattr(shape, "has_text_frame", False):
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if run.font.name:
                        fonts.add(run.font.name)

    return sorted(fonts)


def list_installed_fonts(font_dir: str | Path = "/usr/share/fonts/company") -> list[str]:
    path = Path(font_dir)
    if not path.exists():
        return []
    result = subprocess.run(
        ["fc-list", str(path), "family"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    names: set[str] = set()
    for line in result.stdout.splitlines():
        for name in line.split(","):
            clean_name = name.strip()
            if clean_name:
                names.add(clean_name)
    return sorted(names)


def compare_fonts(
    pptx_path: str | Path,
    font_dir: str | Path = "/usr/share/fonts/company",
) -> tuple[list[str], list[str]]:
    used = extract_pptx_fonts(pptx_path)
    installed = set(list_installed_fonts(font_dir))
    missing = [font for font in used if font not in installed]
    return used, missing


def _walk_shapes(shapes: Any) -> list[Any]:
    collected: list[Any] = []
    for shape in shapes:
        if getattr(shape, "shape_type", None) == 6 and hasattr(shape, "shapes"):
            collected.extend(_walk_shapes(shape.shapes))
        else:
            collected.append(shape)
    return collected
