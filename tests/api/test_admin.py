"""Tests for govlink.api.routes.admin — operational endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.orm import Session

from govlink.core.models import Dataset, DatasetFrequency


def _seed_dataset_row(db_session: Session, last_ingested: datetime | None = None) -> Dataset:
    ds = Dataset(
        slug="exchange-rates",
        title="Daily Valuation Exchange Rates",
        publisher="Central Bank of The Gambia",
        source_url="https://www.cbg.gm/daily-valuation-exchange-rate",
        frequency=DatasetFrequency.DAILY,
        last_ingested_at=last_ingested,
    )
    db_session.add(ds)
    db_session.commit()
    return ds


@pytest.mark.asyncio
async def test_admin_health_returns_per_dataset_status(
    client: httpx.AsyncClient,
    db_session: Session,
) -> None:
    """Returns a list of datasets with slug, last_ingested_at, latest_snapshot_date, is_stale."""
    _seed_dataset_row(db_session, last_ingested=datetime.now(UTC) - timedelta(hours=1))
    response = await client.get("/admin/health")
    assert response.status_code == 200
    body = response.json()
    assert "datasets" in body
    assert body["count"] == 1
    item = body["datasets"][0]
    assert item["slug"] == "exchange-rates"
    assert "last_ingested_at" in item
    assert "latest_snapshot_date" in item
    assert "is_stale" in item


@pytest.mark.asyncio
async def test_admin_health_shows_never_ingested(
    client: httpx.AsyncClient,
) -> None:
    """A dataset with no Dataset row at all shows null + is_stale=True."""
    response = await client.get("/admin/health")
    body = response.json()
    item = body["datasets"][0]
    assert item["last_ingested_at"] is None
    assert item["is_stale"] is True


@pytest.mark.asyncio
async def test_admin_health_shows_fresh_dataset(
    client: httpx.AsyncClient,
    db_session: Session,
) -> None:
    """A dataset ingested 1 hour ago is NOT stale (daily threshold is 26h)."""
    _seed_dataset_row(db_session, last_ingested=datetime.now(UTC) - timedelta(hours=1))
    response = await client.get("/admin/health")
    body = response.json()
    item = body["datasets"][0]
    assert item["is_stale"] is False
    assert item["last_ingested_at"] is not None


@pytest.mark.asyncio
async def test_admin_health_shows_stale_dataset(
    client: httpx.AsyncClient,
    db_session: Session,
) -> None:
    """A daily dataset ingested 30 hours ago IS stale (>26h threshold)."""
    _seed_dataset_row(db_session, last_ingested=datetime.now(UTC) - timedelta(hours=30))
    response = await client.get("/admin/health")
    body = response.json()
    item = body["datasets"][0]
    assert item["is_stale"] is True


@pytest.mark.asyncio
async def test_admin_health_unknown_dataset_still_listed(
    client: httpx.AsyncClient,
) -> None:
    """A registered definition with no DB Dataset row still appears in the response."""
    response = await client.get("/admin/health")
    body = response.json()
    slugs = [item["slug"] for item in body["datasets"]]
    assert "exchange-rates" in slugs
    item = next(i for i in body["datasets"] if i["slug"] == "exchange-rates")
    assert item["last_ingested_at"] is None
    assert item["latest_snapshot_date"] is None


@pytest.mark.asyncio
async def test_admin_health_reports_latest_snapshot_date(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    """When the data table has rows, ``latest_snapshot_date`` is the max."""
    response = await client.get("/admin/health")
    body = response.json()
    item = body["datasets"][0]
    assert item["latest_snapshot_date"] == "2026-04-30"


@pytest.mark.asyncio
async def test_admin_health_not_rate_limited(client: httpx.AsyncClient) -> None:
    """Admin endpoints are NOT rate-limited (Prometheus, uptime probes)."""
    for _ in range(120):
        response = await client.get("/admin/health")
        assert response.status_code == 200
