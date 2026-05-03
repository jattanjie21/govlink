---
name: ship-page
description: Port one HTML mock from frontend/docs/html/ into a real React route on feat/frontend-public, wire it to live backend endpoints, and tick the corresponding row in frontend/docs/pages-tracker.md. Use when the user asks to "build the X page", "implement the reports page", "port the developer page", or otherwise points at one of the 🟢 (or newly-unblocked) entries in the pages tracker.
disable-model-invocation: true
---

# ship-page

Translates a single HTML reference design from `frontend/docs/html/<page>.html` into a real React route under `frontend/src/routes/`, against today's backend, in the project's existing visual contract. Mirrors the workflow already in use on `feat/frontend-public`.

This skill creates and modifies files. Always confirm which page before scaffolding.

## When to invoke

Triggers:
- "Implement the reports page" / "build /reports"
- "Port `developer.html` to React"
- "Now that the backend has X, ship the Y page"
- A request that matches a row in `frontend/docs/pages-tracker.md`

Don't invoke for:
- Editing an existing page (just edit it)
- New components that aren't a page (build them in `src/components/`)
- Backend work (use `add-dataset` for ingestion plugins)

## Inputs to gather

| Input | Example | Notes |
|---|---|---|
| Mock file | `reports.html` | Must exist under `frontend/docs/html/` |
| Route path | `/reports` | Where it lives in the router |
| Tracker row | "Public site #5" | Confirms it's currently 🟢 buildable |
| Backend endpoints | `GET /reports`, `GET /reports/:slug` | Must already exist; if not, push back |

## The 4-step workflow (lifted from `frontend/docs/pages-tracker.md`)

1. **Land any tokens once**
   The design system already lives in the app — don't re-import `tokens.css` or rewrite `tailwind.config.ts`. Use the existing classes (`bg-canvas`, `text-ink`, `border-rule`, `font-display`, etc.).

2. **Build primitives from `frontend/docs/html/components.html` first**
   If the page needs a primitive that doesn't exist in `frontend/src/components/`, create it there before the page (Button, Tabs, etc.). Use `handoff.html` as the shadcn-mapping guide.

3. **Build the page top-to-bottom**
   - Open the mock side-by-side: `frontend/docs/html/<page>.html`
   - Decompose into sections (hero / strip / grid / table / footer)
   - Recreate in JSX section-by-section, replacing repeated markup with shared primitives (`Container`, `Eyebrow`, `Breadcrumbs`, `DatasetCard`, `DataTable`, `EmptyState`/`ErrorState`/`LoadingCardGrid`)
   - Replace mock data with TanStack Query hooks via `src/lib/queries.ts` — add new hooks if a new endpoint shape is needed
   - Pipe responses through `apiGet` / `apiGetEnvelope` / `apiGetRaw` from `src/lib/api.ts` (envelope-aware, throws typed `ApiError`)
   - Wire empty / error / loading using the matching `States.tsx` helpers
   - Pixel-check at 1440 / 768 / 375 in the browser

4. **Plumbing**
   - Register the route in `src/App.tsx`
   - Add to `SiteHeader` nav if it's a top-level page
   - Tick the row in `frontend/docs/pages-tracker.md` (`[ ]` → `[x]`)

## Hard rules (lifted from this codebase)

- **Decimals stay strings.** Backend uses `DecimalStr` (CLAUDE.md §1). Format with `formatDecimalStr` from `src/lib/format.ts`. **Never `Number(rate)`** — you'll lose precision.
- **Dates use `formatDate`** (`DD MMM YYYY`) per `frontend/docs/html/brand-spec.md`.
- **Tables use `DataTable`** (newspaper rules, no zebra, tabular numerals, auto-right-align numeric cols, auto-format `*_date` cells).
- **Don't import the `.html` files.** They're reference material, not source.
- **Don't redesign while porting.** If a mock is wrong, file a follow-up — don't fix inline.
- **Don't replace tokens with ad-hoc values.** Everything goes through `tokens.css` / Tailwind aliases.
- **Public-facing URLs** (Swagger, snippets) come from `API_PUBLIC_URL` in `src/lib/env.ts`. Don't hardcode `localhost:8000`.
- **Mobile-first sanity check.** SiteHeader is the most fragile spot — verify the page chrome doesn't break at 375px.

## Verify before committing

```bash
cd frontend
npm run typecheck   # tsc -b clean
npm run lint        # eslint clean
npm run build       # vite build clean
```

Manual browser check (the mock is the contract, divergence needs a deliberate decision):
- `npm run dev` → navigate to the new route
- Toggle dark/light theme — both should look intentional
- Resize through 1440 / 768 / 375 — header chrome, tables, and grids should all hold

## Commit shape

One commit per page on `feat/frontend-public`. Message body should call out:
- What HTML mock was ported
- Which backend endpoint(s) it consumes
- Any deviations from the mock (and why)
- Tracker row ticked

## Reference paths (always-loaded by Claude when this skill fires)

- `frontend/docs/pages-tracker.md` — what's buildable, what's done
- `frontend/docs/html/<page>.html` — the visual contract for the target page
- `frontend/docs/html/brand-spec.md` — type, palette, motion rules
- `frontend/docs/html/handoff.html` — shadcn primitive mapping
- `frontend/src/components/` — existing primitives (Container, Eyebrow, DatasetCard, DataTable, States, …)
- `frontend/src/lib/queries.ts` — every existing TanStack Query hook
