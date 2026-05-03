# Adding a New Dataset

This guide walks you through adding a new government dataset to govlink end-to-end. We'll use a hypothetical **inflation index** dataset from the Gambia Bureau of Statistics as the worked example. Substitute your own slug, source, and schema as you go.

## Overview

A "dataset" in govlink is a **self-contained plugin** under `govlink/datasets/<slug>/`. The plugin registers itself with a process-wide registry at import time, and the rest of the application — CLI, ingestion orchestrator, REST API, CSV exporter — operates on it generically. There is no per-dataset route code, no per-dataset CLI command. Add the four files, write the tests, ship.

Every dataset ships four files:

| File | Purpose |
|------|---------|
| `model.py` | SQLAlchemy ORM model + Pydantic record/response schemas |
| `parser.py` | `BaseParser` subclass converting raw bytes → typed records |
| `source.py` | `BaseSource` subclass discovering and fetching upstream files |
| `dataset.py` | `DatasetDefinition` construction + `register()` call |

The contract:

- The **source** knows how to find and download files. It is unaware of file contents.
- The **parser** knows how to convert bytes to records. It is unaware of where the bytes came from.
- The **ORM model** persists records.
- The **dataset module** wires the four pieces together via `DatasetDefinition` and registers them.

## Prerequisites

