"""Admin and monitoring endpoints — intentionally NOT rate-limited.

Monitoring scrapers (Prometheus, uptime checkers, load balancers) poll
these endpoints frequently. Putting them under the rate limiter would
generate false alerts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from govlink.api.deps import get_db_session, get_registry_dep
from govlink.core.models import Dataset
from govlink.core.registry import DatasetRegistry

router = APIRouter(prefix="/admin", tags=["admin"])

# Per-frequency staleness thresholds, with a small grace window over the
# nominal cadence to absorb publication delays.
_STALENESS_HOURS: dict[str, int] = {
    "daily": 26,
    "weekly": 170,
    "monthly": 745,
    "quarterly": 2208,
    "annual": 8784,
    "irregular": 8784,
}
_DEFAULT_STALENESS_HOURS = 48


def _is_stale(last_ingested_at: datetime | None, frequency: str) -> bool:
    if last_ingested_at is None:
        return True
    # SQLite strips tzinfo on read-back; the value was written as UTC.
    if last_ingested_at.tzinfo is None:
        last_ingested_at = last_ingested_at.replace(tzinfo=UTC)
    threshold = timedelta(hours=_STALENESS_HOURS.get(frequency, _DEFAULT_STALENESS_HOURS))
    return (datetime.now(UTC) - last_ingested_at) > threshold


@router.get("/health")
async def admin_health(
    registry: Annotated[DatasetRegistry, Depends(get_registry_dep)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    """Per-dataset freshness report."""
    items: list[dict[str, Any]] = []
    for definition in registry.list_all():
        ds_row = session.execute(
            select(Dataset).where(Dataset.slug == definition.slug)
        ).scalar_one_or_none()
        last_ingested = ds_row.last_ingested_at if ds_row else None

        latest_snapshot = None
        model = definition.model_class
        if hasattr(model, "snapshot_date"):
            latest_snapshot = session.execute(select(func.max(model.snapshot_date))).scalar()

        items.append(
            {
                "slug": definition.slug,
                "frequency": definition.frequency.value,
                "last_ingested_at": (
                    last_ingested.isoformat() if last_ingested is not None else None
                ),
                "latest_snapshot_date": (
                    latest_snapshot.isoformat() if latest_snapshot is not None else None
                ),
                "is_stale": _is_stale(last_ingested, definition.frequency.value),
            }
        )
    return {"datasets": items, "count": len(items)}
