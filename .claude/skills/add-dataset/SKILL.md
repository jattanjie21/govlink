---
name: add-dataset
description: Scaffold a new govlink backend dataset plugin (source.py, parser.py, model.py, dataset.py + tests + Alembic migration). Use when the user asks to "add a dataset", "register a new dataset", "scaffold a govlink dataset plugin", or names a new publisher/source for ingestion.
disable-model-invocation: true
---

# add-dataset

Scaffolds a new govlink backend dataset plugin under `backend/govlink/datasets/<slug>/`, following the contract in `backend/docs/adding-a-dataset.md`. The architectural bet (per `backend/CLAUDE.md`) is that **adding a dataset must NOT require changes outside that directory** — preserve that property.

This skill creates files. Always confirm slug and source URL with the user before writing.

## When to invoke

Triggers:
- "add a dataset called X"
- "scaffold the inflation index dataset"
- "register a new dataset for Y"
- A request that names a publisher + source URL + cadence and implies ingestion

Don't invoke for:
- Modifying an existing dataset (just edit the files)
- Adding API routes (the API is generic — there are no per-dataset routes)
- Adding a frontend page for a dataset (also generic)

## Inputs to gather (ask before scaffolding)

| Input | Example | Notes |
|---|---|---|
| `slug` (kebab-case) | `inflation-index` | URL-safe; becomes the API path segment |
| `dir_name` (snake_case) | `inflation_index` | Python identifier; auto-derived as `slug.replace("-", "_")` |
| `title` | `Consumer Price Index` | Human display |
| `publisher` | `Gambia Bureau of Statistics` | Authoritative source organisation |
| `source_url` | `https://www.gbos.gm/cpi` | The publisher's listing/landing page |
| `frequency` | `monthly` | One of: `daily`, `weekly`, `monthly`, `quarterly`, `annual`, `irregular` |
| Source format | `pdf` / `xlsx` / `csv` / `html-table` | Drives the parser shape |
| Schema fields | `[snapshot_date, region, cpi_value, …]` | Decimal columns must use `DecimalStr` |

## The four files (the contract)

Every dataset directory holds these four, no more no less:

```
backend/govlink/datasets/<dir_name>/
├── __init__.py        # empty
├── model.py           # SQLAlchemy ORM model + Pydantic record schema
├── parser.py          # BaseParser subclass: bytes → list[Record]
├── source.py          # BaseSource subclass: discover + fetch
└── dataset.py         # DatasetDefinition + register() side effect
```

Read the canonical reference before writing anything new:
- `backend/govlink/datasets/exchange_rates/model.py`
- `backend/govlink/datasets/exchange_rates/parser.py`
- `backend/govlink/datasets/exchange_rates/source.py`
- `backend/govlink/datasets/exchange_rates/dataset.py`

The contributor walkthrough is canonical — load it before scaffolding:
- `backend/docs/adding-a-dataset.md`

## Workflow

1. **Confirm inputs** with the user (table above). If anything is missing, ask — don't guess slugs or URLs.
2. **Read the reference** — open the four exchange_rates files plus `backend/docs/adding-a-dataset.md`. Mirror their structure.
3. **Create the directory**: `mkdir -p backend/govlink/datasets/<dir_name>`, add empty `__init__.py`.
4. **Write `model.py`** — Mapped SQLAlchemy model on `Base` from `govlink.db`. Use `data_<dir_name>` as `__tablename__`. Decimal columns: `Mapped[Decimal] = mapped_column(Numeric(precision, scale))`. Pydantic schema uses `DecimalStr` from `govlink.core.schemas` for any decimal serialised to JSON/CSV. `model_config = ConfigDict(extra="forbid", from_attributes=True)`.
5. **Write `parser.py`** — Subclass `BaseParser[Record]`. Implement `parse(self, raw: bytes, source_ref: SourceFileRef) -> list[Record]`. Use `pdfplumber` for PDFs, `openpyxl`/`pandas` for XLSX, builtin `csv` for CSV. Raise `ParseError` (NOT bare `Exception`) on failure. Use `self.logger` not `print`.
6. **Write `source.py`** — Subclass `BaseSource`. Implement `discover() -> list[SourceFileRef]` and `fetch(ref) -> bytes`. Use `httpx` (NOT `requests`/`aiohttp`). The publisher's listing page should be the only HTTP call in `discover()`; per-file fetches happen in `fetch()`.
7. **Write `dataset.py`** — Build a `DatasetDefinition` and call `get_registry().register(definition)` at module top level. This is the only side-effect file; auto-discovery imports it at startup.
8. **Generate the Alembic migration**:
   ```bash
   cd backend && GOVLINK_DATABASE_URL=sqlite:///./_dev.db uv run alembic revision --autogenerate -m "add <dir_name>"
   ```
   Inspect the generated file under `alembic/versions/` — Alembic occasionally botches enum CHECKs and constraint names. Hand-fix only those. Do NOT reformat with ruff (the directory is excluded for that reason).
9. **Add tests**:
   ```
   backend/tests/unit/datasets/<dir_name>/__init__.py        # empty
   backend/tests/unit/datasets/<dir_name>/test_model.py
   backend/tests/unit/datasets/<dir_name>/test_parser.py
   backend/tests/unit/datasets/<dir_name>/test_source.py
   backend/tests/unit/datasets/<dir_name>/test_dataset.py
   ```
   Mirror the patterns in `backend/tests/unit/datasets/exchange_rates/`. HTTP mocking uses `httpx.MockTransport` (NOT `respx`) — see `tests/unit/datasets/exchange_rates/test_source.py`. Plugin import-time side effects require `_force_dataset_reregistration()` in tests using `isolated_global_registry`.
10. **Verify** — from `backend/`:
    ```bash
    uv run pytest tests/unit/datasets/<dir_name>/ -v
    uv run ruff check govlink/datasets/<dir_name>/
    uv run mypy govlink/datasets/<dir_name>/
    ```
11. **Sanity-check end-to-end** — start the API, hit the new endpoints:
    ```bash
    uv run govlink db init
    curl http://localhost:8000/datasets               # the new slug should appear
    curl http://localhost:8000/datasets/<slug>/latest  # likely empty until ingested
    uv run govlink ingest <slug>                       # if the source is reachable
    ```

## Hard rules (lifted from `backend/CLAUDE.md`)

- Slug uses **hyphens**, directory uses **underscores**. They MUST match: `slug.replace("-", "_") == dir_name`.
- All decimal money/measurement values use `DecimalStr` for serialisation. **Never `float`.**
- All `datetime` values are UTC-aware via `datetime.now(UTC)`. **Never `datetime.utcnow()`.**
- HTTP via `httpx`. **Never `requests` or `aiohttp`.**
- Logging via `structlog`. **Never `print`.**
- All Pydantic models: `model_config = ConfigDict(extra="forbid", ...)`.
- Don't catch bare `Exception` and continue silently — fail loud, the orchestrator records it.
- Don't add a route or CLI command specific to your dataset. The API is generic by design.

## When the work is done

- All four plugin files exist, ruff- and mypy-clean
- Alembic migration generated, inspected, committed
- Tests pass, ideally 100% coverage on the new dataset module
- `GET /datasets` lists the new slug
- Update `backend/README.md`'s "Available datasets" table to include the new entry
- Open a PR — the title should match `feat(dataset): add <slug>`