- Python 3.12 with [uv](https://docs.astral.sh/uv/) installed
- Repo cloned and `uv sync` run
- Comfort with SQLAlchemy 2.0's typed ORM (`Mapped[...]`, `mapped_column(...)`)
- Comfort with Pydantic v2 (`BaseModel`, `model_config`, `field_validator`)
- Comfort with pytest

Take a few minutes to read through the existing exchange-rates dataset under `govlink/datasets/exchange_rates/` — it's the canonical reference implementation.

## Step 1: Create the dataset directory

```bash
mkdir -p govlink/datasets/inflation_index
touch govlink/datasets/inflation_index/__init__.py
```

**Naming convention:** the **directory name** uses underscores (it must be a valid Python identifier so `pkgutil.iter_modules` can import it). The **slug** uses hyphens (it appears in URLs and is more readable for humans). For our example: directory `inflation_index`, slug `inflation-index`.

Add a one-line module docstring to the new `__init__.py`:

```python
"""GBoS monthly inflation index dataset plugin."""
```

## Step 2: Define the ORM model and Pydantic schemas

Create `govlink/datasets/inflation_index/model.py`:

```python
"""ORM model and Pydantic schemas for the inflation-index dataset."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    DECIMAL,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from govlink.core.schemas import DecimalStr
from govlink.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class InflationIndex(Base):
    """One per-category inflation reading for a single snapshot date."""

    __tablename__ = "data_inflation_index"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_date",
            "category",
            name="uq_data_inflation_index_snapshot_date_category",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    index_value: Mapped[Decimal] = mapped_column(DECIMAL(10, 4), nullable=False)
    yoy_change_pct: Mapped[Decimal | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        nullable=False,
    )


class InflationIndexRecord(BaseModel):
    """The structured record produced by :class:`InflationIndexParser`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_date: date
    category: str = Field(min_length=1, max_length=64)
    index_value: DecimalStr
    yoy_change_pct: DecimalStr | None = None


class InflationIndexResponseItem(BaseModel):
    """Public API representation of an inflation index row."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    snapshot_date: date
    category: str
    index_value: DecimalStr
    yoy_change_pct: DecimalStr | None = None
```

**Required conventions:**

- **Table name** is `data_<slug_underscored>` — the registry's `data_table_name` property derives this from the slug. The orchestrator does NOT enforce this, but every consumer assumes it.
- **`snapshot_date`** is the natural time dimension every dataset needs. The API's `/latest`, `/historical?from=...&to=...` filters all key on this column. If your dataset doesn't have a snapshot date, the routes won't work for it without code changes.
- **`source_file_id`** is the FK back to the registry-layer `source_files` table. ON DELETE SET NULL — deleting the source file leaves the data behind.
- **`ingested_at`** uses the project's dual default pattern (`server_default=func.now()` + `default=_utcnow`). This is the convention from Phase 2; SQLite preserves the Python-side default's tzinfo while server defaults handle raw SQL inserts.
- **Decimal fields** use `DECIMAL(precision, scale)` on the ORM side and `DecimalStr` on the Pydantic side. `DecimalStr` is the project-wide alias from `govlink.core.schemas` that guarantees JSON serialisation as a plain string (no scientific notation, no float drift).
- **Pydantic `model_config`** uses `extra="forbid"` everywhere. The record schema is `frozen=True` because records flow from parser → orchestrator → DB and shouldn't mutate. The response schema uses `from_attributes=True` so it can be built from an ORM instance via `model_validate(orm_obj, from_attributes=True)`.
- **Unique constraint** on the natural key. For exchange rates that's `(snapshot_date, currency_code)`; for inflation it's `(snapshot_date, category)`. This is what makes the orchestrator's idempotency guarantee meaningful — re-ingesting the same source file is a no-op rather than a duplication.

## Step 3: Write the parser

Create `govlink/datasets/inflation_index/parser.py`:

```python
"""PDF parser for GBoS monthly inflation index publications."""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from decimal import Decimal

import pdfplumber

from govlink.core.base_parser import BaseParser
from govlink.datasets.inflation_index.model import InflationIndexRecord


class ParseError(ValueError):
    """Raised when an inflation-index PDF cannot be parsed."""


_CATEGORY_LINE = re.compile(
    r"^\s*(?P<category>[A-Za-z &/-]+?)\s+(?P<value>[\d.]+)(?:\s+(?P<yoy>-?[\d.]+))?\s*$"
)
_DATE_FORMATS = ("%B %Y", "%B %d, %Y")


class InflationIndexParser(BaseParser[InflationIndexRecord]):
    """Parse GBoS monthly inflation reports."""

    def parse(self, raw_bytes: bytes) -> list[InflationIndexRecord]:
        """Convert bytes to records; raises :class:`ParseError` on failure."""
        if not raw_bytes:
            raise ParseError("empty input bytes")
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        snapshot_date = self._extract_date(text)
        records = self._extract_rows(text, snapshot_date)
        if not records:
            raise ParseError("no inflation rows found in PDF body")
        self.logger.info(
            "parse_complete",
            snapshot_date=snapshot_date.isoformat(),
            row_count=len(records),
        )
        return records

    @staticmethod
    def _extract_date(text: str) -> date:
        for line in text.splitlines()[:5]:
            for fmt in _DATE_FORMATS:
                try:
                    return datetime.strptime(line.strip(), fmt).date()
                except ValueError:
                    continue
        raise ParseError("no snapshot date found in PDF body")

    @staticmethod
    def _extract_rows(text: str, snapshot_date: date) -> list[InflationIndexRecord]:
        records: list[InflationIndexRecord] = []
        for line in text.splitlines():
            match = _CATEGORY_LINE.match(line)
            if not match:
                continue
            yoy = match.group("yoy")
            records.append(
                InflationIndexRecord(
                    snapshot_date=snapshot_date,
                    category=match.group("category").strip(),
                    index_value=Decimal(match.group("value")),
                    yoy_change_pct=Decimal(yoy) if yoy else None,
                )
            )
        return records
```

**Required conventions:**

- **The parser is pure.** Same bytes in → same records out. No DB writes, no filesystem writes (other than reading the in-memory PDF stream), no network calls. Persistence is the orchestrator's job.
- **Authoritative date comes from the PDF body**, never from external metadata. Link-text dates from listing pages are notoriously wrong (typos, wrong years). Trust the document.
- **Fail loud.** Empty input, missing date, zero rows: raise `ParseError`. Unknown categorical values that you haven't mapped: raise a clear, named exception (see exchange-rates' `UnknownCurrencyError`). Silent empty returns hide data-quality problems.
- **Use `self.logger`** for structured logging — `BaseParser` provides one bound with `parser=<ClassName>`.
- **Return a `list[R]`**, not a generator. Consumers need to iterate twice (e.g., to count rows AND insert them).

