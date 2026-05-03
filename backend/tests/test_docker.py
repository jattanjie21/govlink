"""Configuration-only tests for Docker assets.

These tests do NOT require Docker to be running. They validate that the
Dockerfile, docker-compose, dockerignore, and env template files are
internally consistent and reference the right ports/services/volumes.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
COMPOSE = REPO_ROOT / "docker-compose.yml"
ENV_DOCKER = REPO_ROOT / ".env.docker"


def test_dockerfile_exists_and_is_valid() -> None:
    """Dockerfile uses our pinned base image, exposes 8000, runs as non-root."""
    assert DOCKERFILE.exists(), "Dockerfile is missing"
    text = DOCKERFILE.read_text()
    assert "FROM python:3.12-slim" in text
    assert "EXPOSE 8000" in text
    assert "HEALTHCHECK" in text
    assert "USER govlink" in text
    assert "uvicorn" in text


def test_dockerignore_excludes_expected_paths() -> None:
    assert DOCKERIGNORE.exists()
    text = DOCKERIGNORE.read_text()
    for pattern in (".git", "tests/", ".env", "*.db"):
        assert pattern in text, f"missing exclusion: {pattern!r}"


def _load_compose() -> dict[str, object]:
    return yaml.safe_load(COMPOSE.read_text())


def test_docker_compose_has_required_services() -> None:
    cfg = _load_compose()
    services = cfg["services"]  # type: ignore[index]
    assert isinstance(services, dict)
    assert {"db", "migrate", "api"} <= set(services.keys())


def test_docker_compose_migrate_depends_on_db() -> None:
    cfg = _load_compose()
    migrate = cfg["services"]["migrate"]  # type: ignore[index]
    deps = migrate["depends_on"]
    assert "db" in deps
    assert deps["db"]["condition"] == "service_healthy"


def test_docker_compose_api_depends_on_migrate() -> None:
    cfg = _load_compose()
    api = cfg["services"]["api"]  # type: ignore[index]
    deps = api["depends_on"]
    assert "migrate" in deps
    assert deps["migrate"]["condition"] == "service_completed_successfully"


def test_docker_compose_api_exposes_port_8000() -> None:
    cfg = _load_compose()
    api = cfg["services"]["api"]  # type: ignore[index]
    ports = api["ports"]
    assert any(":8000" in str(p) for p in ports)


def test_docker_compose_volumes() -> None:
    cfg = _load_compose()
    volumes = cfg["volumes"]  # type: ignore[index]
    assert "pgdata" in volumes
    assert "rawdata" in volumes


def test_env_docker_exists() -> None:
    """The .env.docker template is committed (dev defaults only)."""
    assert ENV_DOCKER.exists()
    text = ENV_DOCKER.read_text()
    assert "POSTGRES_PASSWORD" in text
    assert "API_PORT" in text


def test_dockerfile_runs_as_non_root() -> None:
    """The runtime stage drops to a dedicated user, never runs as root."""
    text = DOCKERFILE.read_text()
    # The 'USER govlink' line must come BEFORE the CMD.
    user_idx = text.find("USER govlink")
    cmd_idx = text.find("CMD")
    assert user_idx > 0
    assert cmd_idx > user_idx, "USER directive must appear before CMD"


def test_docker_compose_has_named_postgres_image() -> None:
    cfg = _load_compose()
    db = cfg["services"]["db"]  # type: ignore[index]
    assert db["image"].startswith("postgres:")


def test_docker_compose_uses_psycopg_driver_url() -> None:
    """The DATABASE_URL uses ``postgresql+psycopg://`` (psycopg3, not psycopg2)."""
    cfg = _load_compose()
    api_env = cfg["services"]["api"]["environment"]  # type: ignore[index]
    assert "postgresql+psycopg://" in api_env["GOVLINK_DATABASE_URL"]
