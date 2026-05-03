"""End-to-end tests for the exchange-rates dataset.

These tests glue source + parser together against real fixture files,
proving they interoperate. The DB layer is not involved — that's
Phase 5 (orchestrator) territory.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from govlink.core.models import DatasetFrequency
from govlink.core.registry import DatasetRegistry
from govlink.datasets.exchange_rates.model import (
    ExchangeRate,
    ExchangeRateRecord,
)
from govlink.datasets.exchange_rates.parser import ExchangeRatesParser
from govlink.datasets.exchange_rates.source import ExchangeRatesSource

_DATASET_MODULE_NAME = "govlink.datasets.exchange_rates.dataset"


def test_full_flow_listing_html_to_parsed_records(
    load_html_fixture: Callable[[str], str],
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    """Discover from the listing HTML, fetch each PDF, parse — fully end-to-end.

    All HTTP traffic is mocked via ``httpx.MockTransport`` so the test is
    deterministic and offline-safe. The mocked transport returns the
    listing HTML for the listing URL, and a known PDF for each known
    fixture URL keyed by source_uuid.
    """
    listing_html = load_html_fixture("cbg_listing_2026-05.html")

    # Map from source_uuid → (fixture_stem, expected_snapshot_date)
    fixture_map: dict[str, tuple[str, date]] = {
        "01f3604a-4474-11f1-8725-02e599c15748": ("2026-04-30", date(2026, 4, 30)),
    }
    pdf_payloads: dict[str, bytes] = {
        uuid: load_pdf_fixture(stem) for uuid, (stem, _date) in fixture_map.items()
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/daily-valuation-exchange-rate"):
            return httpx.Response(200, text=listing_html)
        for uuid, payload in pdf_payloads.items():
            if uuid in url:
                return httpx.Response(200, content=payload)
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)

    src = ExchangeRatesSource(client=client)
    parser = ExchangeRatesParser()

    refs = list(src.discover())
    assert len(refs) > 0
    refs_by_uuid = {r.source_uuid: r for r in refs}

    for uuid, (_stem, expected_date) in fixture_map.items():
        ref = refs_by_uuid[uuid]
        body = src.fetch(ref)
        records = parser.parse(body)
        assert all(isinstance(r, ExchangeRateRecord) for r in records)
        assert all(r.snapshot_date == expected_date for r in records)
        assert len(records) == 33  # known row count for the 96K-era fixture

    src.close()


def test_dataset_registered_via_auto_discover(
    isolated_global_registry: DatasetRegistry,
) -> None:
    """``auto_discover`` finds and imports the exchange-rates dataset module.

    We pop the module from ``sys.modules`` first so ``auto_discover`` 's
    ``importlib.import_module`` actually runs the registration body
    against the freshly-isolated global registry.
    """
    sys.modules.pop(_DATASET_MODULE_NAME, None)
    isolated_global_registry.auto_discover(package="govlink.datasets")

    assert "exchange-rates" in isolated_global_registry
    definition = isolated_global_registry.get("exchange-rates")
    assert definition.slug == "exchange-rates"
    assert definition.title == "Daily Valuation Exchange Rates"
    assert definition.publisher == "Central Bank of The Gambia"
    assert definition.frequency is DatasetFrequency.DAILY
    assert isinstance(definition.source, ExchangeRatesSource)
    assert isinstance(definition.parser, ExchangeRatesParser)
    assert definition.model_class is ExchangeRate
    assert definition.schema_class is ExchangeRateRecord


def test_full_flow_against_all_four_fixtures(
    load_pdf_fixture: Callable[[str], bytes],
    load_pdf_expected: Callable[[str], dict[str, Any]],
) -> None:
    """For every fixture PDF, fetched bytes through the parser yield the oracle.

    Confirms source.fetch -> parser.parse round-trip on every era-shape
    PDF in the suite. No HTML — fetch is exercised with a synthetic
    direct-download URL per fixture.
    """
    stems = ["2026-04-30", "2025-12-15", "2025-08-25", "2025-04-30"]

    payload_for: dict[str, bytes] = {stem: load_pdf_fixture(stem) for stem in stems}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for stem, payload in payload_for.items():
            if stem in url:
                return httpx.Response(200, content=payload)
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    src = ExchangeRatesSource(client=client)
    parser = ExchangeRatesParser()

    from govlink.core.source_ref import SourceFileRef

    for stem in stems:
        ref = SourceFileRef(
            source_uuid=stem.replace("-", ""),
            url=f"https://example.gm/{stem}.pdf",
            link_text=None,
        )
        body = src.fetch(ref)
        records = parser.parse(body)
        oracle = load_pdf_expected(stem)
        assert len(records) == len(oracle["records"])
        assert records[0].snapshot_date.isoformat() == oracle["snapshot_date"]

    src.close()
