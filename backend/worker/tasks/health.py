import subprocess
from pathlib import Path

from worker.celery_app import celery_app

COMPANY_FONT_DIR = Path("/usr/share/fonts/company")


@celery_app.task(name="worker.tasks.health.list_company_fonts")
def list_company_fonts() -> dict[str, list[str]]:
    if not COMPANY_FONT_DIR.exists():
        return {"fonts": []}

    completed = subprocess.run(
        ["fc-list", str(COMPANY_FONT_DIR), "family"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        return {"fonts": []}

    fonts = sorted(
        {
            line.strip().split(",", maxsplit=1)[0]
            for line in completed.stdout.splitlines()
            if line.strip()
        }
    )
    return {"fonts": fonts}