## Step 4: Write the source

Create `govlink/datasets/inflation_index/source.py`:

```python
"""Source: scrape the GBoS inflation page and fetch monthly PDFs."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Final

import httpx
from bs4 import BeautifulSoup, Tag

from govlink.core.base_source import BaseSource
from govlink.core.source_ref import SourceFileRef

_LISTING_URL: Final[str] = "https://gbos.gov.gm/inflation"
_USER_AGENT: Final[str] = "govlink/0.1 (+https://github.com/TODO/govlink)"
_DATE_FORMATS: Final[tuple[str, ...]] = ("%Y-%m", "%B %Y")
_DOWNLOAD_RE: Final[re.Pattern[str]] = re.compile(
    r"/inflation/(?P<uuid>[\w-]+)\.pdf"
)


class InflationIndexSource(BaseSource):
    """Source for GBoS monthly inflation PDFs."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        listing_url: str = _LISTING_URL,
    ) -> None:
        super().__init__()
        self._listing_url = listing_url
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )

    def discover(self) -> Iterable[SourceFileRef]:
        """Scrape the GBoS listing for PDF entries."""
        response = self._client.get(self._listing_url)
        response.raise_for_status()
        refs = list(self._parse_listing(response.text))
        self.logger.info("discover_complete", discovered_count=len(refs))
        return refs

    def fetch(self, ref: SourceFileRef) -> bytes:
        """Download the bytes of one PDF; HTTP errors propagate."""
        response = self._client.get(ref.url, headers={"User-Agent": _USER_AGENT})
        response.raise_for_status()
        return response.content

    def _parse_listing(self, html: str) -> Iterable[SourceFileRef]:
        soup = BeautifulSoup(html, "html.parser")
        for raw in soup.find_all("a", href=True):
            anchor: Tag = raw
            href = str(anchor.get("href", ""))
            match = _DOWNLOAD_RE.search(href)
            if not match:
                continue
            text = anchor.get_text(" ", strip=True)
            yield SourceFileRef(
                source_uuid=match.group("uuid"),
                url=href if href.startswith("http") else f"https://gbos.gov.gm{href}",
                link_text=text[:512] or None,
                published_date_hint=self._parse_date(text),
            )

    @staticmethod
    def _parse_date(text: str) -> date | None:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text.strip()[:7], fmt).date()
            except ValueError:
                continue
        return None

    def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            self._client.close()
```

**Required conventions:**

- **`discover()` returns an `Iterable[SourceFileRef]`** in newest-first order. The orchestrator's `latest=True` mode takes the first ref, so order matters.
- **`source_uuid` is stable across re-discoveries.** A UUID extracted from the URL is ideal. If the upstream site doesn't have stable URLs, derive a hash of `url + link_text` as a fallback — but document the choice clearly.
- **`fetch(ref)` returns raw `bytes`.** HTTP errors propagate (not caught here); the orchestrator decides retry policy.
- **Accept a custom `httpx.Client`** in the constructor. This is the single most important affordance for testability — tests inject `httpx.MockTransport` and avoid real network calls.
- **Discovery is tolerant; fetch is strict.** A malformed listing entry is skipped with a warning log. A failed fetch raises.
- **`published_date_hint` is a HINT, never authoritative.** The parser extracts the real date from the document body. Link-text dates have typos.

## Step 5: Write the registration module

Create `govlink/datasets/inflation_index/dataset.py`:

```python
"""Registration of the inflation-index dataset."""

from __future__ import annotations

from govlink.core.definition import DatasetDefinition
from govlink.core.models import DatasetFrequency
from govlink.core.registry import get_registry
from govlink.datasets.inflation_index.model import (
    InflationIndex,
    InflationIndexRecord,
)
from govlink.datasets.inflation_index.parser import InflationIndexParser
from govlink.datasets.inflation_index.source import InflationIndexSource

definition = DatasetDefinition(
    slug="inflation-index",
    title="Monthly Inflation Index",
    description=(
        "Consumer price index by category, published monthly by the "
        "Gambia Bureau of Statistics."
    ),
    publisher="Gambia Bureau of Statistics",
    source_url="https://gbos.gov.gm/inflation",
    frequency=DatasetFrequency.MONTHLY,
    source=InflationIndexSource(),
    parser=InflationIndexParser(),
    model_class=InflationIndex,
    schema_class=InflationIndexRecord,
)

get_registry().register(definition)
```

**This module is imported by `auto_discover()` at startup.** The `register()` call is an import-time side effect — that's intentional and is the standard plugin pattern. The registry's `auto_discover` walks every subpackage of `govlink/datasets/` and imports its `dataset` module exactly once per process.

## Step 6: Generate the Alembic migration

```bash
GOVLINK_DATABASE_URL="sqlite:///./_dev_migration.db" \
  uv run alembic revision --autogenerate -m "add inflation-index"
```

Inspect the generated file under `alembic/versions/`. Verify:

- The new table is `data_inflation_index`.
- The unique constraint name matches our naming convention (`uq_data_inflation_index_snapshot_date_category` or similar).
- The composite indexes look right.
- The foreign key to `source_files.id` has `ondelete='SET NULL'`.

Apply the migration locally and verify it round-trips:

```bash
GOVLINK_DATABASE_URL="sqlite:///./_dev_migration.db" uv run alembic upgrade head
GOVLINK_DATABASE_URL="sqlite:///./_dev_migration.db" uv run alembic downgrade -1
GOVLINK_DATABASE_URL="sqlite:///./_dev_migration.db" uv run alembic upgrade head
rm _dev_migration.db
```

Commit the migration file along with your dataset code.

## Step 7: Write tests

The project follows strict TDD: write the failing test first, watch it fail for the right reason, write the minimum implementation, watch it pass.

Create the test directory:

```bash
mkdir -p tests/unit/datasets/inflation_index
touch tests/unit/datasets/inflation_index/__init__.py
```

You'll write four test files:

| File | What it covers |
|------|----------------|
| `test_model.py` | ORM constraints, Pydantic validation, computed fields |
| `test_parser.py` | Fixture-driven oracle comparisons, error paths via mocked `pdfplumber` |
| `test_source.py` | Discovery + fetch via `httpx.MockTransport` |
| `test_dataset.py` | Registration side-effect via `_force_dataset_reregistration` + `isolated_global_registry` |

### Test fixtures

Download a couple of real sample PDFs from the upstream source and place them under `tests/fixtures/pdfs/`. For each one, generate an expected-output JSON oracle:

1. Use `pdfplumber` directly (not your parser) to extract the raw text.
2. Walk the text by hand, building the expected list of `{snapshot_date, category, index_value, yoy_change_pct}` records.
3. Save as `tests/fixtures/pdfs/<stem>.expected.json`.

The conftest fixtures `load_pdf_fixture` and `load_pdf_expected` (from `tests/conftest.py`) load these by stem. Add as many fixtures as it takes to cover the layout variants you've observed.

### HTTP mocking

Never make real network calls in tests. Use `httpx.MockTransport`:

```python
def _client_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)

def test_discover_against_html_fixture(load_html_fixture):
    html = load_html_fixture("gbos_listing.html")
    src = InflationIndexSource(
        client=_client_with(lambda _r: httpx.Response(200, text=html))
    )
    refs = list(src.discover())
    src.close()
    assert len(refs) > 0
```

### Registry isolation

Tests that exercise the registration side effect must use `isolated_global_registry` and the `_force_dataset_reregistration()` helper. See `tests/unit/datasets/exchange_rates/test_dataset.py` for the canonical pattern:

```python
import sys
import importlib

_DATASET_MODULE = "govlink.datasets.inflation_index.dataset"


def _reload_dataset_module() -> None:
    sys.modules.pop(_DATASET_MODULE, None)
    importlib.import_module(_DATASET_MODULE)


def test_dataset_module_registers_on_import(isolated_global_registry):
    _reload_dataset_module()
    assert "inflation-index" in isolated_global_registry
```

