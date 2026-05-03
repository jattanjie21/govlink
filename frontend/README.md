# GovLink — Frontend

The web client for [GovLink](../README.md). Built with React 19 and Vite.

## Stack

- **React 19** — UI library
- **Vite 8** — dev server and build tool
- **ESLint** — linting (flat config, see `eslint.config.js`)

## Prerequisites

- **Node.js** 20.19+ or 22.12+ (required by Vite 8)
- **npm** 10+ (or `pnpm` / `yarn` if you prefer — lockfile is npm)

Check your version:

```bash
node --version
npm --version
```

## Setup

From the repository root:

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

Vite will start a dev server (default: http://localhost:5173) with hot module reload.

## Available scripts

| Script | What it does |
|---|---|
| `npm run dev` | Start the Vite dev server with HMR |
| `npm run build` | Type-check and produce a production bundle in `dist/` |
| `npm run preview` | Serve the production build locally for a final smoke-test |
| `npm run lint` | Run ESLint across the project |

## Folder structure

```
frontend/
├── public/              # Static assets served as-is (favicon, icons)
├── src/
│   ├── assets/          # Images and other imported assets
│   ├── App.jsx          # Root component
│   ├── main.jsx         # Entry point — mounts <App /> to #root
│   └── index.css        # Global styles
├── index.html           # HTML template (Vite entry)
├── eslint.config.js     # ESLint flat config
├── vite.config.js       # Vite config
└── package.json
```

## Talking to the backend

The backend API is developed on the [`backend`](../../../tree/backend) branch and exposes a REST API (default: `http://localhost:8000`). Once it lands on `main`, point the frontend at it via an environment variable — to be added when the integration work begins.

For now, the frontend is a standalone shell. You can develop UI, components, and design without a running backend.

## Contributing

See the [top-level contributing notes](../README.md#contributing). Before opening a PR, make sure:

- [ ] `npm run lint` is clean
- [ ] `npm run build` succeeds
- [ ] You have manually verified your change in the browser via `npm run dev`
