"""Tests for govlink.main — FastAPI application factory."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from govlink import __version__
from govlink.core.registry import DatasetRegistry


def test_create_app_returns_fastapi_instance() -> None:
    from govlink.main import create_app

    app = create_app()
    assert isinstance(app, FastAPI)


def test_app_has_correct_title_and_version() -> None:
    from govlink.main import create_app

    app = create_app()
    assert app.title == "govlink"
    assert app.version == __version__


def test_app_includes_cors_middleware() -> None:
    """CORS middleware is in the app's middleware stack."""
    from govlink.main import create_app

    app = create_app()
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middleware_classes


def test_app_registers_all_routers(app: FastAPI) -> None:
    """Routes for /, /health, /datasets, /admin/health are all present."""
    paths = {route.path for route in app.routes if hasattr(route, "path")}  # type: ignore[attr-defined]
    assert "/" in paths
    assert "/health" in paths
    assert "/datasets" in paths
    assert "/admin/health" in paths


@pytest.mark.asyncio
async def test_app_lifespan_calls_auto_discover(
    client: httpx.AsyncClient,
    isolated_global_registry: DatasetRegistry,
) -> None:
    """After app startup, the dataset registry contains the discovered datasets."""
    # The first request triggers the lifespan startup via ASGITransport.
    response = await client.get("/health")
    assert response.status_code == 200
    assert "exchange-rates" in isolated_global_registry


@pytest.mark.asyncio
async def test_app_lifespan_calls_init_db(client: httpx.AsyncClient) -> None:
    """After startup, the DB engine is initialised and reachable."""
    response = await client.get("/health")
    assert response.status_code == 200
    # Engine accessible (no exception means init_db ran successfully).
    from govlink.db import get_engine

    engine = get_engine()
    assert engine is not None


@pytest.mark.asyncio
async def test_dataset_not_found_global_handler() -> None:
    """An uncaught ``DatasetNotFoundError`` is rendered as a 404 with our envelope."""
    from starlette.requests import Request

    from govlink.core.registry import DatasetNotFoundError
    from govlink.main import create_app

    app: FastAPI = create_app()
    handler = app.exception_handlers[DatasetNotFoundError]
    fake_req = Request({"type": "http", "method": "GET", "headers": [], "path": "/x"})
    response = await handler(fake_req, DatasetNotFoundError("missing-slug"))
    assert response.status_code == 404
    import json

    body = json.loads(response.body)
    assert body["error"]["code"] == "dataset_not_found"
    assert "missing-slug" in body["error"]["message"]


@pytest.mark.asyncio
async def test_rate_limit_global_handler() -> None:
    """A ``RateLimitExceeded`` is rendered as a 429 with our envelope."""
    from slowapi.errors import RateLimitExceeded
    from starlette.requests import Request

    from govlink.main import create_app

    app: FastAPI = create_app()
    handler = app.exception_handlers[RateLimitExceeded]
    fake_req = Request({"type": "http", "method": "GET", "headers": [], "path": "/x"})

    # Construct a minimal RateLimitExceeded — slowapi's signature requires a
    # Limit-like object, so we use a lightweight stand-in.
    class _FakeLimit:
        error_message = "60 per 1 minute"

    exc = RateLimitExceeded(_FakeLimit())  # type: ignore[arg-type]
    response = await handler(fake_req, exc)
    assert response.status_code == 429
    import json

    body = json.loads(response.body)
    assert body["error"]["code"] == "rate_limit_exceeded"
