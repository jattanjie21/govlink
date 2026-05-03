# Vercel deployment

The frontend is a static Vite SPA. Vercel auto-detects the framework, runs `npm run build`, and serves the contents of `dist/`.

## Live URLs

- **Production:** <https://govlink.vercel.app>
- **Project dashboard:** <https://vercel.com/musa-a-jallows-projects/govlink>

The Vercel project is linked to the `musa-a-jallows-projects` scope. The first production deploy was promoted directly via `vercel deploy --prod`.

## What's already wired in the repo

| File                       | Purpose                                                                                    |
|----------------------------|--------------------------------------------------------------------------------------------|
| `vercel.json`              | SPA rewrite: every path falls back to `/index.html` so client-side routes survive refresh. |
| `package.json` scripts     | `deploy:preview` → `vercel deploy`, `deploy:prod` → `vercel deploy --prod`.                |
| `vercel` (devDependency)   | CLI pinned per-project; no global install needed. Use `npx vercel ...`.                    |
| Root `.gitignore`          | Ignores `.vercel/` so the project-link metadata stays local.                                |

## Prerequisites

- Node ≥ 20 and `npm` on the machine you're deploying from.
- A free Vercel account (sign in with GitHub or Google when prompted).

## First-time setup

Run from `frontend/`:

```bash
cd frontend

# 1) One-time login (opens a browser to authorise the CLI)
npx vercel login

# 2) Link the folder to a Vercel project (creates one if needed)
#    Prompts and recommended answers:
#      Set up and deploy?                       Y
#      Which scope?                             <your personal account>
#      Link to existing project?                N
#      What's your project's name?              govlink            # becomes the subdomain
#      In which directory is your code located? ./                 # default
#      Auto-detect framework / settings?        Y                  # accept Vite defaults
#
#    The first run also produces a preview deploy URL of the form
#    https://govlink-<hash>-<scope>.vercel.app
npx vercel
```

After this, a `.vercel/` folder appears with `project.json` linking the repo to the Vercel project. It is gitignored.

## Day-to-day deploys

```bash
cd frontend

# Preview deploy — gets a unique URL, doesn't touch production
npm run deploy:preview

# Promote to production — overwrites the canonical https://<project>.vercel.app URL
npm run deploy:prod
```

Vercel uses the **default `*.vercel.app` domain** until a custom domain is added via the dashboard. No domain configuration is required for either preview or production.

## Environment variables

The frontend reads three Vite-time env vars (see `frontend/.env.example`):

| Variable                  | Purpose                                                                  | Production value                |
|---------------------------|--------------------------------------------------------------------------|---------------------------------|
| `VITE_API_URL`            | Axios `baseURL` — where browser fetches go.                              | The deployed backend's origin.  |
| `VITE_API_PUBLIC_URL`     | Public-facing URL shown in code snippets and Swagger / OpenAPI links.   | Same as `VITE_API_URL`.         |
| `VITE_API_PROXY_TARGET`   | Only used by the local dev proxy. Not needed in production.             | *(leave unset on Vercel)*       |

Set them on Vercel **per environment** (Production / Preview / Development). Two ways:

```bash
# Via CLI — adds to Production by default; pass `preview` or `development` to scope it
npx vercel env add VITE_API_URL production
npx vercel env add VITE_API_PUBLIC_URL production
```

Or via the dashboard: **Project → Settings → Environment Variables**.

After changing env vars, redeploy: `npm run deploy:prod` (env vars are baked into the bundle at build time, so a redeploy is required for changes to take effect).

## Current state — backend not yet deployed

The production deploy at <https://govlink.vercel.app> is live but no `VITE_*` env vars are set on Vercel yet. The frontend falls back to its dev defaults:

| Variable                | Build-time fallback         | Effect on production                                                  |
|-------------------------|-----------------------------|-----------------------------------------------------------------------|
| `VITE_API_URL`          | `/api`                      | Browser fetches go to `https://govlink.vercel.app/api/*` and 404.     |
| `VITE_API_PUBLIC_URL`   | `http://localhost:8000`     | Code snippets and Swagger / OpenAPI links point at localhost.         |

Pages render correctly. Browse / dataset detail / Operator render the calm "No data available" empty state instead of a hard error (see `src/components/States.tsx`). That is the intended interim experience; do **not** set the env vars to placeholder values, since pointing the bundle at a dead URL is worse than the current state.

## When the backend ships

Once the backend has a public origin (assume `https://api.example.com` below):

```bash
cd frontend

# Add the two production env vars (interactive prompt asks for the value)
npx vercel env add VITE_API_URL production
npx vercel env add VITE_API_PUBLIC_URL production

# Both should be set to the backend's public origin, e.g.:
#   VITE_API_URL          = https://api.example.com
#   VITE_API_PUBLIC_URL   = https://api.example.com

# Rebuild — env vars are baked in at build time, so a redeploy is mandatory
npm run deploy:prod
```

Backend side, before the redeploy:

- Add `https://govlink.vercel.app` (and `https://*.vercel.app` if previews should reach prod data) to the FastAPI CORS allow-list.
- Confirm `/datasets`, `/datasets/{slug}`, `/admin/health`, etc. are reachable over plain HTTPS from the new origin.

## Troubleshooting

- **404 on direct load of `/about` (or any non-root route)** — `vercel.json` is missing the SPA rewrite. Check it exists at `frontend/vercel.json` and is committed.
- **API calls 404 in production** — `VITE_API_URL` is unset, so it falls back to the dev default `/api`. Add it via the dashboard or `npx vercel env add` and redeploy.
- **Build fails with "Module not found `vercel`"** — run `npm install` in `frontend/` to pull the pinned CLI from `package.json`.
- **`vercel login` opens nothing** — copy the URL the CLI prints into a browser manually.
