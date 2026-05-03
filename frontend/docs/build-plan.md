# Frontend build plan

Source of truth for what the React client needs to do, derived from the backend implementation in `../backend/` (see `backend/CLAUDE.md` and `backend/docs/api-reference.md`).

This is **not** the original DataSetu spec — that scope (admin upload wizard, RBAC, reports editor, insights dashboards) was dropped when the project pivoted to "open data viewer for Gambian government datasets." The frontend is a public, read-only site plus an operator health page.

---

## Backend at a glance

> **The architectural bet (CLAUDE.md):** *adding a new dataset should require zero changes outside `govlink/datasets/<slug>/`.*

The backend exposes one set of generic endpoints that work for **any** registered dataset. The frontend should mirror this — no dataset-specific pages or hard-coded columns.

Currently registered: **one dataset, `exchange-rates`** (CBG daily). More will land via the backend's plugin pattern.

### All available endpoints (no auth, CORS open)

| Method | Path                            | Notes                                                   | Rate limit |
|--------|---------------------------------|---------------------------------------------------------|------------|
| GET    | `/`                             | Service info                                            | none       |
| GET    | `/health`                       | Liveness probe                                          | none       |
| GET    | `/datasets`                     | List registered datasets                                | none       |
| GET    | `/datasets/{slug}`              | Metadata + declared field schema                        | none       |
| GET    | `/datasets/{slug}/latest`       | Most recent snapshot, all rows                          | 60/min/IP  |
| GET    | `/datasets/{slug}/historical`   | `from`, `to`, `currency?`, `limit` (1–1000), `offset`   | 60/min/IP  |
| GET    | `/datasets/{slug}/csv`          | CSV stream; same filters as historical (no pagination)  | 60/min/IP  |
| GET    | `/admin/health`                 | Per-dataset freshness for monitoring                    | none       |

Swagger UI: `GET /docs`. ReDoc: `GET /redoc`. OpenAPI: `GET /openapi.json`.

### Response envelope (every data response)

```ts
{
  data: T | T[],
  meta: {
    dataset: string,
    count: number,
    total?: number,           // only on /historical
    limit?: number,           // only on /historical
    offset?: number,          // only on /historical
    snapshot_date?: string,   // only on /latest, format YYYY-MM-DD
    generated_at: string      // ISO-8601 UTC
  }
}
```

### Error envelope (when an endpoint fails)

```ts
{ error: { code: string, message: string, details?: unknown } }
```

Common codes:
- `404` → `dataset_not_found`
- `429` → `rate_limit_exceeded`
- `422` → **NOT** this envelope — FastAPI's default validation shape

### Conventions the frontend MUST honour

1. **Decimals are JSON strings.** Backend uses `DecimalStr` (`Annotated[Decimal, PlainSerializer(str)]`) so values like `"rate": "1132.65"` come over the wire as strings to avoid float-precision drift. **Do not** `Number(rate)` for display; either keep them as strings or parse with `decimal.js` only at the formatting boundary.
2. **Dates** are `YYYY-MM-DD` strings (`snapshot_date`).
3. **Datetimes** are ISO-8601 UTC strings (`generated_at`, `last_ingested_at`).
4. **Pagination** is offset-based (not cursor). Use `meta.total` to drive a paginator.
5. **`currency` filter** only makes sense on datasets whose schema includes a `currency_code` field — render the filter conditionally based on `GET /datasets/:slug` response.

---

## Pages to build

### 1. Home (`/`)
- One-paragraph pitch ("open data for Gambian government datasets")
- Card grid of registered datasets (calls `GET /datasets`)
- Each card → `/datasets/:slug`
- Link to `/operator` for the freshness page
- Footer with credits + GitHub link

### 2. Datasets index (`/datasets`)
- Same data as Home's grid, denser list view (one row per dataset)
- Columns: title, publisher, frequency, last updated (joins with `/admin/health` data)