Without this pattern, Python's import cache means the second test in the file gets a stale module and the registration side effect doesn't fire against the fresh isolated registry.

### Mocking `pdfplumber` for error-path tests

For tests of empty input, missing date, malformed PDF — mock `pdfplumber.open`:

```python
from unittest.mock import MagicMock, patch


def _fake_pdf(text: str):
    page = MagicMock()
    page.extract_text.return_value = text
    pdf = MagicMock()
    pdf.pages = [page]
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=pdf)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_parse_raises_on_missing_date():
    parser = InflationIndexParser()
    fake = _fake_pdf("Some heading\nFood 124.5\n")  # no date
    with patch("pdfplumber.open", return_value=fake), pytest.raises(ParseError):
        parser.parse(b"%PDF-fake")
```

## Step 8: Verify everything works

```bash
uv run pytest                           # all tests pass
uv run pytest --cov=govlink              # ≥95% coverage on new modules
uv run ruff check .                      # lint clean
uv run ruff format --check .             # format clean
uv run mypy govlink                      # type-check clean (strict mode)
uv run govlink datasets list             # your dataset appears in the listing
uv run govlink ingest inflation-index    # the orchestrator runs end-to-end
```

Then start the API and hit your dataset's endpoints:

```bash
uv run uvicorn govlink.main:create_app --factory --port 8000
curl http://localhost:8000/datasets/inflation-index/latest
curl "http://localhost:8000/datasets/inflation-index/historical?from=2026-01-01"
curl http://localhost:8000/datasets/inflation-index/csv
```

If those four routes work without code changes, the generic-dataset architecture has held — you've added a new dataset without touching the API layer.

## Step 9: Submit a PR

PR checklist:

- [ ] All tests pass (`uv run pytest`)
- [ ] Coverage ≥ 95% on new modules
- [ ] `ruff check .` and `ruff format --check .` clean
- [ ] `mypy govlink` clean (strict mode)
- [ ] Alembic migration included and locally tested (upgrade + downgrade + upgrade)
- [ ] At least one fixture PDF + expected JSON oracle committed to `tests/fixtures/pdfs/`
- [ ] `dataset.py` calls `get_registry().register(...)` at module level
- [ ] `govlink datasets list` shows the new dataset
- [ ] `govlink ingest <slug>` runs end-to-end against the real upstream (you've manually verified at least one ingest succeeds)
- [ ] README's "Available Datasets" table updated with a new row

## Common pitfalls

| Symptom | Cause |
|---------|-------|
| `auto_discover` doesn't find your dataset | Missing `__init__.py` in the dataset directory |
| `Dataset already registered` errors in tests | Forgot `_force_dataset_reregistration()` before re-asserting registration |
| `dict contains fields not in fieldnames` from CSV | Schema has a `computed_field`; the project's CSV exporter handles this — make sure your schema is the one passed to `definition.schema_class` |
| `tzinfo is None` on read-back from SQLite | Known SQLite limitation (Phase 2); compare naive-to-naive in tests, or use the `last_ingested_at` UTC shim pattern from `admin.py` |
| Floating-point drift in API responses | Used `Decimal` instead of `DecimalStr` on a Pydantic field — `Decimal` serialises as float in JSON; `DecimalStr` serialises as plain string |
| Parser silently returns empty list | Missing the `if not records: raise ParseError(...)` guard — fail loud |
| Source uses `async def discover/fetch` | The orchestrator expects synchronous methods; if you need async I/O, do it inside the method and `asyncio.run(...)` it |
| Hard-coded date from listing page | Always extract the snapshot date from the document body. Listing-page dates have typos. |

## When in doubt

The exchange-rates dataset under `govlink/datasets/exchange_rates/` is the working reference — every pattern in this guide is implemented there. When the abstractions feel ambiguous, read the corresponding file in that dataset.
