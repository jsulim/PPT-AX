from app.settings import Settings


def test_settings_parses_csv_values() -> None:
    settings = Settings(BACKEND_CORS_ORIGINS="http://localhost:3000, http://127.0.0.1:3000")

    assert settings.backend_cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]
