"""Tests for govlink.api.routes.meta — root and health endpoints."""

from __future__ import annotations

import httpx
import pytest

from govlink import __version__


@pytest.mark.asyncio
async def test_root_returns_service_info(client: httpx.AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body == {"name": "govlink", "version": __version__, "docs": "/docs"}


@pytest.mark.asyncio
async def test_health_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root_is_not_rate_limited(client: httpx.AsyncClient) -> None:
    """Hammering ``/`` past the per-minute budget never returns 429."""
    for _ in range(120):
        response = await client.get("/")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_is_not_rate_limited(client: httpx.AsyncClient) -> None:
    for _ in range(120):
        response = await client.get("/health")
        assert response.status_code == 200
