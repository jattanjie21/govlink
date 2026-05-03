"""End-to-end ingestion tests against real fixture data, using a real SQLite DB."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from govlink.core.base_source import BaseSource
from govlink.core.models import (
    Dataset,
    IngestionLog,
    IngestionStatus,
    SourceFile,
)
from govlink.core.source_ref import SourceFileRef
from govlink.datasets.exchange_rates.dataset import definition as exchange_rates_def
from govlink.datasets.exchange_rates.model import ExchangeRate
from govlink.datasets.exchange_rates.parser import ExchangeRatesParser
from govlink.datasets.exchange_rates.source import ExchangeRatesSource
from govlink.ingestion.orchestrator import Orchestrator


def _client_serving_listing_and_pdf(
    listing_html: str, pdf_payloads: dict[str, bytes]
) -> httpx.Client:
    """Build a mocked httpx client that serves the listing + the keyed PDFs."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/daily-valuation-exchange-rate"):
            return httpx.Response(200, text=listing_html)
        for uuid, payload in pdf_payloads.items():
            if uuid in url:
                return httpx.Response(200, content=payload)
        return httpx.Response(404, text="Not Found")

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def _make_definition_with(source: BaseSource) -> Any:
    """Build a fresh DatasetDefinition for exchange-rates, swapping in a custom source."""
    from govlink.core.definition import DatasetDefinition

    return DatasetDefinition(
        slug=exchange_rates_def.slug,
        title=exchange_rates_def.title,
        description=exchange_rates_def.description,
        publisher=exchange_rates_def.publisher,
        source_url=exchange_rates_def.source_url,
        frequency=exchange_rates_def.frequency,
        source=source,
        parser=ExchangeRatesParser(),
        model_class=exchange_rates_def.model_class,
        schema_class=exchange_rates_def.schema_class,
    )


def test_ingest_latest_exchange_rates_from_fixtures(
    initialized_db: Session,
    load_html_fixture: Callable[[str], str],
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    """Full pipeline against the real 2026-04-30 PDF and listing HTML fixtures."""
    listing = load_html_fixture("cbg_listing_2026-05.html")
    pdf_bytes = load_pdf_fixture("2026-04-30")
    uuid_2026 = "01f3604a-4474-11f1-8725-02e599c15748"

    client = _client_serving_listing_and_pdf(listing, {uuid_2026: pdf_bytes})
    source = ExchangeRatesSource(client=client)
    definition = _make_definition_with(source)

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(definition, latest=True)

    source.close()

    assert summary.files_ingested == 1
    assert summary.total_rows_added == 33

    source_files = initialized_db.execute(select(SourceFile)).scalars().all()
    assert len(source_files) == 1
    assert source_files[0].source_uuid == uuid_2026

    rows = initialized_db.execute(select(ExchangeRate)).scalars().all()
    assert len(rows) == 33

    by_code = {r.currency_code: r for r in rows}
    assert by_code["USD"].rate == Decimal("72.39")
    assert by_code["JPY"].unit_multiplier == 100

    logs = initialized_db.execute(select(IngestionLog)).scalars().all()
    assert len(logs) == 1
    assert logs[0].status is IngestionStatus.SUCCESS
    assert logs[0].rows_added == 33

    ds = initialized_db.execute(
        select(Dataset).where(Dataset.slug == "exchange-rates")
    ).scalar_one()
    assert ds.last_ingested_at is not None


def test_ingest_idempotent_second_run_skips(
    initialized_db: Session,
    load_html_fixture: Callable[[str], str],
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    listing = load_html_fixture("cbg_listing_2026-05.html")
    pdf_bytes = load_pdf_fixture("2026-04-30")
    uuid_2026 = "01f3604a-4474-11f1-8725-02e599c15748"

    client = _client_serving_listing_and_pdf(listing, {uuid_2026: pdf_bytes})
    source = ExchangeRatesSource(client=client)
    definition = _make_definition_with(source)

    orch = Orchestrator(session=initialized_db)
    first = orch.ingest(definition, latest=True)
    second = orch.ingest(definition, latest=True)
    source.close()

    assert first.files_ingested == 1
    assert second.files_ingested == 0
    assert second.files_skipped == 1
    assert len(initialized_db.execute(select(ExchangeRate)).scalars().all()) == 33


class _RepeatingFixedSource(BaseSource):
    """Source returning N controlled refs, all serving the same PDF bytes.

    Used by ``test_ingest_backfill_processes_multiple_files`` to verify that
    when files 2 and 3 collide on the unique constraint (because they all
    parse to the same snapshot date), the per-file SAVEPOINT keeps file 1's
    successful inserts intact.
    """

    def __init__(self, refs: list[SourceFileRef], payload: bytes) -> None:
        super().__init__()
        self._refs = refs
        self._payload = payload

    def discover(self) -> Iterable[SourceFileRef]:
        return list(self._refs)

    def fetch(self, ref: SourceFileRef) -> bytes:
        return self._payload


def test_ingest_backfill_processes_multiple_files(
    initialized_db: Session,
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    pdf_bytes = load_pdf_fixture("2026-04-30")
    refs = [
        SourceFileRef(
            source_uuid=f"backfill-{i}",
            url=f"https://example.gm/downloads-file/backfill-{i}",
            link_text=f"backfill-{i}",
            published_date_hint=date(2026, m, 1),
        )
        for i, m in enumerate([3, 2, 1])
    ]
    source = _RepeatingFixedSource(refs=refs, payload=pdf_bytes)
    definition = _make_definition_with(source)

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(definition, latest=False, backfill_from=date(2026, 1, 1))

    # File 1 succeeds (33 rows for snapshot_date=2026-04-30 from PDF body).
    # Files 2 & 3 fail on the (snapshot_date, currency_code) unique constraint.
    assert summary.files_ingested == 1
    assert summary.files_failed == 2
    assert summary.total_rows_added == 33

    rows = initialized_db.execute(select(ExchangeRate)).scalars().all()
    assert len(rows) == 33  # file 1's rows survive

    # All three SourceFile rows persist (each was successfully fetched).
    source_files = initialized_db.execute(select(SourceFile)).scalars().all()
    assert len(source_files) == 3

    # IngestionLog: 1 SUCCESS + 2 FAILED.
    logs = initialized_db.execute(select(IngestionLog)).scalars().all()
    statuses = sorted(log.status.value for log in logs)
    assert statuses == ["failed", "failed", "success"]


def test_in_memory_engine_includes_data_exchange_rates(
    in_memory_engine: Engine,
) -> None:
    """Sanity check: conftest's model import populates Base.metadata correctly."""
    from sqlalchemy import inspect

    inspector = inspect(in_memory_engine)
    tables = set(inspector.get_table_names())
    assert "data_exchange_rates" in tables
    assert {"datasets", "source_files", "ingestion_logs"} <= tables
