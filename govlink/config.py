"""Application configuration via pydantic-settings.

Loads environment variables (prefixed with ``GOVLINK_``) into a typed
``Settings`` object. Provides database URL, log level, rate limits,
CORS origins, and raw data directory.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_VALID_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})


class Settings(BaseSettings):
    """Typed application settings sourced from env vars and ``.env``."""

    model_config = SettingsConfigDict(
        env_prefix="GOVLINK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    database_url: str | None = None
    raw_data_dir: Path = Path("./data/raw")
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    rate_limit_per_minute: int = Field(default=60, gt=0)
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("log_level must be a string")
        upper = v.upper()
        if upper not in _VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level {v!r}; must be one of {sorted(_VALID_LOG_LEVELS)}")
        return upper

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def _resolve_database_url(self) -> Settings:
        if self.database_url is None:
            if self.env == "production":
                raise ValueError("GOVLINK_DATABASE_URL is required when GOVLINK_ENV=production")
            self.database_url = "sqlite:///./govlink.db"
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide ``Settings`` instance.

    Cached via ``functools.lru_cache``; tests must call
    ``get_settings.cache_clear()`` between mutations of ``GOVLINK_*``
    env vars (the ``settings_env`` fixture in ``conftest.py`` does this).
    """
    return Settings()
