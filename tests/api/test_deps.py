"""Tests for govlink.api.deps — FastAPI dependencies."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy.orm import Session

from govlink.api.deps import (
    get_db_session,
    get_pagination,
    get_registry_dep,
    limiter,
)
from govlink.core.registry import DatasetRegistry
from govlink.core.schemas import PaginationParams


def test_get_db_session_yields_session(initialized_db: Session) -> None:
    """``get_db_session`` is a generator dependency yielding a usable Session."""
    gen = get_db_session()
    session = next(gen)
    assert isinstance(session, Session)
    # Session should close cleanly when generator exhausts.
    with pytest.raises(StopIteration):
        gen.send(None)


def test_get_registry_dep_returns_registry(
    isolated_global_registry: DatasetRegistry,
) -> None:
    """``get_registry_dep`` returns the process-global registry."""
    result = get_registry_dep()
    assert result is isolated_global_registry


def test_get_pagination_parses_query_params() -> None:
    """``get_pagination`` produces a ``PaginationParams`` from explicit args."""
    p = get_pagination(limit=50, offset=10)
    assert isinstance(p, PaginationParams)
    assert p.limit == 50
    assert p.offset == 10


def test_get_pagination_uses_defaults() -> None:
    """``get_pagination`` defaults to limit=100, offset=0."""
    p = get_pagination()
    assert p.limit == 100
    assert p.offset == 0


@pytest.mark.asyncio
async def test_get_pagination_rejects_invalid_limit(client: httpx.AsyncClient) -> None:
    """A request with limit beyond the allowed bounds returns 422."""
    response = await client.get("/datasets/exchange-rates/historical?limit=5000")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit(client: httpx.AsyncClient) -> None:
    """A handful of requests well under the 60/minute limit all succeed."""
    for _ in range(3):
        response = await client.get("/datasets")
        assert response.status_code == 200


def test_limiter_is_a_slowapi_limiter() -> None:
    """The shared ``limiter`` is an instance of ``slowapi.Limiter``."""
    from slowapi import Limiter

    assert isinstance(limiter, Limiter)
