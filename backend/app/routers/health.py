from fastapi import APIRouter

from app.schemas.health import ComponentHealth, FontHealth, HealthResponse
from app.services.health import check_database, check_redis, check_worker, list_company_fonts

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    checks = {
        "db": check_database(),
        "redis": check_redis(),
        "worker": check_worker(),
    }
    status = "ok" if all(item.ok for item in checks.values()) else "degraded"
    return HealthResponse(status=status, components=checks)


@router.get("/health/fonts", response_model=FontHealth)
def health_fonts() -> FontHealth:
    result = list_company_fonts()
    return FontHealth(
        status="ok" if result.ok else "degraded",
        worker=ComponentHealth(ok=result.ok, detail=result.detail),
        fonts=result.fonts,
    )
