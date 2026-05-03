# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`govlink` is an open-data REST API for Gambian government datasets, starting with Central Bank of The Gambia daily exchange rates. The architectural bet is that **adding a new dataset should require zero changes outside `govlink/datasets/<slug>/`** — the API, CLI, ingestion orchestrator, and CSV exporter all operate on any registered dataset generically. When changing core code, preserve that property; if a change in `core/`, `api/`, or `ingestion/` would force a contributor to also touch unrelated dataset code, push back on the design.

## Common commands

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run tests | `uv run pytest` |
| Single test | `uv run pytest tests/unit/test_orchestrator.py::test_ingest_is_idempotent` |
| Coverage report | `uv run pytest --cov=govlink --cov-report=term-missing` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` (or `--check` for CI mode) |
| Type check | `uv run mypy govlink` |
| Init local SQLite DB | `uv run govlink db init` |
| Run ingestion | `uv run govlink ingest exchange-rates` |
| List datasets | `uv run govlink datasets list` |
| Run API | `uv run uvicorn govlink.main:create_app --factory --port 8000` |
| Alembic upgrade | `GOVLINK_DATABASE_URL=sqlite:///./db.db uv run alembic upgrade head` |
| Alembic autogen | `GOVLINK_DATABASE_URL=sqlite:///./db.db uv run alembic revision --autogenerate -m "msg"` |
| Docker stack | `docker compose up -d` |
| Docker build | `docker build -t govlink:test .` |

`uv` is non-negotiable — don't fall back to `pip` or `poetry`. Python 3.12 is pinned via `.python-version`; mypy and ruff are both pinned to py312 syntax.

## Architecture: the registry pattern

`DatasetRegistry` (`govlink/core/registry.py`) is a process-global singleton mapping `slug → DatasetDefinition`. At startup, `auto_discover()` walks every immediate subpackage of `govlink/datasets/` and imports its `dataset.py` module. Each `dataset.py` calls `get_registry().register(...)` as an **import-time side effect** — that's the plugin mechanism.

A `DatasetDefinition` (`govlink/core/definition.py`) is a frozen Pydantic model bundling:
- identity (`slug`, `title`, `publisher`, `frequency`)
- `source: BaseSource` — discovers and fetches files
- `parser: BaseParser[Record]` — converts bytes → typed records (pure)
- `model_class: type[Base]` — the SQLAlchemy ORM model for this dataset's data table
- `schema_class: type[BaseModel]` — the Pydantic schema the parser produces and the API returns

Convention: **directory name uses underscores** (Python identifier), **slug uses hyphens** (URL-friendly). Data table name is `data_<slug_underscored>`, derived via `definition.data_table_name`.

The reference implementation is `govlink/datasets/exchange_rates/` — read these four files (`model.py`, `parser.py`, `source.py`, `dataset.py`) when designing anything dataset-shaped. The end-to-end contributor walkthrough is `docs/adding-a-dataset.md`.

## Architecture: the orchestrator + per-file SAVEPOINTs

`Orchestrator.ingest()` (`govlink/ingestion/orchestrator.py`) processes each `SourceFileRef` inside its own `session.begin_nested()` SAVEPOINT. A failure on file 3 rolls back ONLY file 3's data rows — files 1 and 2 stay committed at the outer-transaction level. This is intentional and load-bearing.

Order within `_process_one`:
1. Fetch (failure → no `SourceFile` row, FAILED log).
2. **Commit `SourceFile`** (separately, before the SAVEPOINT) — fetched bytes always get persisted, even if parsing fails afterwards.
3. SAVEPOINT { parse → flush → release } (failure → rolls back data rows only; `SourceFile` row survives).

Idempotency is keyed on `source_uuid`. Re-running ingest is a no-op for already-seen files.

## Architecture: generic API routes

Every route under `/datasets/{slug}/...` looks up the `DatasetDefinition` via the slug, then queries `definition.model_class` dynamically (`select(model_class).where(model_class.snapshot_date == ...)`). Serialisation goes through `definition.schema_class.model_validate(orm_obj, from_attributes=True).model_dump(mode="json")`.

Two pragmatic exceptions to "fully generic":
- The `currency` query parameter is gated on `hasattr(model, "currency_code")` — only applies where it makes sense.
- Routes don't use `response_model=Response[T]` (would force per-dataset typing); they return a `dict` matching the envelope shape. Swagger docs are slightly less specific as a result.

All data routes are rate-limited via `@limiter.limit("60/minute")` decorators (`govlink/api/deps.py`). Meta (`/`, `/health`) and admin (`/admin/...`) routes are intentionally NOT rate-limited so monitoring scrapers don't trip the limiter.

## Project-wide conventions

These are non-obvious enough that violating them silently breaks tests:

1. **`DecimalStr` for any decimal that appears in JSON or CSV.** It's an `Annotated[Decimal, PlainSerializer(str)]` alias in `govlink/core/schemas.py`. Bare `Decimal` serialises as a JSON float — financial data must be strings.

2. **All Pydantic models use `model_config = ConfigDict(extra="forbid", ...)`.** Most also use `frozen=True` (record/value objects) or `from_attributes=True` (response schemas built from ORM rows).

3. **All datetime values are UTC-aware via `datetime.now(UTC)`.** Never `datetime.utcnow()` (deprecated in 3.12). All `DateTime(timezone=True)` columns combine `server_default=func.now()` AND `default=_utcnow` — the Python-side default keeps tzinfo on SQLite where the SQL default would not.

