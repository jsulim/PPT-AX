from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PPT AX"
    environment: str = "local"
    source: str = "local"
    ai_enabled: bool = False

    database_url: str = "postgresql+psycopg://ppt_ax:change-me@db:5432/ppt_ax"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    data_dir: Path = Path("/data")

    backend_cors_origins_raw: str = Field(
        default="http://localhost:3000",
        validation_alias="BACKEND_CORS_ORIGINS",
    )
    admin_emails_raw: str = Field(default="", validation_alias="ADMIN_EMAILS")

    @property
    def backend_cors_origins(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins_raw.split(",") if item.strip()]

    @property
    def admin_emails(self) -> list[str]:
        return [item.strip() for item in self.admin_emails_raw.split(",") if item.strip()]

    @property
    def originals_dir(self) -> Path:
        return self.data_dir / "originals"

    @property
    def thumbs_dir(self) -> Path:
        return self.data_dir / "thumbs"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
