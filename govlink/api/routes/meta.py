"""Meta routes — root and health endpoints.

These are intentionally NOT rate-limited so monitoring scrapers and
load-balancer probes don't trip the limiter.
"""

from __future__ import annotations

from fastapi import APIRouter

from govlink import __version__

router = APIRouter(tags=["meta"])


@router.get("/")
async def root() -> dict[str, str]:
    """Return basic service info — name, version, and docs URL."""
    return {"name": "govlink", "version": __version__, "docs": "/docs"}


@router.get("/health")
async def health() -> dict[str, str]:
    """Health probe — always returns ``{"status": "ok"}`` if the app is up."""
    return {"status": "ok"}