4. **SQLite strips tzinfo on read-back.** A datetime written tz-aware comes back naive. Tests that re-query the value compare naive-to-naive. The `admin/health` endpoint coerces naive → UTC before comparing to `datetime.now(UTC)` — see `_is_stale()`.

5. **Logging via `structlog`, never `print`.** Modules use `_logger = structlog.get_logger(__name__)`. `BaseSource`/`BaseParser` subclasses get `self.logger` for free, bound with `source=ClassName` / `parser=ClassName`.

6. **`pyproject.toml` has `filterwarnings = ["error"]`** under `[tool.pytest.ini_options]`. DeprecationWarnings are fatal in tests. If a third-party warning surfaces, add a targeted ignore for that specific warning rather than relaxing the global rule.

7. **Enum columns use `Enum(EnumClass, native_enum=False, create_constraint=True, validate_strings=True, values_callable=_enum_values)`.** This is the only combination that produces lowercase CHECK constraints on SQLite, native ENUM-equivalent on Postgres, and synchronous Python-side validation. See `govlink/core/models.py`'s frequency/status columns.

## Testing patterns that bite if you ignore them

1. **Plugin import-time side effects + isolated registry**: tests using `isolated_global_registry` must pop the dataset module from `sys.modules` so `auto_discover()`'s next import re-fires the `register()` call against the fresh registry. Use the `_force_dataset_reregistration()` helper (defined in `tests/unit/datasets/exchange_rates/test_dataset.py`, `tests/api/conftest.py`, and `tests/integration/test_exchange_rates_e2e.py`). Without this, test 1 registers fine, test 2 sees an empty registry and fails.

2. **HTTP mocking uses `httpx.MockTransport`, not `respx`.** Construct a transport with a handler callback returning `httpx.Response(...)`, then pass `httpx.Client(transport=...)` into the `BaseSource` subclass. See `tests/unit/datasets/exchange_rates/test_source.py` for the canonical pattern.

3. **API tests trigger lifespan manually.** `httpx.ASGITransport` does NOT run FastAPI lifespan events on its own. The `client` fixture in `tests/api/conftest.py` enters `app.router.lifespan_context(app)` before yielding the client — necessary for `init_db()` and `auto_discover()` to fire.

4. **`pdfplumber.open` is mocked for parser error-path tests.** Empty input, missing date, unknown currency — all use a `MagicMock`-based fake context manager. See `_make_fake_pdf_with_text()` in `tests/unit/datasets/exchange_rates/test_parser.py`. Real PDFs are used for the four oracle-comparison tests; mocking is only for synthesised edge cases.

5. **`get_settings.cache_clear()` between settings mutations.** The `settings_env` fixture does this around each test. If you mutate `GOVLINK_*` env vars without using the fixture, the lru_cache returns stale results.

6. **Fixture PDFs and JSON oracles** live under `tests/fixtures/pdfs/`. The oracles are committed and treated as the authoritative expected output — the parser tests assert against them exactly. To regenerate after a parser change, run pdfplumber directly (NOT through the parser) and rebuild the JSON manually; this keeps the oracle independent of the code under test.

## Alembic specifics

- `alembic/env.py` calls `get_registry().auto_discover()` so every dataset's model module loads and `Base.metadata` knows about every `data_<slug>` table before autogenerate runs. Don't replace this with per-dataset imports — auto-discovery is what keeps `env.py` from needing edits when a new dataset arrives.
- `alembic/versions/*.py` is **excluded from ruff** (`extend-exclude = ["alembic/versions"]` in `ruff.toml`) so Alembic's autogenerated long lines and trailing whitespace produce clean diffs on regeneration. Don't hand-format migration files.
- For a new dataset, run `GOVLINK_DATABASE_URL=sqlite:///./_dev.db uv run alembic revision --autogenerate -m "add <slug>"`, inspect the file (Alembic occasionally botches enum CHECKs and constraint names), commit it.

## What lives where

```
govlink/
├── api/                FastAPI: routes (datasets, meta, admin), deps, exporters
├── core/               base classes (BaseSource/BaseParser), registry, definition,
│                       SourceFileRef, registry-layer ORM models, shared schemas
├── datasets/           one subpackage per dataset (the plugin layer)
├── ingestion/          orchestrator + cross-dataset utilities (currency_codes)
├── cli.py              Typer CLI: ingest, datasets list, db init, --version
├── config.py           pydantic-settings (GOVLINK_*-prefixed env)
├── db.py               SQLAlchemy engine + session + DeclarativeBase + naming convention
├── logging.py          structlog setup (JSON in prod, console in dev)
└── main.py             FastAPI application factory + lifespan
```

Tests mirror the source layout: `tests/unit/<module>.py`, `tests/unit/datasets/<slug>/`, `tests/api/`, `tests/integration/`. All test fixtures live in the nearest `conftest.py` (root, `tests/api/`, etc.).

## Don't do this

- Don't add a `print()` — use `structlog`.
- Don't use `float` for any numeric value the API returns or persists — use `Decimal`/`DecimalStr`.
- Don't add an endpoint specific to one dataset. If you genuinely need per-dataset routing, push back and discuss the design first.
- Don't catch `Exception` and continue silently in the orchestrator or parsers. Fail loud; the `IngestionLog` records what failed.
- Don't introduce `requests` or `aiohttp`. The project uses `httpx` everywhere.
- Don't introduce `pip install ...` instructions in docs. `uv sync` and `uv run` are the only entry points.
