# API Reference

The govlink REST API exposes every registered dataset through the same set of generic endpoints. There is no per-dataset code path — the same `/datasets/{slug}/latest` route serves exchange rates, inflation, or anything else that's been registered.

For an interactive playground, run the API locally and open `http://localhost:8000/docs` (Swagger UI) or `/redoc`.

## Conventions

### Authentication

None. The API is open. Per-IP rate limiting is the only guardrail.

### Rate limiting

| Endpoint group | Limit |
|----------------|-------|
| Data endpoints (`/datasets/{slug}/...`) | 60 requests/minute per IP |
| Meta endpoints (`/`, `/health`) | Unlimited |
| Admin endpoints (`/admin/...`) | Unlimited |

A 429 response uses the standard error envelope (see below) with `error.code = "rate_limit_exceeded"`.

### Response envelope

Every data-bearing response wraps its payload in:

```json
{
  "data": [ ... ],
  "meta": {
    "dataset": "exchange-rates",
    "count": 33,
    "total": null,
    "limit": null,
    "offset": null,
    "snapshot_date": "2026-04-30",
    "generated_at": "2026-05-03T06:42:01.123456Z"
  }
}
```

`meta.count` is the number of items in `data`. `meta.total` is the total matching the query (only set on paginated endpoints). `meta.dataset`, `meta.snapshot_date`, and `meta.generated_at` provide context.

### Error format

```json
{
  "error": {
    "code": "dataset_not_found",
    "message": "Dataset 'foo' not found",
    "details": null
  }
}
```

Common error codes: `dataset_not_found`, `rate_limit_exceeded`. Validation errors from query parameters return a 422 with FastAPI's default error shape (path-list + message), not the envelope.

### Decimal precision

All monetary values (`rate`, `rate_per_unit` for exchange rates, etc.) are serialised as **JSON strings**, not numbers. This avoids float-precision drift on round-trips. Example:

```json
{ "rate": "1132.65", "rate_per_unit": "11.3265" }
```

Parse client-side with whatever decimal library you prefer.

### Pagination

Two query parameters apply to historical endpoints:

| Param | Type | Default | Range |
|-------|------|---------|-------|
| `limit` | int | 100 | 1–1000 |
| `offset` | int | 0 | ≥0 |

Out-of-range values return a 422 from FastAPI's query validator.

### Date filtering

Where supported (`/datasets/{slug}/historical`, `/datasets/{slug}/csv`):

| Param | Format | Notes |
|-------|--------|-------|
| `from` | `YYYY-MM-DD` | Inclusive lower bound on `snapshot_date` |
| `to` | `YYYY-MM-DD` | Inclusive upper bound on `snapshot_date` |
| `currency` | string | Optional; only applies to datasets whose model has a `currency_code` column |

Invalid formats return 422.

---

## Endpoints

### `GET /` — Service info

Identifying information for monitoring and debugging.

```bash
curl http://localhost:8000/
```

```json
{
  "name": "govlink",
  "version": "0.1.0",
  "docs": "/docs"
}
```

---

### `GET /health` — Liveness probe

Always returns `200 OK` if the application process is up. Suitable for load-balancer probes.

```bash
curl http://localhost:8000/health
```

```json
{ "status": "ok" }
```

---

### `GET /datasets` — List all registered datasets

```bash
curl http://localhost:8000/datasets
```

```json
{
  "data": [
    {
      "slug": "exchange-rates",
      "title": "Daily Valuation Exchange Rates",
      "description": "Official daily valuation exchange rates published by the Central Bank of The Gambia ...",
      "publisher": "Central Bank of The Gambia",
      "source_url": "https://www.cbg.gm/daily-valuation-exchange-rate",
      "frequency": "daily"
    }
  ],
  "meta": { "count": 1, "generated_at": "2026-05-03T06:42:01.123456Z", ... }
}
```

---

### `GET /datasets/{slug}` — Dataset metadata

Returns the dataset's identifying metadata plus its declared field schema.

```bash
curl http://localhost:8000/datasets/exchange-rates
```

```json
{
  "data": {
    "slug": "exchange-rates",
    "title": "Daily Valuation Exchange Rates",
    "description": "...",
    "publisher": "Central Bank of The Gambia",
    "source_url": "https://www.cbg.gm/daily-valuation-exchange-rate",
    "frequency": "daily",
    "data_table_name": "data_exchange_rates",
    "fields": [
      { "name": "snapshot_date", "type": "<class 'datetime.date'>" },
      { "name": "currency_code", "type": "<class 'str'>" },
      { "name": "currency_name", "type": "<class 'str'>" },
      { "name": "rate", "type": "..." },
      { "name": "unit_multiplier", "type": "<class 'int'>" }
    ]
  },
  "meta": { "count": 1, "dataset": "exchange-rates", ... }
}
```

