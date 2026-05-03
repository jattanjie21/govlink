# Contributing to govlink

Thank you for your interest in contributing. This project makes Gambian government data accessible to researchers, journalists, and developers, and contributions of any size — bug reports, new datasets, documentation fixes — are genuinely valued.

## Getting started

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/govlink.git
cd govlink

# 2. Install dependencies
uv sync

# 3. Run the test suite to confirm a clean baseline
uv run pytest

# 4. Branch off main for your work
git checkout -b feature/short-description
```

## Development workflow

The project follows **strict TDD**: write the failing test first, watch it fail for the right reason, write the minimum implementation, watch it pass.

A typical loop:

```bash
uv run pytest tests/unit/path/to/test_new_thing.py   # red
# ... write code ...
uv run pytest tests/unit/path/to/test_new_thing.py   # green
uv run ruff check .                                   # lint clean
uv run ruff format --check .                          # format clean
uv run mypy govlink                                   # type-check clean
```

When the unit test cycle is green, run the full suite:

```bash
uv run pytest --cov=govlink
```

## Code style and conventions

| Area | Convention |
|------|-----------|
| Python version | 3.12 (pinned via `.python-version`) |
| Type hints | Everywhere; `mypy --strict` must pass |
| Pydantic | v2; `model_config = ConfigDict(extra="forbid", ...)` on every model |
| ORM | SQLAlchemy 2.0 typed syntax (`Mapped[...]`, `mapped_column(...)`) |
| Decimal handling | Always `Decimal` (never `float`) for numeric data; use `DecimalStr` from `govlink.core.schemas` for fields that appear in API/CSV |
| Datetime | UTC-aware via `datetime.now(UTC)`; never `datetime.utcnow()` |
| Logging | `structlog` via `self.logger` (sources/parsers) or `structlog.get_logger(__name__)` (modules); never `print` |
| Lint + format | `ruff` (configured in `ruff.toml`); imports auto-sorted |

## Adding a new dataset

The most common contribution. See the dedicated step-by-step guide:

**→ [docs/adding-a-dataset.md](docs/adding-a-dataset.md)**

It walks through every file you need to create, every test you need to write, and every command you need to run, using a worked example.

## Pull request checklist

Before opening a PR, verify:

- [ ] All tests pass: `uv run pytest`
- [ ] Lint clean: `uv run ruff check .`
- [ ] Format clean: `uv run ruff format --check .`
- [ ] Type-check clean: `uv run mypy govlink`
- [ ] Coverage ≥ 95% on new code (the project as a whole stays at 100%)
- [ ] Documentation updated for any user-visible change
- [ ] If adding a new dataset: Alembic migration committed; fixture PDF + JSON oracle committed; README's "Available Datasets" table updated

## Reporting issues

Open an issue on GitHub with:

- **What you expected** to happen
- **What actually happened** (including any error messages or stack traces)
- **Steps to reproduce** — the smallest possible recipe
- **Environment**: Python version, OS, govlink version (or git SHA)

For security issues, please do not open a public issue. Contact the maintainers privately first.

## Project layout (orientation)

```
govlink/
├── govlink/
│   ├── api/              FastAPI routes, dependencies, exporters
│   ├── core/             Registry, base classes, ORM models, shared schemas
│   ├── datasets/         One subpackage per dataset (the plugin layer)
│   ├── ingestion/        Orchestrator + cross-dataset utilities
│   ├── cli.py            Typer CLI entrypoint
│   ├── config.py         pydantic-settings configuration
│   ├── db.py             SQLAlchemy engine + session
│   ├── logging.py        structlog setup
│   └── main.py           FastAPI application factory
├── tests/                Mirrors govlink/ layout; fixtures under tests/fixtures/
├── alembic/              Schema migrations (one per change)
├── docs/                 Contributor and operator guides
└── docker-compose.yml    Production stack: Postgres + migrations + API
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
