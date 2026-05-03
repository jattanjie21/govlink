"""Tests for govlink.api.routes.datasets — generic dataset endpoints."""

from __future__ import annotations

import csv
from io import StringIO

import httpx
import pytest
from sqlalchemy.orm import Session

# --- list / metadata -----------------------------------------------------


@pytest.mark.asyncio
async def test_list_datasets_returns_all_registered(client: httpx.AsyncClient) -> None:
    response = await client.get("/datasets")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["count"] == 1
    item = body["data"][0]
    assert item["slug"] == "exchange-rates"
    assert item["title"] == "Daily Valuation Exchange Rates"
    assert item["publisher"] == "Central Bank of The Gambia"
    assert item["frequency"] == "daily"


@pytest.mark.asyncio
async def test_list_datasets_empty_when_none_registered(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With auto_discover suppressed, the list is empty."""
    from govlink.core.registry import DatasetRegistry

    # Clear what auto_discover already populated.
    monkeypatch.setattr(DatasetRegistry, "list_all", lambda _self: [])
    response = await client.get("/datasets")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_dataset_returns_metadata(client: httpx.AsyncClient) -> None:
    response = await client.get("/datasets/exchange-rates")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["slug"] == "exchange-rates"
    assert body["data"]["data_table_name"] == "data_exchange_rates"
    assert "fields" in body["data"]
    field_names = {f["name"] for f in body["data"]["fields"]}
    assert {"snapshot_date", "currency_code", "currency_name", "rate"} <= field_names


@pytest.mark.asyncio
async def test_get_dataset_unknown_slug_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/datasets/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body or "detail" in body


# --- latest --------------------------------------------------------------


@pytest.mark.asyncio
async def test_latest_returns_most_recent_snapshot(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["count"] == 5
    snapshot_dates = {item["snapshot_date"] for item in body["data"]}
    assert snapshot_dates == {"2026-04-30"}  # only the newest, never the older snapshot


@pytest.mark.asyncio
async def test_latest_response_envelope_has_correct_meta(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/latest")
    body = response.json()
    assert body["meta"]["dataset"] == "exchange-rates"
    assert body["meta"]["count"] == 5
    assert body["meta"]["snapshot_date"] == "2026-04-30"


@pytest.mark.asyncio
async def test_latest_records_have_expected_fields(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/latest")
    body = response.json()
    item = body["data"][0]
    assert set(item.keys()) == {
        "snapshot_date",
        "currency_code",
        "currency_name",
        "rate",
        "unit_multiplier",
        "rate_per_unit",
    }


@pytest.mark.asyncio
async def test_latest_rates_are_decimal_strings_not_floats(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    """``rate`` and ``rate_per_unit`` serialise as strings to preserve precision."""
    response = await client.get("/datasets/exchange-rates/latest")
    body = response.json()
    for item in body["data"]:
        assert isinstance(item["rate"], str)
        assert isinstance(item["rate_per_unit"], str)


@pytest.mark.asyncio
async def test_latest_empty_dataset_returns_empty_data_with_meta(
    client: httpx.AsyncClient,
    empty_dataset_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["count"] == 0
    assert body["meta"]["snapshot_date"] is None


@pytest.mark.asyncio
async def test_latest_unknown_slug_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/datasets/nonexistent/latest")
    assert response.status_code == 404


# --- historical ----------------------------------------------------------


@pytest.mark.asyncio
async def test_historical_returns_all_records_paginated(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical")
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 10  # 5 currencies x 2 dates
    assert body["meta"]["total"] == 10


@pytest.mark.asyncio
async def test_historical_respects_limit_and_offset(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?limit=3&offset=2")
    body = response.json()
    assert len(body["data"]) == 3
    assert body["meta"]["total"] == 10
    assert body["meta"]["limit"] == 3
    assert body["meta"]["offset"] == 2


@pytest.mark.asyncio
async def test_historical_from_filter(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?from=2026-04-30")
    body = response.json()
    snapshots = {item["snapshot_date"] for item in body["data"]}
    assert snapshots == {"2026-04-30"}


@pytest.mark.asyncio
async def test_historical_to_filter(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?to=2026-04-29")
    body = response.json()
    snapshots = {item["snapshot_date"] for item in body["data"]}
    assert snapshots == {"2026-04-29"}


@pytest.mark.asyncio
async def test_historical_from_and_to_combined(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?from=2026-04-29&to=2026-04-30")
    body = response.json()
    snapshots = {item["snapshot_date"] for item in body["data"]}
    assert snapshots == {"2026-04-29", "2026-04-30"}


@pytest.mark.asyncio
async def test_historical_meta_includes_total_count(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?limit=3")
    body = response.json()
    assert body["meta"]["total"] == 10
    assert len(body["data"]) == 3


@pytest.mark.asyncio
async def test_historical_meta_includes_pagination_info(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?limit=4&offset=6")
    body = response.json()
    assert body["meta"]["limit"] == 4
    assert body["meta"]["offset"] == 6


@pytest.mark.asyncio
async def test_historical_currency_filter(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?currency=USD")
    body = response.json()
    assert all(item["currency_code"] == "USD" for item in body["data"])
    assert body["meta"]["total"] == 2  # 2 dates x 1 currency


@pytest.mark.asyncio
async def test_historical_empty_result(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?from=2099-01-01")
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_historical_unknown_slug_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/datasets/nonexistent/historical")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_historical_invalid_date_format_returns_422(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/datasets/exchange-rates/historical?from=not-a-date")
    assert response.status_code == 422


# --- CSV export ----------------------------------------------------------


@pytest.mark.asyncio
async def test_csv_returns_csv_content_type(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


@pytest.mark.asyncio
async def test_csv_has_correct_headers(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/csv")
    first_line = response.text.splitlines()[0]
    assert (
        first_line == "snapshot_date,currency_code,currency_name,rate,unit_multiplier,rate_per_unit"
    )


@pytest.mark.asyncio
async def test_csv_has_correct_row_count(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/csv")
    rows = list(csv.reader(StringIO(response.text)))
    # 1 header row + 10 data rows
    assert len(rows) == 11


@pytest.mark.asyncio
async def test_csv_respects_from_and_to_filters(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/csv?from=2026-04-30&to=2026-04-30")
    rows = list(csv.DictReader(StringIO(response.text)))
    assert len(rows) == 5
    assert all(r["snapshot_date"] == "2026-04-30" for r in rows)


@pytest.mark.asyncio
async def test_csv_content_disposition_header(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "exchange-rates.csv" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_csv_empty_dataset_returns_headers_only(
    client: httpx.AsyncClient,
    empty_dataset_db: Session,
) -> None:
    response = await client.get("/datasets/exchange-rates/csv")
    rows = response.text.splitlines()
    assert len(rows) == 1  # header only
    assert "snapshot_date" in rows[0]


@pytest.mark.asyncio
async def test_csv_unknown_slug_returns_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/datasets/nonexistent/csv")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_csv_currency_filter(
    client: httpx.AsyncClient,
    seeded_db: Session,
) -> None:
    """``?currency=USD`` on the CSV endpoint filters to one currency."""
    response = await client.get("/datasets/exchange-rates/csv?currency=USD")
    assert response.status_code == 200
    rows = list(csv.DictReader(StringIO(response.text)))
    assert len(rows) == 2  # 2 dates x 1 currency
    assert all(r["currency_code"] == "USD" for r in rows)
