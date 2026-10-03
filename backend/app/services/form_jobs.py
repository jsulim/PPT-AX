from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HwpxFormJob:
    job_id: str
    created_at: str
    source_filename: str
    original_filename: str
    output_filename: str
    download_url: str
    filled: list[str]
    missing: list[dict[str, str]]
    skipped: list[dict[str, str]]
    mappings: list[dict[str, Any]]
    trim_applied: bool

    @property
    def filled_count(self) -> int:
        return len(self.filled)

    @property
    def missing_count(self) -> int:
        return len(self.missing)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def write_hwpx_form_job(jobs_dir: Path, job: HwpxFormJob) -> Path:
    form_jobs_dir = _form_jobs_dir(jobs_dir)
    form_jobs_dir.mkdir(parents=True, exist_ok=True)
    job_path = form_jobs_dir / f"{job.job_id}.json"
    job_path.write_text(
        json.dumps(asdict(job), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return job_path


def read_hwpx_form_job(jobs_dir: Path, job_id: str) -> HwpxFormJob | None:
    if "/" in job_id or "\\" in job_id or not job_id:
        return None
    job_path = _form_jobs_dir(jobs_dir) / f"{job_id}.json"
    if not job_path.exists():
        return None
    data = json.loads(job_path.read_text(encoding="utf-8"))
    return HwpxFormJob(**data)


def list_hwpx_form_jobs(jobs_dir: Path, limit: int = 50) -> list[HwpxFormJob]:
    form_jobs_dir = _form_jobs_dir(jobs_dir)
    if not form_jobs_dir.exists():
        return []
    jobs: list[HwpxFormJob] = []
    for job_path in sorted(form_jobs_dir.glob("*.json"), key=_mtime, reverse=True):
        if len(jobs) >= limit:
            break
        try:
            data = json.loads(job_path.read_text(encoding="utf-8"))
            jobs.append(HwpxFormJob(**data))
        except (OSError, TypeError, ValueError):
            continue
    return jobs


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _form_jobs_dir(jobs_dir: Path) -> Path:
    return jobs_dir / "forms"


def _mtime(path: Path) -> float:
    return path.stat().st_mtime
