"""FastAPI application factory.

Use ``create_app()`` (not a module-level ``app`` instance) so tests can
build fresh app instances per test with their own dependency overrides.
The lifespan handles startup-time initialisation: database engine + the
dataset registry's auto-discovery.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from govlink import __version__
from govlink.api.deps import limiter
from govlink.api.routes import admin, datasets, meta
from govlink.config import get_settings
from govlink.core.registry import DatasetNotFoundError, get_registry
from govlink.core.schemas import ErrorDetail, ErrorResponse
from govlink.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup: initialise the DB engine and discover all dataset plugins."""
    init_db()
    get_registry().auto_discover()
    yield


def create_app() -> FastAPI:
    """Build a configured :class:`FastAPI` instance ready to serve requests."""
    settings = get_settings()

    app = FastAPI(
        title="govlink",
        description="Open data API for Gambian government datasets.",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiter wiring — per-route ``@limiter.limit(...)`` decorators
    # opt routes into the limit. Meta and admin routes are intentionally
    # unrate-limited.
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(_req: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="rate_limit_exceeded",
                    message=f"Rate limit exceeded: {exc.detail}",
                )
            ).model_dump(mode="json"),
        )

    @app.exception_handler(DatasetNotFoundError)
    async def _dataset_not_found_handler(_req: Request, exc: DatasetNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="dataset_not_found",
                    message=str(exc),
                )
            ).model_dump(mode="json"),
        )

    app.include_router(meta.router)
    app.include_router(datasets.router)
    app.include_router(admin.router)

    return app


# Backwards-compatible accessor: some tooling expects a callable named ``app``.
def app() -> FastAPI:  # pragma: no cover — convenience wrapper for `uvicorn ... --factory`
    return create_app()


__all__: list[Any] = ["app", "create_app", "lifespan"]
