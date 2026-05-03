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

![Status](https://img.shields.io/badge/status-pre--alpha-orange)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

This project is in **pre-alpha**. The repository currently contains only the
project scaffold — no working ingestion, no API endpoints, no published data.
The skeleton is being filled in across a series of phased contributions.

## Quickstart (local, SQLite)

`govlink` is managed with [uv](https://docs.astral.sh/uv/). To get started:

```bash
git clone https://github.com/TODO/govlink.git
cd govlink
uv sync
cp .env.example .env
uv run govlink --help
```

> The `govlink` CLI and the API surface are placeholders in this phase. The
> commands above will install dependencies and confirm the package is
> importable; they will not yet perform ingestion or serve data.

## Quickstart (Docker)

Docker support will be added in a later phase. Once available, the workflow
will be `docker compose up` against a bundled `compose.yaml` that runs the
API, a Postgres instance, and a one-shot ingestion job.

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

Contributions are welcome. The project is intentionally small in scope per
phase, and the contribution model favours small, well-tested pull requests.
All PRs must pass the full test suite, the ruff lint check, and the mypy
type check before they can be merged. Please open an issue before starting
non-trivial work so we can align on approach.

## License

`govlink` is released under the [MIT License](LICENSE).

## Acknowledgements

`govlink` is built on top of public data published by the people and
institutions of The Gambia. Particular thanks are owed to the **Central
Bank of The Gambia**, whose published exchange rate sheets are the project's
first dataset. Additional acknowledgements will be added as new sources are
integrated.
