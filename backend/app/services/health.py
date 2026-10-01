from dataclasses import dataclass
from typing import Any

from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.health import ComponentHealth
from app.settings import get_settings
from db.session import engine
from worker.celery_app import celery_app


@dataclass(frozen=True)
class FontTaskResult:
    ok: bool
    detail: str
    fonts: list[str]


def check_database() -> ComponentHealth:
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
    except SQLAlchemyError as exc:
        return ComponentHealth(ok=False, detail=f"DB 연결에 실패했습니다: {exc.__class__.__name__}")
    return ComponentHealth(ok=True, detail="DB 연결이 정상입니다.")


def check_redis() -> ComponentHealth:
    settings = get_settings()
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(
            ok=False,
            detail=f"Redis 연결에 실패했습니다: {exc.__class__.__name__}",
        )
    return ComponentHealth(ok=True, detail="Redis 연결이 정상입니다.")


def check_worker() -> ComponentHealth:
    try:
        replies: list[dict[str, Any]] | None = celery_app.control.ping(timeout=1)
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(
            ok=False,
            detail=f"작업자 확인에 실패했습니다: {exc.__class__.__name__}",
        )
    if not replies:
        return ComponentHealth(ok=False, detail="응답한 작업자가 없습니다.")
    return ComponentHealth(ok=True, detail=f"작업자 {len(replies)}개가 응답했습니다.")


def list_company_fonts() -> FontTaskResult:
    try:
        async_result = celery_app.send_task("worker.tasks.health.list_company_fonts")
        payload = async_result.get(timeout=3)
    except Exception as exc:  # noqa: BLE001
        return FontTaskResult(
            ok=False,
            detail=f"작업자에서 폰트 목록을 가져오지 못했습니다: {exc.__class__.__name__}",
            fonts=[],
        )
    fonts = payload.get("fonts", []) if isinstance(payload, dict) else []
    return FontTaskResult(ok=True, detail="폰트 목록을 확인했습니다.", fonts=fonts)
