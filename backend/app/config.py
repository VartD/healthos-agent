from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            _PROJECT_ROOT / ".env",
            _BACKEND_ROOT / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg2://healthos:healthos@localhost:5432/healthos"


settings = Settings()
