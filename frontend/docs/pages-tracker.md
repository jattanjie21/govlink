# Frontend pages tracker

Maps every HTML mockup in `./html/` to its backend dependency and current implementation status.

**Legend**
- 🟢 **Buildable now** — backend endpoints exist
- 🟡 **Partially buildable** — frontend can render with stubs/mocks; some interactions need backend work
- 🔴 **Blocked on backend** — wait until matching API ships
- ➖ **Reference only** — not a runtime page

When the backend grows new capabilities, flip 🔴 → 🟢 and start building.

---

## Public site (`html/` → `src/routes/`)

| # | Mock                          | Status | Backend dependency                                                  | Implemented |
|---|-------------------------------|--------|---------------------------------------------------------------------|:-----------:|
| 1 | `index.html`                  | 🟢     | `GET /datasets`                                                     |     [x]     |
| 2 | `browse.html`                 | 🟡     | `GET /datasets` (server-side faceted filters by category/org/country/tags don't exist — implement client-side filter only) | [x]         |
| 3 | `dataset-detail.html`         | 🟢     | `GET /datasets/:slug`, `GET /datasets/:slug/latest`, `GET /datasets/:slug/historical` (drives the Preview tab) |     [x]     |
| 4 | `dataset-api.html`            | 🟢     | Static docs page — endpoints already exist; live "Try it" calls `GET /datasets/:slug/{latest,historical,csv}` | [x] |
| 5 | `reports.html`                | 🔴     | No `/reports` backend                                               |     [ ]     |
| 6 | `report-read.html`            | 🔴     | No `/reports/:slug` backend                                         |     [ ]     |
| 7 | `developer.html`              | 🔴     | No `/me/api-keys`, no quota endpoints, no auth                      |     [ ]     |
| 8 | `auth.html`                   | 🔴     | No `/auth/*` backend                                                |     [ ]     |

## Admin dashboard (`html/admin-*.html` → `src/routes/admin/`)

| #  | Mock                             | Status | Backend dependency                                                            | Implemented |
|----|----------------------------------|--------|--------------------------------------------------------------------------------|:-----------:|
| 9  | `admin-overview.html`            | 🔴     | KPIs + ingestion queue + alerts feed — none of these endpoints exist           |     [ ]     |
| 10 | `admin-ingestion-wizard.html`    | 🔴     | No upload pipeline. Backend ingestion is plugin-based via Python — no UI hook  |     [ ]     |
| 11 | `admin-ingestion-job.html`       | 🔴     | No SSE stream, no job status endpoints                                          |     [ ]     |
| 12 | `admin-dataset-insights.html`    | 🔴     | No `/insights/*` analytics                                                      |     [ ]     |
| 13 | `admin-reports-editor.html`      | 🔴     | No `/admin/reports/*`                                                           |     [ ]     |
| 14 | `admin-users.html`               | 🔴     | No `/admin/users` (and no auth)                                                 |     [ ]     |
| 15 | `admin-settings.html`            | 🔴     | No `/admin/settings`                                                            |     [ ]     |

## Pages NOT in the HTML mocks but worth building

| Mock | Status | Backend dependency | Implemented |
|------|--------|--------------------|:-----------:|
| **Operator health** (`/operator`) — no mock; mirror `style-guide.html` patterns | 🟢 | `GET /admin/health` | [x] |
| **API docs landing** (`/api-docs`) — no mock; complements per-dataset API tab | 🟢 | `GET /datasets` | [x] |
| **404** | 🟢 | none | [x] |

## System artifacts (reference only, not React routes)

| #  | File                  | Use during development                                                  |
|----|-----------------------|-------------------------------------------------------------------------|
| 16 | `style-guide.html`    | Visual contract for tokens, type, motion, accessibility                 |
| 17 | `components.html`     | Component library — every state for every primitive (build these first) |
| 18 | `handoff.html`        | shadcn primitive mapping + recommended file layout                       |
| 19 | `brand-assets.html`   | Wordmark, mark, favicon set, OG card                                    |
| 20 | `command-palette.html`| Reference for `Cmd+K` palette (optional feature, would need a search backend or client-side index) |

## Source files (drop into the React app)

| File                  | Where it goes                                                              |
|-----------------------|----------------------------------------------------------------------------|
| `tokens.css`          | `src/styles/tokens.css`, imported once at the top of `src/index.css`        |
| `tailwind.config.ts`  | Repo root (replace any starter config). Tailwind v4 reads it via `@config`  |
| `brand-spec.md`       | Stays in `docs/html/` as authoritative reference                            |

---

## v0 buildable scope (shipped)

Pages live against today's backend on `feat/frontend-public`:

1. ☑ Home (`/`)
2. ☑ Browse (`/datasets`)
3. ☑ Dataset detail (`/datasets/:slug`) — Overview + Preview + API tabs
4. ☑ Dataset API tab (`/datasets/:slug/api`) — live try-it + 4-language snippets
5. ☑ Operator health (`/operator`)
6. ☑ API docs landing (`/api-docs`)
7. ☑ 404 (`*`)

Everything else is parked until the backend ships the underlying endpoints.

---

## How to translate the HTML mocks into React

The HTML files are **the visual contract**, not the implementation. They're hand-authored, theme-toggle ready, and reference real Gambian context — treat them as a higher-fidelity Figma. Recommended workflow:

### Step 1 — Land the design system once
1. Copy `html/tokens.css` → `src/styles/tokens.css` and `@import` it from `src/index.css`. This gives every component the same CSS custom properties the mocks use (`var(--canvas)`, `var(--ink)`, etc.).
2. Copy `html/tailwind.config.ts` to the repo root. Tailwind utilities resolve through the same tokens, so a class like `bg-canvas` in HTML works the same in JSX.
3. Add the Google Fonts link (Fraunces 400/600 + Geist 400/500/600 + JetBrains Mono 400/500) to `index.html`.
4. Mount the theme toggle: `<html data-theme="light|dark">` driven by `localStorage['govlink-theme']` — match the mock's behaviour exactly.

After this, any markup pasted from a mock should look identical in the React app.

### Step 2 — Build primitives from `components.html` first
Open `components.html`. It shows every primitive in every state (default / hover / focus / active / disabled / loading / empty / error). Port them into `src/components/ui/` **before** any pages:
- `Button`, `Input`, `Select`, `Checkbox`, `Tabs`, `Chip`, `StatusPill`, `Badge`, `Card`, `Table`, `EmptyState`, `ErrorState`, `LoadingTable`, `Skeleton`, `Toast`, `Dialog`

Use `handoff.html` as the shadcn-primitive mapping guide — it tells you which shadcn component to start from and what to override.

### Step 3 — Build layout chrome from `index.html`
- `SiteHeader` (wordmark, nav, theme toggle, Cmd+K trigger)
- `SiteFooter` (with the 1px national-color stripe per `brand-spec.md`)
- `Container` (12-col, 1200px max, responsive gutters)

These are reused on every public page.

### Step 4 — Port one page at a time
For each of the six v0 pages, follow the same loop:

1. **Open the mock** in a browser and the corresponding React file in your editor side-by-side.
2. **Read structure top to bottom**, identify the section breaks (hero / strip / grid / table / footer).
3. **Recreate in JSX** section by section, replacing repeated markup with the primitives from step 2 and your shared components (`DatasetCard`, `SchemaTable`, etc.).
4. **Swap mock data for TanStack Query** — wrap the API call in a hook (`useDatasets()`, `useDatasetDetail(slug)`), pipe through the `unwrap()` envelope helper.
5. **Wire empty / error / loading states** using the matching `components.html` patterns.
6. **Pixel-check** against the mock at 1440 / 768 / 375. The mock is the contract — divergence needs a deliberate decision.

### What NOT to do
- ❌ Don't copy raw markup into a single giant component. Decompose first.
- ❌ Don't import the `.html` files at runtime or render them via `dangerouslySetInnerHTML`. They are reference material, not source.
- ❌ Don't redesign while porting. If a mock is wrong, file it as a follow-up — don't fix it inline.
- ❌ Don't replace the design tokens with ad-hoc values. Everything goes through `tokens.css`.

### Tooling shortcuts
- Keep the mock open in a browser tab while you code; refresh the React dev server side-by-side.
- Most class names in the mocks are direct Tailwind utilities — they should compile against your config without translation. Audit anything that looks bespoke (custom data-attributes, raw `style="..."`).
- For tables: copy the `<table>` skeleton verbatim, swap mock `<tr>`s for a `.map()`, keep the column-rule hairlines and tabular numerals classes intact.

---

## When the backend grows

Each new backend endpoint unlocks a 🔴 row. Process:

1. Update this file: flip status, link the new endpoint(s).
2. Spin a feature branch off `feat/frontend-public` (e.g. `feat/reports-page`).
3. Port the corresponding HTML mock following the four steps above.
4. Tick the checkbox here when the page lands on `main`.