**Errors:** `404` with `error.code = "dataset_not_found"` if the slug is unknown.

---

### `GET /datasets/{slug}/latest` — Most recent snapshot

Returns every record from the most recent `snapshot_date`.

```bash
curl http://localhost:8000/datasets/exchange-rates/latest
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
      "rate_per_unit": "72.39"
    },
    {
      "snapshot_date": "2026-04-30",
      "currency_code": "JPY",
      "currency_name": "JAPANESE YEN",
      "rate": "45.18",
      "unit_multiplier": 100,
      "rate_per_unit": "0.4518"
    }
  ],
  "meta": {
    "dataset": "exchange-rates",
    "count": 33,
    "snapshot_date": "2026-04-30",
    "generated_at": "2026-05-03T06:42:01.123456Z"
  }
}
```

If the dataset has no records yet, `data` is `[]` and `meta.snapshot_date` is `null`.

**Errors:** `404` if the slug is unknown. `429` if rate-limited.

**Rate limit:** 60/minute per IP.

---

### `GET /datasets/{slug}/historical` — Paginated historical records

```bash
curl "http://localhost:8000/datasets/exchange-rates/historical?from=2026-01-01&to=2026-04-30&limit=50"
```

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `from` | date (`YYYY-MM-DD`) | none | Inclusive lower bound on `snapshot_date` |
| `to` | date (`YYYY-MM-DD`) | none | Inclusive upper bound on `snapshot_date` |
| `currency` | string | none | Filter to one currency code (only on datasets with `currency_code`) |
| `limit` | int (1–1000) | 100 | Page size |
| `offset` | int (≥0) | 0 | Page offset |

**Response shape:** same as `/latest` but with pagination metadata:

```json
{
  "data": [ /* up to {limit} records, newest first */ ],
  "meta": {
    "dataset": "exchange-rates",
    "count": 50,
    "total": 248,
    "limit": 50,
    "offset": 0,
    "generated_at": "2026-05-03T06:42:01.123456Z"
  }
}
```

`meta.total` reflects total matching records across the entire query, not just this page — useful for building a paginator.

**Errors:** `404` if slug unknown. `422` if `from`/`to` not in `YYYY-MM-DD` format or `limit`/`offset` out of range. `429` if rate-limited.

---

### `GET /datasets/{slug}/csv` — CSV export

Streams a CSV file with one row per record, columns in schema-declaration order.

```bash
curl -O "http://localhost:8000/datasets/exchange-rates/csv"
curl -O "http://localhost:8000/datasets/exchange-rates/csv?from=2026-04-01&to=2026-04-30&currency=USD"
```

**Response headers:**

```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="exchange-rates.csv"
```

**Response body** (truncated):

```csv
snapshot_date,currency_code,currency_name,rate,unit_multiplier,rate_per_unit
2026-04-30,USD,US DOLLAR,72.39,1,72.39
2026-04-30,EUR,EURO,86.56,1,86.56
2026-04-30,JPY,JAPANESE YEN,45.18,100,0.4518
...
```

Same query parameters as `/historical` (no `limit`/`offset` — CSV streams the full filtered set). An empty result produces a CSV with just the header row.

**Errors:** `404` if slug unknown. `429` if rate-limited.

---

### `GET /admin/health` — Per-dataset freshness

Operational endpoint for monitoring data freshness. **Not rate-limited** — designed to be polled by Prometheus, uptime monitors, etc.

```bash
curl http://localhost:8000/admin/health
```

```json
{
  "datasets": [
    {
      "slug": "exchange-rates",
      "frequency": "daily",
      "last_ingested_at": "2026-05-03T01:14:22.345678+00:00",
      "latest_snapshot_date": "2026-04-30",
      "is_stale": false
    }
  ],
  "count": 1
}
```

**`is_stale` thresholds** (from the dataset's declared frequency):

| Frequency | Threshold |
|-----------|-----------|
| daily | 26 hours |
| weekly | 170 hours |
| monthly | 745 hours |
| quarterly | 2208 hours |
| annual | 8784 hours |
| irregular | 8784 hours |
| (any other) | 48 hours |

Each threshold is the nominal cadence plus a small grace window for publication delays. A dataset that's never been ingested has `last_ingested_at: null` and `is_stale: true`.

---

## Swagger / OpenAPI

The full machine-readable schema lives at `GET /openapi.json`. Two pre-rendered viewers:

- `/docs` — Swagger UI (interactive, supports try-it-out)
- `/redoc` — ReDoc (cleaner read-only layout)

Both are served by FastAPI automatically; no extra configuration needed.
