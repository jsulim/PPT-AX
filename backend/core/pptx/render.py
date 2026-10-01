from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderedSlide:
    slide_index: int
    thumb_path: Path
    preview_path: Path


def render_pptx(
    pptx_path: str | Path,
    output_dir: str | Path,
    *,
    timeout_seconds: int = 120,
) -> list[RenderedSlide]:
    source = Path(pptx_path)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp_dir = Path(tmp_name)
        working_pptx = tmp_dir / source.name
        shutil.copy2(source, working_pptx)

        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_dir),
                str(working_pptx),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        pdf_path = working_pptx.with_suffix(".pdf")
        if not pdf_path.exists():
            raise RuntimeError("LibreOffice가 PDF를 만들지 못했습니다.")

        preview_prefix = destination / "preview"
        thumb_prefix = destination / "thumb"
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-scale-to-x",
                "1600",
                "-scale-to-y",
                "-1",
                str(pdf_path),
                str(preview_prefix),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-scale-to-x",
                "480",
                "-scale-to-y",
                "-1",
                str(pdf_path),
                str(thumb_prefix),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

    rendered: list[RenderedSlide] = []
    for preview_path in sorted(destination.glob("preview-*.png")):
        suffix = preview_path.stem.split("-")[-1]
        slide_index = int(suffix)
        thumb_path = destination / f"thumb-{suffix}.png"
        if thumb_path.exists():
            rendered.append(
                RenderedSlide(
                    slide_index=slide_index,
                    thumb_path=thumb_path,
                    preview_path=preview_path,
                )
            )
    return rendered
