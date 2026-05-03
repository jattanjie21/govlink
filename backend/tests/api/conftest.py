"""Shared fixtures for the FastAPI API test suite.

These fixtures wire a fresh FastAPI app to a fresh in-memory SQLite DB
and a fresh isolated registry per test. The lifespan still runs (so we
exercise the real startup hooks), but its writes go to the same isolated
state the tests inspect.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Generator
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.orm import Session

from govlink.core.models import Dataset, DatasetFrequency
from govlink.core.registry import DatasetRegistry
from govlink.datasets.exchange_rates.model import ExchangeRate

_DATASET_MODULE = "govlink.datasets.exchange_rates.dataset"


def _force_dataset_reregistration() -> None:
    """Drop the dataset module from sys.modules so the next import re-registers.

    See Phase 4/5 ``_force_dataset_reregistration`` for the full rationale —
    in short, ``isolated_global_registry`` swaps the global, but Python's
    import cache means a re-imported ``dataset.py`` won't fire its
    ``register()`` side effect a second time.
    """
    sys.modules.pop(_DATASET_MODULE, None)


@pytest.fixture
def app(
    initialized_db: Session,
    db_session: Session,
    isolated_global_registry: DatasetRegistry,
    mock_settings: object,
) -> Generator[FastAPI, None, None]:
    """A FastAPI app with the test DB session + isolated registry overrides."""
    from govlink.api.deps import get_db_session, get_registry_dep
    from govlink.main import create_app

    _force_dataset_reregistration()
    application = create_app()

    def _test_session() -> Generator[Session, None, None]:
        yield db_session

    application.dependency_overrides[get_db_session] = _test_session
    application.dependency_overrides[get_registry_dep] = lambda: isolated_global_registry

    yield application

    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Async httpx client with the FastAPI app's lifespan context entered.

    ``ASGITransport`` does NOT run lifespan events on its own, so we enter
    ``app.router.lifespan_context(app)`` manually around the client. This
    fires the real startup (``init_db`` + ``auto_discover``) once per test.
    """
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    """DB pre-seeded with a Dataset row + 10 ExchangeRate rows (5 currencies x 2 dates)."""
    ds = Dataset(
        slug="exchange-rates",
        title="Daily Valuation Exchange Rates",
        publisher="Central Bank of The Gambia",
        source_url="https://www.cbg.gm/daily-valuation-exchange-rate",
        frequency=DatasetFrequency.DAILY,
    )
    db_session.add(ds)
    db_session.flush()

    rows: list[tuple[str, str, Decimal, int]] = [
        ("USD", "US DOLLAR", Decimal("72.39"), 1),
        ("EUR", "EURO", Decimal("86.56"), 1),
        ("GBP", "GBP", Decimal("96.10"), 1),
        ("JPY", "JAPANESE YEN", Decimal("45.18"), 100),
        ("XOF", "CFA FRANC", Decimal("639.49"), 5000),
    ]
    for snap in (date(2026, 4, 29), date(2026, 4, 30)):
        for code, name, rate, mult in rows:
            db_session.add(
                ExchangeRate(
                    snapshot_date=snap,
                    currency_code=code,
                    currency_name=name,
                    rate=rate,
                    unit_multiplier=mult,
                    rate_per_unit=rate / Decimal(mult),
                )
            )
    db_session.commit()
    return db_session


@pytest.fixture
def empty_dataset_db(db_session: Session) -> Session:
    """DB with the Dataset metadata row but no data rows."""
    ds = Dataset(
        slug="exchange-rates",
        title="Daily Valuation Exchange Rates",
        publisher="Central Bank of The Gambia",
        source_url="https://www.cbg.gm/daily-valuation-exchange-rate",
        frequency=DatasetFrequency.DAILY,
    )
    db_session.add(ds)
    db_session.commit()
    return db_session


@pytest.fixture
def serialise_envelope_for_assertions() -> Any:
    """Helper for tests that need to inspect raw JSON envelopes."""
    return None
