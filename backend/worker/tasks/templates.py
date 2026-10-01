from __future__ import annotations

import uuid

from app.services.templates import analyze_template
from app.settings import get_settings
from db.session import SessionLocal
from worker.celery_app import celery_app


@celery_app.task(name="worker.tasks.templates.analyze_template")
def analyze_template_task(template_id: str) -> str:
    settings = get_settings()
    with SessionLocal() as db:
        analyze_template(db, uuid.UUID(template_id), settings)
    return template_id
