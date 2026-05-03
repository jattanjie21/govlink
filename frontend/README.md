# GovLink — Frontend

The web client for [GovLink](../README.md). React 19 + TypeScript on Vite.

## Stack

- **React 19** + TypeScript + Vite 8
- **React Router 7** — routing (BrowserRouter, nested layouts)
- **TanStack Query 5** — data fetching, caching, auto-refresh
- **axios** — HTTP client (typed envelope + ApiError class)
- **Tailwind CSS 3.4** — utilities, theme wired through CSS variables
- **lucide-react** — icons
- **ESLint** — flat config, TypeScript-aware

The visual system (tokens, fonts, dark mode) lives in `src/styles/tokens.css` and `tailwind.config.ts`; the source-of-truth design reference is in [`docs/html/`](docs/html/README.md).

## Prerequisites

- Node.js 20.19+ or 22.12+ (required by Vite 8)
- npm 10+

## Setup

```bash
cd frontend
cp .env.example .env
npm install
```

## Development

```bash
npm run dev
```

Vite serves at `http://localhost:5173` and proxies `/api/*` to `http://localhost:8000` (the FastAPI backend). Override with `VITE_API_PROXY_TARGET` in `.env`. To start the backend, see [`../backend/README.md`](../backend/README.md).

## Available scripts

| Script | What it does |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | `tsc -b` + production bundle to `dist/` |
| `npm run typecheck` | TypeScript check, no emit |
| `npm run lint` | ESLint across `.ts` / `.tsx` |
| `npm run preview` | Serve the production build locally |

## Folder structure

```
frontend/
├── public/                Static assets
├── src/
│   ├── components/        Reusable UI primitives (DatasetCard, DataTable, …)
│   ├── layouts/           SiteLayout (header + outlet + footer)
│   ├── routes/            Page components (Home, Browse, Operator, …)
│   │   └── dataset/       Dataset detail layout + Overview / Preview / API tabs
│   ├── lib/               api, queries, types, format, theme, utils
│   ├── styles/tokens.css  Design tokens (light + dark)
│   ├── App.tsx            Route table
│   ├── main.tsx           Entry — providers (Query, Router) + AppShell
│   └── index.css          Tailwind + tokens import + base styles
├── docs/
│   ├── build-plan.md      What to build, derived from backend/CLAUDE.md
│   ├── pages-tracker.md   Per-page status (built / blocked-on-backend)
│   └── html/              Reference HTML mocks + tokens + tailwind config
├── tailwind.config.ts     Theme extension wired through tokens.css
├── tsconfig.{,app,node}.json
├── vite.config.ts         Includes /api → :8000 proxy
└── package.json
```

## Talking to the backend

`src/lib/api.ts` builds an axios client from `VITE_API_URL` (defaults to `/api`, which Vite proxies to the FastAPI server). Responses use the `{ data, meta }` envelope; errors are decoded into a typed `ApiError` class (`code`, `status`, `isNotFound`, `isRateLimited`).

Decimal values arrive as JSON strings (`DecimalStr`) — keep them as strings, format via `formatDecimalStr` from `src/lib/format.ts`. Never `Number(...)` them; you'll lose precision.

## Pages

Live (against today's backend):
- `/` Home
- `/datasets` Browse + client-side search
- `/datasets/:slug` Dataset detail — Overview / Preview / API tabs
- `/operator` Per-dataset freshness, auto-refresh
- `/api-docs` Endpoint reference + Swagger link
- `*` 404

Pages parked until the backend ships them (auth, reports, admin tooling) are tracked in [`docs/pages-tracker.md`](docs/pages-tracker.md).

## Contributing

Before opening a PR:

- [ ] `npm run typecheck` is clean
- [ ] `npm run lint` is clean
- [ ] `npm run build` succeeds
- [ ] You manually verified the change in the browser
