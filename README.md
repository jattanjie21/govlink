# GovLink

An open-source platform that makes Gambian government data accessible to researchers, journalists, civic technologists, and the wider developer community. Public data published by Gambian institutions is overwhelmingly distributed as PDFs scattered across departmental websites — useful for a human reader, but effectively closed to anyone trying to build on it. GovLink does the scraping, parsing, and normalising once, in the open, and exposes the result through a clean web interface and a stable REST API.

## Repository layout

This repository is a monorepo with two top-level folders. Pick the one that matches what you want to work on:

```
govlink/
├── frontend/   # React + Vite web client  →  see frontend/README.md
└── backend/    # Python REST API + ingestion pipeline  →  see backend/README.md
```

Each folder is self-contained with its own dependencies, setup instructions, and development server. You do not need to install or run the other side to work on one.

## Choosing where to contribute

| If you are interested in… | Work in | Stack |
|---|---|---|
| UI, design, data visualisations, accessibility, user-facing features | `frontend/` | React 19, Vite, JavaScript |
| Datasets, parsers, ingestion, API endpoints, database schema | `backend/` | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Both | Either folder — they are independent and can be developed in parallel | — |

## Quickstart

```bash
git clone https://github.com/<org>/govlink.git
cd govlink
```

Then follow the README in the folder you want to work on:

- **Frontend:** [`frontend/README.md`](frontend/README.md)
- **Backend:** [`backend/README.md`](backend/README.md)

## Contributing

Contributions of any size — bug reports, new datasets, UI improvements, documentation fixes — are welcome. The goal is for any Gambian (and anyone else who cares) to be able to contribute.

1. Fork the repo and clone your fork.
2. Decide whether your change belongs in `frontend/` or `backend/`.
3. Create a branch off `main`: `git checkout -b feature/short-description`.
4. Make your change, run the relevant tests/linters (see the folder's README), and open a pull request.

Cross-cutting changes that touch both sides should be split into two PRs — one per folder — so reviewers can move independently.

The detailed backend contributor guide (style, TDD workflow, PR checklist) lives at [`backend/CONTRIBUTING.md`](backend/CONTRIBUTING.md).

## License

`govlink` is released under the [MIT License](LICENSE).