### 3. Dataset detail (`/datasets/:slug`) — **the main screen**
Driven entirely by `GET /datasets/:slug`. **Do not hard-code columns.**
- **Hero:** title, publisher (with verified badge if `gov`), frequency chip, source URL link, "last updated" from `/admin/health`
- **Tabs:**
  - **Latest** — table of `GET /datasets/:slug/latest`. Columns from `data[0]` keys (or schema). Show `meta.snapshot_date` as the heading.
  - **Historical** — `from`/`to` date pickers, optional `currency` dropdown (render only if `currency_code` in schema), paginator using `meta.total` + `limit`/`offset`. Table same shape as Latest.
  - **Download** — CSV button (anchor to `/datasets/:slug/csv?...` with current filters). Show estimated row count from a HEAD-ish summary (or just from historical's `meta.total`).
  - **API** — list the 4 endpoints with curl snippets that reflect the current filter state. "Copy" button on each.
- **Empty/error states:** dataset has no rows yet → "Not yet ingested." `404` → "Dataset not found." `429` → "Rate limited, try again in a minute."

### 4. Operator health (`/operator`)
- Renders `GET /admin/health` as a freshness grid
- Each card: dataset slug, frequency, `last_ingested_at` ("3 hours ago"), `latest_snapshot_date`, `is_stale` badge
- Auto-refresh every 30s (TanStack Query `refetchInterval`)
- No auth — this is an open monitoring page, matching the backend's design

### 5. 404 (`*`)
- Catch-all for unknown routes

---

## Stack to install

| Library                        | Why                                            |
|--------------------------------|-----------------------------------------------|
| `typescript`                   | Strict types                                  |
| `tailwindcss@4` + `@tailwindcss/vite` | Editorial design tokens                |
| `react-router-dom@7`           | Routing                                        |
| `@tanstack/react-query@5`      | Caching + auto-refresh on `/operator`         |
| `axios`                        | HTTP client                                   |
| `clsx` + `tailwind-merge`      | `cn()` helper                                  |
| `lucide-react`                 | Icons                                          |
| `decimal.js` *(optional)*      | Format `DecimalStr` values precisely          |

**Not needed** (compared to the archived admin work): no auth context, no `RequireAuth`, no recharts (no insights dashboards now), no codemirror (no reports editor).

---

## Design direction (kept from spec §8)

Authoritative, calm, editorial. Reference: The Pudding × Our World in Data × Stripe Docs.

- **Type:** Fraunces (display) + Inter Tight (body) — load from Google Fonts
- **Palette:** off-white `#FAF8F4` canvas · ink `#1A1A1A` · single accent **deep teal `#0F4C5C`** · `accent-soft #E6EEF0`
- **Tables:** newspaper style — rule lines, tabular numerals, no zebra-striping
- **Motion:** restrained — fade-ins only, no parallax, no hero video
- **Avoid:** purple gradients, glassmorphism, neon, "AI-generated" looking cards

---

## Key shared utilities to write first

1. **`lib/api.ts`** — axios client with `baseURL = VITE_API_URL ?? "/api"` (Vite proxy → FastAPI `:8000`)
2. **`lib/envelope.ts`** — `unwrap<T>(promise)` helper that pulls `.data.data` and parses errors into a typed `ApiError` class. Without this every component writes `result?.data?.[0]`.
3. **`lib/format.ts`** — `formatDecimalStr(s, opts)`, `formatRelativeTime(iso)`, `formatDate(yyyymmdd)`
4. **`lib/types.ts`** — backend response types (`Envelope<T>`, `DatasetMeta`, `DatasetField`, `DatasetHealth`, `ApiErrorEnvelope`)

These four files unblock every page.

---

## Build order (suggested)

1. **Stack setup + theme** — install deps, Tailwind tokens (teal), Fraunces/Inter Tight, `cn` util
2. **API client + envelope helper + types** — the four shared utilities above
3. **App shell** — top nav (GovLink wordmark, links to Datasets + Operator), footer, route skeleton with index + 404
4. **Home + datasets index** — both consume `GET /datasets`; share a `DatasetCard` component
5. **Dataset detail (Overview + Latest tabs)** — generic table component, hero, tabs scaffold
6. **Dataset detail — Historical tab** — date pickers, currency filter (conditional), paginator
7. **Dataset detail — Download + API tabs** — CSV link, code-snippet panel
8. **Operator health page** — auto-refreshing freshness grid
9. **Polish** — empty/error/loading states across the board, 429 handling, accessibility pass

Each step gets its own commit on `feat/frontend-public`.

---

## Open questions to settle before merging the PR

1. Where does the frontend get deployed, and what `VITE_API_URL` should production use?
2. Do we want an `/about` page describing the project for non-technical visitors?
3. Light-mode only, or add a dark theme? (Spec didn't decide; recommend light-only for v0.)
4. Should the `/operator` page be linked from the public nav, or stay an unlisted ops URL? (Backend treats it as monitoring-grade; either works.)
