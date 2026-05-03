"""FastAPI dependency injection functions.

Provides reusable dependencies for the API layer:

- ``get_db_session`` — yields a SQLAlchemy session and closes it after the request
- ``get_registry_dep`` — returns the process-global ``DatasetRegistry``
- ``get_pagination`` — parses and validates ``?limit=...&offset=...`` query params
- ``limiter`` — the project-wide ``slowapi.Limiter`` used by per-route decorators
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from govlink.core.registry import DatasetRegistry, get_registry
from govlink.core.schemas import PaginationParams
from govlink.db import get_session


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session; close it when the request finishes."""
    yield from get_session()


def get_registry_dep() -> DatasetRegistry:
    """Return the process-global dataset registry."""
    return get_registry()


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginationParams:
    """Parse and validate pagination query parameters."""
    return PaginationParams(limit=limit, offset=offset)


# Project-wide rate limiter. Per-route ``@limiter.limit("60/minute")`` decorators
# opt routes into rate limiting; meta endpoints (``/``, ``/health``, ``/admin/*``)
# are intentionally not decorated and remain unlimited.
limiter = Limiter(key_func=get_remote_address)
