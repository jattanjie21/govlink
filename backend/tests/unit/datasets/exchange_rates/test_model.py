"""Tests for govlink.datasets.exchange_rates.model — ORM + Pydantic schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from govlink.core.models import Dataset, DatasetFrequency, SourceFile
from govlink.datasets.exchange_rates.model import (
    ExchangeRate,
    ExchangeRateRecord,
    ExchangeRateResponseItem,
)


def _seed_dataset_and_source(db_session: Session) -> tuple[Dataset, SourceFile]:
    ds = Dataset(
        slug="exchange-rates",
        title="Daily Exchange Rates",
        publisher="Central Bank of The Gambia",
        source_url="https://www.cbg.gm/daily-valuation-exchange-rate",
        frequency=DatasetFrequency.DAILY,
    )
    db_session.add(ds)
    db_session.commit()
    sf = SourceFile(
        dataset_id=ds.id,
        source_uuid="01f3604a-4474-11f1-8725-02e599c15748",
        source_url="https://www.cbg.gm/downloads-file/01f3604a-4474-11f1-8725-02e599c15748",
    )
    db_session.add(sf)
    db_session.commit()
    return ds, sf


def test_orm_tablename_is_data_exchange_rates() -> None:
    assert ExchangeRate.__tablename__ == "data_exchange_rates"


def test_orm_can_insert_valid_row(db_session: Session) -> None:
    _, sf = _seed_dataset_and_source(db_session)
    row = ExchangeRate(
        snapshot_date=date(2026, 4, 30),
        currency_code="USD",
        currency_name="US DOLLAR",
        rate=Decimal("72.39"),
        unit_multiplier=1,
        rate_per_unit=Decimal("72.39"),
        source_file_id=sf.id,
    )
    db_session.add(row)
    db_session.commit()

    fetched = db_session.execute(
        select(ExchangeRate).where(ExchangeRate.currency_code == "USD")
    ).scalar_one()
    assert fetched.snapshot_date == date(2026, 4, 30)
    assert fetched.rate == Decimal("72.39")
    assert fetched.rate_per_unit == Decimal("72.39")
    assert fetched.ingested_at is not None
    assert fetched.ingested_at.tzinfo is not None


def test_orm_unique_on_snapshot_date_and_currency_code(db_session: Session) -> None:
    _, sf = _seed_dataset_and_source(db_session)
    db_session.add(
        ExchangeRate(
            snapshot_date=date(2026, 4, 30),
            currency_code="USD",
            currency_name="US DOLLAR",
            rate=Decimal("72.39"),
            unit_multiplier=1,
            rate_per_unit=Decimal("72.39"),
            source_file_id=sf.id,
        )
    )
    db_session.commit()
    db_session.add(
        ExchangeRate(
            snapshot_date=date(2026, 4, 30),
            currency_code="USD",
            currency_name="US DOLLAR (duplicate)",
            rate=Decimal("99.99"),
            unit_multiplier=1,
            rate_per_unit=Decimal("99.99"),
            source_file_id=sf.id,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_orm_indexes_on_snapshot_date_and_currency_code() -> None:
    """The composite ``(snapshot_date, currency_code)`` index exists for range queries."""
    table = ExchangeRate.__table__
    target_cols = {"snapshot_date", "currency_code"}
    composite_indexes = [
        idx for idx in table.indexes if {col.name for col in idx.columns} == target_cols
    ]
    assert len(composite_indexes) >= 1
    # Plus the unique constraint on the same pair.
    uq_constraints = [
        c
        for c in table.constraints
        if isinstance(c, UniqueConstraint)
        and {col.name for col in c.columns} == {"snapshot_date", "currency_code"}
    ]
    assert len(uq_constraints) == 1


def test_orm_rate_per_unit_is_persisted_decimal(db_session: Session) -> None:
    _, sf = _seed_dataset_and_source(db_session)
    row = ExchangeRate(
        snapshot_date=date(2026, 4, 30),
        currency_code="DKK",
        currency_name="DANISH KRONE (100)",
        rate=Decimal("1132.65"),
        unit_multiplier=100,
        rate_per_unit=Decimal("11.3265"),
        source_file_id=sf.id,
    )
    db_session.add(row)
    db_session.commit()
    fetched = db_session.execute(
        select(ExchangeRate).where(ExchangeRate.currency_code == "DKK")
    ).scalar_one()
    assert isinstance(fetched.rate_per_unit, Decimal)
    assert fetched.rate_per_unit == Decimal("11.3265")


def test_orm_foreign_key_to_source_files_set_null_on_delete(db_session: Session) -> None:
    _, sf = _seed_dataset_and_source(db_session)
    row = ExchangeRate(
        snapshot_date=date(2026, 4, 30),
        currency_code="EUR",
        currency_name="EURO",
        rate=Decimal("86.56"),
        unit_multiplier=1,
        rate_per_unit=Decimal("86.56"),
        source_file_id=sf.id,
    )
    db_session.add(row)
    db_session.commit()

    db_session.delete(sf)
    db_session.commit()
    db_session.refresh(row)
    assert row.source_file_id is None


def test_orm_repr_includes_date_and_code() -> None:
    row = ExchangeRate(
        snapshot_date=date(2026, 4, 30),
        currency_code="USD",
        currency_name="US DOLLAR",
        rate=Decimal("72.39"),
        unit_multiplier=1,
        rate_per_unit=Decimal("72.39"),
    )
    text = repr(row)
    assert "2026-04-30" in text
    assert "USD" in text
    assert "ExchangeRate" in text


def test_pydantic_record_validates_currency_code_format() -> None:
    base = {
        "snapshot_date": date(2026, 4, 30),
        "currency_name": "US DOLLAR",
        "rate": Decimal("72.39"),
        "unit_multiplier": 1,
    }
    # Valid: 3 uppercase letters
    ExchangeRateRecord(currency_code="USD", **base)
    # Valid: 4-letter synthetic
    ExchangeRateRecord(currency_code="WAUA", **base)
    # Valid: XDR (synthetic but ISO-shaped)
    ExchangeRateRecord(currency_code="XDR", **base)
    # Invalid: lowercase
    with pytest.raises(ValidationError):
        ExchangeRateRecord(currency_code="usd", **base)
    # Invalid: 5 chars
    with pytest.raises(ValidationError):
        ExchangeRateRecord(currency_code="USDXX", **base)
    # Invalid: contains digit
    with pytest.raises(ValidationError):
        ExchangeRateRecord(currency_code="US1", **base)


def test_pydantic_record_validates_rate_positive() -> None:
    base = {
        "snapshot_date": date(2026, 4, 30),
        "currency_code": "USD",
        "currency_name": "US DOLLAR",
        "unit_multiplier": 1,
    }
    with pytest.raises(ValidationError):
        ExchangeRateRecord(rate=Decimal("0"), **base)
    with pytest.raises(ValidationError):
        ExchangeRateRecord(rate=Decimal("-1"), **base)


def test_pydantic_record_validates_unit_multiplier_positive_integer() -> None:
    base = {
        "snapshot_date": date(2026, 4, 30),
        "currency_code": "USD",
        "currency_name": "US DOLLAR",
        "rate": Decimal("72.39"),
    }
    with pytest.raises(ValidationError):
        ExchangeRateRecord(unit_multiplier=0, **base)
    with pytest.raises(ValidationError):
        ExchangeRateRecord(unit_multiplier=-1, **base)


def test_pydantic_record_computes_rate_per_unit() -> None:
    rec = ExchangeRateRecord(
        snapshot_date=date(2026, 4, 30),
        currency_code="DKK",
        currency_name="DANISH KRONE (100)",
        rate=Decimal("1132.65"),
        unit_multiplier=100,
    )
    assert rec.rate_per_unit == Decimal("11.3265")


def test_pydantic_record_uses_decimal_for_rates() -> None:
    rec = ExchangeRateRecord(
        snapshot_date=date(2026, 4, 30),
        currency_code="USD",
        currency_name="US DOLLAR",
        rate=Decimal("72.39"),
        unit_multiplier=1,
    )
    assert isinstance(rec.rate, Decimal)
    assert isinstance(rec.rate_per_unit, Decimal)


def test_pydantic_response_item_excludes_source_file_id(db_session: Session) -> None:
    _, sf = _seed_dataset_and_source(db_session)
    row = ExchangeRate(
        snapshot_date=date(2026, 4, 30),
        currency_code="USD",
        currency_name="US DOLLAR",
        rate=Decimal("72.39"),
        unit_multiplier=1,
        rate_per_unit=Decimal("72.39"),
        source_file_id=sf.id,
    )
    db_session.add(row)
    db_session.commit()

    item = ExchangeRateResponseItem.model_validate(row, from_attributes=True)
    payload = item.model_dump(mode="json")
    assert "source_file_id" not in payload
    assert "ingested_at" not in payload
    assert "id" not in payload
    assert payload["currency_code"] == "USD"
    assert payload["snapshot_date"] == "2026-04-30"


def test_pydantic_record_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ExchangeRateRecord(
            snapshot_date=date(2026, 4, 30),
            currency_code="USD",
            currency_name="US DOLLAR",
            rate=Decimal("72.39"),
            unit_multiplier=1,
            unexpected_field="boom",
        )


def test_pydantic_record_is_frozen() -> None:
    rec = ExchangeRateRecord(
        snapshot_date=date(2026, 4, 30),
        currency_code="USD",
        currency_name="US DOLLAR",
        rate=Decimal("72.39"),
        unit_multiplier=1,
    )
    with pytest.raises(ValidationError):
        rec.rate = Decimal("99.99")  # type: ignore[misc]


def test_orm_ingested_at_default_is_utc() -> None:
    row = ExchangeRate(
        snapshot_date=date(2026, 4, 30),
        currency_code="USD",
        currency_name="US DOLLAR",
        rate=Decimal("72.39"),
        unit_multiplier=1,
        rate_per_unit=Decimal("72.39"),
    )
    # Set via Python default to verify behaviour without needing a DB roundtrip.
    if row.ingested_at is None:
        from govlink.datasets.exchange_rates.model import _utcnow

        row.ingested_at = _utcnow()
    assert row.ingested_at.tzinfo is not None
    assert isinstance(row.ingested_at, datetime)
    # Reasonable: within a few seconds of "now".
    delta = abs((datetime.now(UTC) - row.ingested_at).total_seconds())
    assert delta < 5
