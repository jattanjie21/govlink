"""Tests for govlink.config — Settings via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from govlink.config import Settings, get_settings


def test_settings_loads_defaults_when_env_empty(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """Settings must instantiate with sensible defaults when no env vars are set."""
    for key in [
        "GOVLINK_ENV",
        "GOVLINK_LOG_LEVEL",
        "GOVLINK_DATABASE_URL",
        "GOVLINK_RAW_DATA_DIR",
        "GOVLINK_API_HOST",
        "GOVLINK_API_PORT",
        "GOVLINK_RATE_LIMIT_PER_MINUTE",
        "GOVLINK_CORS_ORIGINS",
    ]:
        settings_env.delenv(key, raising=False)

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.env == "development"
    assert s.log_level == "INFO"
    assert s.database_url == "sqlite:///./govlink.db"
    assert s.api_host == "0.0.0.0"
    assert s.api_port == 8000
    assert s.rate_limit_per_minute == 60
    assert s.cors_origins == ["*"]


def test_settings_reads_govlink_prefixed_env_vars(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """The ``GOVLINK_`` prefix must be stripped when reading env vars."""
    settings_env.setenv("GOVLINK_DATABASE_URL", "sqlite:///./custom.db")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.database_url == "sqlite:///./custom.db"


def test_settings_validates_env_choices(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """``GOVLINK_ENV`` only accepts ``development`` or ``production``."""
    settings_env.setenv("GOVLINK_ENV", "staging")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_database_url_required_no_default_for_production(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """In production, missing ``GOVLINK_DATABASE_URL`` must raise."""
    settings_env.setenv("GOVLINK_ENV", "production")
    settings_env.delenv("GOVLINK_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_cors_origins_parses_comma_separated_string(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """A comma-separated env value must be parsed into a list of trimmed strings."""
    settings_env.setenv("GOVLINK_CORS_ORIGINS", "http://a.com, http://b.com ,http://c.com")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.cors_origins == ["http://a.com", "http://b.com", "http://c.com"]


def test_settings_cors_origins_handles_wildcard(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """The wildcard ``*`` must be preserved as a single-element list."""
    settings_env.setenv("GOVLINK_CORS_ORIGINS", "*")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.cors_origins == ["*"]


def test_settings_rate_limit_must_be_positive(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """``rate_limit_per_minute`` must reject zero and negative values."""
    settings_env.setenv("GOVLINK_RATE_LIMIT_PER_MINUTE", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
    settings_env.setenv("GOVLINK_RATE_LIMIT_PER_MINUTE", "-5")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_raw_data_dir_is_path_object(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """``raw_data_dir`` must be exposed as a ``pathlib.Path``."""
    settings_env.setenv("GOVLINK_RAW_DATA_DIR", "/tmp/custom-data")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert isinstance(s.raw_data_dir, Path)
    assert s.raw_data_dir == Path("/tmp/custom-data")


def test_settings_log_level_validated(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """``log_level`` must reject values outside the standard set."""
    settings_env.setenv("GOVLINK_LOG_LEVEL", "TRACE")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_log_level_accepts_lowercase(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """``log_level`` is normalised to uppercase."""
    settings_env.setenv("GOVLINK_LOG_LEVEL", "debug")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.log_level == "DEBUG"


def test_settings_api_port_range(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """``api_port`` is constrained to the valid TCP range."""
    settings_env.setenv("GOVLINK_API_PORT", "70000")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
    settings_env.setenv("GOVLINK_API_PORT", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_log_level_must_be_string() -> None:
    """A non-string ``log_level`` value must raise ValidationError.

    Pydantic strict-mode wouldn't catch this since the type annotation is
    ``str``; the explicit ``isinstance`` check inside the validator does.
    """
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level=123)  # type: ignore[arg-type]


def test_get_settings_is_cached(
    settings_env: pytest.MonkeyPatch,
) -> None:
    """``get_settings`` returns the same instance on repeated calls (lru_cache)."""
    settings_env.setenv("GOVLINK_DATABASE_URL", "sqlite:///./first.db")
    a = get_settings()
    settings_env.setenv("GOVLINK_DATABASE_URL", "sqlite:///./second.db")
    b = get_settings()
    assert a is b
    assert a.database_url == "sqlite:///./first.db"
