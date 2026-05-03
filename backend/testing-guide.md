# govlink — Testing & Integration Guide

A practical, run-it-yourself walkthrough for two audiences:

- **Part 1 — Contributors:** clone the repo, run the full stack locally, run the test suite, ingest real data, and verify everything works end-to-end.
- **Part 2 — Frontend integrators:** consume the API from a browser or Node.js app without ever touching the Python code.

Both parts are independent. Skip to whichever you need.

---

## Part 1 — Contributor Walkthrough

You'll set up the project, run all 311 tests, perform a real ingestion against the live Central Bank of The Gambia website, query the data via the CLI, and start the API server.

**Time estimate:** 15–25 minutes on a fresh machine.

### 1.1 Prerequisites

| Tool | Version | How to install |
|------|---------|----------------|
| Python | 3.12.x | [python.org](https://www.python.org/downloads/) or pyenv |
| uv | latest (≥0.5) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | any recent | system package manager |
| Docker (optional) | 24+ | only needed for the Postgres path |

Verify:

```bash
python3 --version    # 3.12.x
uv --version          # any recent
git --version         # any
```

### 1.2 Clone and install

```bash
git clone https://github.com/govlink/govlink.git
cd govlink
cp .env.example .env
uv sync
```

`uv sync` reads `pyproject.toml` + `uv.lock` and creates `.venv/` with both runtime and dev dependencies. First run takes 30–60 seconds; subsequent runs are near-instant.

**Verify the install:**

```bash
uv run python -c "import govlink; print(govlink.__version__)"
# → 0.1.0

uv run govlink --version
# → govlink 0.1.0
```

### 1.3 Run the test suite

This is the single most important step. If 311 tests pass, the project is healthy on your machine.

```bash
uv run pytest
```

Expected output (tail):

```
==== 311 passed in 8.42s ====
```

Run with coverage to confirm 100%:

```bash
uv run pytest --cov=govlink --cov-report=term-missing
# → TOTAL ... 1010    0   100%
```

Lint, format, and type-check:

```bash
uv run ruff check .          # → All checks passed!
uv run ruff format --check . # → 68 files already formatted
uv run mypy govlink          # → Success: no issues found in 31 source files
```

If any of the above fails on a fresh clone, that's a bug — open an issue.

#### Useful test subset commands

```bash
# A single test file
uv run pytest tests/unit/test_orchestrator.py

# A single test by name
uv run pytest tests/unit/test_orchestrator.py::test_ingest_is_idempotent

# Just the integration tests (slower, hit fixture PDFs)
uv run pytest tests/integration/

# Just the API tests
uv run pytest tests/api/

# Verbose with print output
uv run pytest -v -s
```

### 1.4 Initialize the local database

govlink uses SQLite by default for local development — zero configuration, file-based.

```bash
uv run govlink db init
# → Database initialized at sqlite:///./govlink.db
```

This creates `./govlink.db` with all 5 tables: `datasets`, `dataset_fields`, `source_files`, `ingestion_logs`, `data_exchange_rates`. Inspect with:

```bash
sqlite3 ./govlink.db ".tables"
# → data_exchange_rates  dataset_fields       ingestion_logs
#   datasets             source_files
```

### 1.5 List registered datasets

```bash
uv run govlink datasets list
```

Expected:

```
slug             title                              frequency    last_ingested_at
exchange-rates   Daily Valuation Exchange Rates     daily        never
```

`never` means no ingestion has run yet. We'll fix that next.

### 1.6 Run a real ingestion

This will hit `https://www.cbg.gm` and download the latest exchange rate PDF.

```bash
uv run govlink ingest exchange-rates
```

Expected output:

```
Ingesting exchange-rates...
Files discovered: 1
Files ingested:   1
Rows added:       33
Duration:         2.4s
✓ Ingestion complete
```

If the network is unreachable or CBG's site is down, the command exits with a non-zero code and a clear error — that's by design (fail-loud).

#### Verify the data landed

```bash
sqlite3 ./govlink.db "SELECT snapshot_date, currency_code, rate, rate_per_unit FROM data_exchange_rates ORDER BY currency_code LIMIT 5;"
```

Expected (rates will be whatever CBG most recently published):

```
2026-04-30|AED|19.71|19.71000000
2026-04-30|AUD|51.61|51.61000000
2026-04-30|BRL|14.48|14.48000000
2026-04-30|CAD|52.94|52.94000000
2026-04-30|CHF|93.11|93.11000000
```

#### Re-run ingestion to verify idempotency

```bash
uv run govlink ingest exchange-rates
```

Expected:

```
Files discovered: 1
Files skipped:    1   ← already ingested
Rows added:       0
```

This is the idempotency guarantee in action. The `source_uuid` of the latest PDF is already in `source_files`, so the orchestrator skips it.

#### Backfill historical data (optional)

```bash
uv run govlink ingest exchange-rates --backfill-from 2026-04-01
```

This pulls every PDF published since April 1, 2026. The CBG archive goes back to ~October 2024, so a full backfill (`--backfill-from 2024-10-01`) yields ~400 PDFs and a few thousand rows. Takes 2–5 minutes depending on network.

### 1.7 Start the API server

```bash
uv run uvicorn govlink.main:create_app --factory --host 127.0.0.1 --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

In another terminal, run the smoke checks:

```bash
# Service info
curl -s http://127.0.0.1:8000/ | jq
# → {"name":"govlink","version":"0.1.0","docs":"/docs"}

# Health
curl -s http://127.0.0.1:8000/health | jq
# → {"status":"ok"}

# List datasets
curl -s http://127.0.0.1:8000/datasets | jq
# → {"data":[{"slug":"exchange-rates", ...}], "meta":{"count":1, ...}}

# Latest exchange rates
curl -s http://127.0.0.1:8000/datasets/exchange-rates/latest | jq '.data[0:3]'
# → first three records of the latest snapshot

# Historical with date filter
curl -s "http://127.0.0.1:8000/datasets/exchange-rates/historical?from=2026-04-01&limit=5" | jq

# CSV download
curl -s -o rates.csv http://127.0.0.1:8000/datasets/exchange-rates/csv
head rates.csv

# Admin freshness check
curl -s http://127.0.0.1:8000/admin/health | jq
```

Open Swagger UI at <http://127.0.0.1:8000/docs> to explore interactively.

When you're done, `Ctrl+C` the uvicorn process.

### 1.8 The Postgres + Docker path (optional)

If you want to test against the production stack (Postgres instead of SQLite):

```bash
docker compose up -d
```

This spins up three services: `db` (Postgres 16), `migrate` (one-shot Alembic upgrade, exits when done), and `api` (the same Dockerfile that ships to production). The `api` container won't start until `migrate` finishes successfully.

Verify:

```bash
docker compose ps
# All three services should be visible; 'migrate' will show 'exited (0)'

curl http://localhost:8000/health
# → {"status":"ok"}

# Run ingestion inside the container
docker compose exec api govlink ingest exchange-rates

# Tear down (preserves volumes)
docker compose down

# Tear down and wipe data
docker compose down -v
```

### 1.9 Make a change and verify it doesn't break anything

The TDD discipline of the project means every change should be covered by tests. The fastest way to verify your change is sound:

```bash
# Make your change in govlink/...
# Add or update tests in tests/...

uv run pytest                       # all 311 (or more) green
uv run ruff check .                 # lint clean
uv run ruff format .                # auto-format
uv run mypy govlink                 # type-check clean

# If you modified a model, regenerate the migration:
GOVLINK_DATABASE_URL=sqlite:///./_dev.db uv run alembic revision --autogenerate -m "describe-change"
# Inspect the generated file in alembic/versions/, fix any issues, commit.
```

### 1.10 Adding a new dataset

This is the project's whole reason for existing. Read [`docs/adding-a-dataset.md`](adding-a-dataset.md) — it walks through a complete worked example. Summary of the four files you'll create:

```
govlink/datasets/your_dataset/
├── __init__.py        # empty
├── model.py           # SQLAlchemy ORM + Pydantic schemas
├── parser.py          # YourParser(BaseParser[YourRecord])
├── source.py          # YourSource(BaseSource)
└── dataset.py         # registers a DatasetDefinition
```

Plus an Alembic migration and tests. **No changes to `api/`, `cli.py`, `orchestrator.py`, or anything in `core/`.** If you find yourself needing to modify those, surface it in your PR — that's a design conversation, not a code conversation.

### 1.11 Contributor checklist before opening a PR

- [ ] `uv run pytest` — all green
- [ ] `uv run pytest --cov=govlink` — coverage ≥ 95% on new code
- [ ] `uv run ruff check .` — clean
- [ ] `uv run ruff format --check .` — clean
- [ ] `uv run mypy govlink` — clean (strict mode)
- [ ] If you added a dataset: `uv run govlink datasets list` shows it
- [ ] If you changed the schema: a new Alembic migration is committed
- [ ] If you changed a parser: fixture PDFs and JSON oracles updated/added
- [ ] No `print()` statements (use `structlog`)
- [ ] No `float` for numeric data (use `Decimal` / `DecimalStr`)
- [ ] No `requests` / `aiohttp` (use `httpx`)

---

## Part 2 — Frontend Integration Guide

You don't need Python, uv, or any of the contributor tooling to integrate with govlink. You need an HTTP client and the API base URL.

This section assumes the API is running somewhere reachable. For local testing, follow Part 1 sections 1.1–1.7 to get a server on `http://127.0.0.1:8000`. For production, swap the base URL.

### 2.1 The shape of every response

All data endpoints return the same envelope:

```json
{
  "data": [ /* array of records */ ],
  "meta": {
    "dataset": "exchange-rates",
    "count": 33,
    "total": 33,
    "limit": 100,
    "offset": 0,
    "snapshot_date": "2026-04-30",
    "generated_at": "2026-05-03T14:32:11.123456+00:00"
  }
}
```

- `data` — the records you care about
- `meta.count` — number of records in *this* response
- `meta.total` — number of records matching your query (for pagination math)
- `meta.snapshot_date` — only set on `/latest`; null on `/historical`
- `meta.generated_at` — server-side timestamp, ISO 8601 with timezone

Errors return a different envelope:

```json
{
  "error": {
    "code": "dataset_not_found",
    "message": "Dataset 'foo' not found",
    "details": null
  }
}
```

### 2.2 Decimal values are strings, not numbers

This is the most important thing to know as a frontend dev:

```json
{
  "currency_code": "USD",
  "rate": "72.39",            ← string
  "rate_per_unit": "72.39000000",  ← string
  "unit_multiplier": 1        ← number (it's an integer)
}
```

Why: financial precision. JavaScript's `Number` type can't safely represent values like `0.0082` without loss; serialising as a string preserves the exact value the central bank published. **Always parse with `parseFloat`/`Number` only at the moment of display**, never for math. For currency math, use `BigInt`, `decimal.js`, or your framework's money library.

### 2.3 Endpoint reference (with copy-paste examples)

Base URL in examples: `http://127.0.0.1:8000`. Replace with your deployed URL.

#### `GET /` — Service info

```bash
curl http://127.0.0.1:8000/
```
```json
{ "name": "govlink", "version": "0.1.0", "docs": "/docs" }
```

#### `GET /health` — Health check (use for uptime monitors)

```bash
curl http://127.0.0.1:8000/health
```
```json
{ "status": "ok" }
```

Not rate-limited. Safe to poll every few seconds.

#### `GET /datasets` — List all datasets

```bash
curl http://127.0.0.1:8000/datasets
```
```json
{
  "data": [
    {
      "slug": "exchange-rates",
      "title": "Daily Valuation Exchange Rates",
      "description": "Official daily valuation exchange rates...",
      "publisher": "Central Bank of The Gambia",
      "source_url": "https://www.cbg.gm/daily-valuation-exchange-rate",
      "frequency": "daily",
      "last_ingested_at": "2026-05-03T14:00:00+00:00"
    }
  ],
  "meta": { "count": 1, "generated_at": "..." }
}
```

Use this on your landing page or directory view.

#### `GET /datasets/{slug}` — Single dataset metadata

```bash
curl http://127.0.0.1:8000/datasets/exchange-rates
```

Returns the same shape as a single entry from `/datasets`, plus the field schema for that dataset.

#### `GET /datasets/{slug}/latest` — Most recent snapshot

```bash
curl http://127.0.0.1:8000/datasets/exchange-rates/latest
```
```json
{
  "data": [
    {
      "snapshot_date": "2026-04-30",
      "currency_code": "USD",
      "currency_name": "US DOLLAR",
      "rate": "72.39",
      "unit_multiplier": 1,
      "rate_per_unit": "72.39000000"
    },
    /* ... 32 more rows ... */
  ],
  "meta": {
    "dataset": "exchange-rates",
    "count": 33,
    "snapshot_date": "2026-04-30",
    "generated_at": "..."
  }
}
```

The most useful endpoint for "show me today's rates" UIs.

#### `GET /datasets/{slug}/historical` — Range queries

Query parameters:

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `from` | `YYYY-MM-DD` | none | inclusive lower bound on `snapshot_date` |
| `to` | `YYYY-MM-DD` | none | inclusive upper bound |
| `currency` | string | none | e.g. `USD` (only available on exchange-rates) |
| `limit` | int | 100 | max 1000 |
| `offset` | int | 0 | for pagination |

```bash
# All USD rates for April 2026
curl "http://127.0.0.1:8000/datasets/exchange-rates/historical?from=2026-04-01&to=2026-04-30&currency=USD"

# Page 2 of last 30 days
curl "http://127.0.0.1:8000/datasets/exchange-rates/historical?from=2026-04-01&limit=50&offset=50"
```

Records are returned newest-first (`ORDER BY snapshot_date DESC`).

#### `GET /datasets/{slug}/csv` — CSV export

```bash
# Full dataset
curl -O http://127.0.0.1:8000/datasets/exchange-rates/csv

# Filtered (same query params as historical, except no limit/offset)
curl -O "http://127.0.0.1:8000/datasets/exchange-rates/csv?from=2026-01-01&currency=USD"
```

Returns `text/csv; charset=utf-8` with a `Content-Disposition: attachment` header. Browsers will prompt a download; programmatic clients get the bytes.

The first row is always the header: `snapshot_date,currency_code,currency_name,rate,unit_multiplier,rate_per_unit`.

#### `GET /admin/health` — Per-dataset freshness

```bash
curl http://127.0.0.1:8000/admin/health
```
```json
{
  "data": [
    {
      "slug": "exchange-rates",
      "last_ingested_at": "2026-05-03T14:00:00+00:00",
      "latest_snapshot_date": "2026-04-30",
      "is_stale": false
    }
  ],
  "meta": { "count": 1, "generated_at": "..." }
}
```

`is_stale: true` when last ingestion was longer ago than the dataset's frequency allows (26h for daily, ~31 days for monthly). Useful for status pages and operational dashboards. Not rate-limited — safe for monitoring scrapers.

### 2.4 Rate limiting

Data endpoints (`/datasets/{slug}/latest`, `/historical`, `/csv`) are limited to **60 requests per minute per IP**. Exceeding the limit returns HTTP 429:

```json
{ "error": { "code": "rate_limit_exceeded", "message": "...", "details": null } }
```

Meta endpoints (`/`, `/health`) and admin endpoints (`/admin/*`) are not rate-limited.

If you're building a dashboard that polls every few seconds, prefer `/health` or `/admin/health` for keep-alives, and only hit `/latest` when you actually need fresh data.

### 2.5 CORS

The API enables permissive CORS by default (`*`). For production, the deployed instance should restrict origins via the `GOVLINK_CORS_ORIGINS` environment variable (comma-separated list).

If you're hitting a govlink instance from a browser and getting CORS errors, ask the operator to add your origin to the allowlist.

### 2.6 Integration recipes

#### Vanilla JavaScript (browser fetch)

```javascript
async function getLatestRates() {
  const res = await fetch('http://127.0.0.1:8000/datasets/exchange-rates/latest');
  if (!res.ok) {
    const err = await res.json();
    throw new Error(`${err.error.code}: ${err.error.message}`);
  }
  const { data, meta } = await res.json();
  console.log(`Got ${meta.count} rates for ${meta.snapshot_date}`);
  return data;
}

// Render a table
const rates = await getLatestRates();
rates.forEach(r => {
  console.log(`${r.currency_code}: ${r.rate} (×${r.unit_multiplier})`);
});
```

#### TypeScript types

```typescript
interface ExchangeRate {
  snapshot_date: string;       // 'YYYY-MM-DD'
  currency_code: string;        // 'USD', 'EUR', etc.
  currency_name: string;        // 'US DOLLAR'
  rate: string;                 // decimal as string
  unit_multiplier: number;      // 1, 100, or 5000
  rate_per_unit: string;        // decimal as string
}

interface Meta {
  dataset?: string;
  count: number;
  total?: number;
  limit?: number;
  offset?: number;
  snapshot_date?: string | null;
  generated_at: string;          // ISO 8601
}

interface Response<T> {
  data: T;
  meta: Meta;
}

interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown> | null;
  };
}

// Usage
const res = await fetch('/datasets/exchange-rates/latest');
const body: Response<ExchangeRate[]> = await res.json();
```

#### React hook (with caching via SWR)

```tsx
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useLatestRates() {
  const { data, error, isLoading } = useSWR<Response<ExchangeRate[]>>(
    'http://127.0.0.1:8000/datasets/exchange-rates/latest',
    fetcher,
    { refreshInterval: 60_000 }  // re-fetch every minute
  );
  return {
    rates: data?.data ?? [],
    snapshotDate: data?.meta.snapshot_date,
    isLoading,
    error,
  };
}
```

#### Node.js / server-side rendering

```javascript
// Using built-in fetch (Node 18+)
const API = process.env.GOVLINK_API_URL || 'http://127.0.0.1:8000';

export async function getRatesForDate(date) {
  const url = new URL(`${API}/datasets/exchange-rates/historical`);
  url.searchParams.set('from', date);
  url.searchParams.set('to', date);
  const res = await fetch(url);
  return (await res.json()).data;
}
```

#### Currency converter widget

```javascript
async function convert(amount, fromCode, toCode) {
  const res = await fetch('http://127.0.0.1:8000/datasets/exchange-rates/latest');
  const { data } = await res.json();

  // Build a lookup of GMD per unit of each currency
  const ratesGMD = Object.fromEntries(
    data.map(r => [r.currency_code, parseFloat(r.rate_per_unit)])
  );

  if (fromCode === 'GMD') {
    return amount / ratesGMD[toCode];
  }
  if (toCode === 'GMD') {
    return amount * ratesGMD[fromCode];
  }
  // Cross-currency: GMD as the bridge
  const amountInGMD = amount * ratesGMD[fromCode];
  return amountInGMD / ratesGMD[toCode];
}

// console.log(await convert(100, 'USD', 'EUR'));
```

For a real application, hold this in state and refresh once per day rather than per conversion.

#### CSV download from the browser

```javascript
async function downloadCSV(filename = 'rates.csv') {
  const res = await fetch('http://127.0.0.1:8000/datasets/exchange-rates/csv');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```

### 2.7 Smoke-test your integration in 60 seconds

Drop this in browser DevTools (after starting the API per Part 1 §1.7) to verify your environment can reach the API and parse responses correctly:

```javascript
(async () => {
  const base = 'http://127.0.0.1:8000';

  console.log('1. Health check...');
  console.log(await (await fetch(`${base}/health`)).json());

  console.log('2. List datasets...');
  const list = await (await fetch(`${base}/datasets`)).json();
  console.log(`   → ${list.data.length} dataset(s)`);

  console.log('3. Latest rates...');
  const latest = await (await fetch(`${base}/datasets/exchange-rates/latest`)).json();
  console.log(`   → ${latest.meta.count} rates for ${latest.meta.snapshot_date}`);
  console.log(`   → USD: ${latest.data.find(r => r.currency_code === 'USD')?.rate}`);

  console.log('4. Historical (last 7 days)...');
  const today = new Date().toISOString().slice(0, 10);
  const hist = await (await fetch(`${base}/datasets/exchange-rates/historical?from=${today}&limit=5`)).json();
  console.log(`   → ${hist.data.length} of ${hist.meta.total} matching records`);

  console.log('✓ All checks passed');
})();
```

If any step fails, the error message tells you exactly which one — fix that and re-run.

### 2.8 Deployment hints for frontend apps

- **Don't proxy** API calls through your backend unless you have a reason to. govlink is open data — direct browser calls are fine.
- **Cache aggressively.** Exchange rates update once per weekday; a CDN edge cache with a 1-hour TTL on `/latest` is reasonable.
- **Show staleness honestly.** If `meta.snapshot_date` is more than a couple of business days old, show a banner. Use `/admin/health` as a status indicator if you're building an operational UI.
- **Handle 429s gracefully.** Back off and retry after 60 seconds. Don't retry-storm.
- **Pin to a base URL via env var.** Don't hardcode `127.0.0.1:8000` — make it configurable so the same build works in dev and prod.

---

## Troubleshooting

### Contributor issues

**`uv: command not found`**
Install uv via `curl -LsSf https://astral.sh/uv/install.sh | sh`, then restart your shell.

**Tests fail with `DeprecationWarning treated as error`**
A dependency upgraded and started emitting a new warning. Either pin the dependency or add a targeted ignore in `pyproject.toml`'s `[tool.pytest.ini_options]` `filterwarnings`.

**`ModuleNotFoundError: No module named 'govlink.datasets.foo'` in tests**
The dataset's `dataset.py` is failing to import. Run `uv run python -c "import govlink.datasets.foo.dataset"` to see the underlying error.

**Ingestion fails with `httpx.ConnectError`**
You're offline, or `https://www.cbg.gm` is down. The fixture-driven tests (`uv run pytest`) don't need network; only live ingestion does.

**SQLite `database is locked` during a test**
You're running multiple test processes against the same on-disk DB. Tests use `:memory:` engines per-test by design — if you're seeing this, you've accidentally pointed a test at the real `./govlink.db`.

**`alembic` says "Target database is not up to date"**
Run `GOVLINK_DATABASE_URL=sqlite:///./your.db uv run alembic upgrade head`.

### Frontend integration issues

**CORS error in the browser**
The deployed instance hasn't allowlisted your origin. Ask the operator to update `GOVLINK_CORS_ORIGINS`.

**`rate` is `"72.39"` not `72.39` and my chart library breaks**
By design (financial precision). Convert to number at the display layer: `Number(record.rate)` or `parseFloat(record.rate)`.

**429 Too Many Requests during development**
You're hitting `/datasets/.../latest` more than 60 times per minute. Add caching (SWR, React Query, etc.) or lower your refresh rate.

**Empty `data: []` from `/latest`**
No ingestion has run yet on that instance. Run `govlink ingest exchange-rates` on the server, or wait for the scheduled job.

**`{"error": {"code": "dataset_not_found"}}`**
Check spelling — the slug uses hyphens (`exchange-rates`), not underscores. And `GET /datasets` to see what's actually registered.

---

## What good looks like

You should now be able to:

- Run all 311 tests on your machine in under 10 seconds
- Ingest live data from CBG and query it via the CLI
- Hit every API endpoint with curl and get the documented response shape
- Build a frontend integration with confidence about types, error shapes, and rate limits

If any of those don't work as described, that's a bug in the project or the docs — please open an issue with the exact command and output.
