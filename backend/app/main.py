from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.decks import router as decks_router
from app.routers.forms import router as forms_router
from app.routers.health import router as health_router
from app.routers.integrations import router as integrations_router
from app.routers.templates import router as templates_router
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_origin_regex=settings.backend_cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(templates_router)
    app.include_router(integrations_router)
    app.include_router(decks_router)
    app.include_router(forms_router)
    return app


app = create_app()
