"""Tests for govlink.core.models — registry-layer SQLAlchemy models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from govlink.core.models import (
    Dataset,
    DatasetField,
    DatasetFrequency,
    IngestionLog,
    IngestionStatus,
    SourceFile,
)


def _make_dataset(**overrides: object) -> Dataset:
    """Helper — build a minimally valid Dataset with overridable fields."""
    base: dict[str, object] = {
        "slug": "exchange-rates",
        "title": "Daily Exchange Rates",
        "publisher": "Central Bank of The Gambia",
        "source_url": "https://www.cbg.gm/exchange-rates",
        "frequency": DatasetFrequency.DAILY,
    }
    base.update(overrides)
    return Dataset(**base)  # type: ignore[arg-type]


def test_dataset_with_valid_data(db_session: Session) -> None:
    """A Dataset with valid required fields persists successfully."""
    ds = _make_dataset()
    db_session.add(ds)
    db_session.commit()
    assert ds.id is not None
    assert ds.slug == "exchange-rates"
    assert ds.created_at is not None
    assert ds.updated_at is not None
    assert ds.created_at.tzinfo is not None  # timezone-aware


def test_dataset_slug_must_be_unique(db_session: Session) -> None:
    """Two Datasets with the same slug must violate the unique constraint."""
    db_session.add(_make_dataset(slug="cpi"))
    db_session.commit()
    db_session.add(_make_dataset(slug="cpi", title="Different Title"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_dataset_slug_must_match_pattern() -> None:
    """Slugs must be lowercase, alphanumeric, hyphen-separated.

    Validation runs synchronously on attribute assignment via @validates,
    so a bad slug raises ValueError before any DB interaction.
    """
    with pytest.raises(ValueError):
        _make_dataset(slug="Exchange Rates")
    with pytest.raises(ValueError):
        _make_dataset(slug="-leading-hyphen")
    with pytest.raises(ValueError):
        _make_dataset(slug="trailing-hyphen-")
    with pytest.raises(ValueError):
        _make_dataset(slug="double--hyphen")
    with pytest.raises(ValueError):
        _make_dataset(slug="UPPERCASE")
    with pytest.raises(ValueError):
        _make_dataset(slug="under_score")


def test_dataset_slug_accepts_valid_patterns() -> None:
    """Valid slugs are accepted: lowercase alphanumeric segments separated by single hyphens."""
    for ok in ("cpi", "exchange-rates", "gdp-2024", "a1-b2-c3"):
        ds = _make_dataset(slug=ok)
        assert ds.slug == ok


def test_dataset_field_belongs_to_dataset(db_session: Session) -> None:
    """The Dataset → DatasetField FK relationship works, including cascade delete."""
    ds = _make_dataset()
    ds.fields.append(DatasetField(field_name="usd_buy", field_type="decimal", unit="GMD"))
    ds.fields.append(DatasetField(field_name="usd_sell", field_type="decimal", unit="GMD"))
    db_session.add(ds)
    db_session.commit()
    dataset_id = ds.id

    fetched = db_session.get(Dataset, dataset_id)
    assert fetched is not None
    assert {f.field_name for f in fetched.fields} == {"usd_buy", "usd_sell"}

    db_session.delete(fetched)
    db_session.commit()
    remaining = db_session.query(DatasetField).filter_by(dataset_id=dataset_id).all()
    assert remaining == []


def test_dataset_field_unique_per_dataset(db_session: Session) -> None:
    """The (dataset_id, field_name) composite must be unique."""
    ds = _make_dataset()
    ds.fields.append(DatasetField(field_name="usd_buy", field_type="decimal"))
    ds.fields.append(DatasetField(field_name="usd_buy", field_type="decimal"))
    db_session.add(ds)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_source_file_source_uuid_must_be_unique(db_session: Session) -> None:
    """Two SourceFile rows with the same ``source_uuid`` must violate uniqueness."""
    ds = _make_dataset()
    db_session.add(ds)
    db_session.commit()

    db_session.add(
        SourceFile(
            dataset_id=ds.id,
            source_uuid="01f3604a-4474-11f1-8725-02e599c15748",
            source_url="https://example.gm/a.pdf",
        )
    )
    db_session.commit()

    db_session.add(
        SourceFile(
            dataset_id=ds.id,
            source_uuid="01f3604a-4474-11f1-8725-02e599c15748",
            source_url="https://example.gm/b.pdf",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_source_file_belongs_to_dataset(db_session: Session) -> None:
    """The SourceFile → Dataset FK relationship navigates correctly."""
    ds = _make_dataset()
    sf = SourceFile(
        dataset=ds,
        source_uuid="abc-123",
        source_url="https://example.gm/file.pdf",
        link_text="Daily exchange rates — 2026-05-01",
    )
    db_session.add(sf)
    db_session.commit()

    assert sf.dataset is ds
    assert sf in ds.source_files


def test_source_file_cascade_delete(db_session: Session) -> None:
    """Deleting a Dataset must cascade-delete its SourceFile rows."""
    ds = _make_dataset()
    ds.source_files.append(SourceFile(source_uuid="u1", source_url="https://x.gm/1.pdf"))
    db_session.add(ds)
    db_session.commit()
    dataset_id = ds.id

    db_session.delete(ds)
    db_session.commit()
    remaining = db_session.query(SourceFile).filter_by(dataset_id=dataset_id).all()
    assert remaining == []


def test_ingestion_log_belongs_to_dataset(db_session: Session) -> None:
    """The IngestionLog → Dataset FK relationship works."""
    ds = _make_dataset()
    log = IngestionLog(dataset=ds, status=IngestionStatus.PENDING)
    db_session.add(log)
    db_session.commit()
    assert log.dataset is ds
    assert log in ds.ingestion_logs


def test_ingestion_log_status_constrained(db_session: Session) -> None:
    """An invalid ``status`` value must be rejected.

    SQLAlchemy's ``Enum(..., validate_strings=True)`` rejects unknown values
    early (raising ``StatementError``); the underlying DB CHECK is a safety
    net for direct SQL inserts. We accept either failure path.
    """
    ds = _make_dataset()
    db_session.add(ds)
    db_session.commit()

    with pytest.raises((StatementError, IntegrityError)):
        db_session.execute(
            IngestionLog.__table__.insert().values(
                dataset_id=ds.id,
                status="not-a-status",
                started_at=datetime.now(UTC),
                rows_added=0,
                rows_updated=0,
                rows_skipped=0,
            )
        )
        db_session.commit()


def test_ingestion_log_source_file_set_null_on_delete(db_session: Session) -> None:
    """Deleting a SourceFile must set ``IngestionLog.source_file_id`` to NULL."""
    ds = _make_dataset()
    sf = SourceFile(dataset=ds, source_uuid="u1", source_url="https://x.gm/a.pdf")
    log = IngestionLog(dataset=ds, source_file=sf, status=IngestionStatus.SUCCESS)
    db_session.add_all([ds, sf, log])
    db_session.commit()

    db_session.delete(sf)
    db_session.commit()
    db_session.refresh(log)
    assert log.source_file_id is None


def test_models_have_useful_repr(db_session: Session) -> None:
    """Every model's __repr__ includes its PK and an identifying field."""
    ds = _make_dataset(slug="repr-test")
    db_session.add(ds)
    db_session.commit()
    sf = SourceFile(dataset=ds, source_uuid="repr-uuid", source_url="https://x.gm/r.pdf")
    db_session.add(sf)
    db_session.commit()

    field = DatasetField(dataset=ds, field_name="test_field", field_type="string")
    db_session.add(field)
    db_session.commit()

    log = IngestionLog(dataset=ds, status=IngestionStatus.RUNNING)
    db_session.add(log)
    db_session.commit()

    assert "Dataset" in repr(ds) and "repr-test" in repr(ds) and str(ds.id) in repr(ds)
    assert "SourceFile" in repr(sf) and "repr-uuid" in repr(sf) and str(sf.id) in repr(sf)
    assert "DatasetField" in repr(field) and "test_field" in repr(field)
    assert "IngestionLog" in repr(log) and "running" in repr(log)


def test_dataset_frequency_enum_values() -> None:
    """``DatasetFrequency`` exposes the documented values including IRREGULAR."""
    assert DatasetFrequency.DAILY.value == "daily"
    assert DatasetFrequency.WEEKLY.value == "weekly"
    assert DatasetFrequency.MONTHLY.value == "monthly"
    assert DatasetFrequency.QUARTERLY.value == "quarterly"
    assert DatasetFrequency.ANNUAL.value == "annual"
    assert DatasetFrequency.IRREGULAR.value == "irregular"


def test_ingestion_status_enum_values() -> None:
    """``IngestionStatus`` exposes the four lifecycle values."""
    assert {s.value for s in IngestionStatus} == {"pending", "running", "success", "failed"}
