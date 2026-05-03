# govlink — Open data API for Gambian government datasets

A unified, machine-readable interface for public data published by Gambian
government institutions, starting with daily exchange rates from the Central
Bank of The Gambia.

## Why this exists

Public data published by Gambian government institutions is overwhelmingly
distributed as PDFs scattered across departmental websites — useful for a
human reader, but effectively closed to researchers, journalists, civic
technologists, and the wider developer community. Each new analysis project
repeats the same costly first step: scraping, parsing, and normalising the
same documents from scratch. `govlink` exists to do that work once, in the
open, and expose the resulting structured data through a stable REST API
that anyone can build on.

The project is designed to grow incrementally: each new dataset lives in its
own self-contained plugin, and the surrounding scaffold — ingestion, storage,
API serving, observability — is shared. The first dataset is the Central
Bank of The Gambia daily exchange rate sheet; many more are planned.

## Status

![Status](https://img.shields.io/badge/status-alpha-orange)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-311%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

The project is in **alpha**: one fully-functional dataset (CBG daily exchange
rates) is in production-ready shape, the ingestion pipeline and REST API are
both live, and the architecture is set up to scale to many more datasets via
the plugin pattern.

## Available datasets

| Dataset | Publisher | Frequency | Status |
|---------|-----------|-----------|--------|
| [Daily Exchange Rates](https://www.cbg.gm/daily-valuation-exchange-rate) | Central Bank of The Gambia | Daily (weekdays) | Active |

More datasets coming soon. Want to contribute one? See the
[contributor guide](docs/adding-a-dataset.md).

## Quickstart (local, SQLite)

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/TODO/govlink.git
cd govlink
cp .env.example .env
uv sync

# Initialise the local SQLite database
uv run govlink db init

# Pull the latest CBG exchange rate PDF and load it
uv run govlink ingest exchange-rates

# Start the API server
uv run uvicorn govlink.main:create_app --factory --host 127.0.0.1 --port 8000

# In another terminal:
curl http://localhost:8000/datasets/exchange-rates/latest
```

Open `http://localhost:8000/docs` for the Swagger UI.

## Quickstart (Docker)

Requires Docker and Docker Compose v2.

```bash
git clone https://github.com/TODO/govlink.git
cd govlink
docker compose up -d

# Verify
curl http://localhost:8000/health
# => {"status": "ok"}

# Open Swagger docs
open http://localhost:8000/docs

# Pull the first batch of data
docker compose exec api govlink ingest exchange-rates

# Stop
docker compose down
```

Postgres data and downloaded raw PDFs persist across restarts via Docker
volumes (`pgdata`, `rawdata`). To wipe state:

```bash
docker compose down -v
```

> **Production note:** `.env.docker` ships with dev-only defaults. Set a
> real `POSTGRES_PASSWORD` (and any other overrides) via your
> orchestrator's secrets system before deploying — never commit a
> production password to git.

## Project structure

```
govlink/
├── govlink/          # the Python package
│   ├── api/          # FastAPI routes, dependencies, exporters
│   ├── core/         # shared base classes, dataset registry, models, schemas
│   ├── datasets/     # one subfolder per dataset (plugin-style)
│   ├── cli.py        # Typer CLI entrypoint
│   ├── config.py     # pydantic-settings configuration
│   ├── db.py         # SQLAlchemy engine and session management
│   ├── logging.py    # structlog setup
│   └── main.py       # FastAPI application factory
├── tests/            # unit, integration, and API tests
├── docs/             # contributor and operator documentation
└── pyproject.toml
```

## API usage

Once the server is running (locally or via Docker):

```bash
# Latest snapshot for a dataset
curl http://localhost:8000/datasets/exchange-rates/latest

# Historical records, date-filtered
curl "http://localhost:8000/datasets/exchange-rates/historical?from=2026-01-01&to=2026-04-30"

# Filter by currency
curl "http://localhost:8000/datasets/exchange-rates/historical?currency=USD"

# CSV download
curl -O http://localhost:8000/datasets/exchange-rates/csv

# Per-dataset freshness (for monitoring)
curl http://localhost:8000/admin/health
```

Full endpoint reference: [`docs/api-reference.md`](docs/api-reference.md).
Interactive Swagger UI: `http://localhost:8000/docs` while the server is up.

## Adding a new dataset

Each dataset is a self-contained plugin under `govlink/datasets/`, registered
automatically at startup. See [`docs/adding-a-dataset.md`](docs/adding-a-dataset.md)
for the full guide. In short, a new dataset folder contains a parser, a
source, ORM models, Pydantic schemas, and a registration entry — and is
picked up by the registry without any further wiring.

## Development

Install the project with development dependencies:

```bash
uv sync
```

Run the test suite:

```bash
uv run pytest
```

Run the linter and formatter:

```bash
uv run ruff check .
uv run ruff format .
```

Run the type checker:

```bash
uv run mypy govlink
```

Install the pre-commit hooks (recommended for contributors):

```bash
uv run pre-commit install
```

## Contributing

Contributions are welcome — bug reports, new datasets, documentation
fixes, anything. The full guide lives at
[`CONTRIBUTING.md`](CONTRIBUTING.md). PRs must pass the test suite,
`ruff check`, `ruff format --check`, and `mypy --strict` to merge.

If you want to add a new dataset, the dedicated walkthrough is at
[`docs/adding-a-dataset.md`](docs/adding-a-dataset.md).

## License

`govlink` is released under the [MIT License](LICENSE).

## Acknowledgements

- The **[Central Bank of The Gambia](https://www.cbg.gm/)** for publishing
  daily exchange rate data — the project's first dataset.
- Built with [FastAPI](https://fastapi.tiangolo.com/),
  [SQLAlchemy 2.0](https://www.sqlalchemy.org/),
  [Pydantic](https://docs.pydantic.dev/),
  [pdfplumber](https://github.com/jsvine/pdfplumber),
  [structlog](https://www.structlog.org/),
  and [Typer](https://typer.tiangolo.com/).
- Inspired by the need for accessible open-data infrastructure in
  The Gambia.
