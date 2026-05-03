"""Tests for govlink.ingestion.orchestrator — full ingestion pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import structlog
from pydantic import BaseModel
from sqlalchemy import Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from govlink.core.base_parser import BaseParser
from govlink.core.base_source import BaseSource
from govlink.core.definition import DatasetDefinition
from govlink.core.models import (
    Dataset,
    DatasetFrequency,
    IngestionLog,
    IngestionStatus,
    SourceFile,
)
from govlink.core.source_ref import SourceFileRef
from govlink.datasets.exchange_rates.parser import ParseError
from govlink.db import Base
from govlink.ingestion.orchestrator import IngestionSummary, Orchestrator

# --- test-local fakes (NOT imported from production) ---------------------


class _FakeRecord(BaseModel):
    """Minimal Pydantic record for orchestrator tests."""

    snapshot_date: date
    name: str
    value: int


class _FakeOrm(Base):
    """ORM model with a unique constraint to exercise rollback behaviour."""

    __tablename__ = "data_orchestrator_test"
    __table_args__ = (UniqueConstraint("snapshot_date", "name", name="uq_orchtest"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    source_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class _FakeSource(BaseSource):
    """Source that returns a controlled list of refs and bytes."""

    def __init__(
        self,
        refs: list[SourceFileRef],
        payloads: dict[str, bytes],
        fetch_error: type[Exception] | None = None,
    ) -> None:
        super().__init__()
        self._refs = refs
        self._payloads = payloads
        self._fetch_error = fetch_error

    def discover(self) -> Iterable[SourceFileRef]:
        return list(self._refs)

    def fetch(self, ref: SourceFileRef) -> bytes:
        if self._fetch_error is not None:
            raise self._fetch_error("simulated fetch failure")
        return self._payloads[ref.source_uuid]


class _FakeParser(BaseParser[_FakeRecord]):
    """Parser that returns a fixed list of records, or raises on demand."""

    def __init__(
        self,
        records_per_uuid: dict[str, list[_FakeRecord]] | None = None,
        raise_on_uuid: dict[str, type[Exception]] | None = None,
    ) -> None:
        super().__init__()
        self._records_per_uuid = records_per_uuid or {}
        self._raise_on_uuid = raise_on_uuid or {}
        # Track which uuid is currently being parsed via the bytes header.
        self._current_uuid: str | None = None

    def set_current(self, uuid: str) -> None:
        """Tell the fake which uuid the next parse() call corresponds to."""
        self._current_uuid = uuid

    def parse(self, raw_bytes: bytes) -> list[_FakeRecord]:
        # The fake source encodes the uuid in the first line of payload bytes.
        uuid = raw_bytes.decode().split("\n", 1)[0]
        if uuid in self._raise_on_uuid:
            raise self._raise_on_uuid[uuid]("simulated parse failure")
        return list(self._records_per_uuid.get(uuid, []))


def _ref(uuid: str, hint: date | None = None) -> SourceFileRef:
    return SourceFileRef(
        source_uuid=uuid,
        url=f"https://example.gm/downloads-file/{uuid}",
        link_text=f"sample-{uuid}",
        published_date_hint=hint,
    )


def _payload(uuid: str) -> bytes:
    """Encode the uuid into the payload's first line so the fake parser can route."""
    return f"{uuid}\nbody".encode()


def _records(date_obj: date, count: int) -> list[_FakeRecord]:
    return [_FakeRecord(snapshot_date=date_obj, name=f"r{i}", value=i) for i in range(count)]


def _make_definition(
    source: BaseSource,
    parser: BaseParser[_FakeRecord],
    *,
    slug: str = "orchestrator-test",
    title: str = "Orchestrator Test",
) -> DatasetDefinition:
    return DatasetDefinition(
        slug=slug,
        title=title,
        publisher="Test Publisher",
        source_url="https://example.gm/x",
        frequency=DatasetFrequency.DAILY,
        source=source,
        parser=parser,
        model_class=_FakeOrm,
        schema_class=_FakeRecord,
    )


# --- tests ---------------------------------------------------------------


def test_ingest_latest_fetches_and_stores_one_file(initialized_db: Session) -> None:
    """``latest=True`` fetches only the first ref from discover() and stores its records."""
    refs = [_ref(f"u{i}", date(2026, 4, 30 - i)) for i in range(3)]
    payloads = {r.source_uuid: _payload(r.source_uuid) for r in refs}
    source = _FakeSource(refs=refs, payloads=payloads)
    parser = _FakeParser(
        records_per_uuid={r.source_uuid: _records(date(2026, 4, 30), 5) for r in refs}
    )

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(_make_definition(source, parser), latest=True)

    assert summary.files_ingested == 1
    assert summary.files_skipped == 0
    assert summary.total_rows_added == 5

    source_files = initialized_db.execute(select(SourceFile)).scalars().all()
    assert len(source_files) == 1
    assert source_files[0].source_uuid == "u0"  # first in list = newest

    data = initialized_db.execute(select(_FakeOrm)).scalars().all()
    assert len(data) == 5

    logs = initialized_db.execute(select(IngestionLog)).scalars().all()
    assert len(logs) == 1
    assert logs[0].status is IngestionStatus.SUCCESS


def test_ingest_all_fetches_all_new_files(initialized_db: Session) -> None:
    """``latest=False`` processes every ref."""
    refs = [_ref(f"u{i}", date(2026, 4, 30 - i)) for i in range(3)]
    payloads = {r.source_uuid: _payload(r.source_uuid) for r in refs}
    source = _FakeSource(refs=refs, payloads=payloads)
    parser = _FakeParser(
        records_per_uuid={
            "u0": _records(date(2026, 4, 30), 5),
            "u1": _records(date(2026, 4, 29), 5),
            "u2": _records(date(2026, 4, 28), 5),
        }
    )

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(_make_definition(source, parser), latest=False)

    assert summary.files_ingested == 3
    assert summary.total_rows_added == 15

    source_files = initialized_db.execute(select(SourceFile)).scalars().all()
    assert len(source_files) == 3
    data = initialized_db.execute(select(_FakeOrm)).scalars().all()
    assert len(data) == 15
    logs = initialized_db.execute(select(IngestionLog)).scalars().all()
    assert len(logs) == 3
    assert all(log.status is IngestionStatus.SUCCESS for log in logs)


def test_ingest_skips_already_ingested_files(initialized_db: Session) -> None:
    """A SourceFile row whose source_uuid matches a ref makes the orchestrator skip it."""
    refs = [_ref(f"u{i}") for i in range(3)]
    payloads = {r.source_uuid: _payload(r.source_uuid) for r in refs}
    source = _FakeSource(refs=refs, payloads=payloads)
    parser = _FakeParser(
        records_per_uuid={
            r.source_uuid: _records(date(2026, 4, 30 - i), 2) for i, r in enumerate(refs)
        }
    )

    # Pre-create the dataset and pre-mark u1 as already ingested.
    definition = _make_definition(source, parser)
    ds = Dataset(
        slug=definition.slug,
        title=definition.title,
        publisher=definition.publisher,
        source_url=definition.source_url,
        frequency=definition.frequency,
    )
    initialized_db.add(ds)
    initialized_db.commit()
    initialized_db.add(
        SourceFile(
            dataset_id=ds.id,
            source_uuid="u1",
            source_url="https://example.gm/u1",
        )
    )
    initialized_db.commit()

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(definition, latest=False)

    assert summary.files_skipped == 1
    assert summary.files_ingested == 2


def test_ingest_latest_skips_if_latest_already_ingested(initialized_db: Session) -> None:
    """If the newest ref is already in source_files, latest=True is a no-op."""
    refs = [_ref("u0", date(2026, 4, 30)), _ref("u1", date(2026, 4, 29))]
    payloads = {r.source_uuid: _payload(r.source_uuid) for r in refs}
    source = _FakeSource(refs=refs, payloads=payloads)
    parser = _FakeParser()

    definition = _make_definition(source, parser)
    ds = Dataset(
        slug=definition.slug,
        title=definition.title,
        publisher=definition.publisher,
        source_url=definition.source_url,
        frequency=definition.frequency,
    )
    initialized_db.add(ds)
    initialized_db.commit()
    initialized_db.add(
        SourceFile(dataset_id=ds.id, source_uuid="u0", source_url="https://example.gm/u0")
    )
    initialized_db.commit()

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(definition, latest=True)
    assert summary.files_ingested == 0
    assert summary.files_skipped == 1


def test_ingest_creates_dataset_row_if_not_exists(initialized_db: Session) -> None:
    """First ingestion creates the ``Dataset`` row from the definition's metadata."""
    refs = [_ref("u0")]
    payloads = {"u0": _payload("u0")}
    source = _FakeSource(refs=refs, payloads=payloads)
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 2)})

    definition = _make_definition(source, parser, slug="brand-new", title="Brand New DS")
    orch = Orchestrator(session=initialized_db)
    orch.ingest(definition, latest=True)

    ds = initialized_db.execute(select(Dataset).where(Dataset.slug == "brand-new")).scalar_one()
    assert ds.title == "Brand New DS"
    assert ds.publisher == "Test Publisher"


def test_ingest_updates_dataset_last_ingested_at(initialized_db: Session) -> None:
    """``Dataset.last_ingested_at`` is set after a successful ingestion.

    SQLite strips tzinfo on read-back (Phase 2 known limitation). We compare
    against naive UTC bounds to stay consistent with that contract.
    """
    refs = [_ref("u0")]
    source = _FakeSource(refs=refs, payloads={"u0": _payload("u0")})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 1)})

    orch = Orchestrator(session=initialized_db)
    before = datetime.now(UTC).replace(tzinfo=None)
    orch.ingest(_make_definition(source, parser), latest=True)
    after = datetime.now(UTC).replace(tzinfo=None)

    ds = initialized_db.execute(
        select(Dataset).where(Dataset.slug == "orchestrator-test")
    ).scalar_one()
    assert ds.last_ingested_at is not None
    # Compare naive-to-naive (SQLite returns naive; Python set tz-aware).
    naive = ds.last_ingested_at.replace(tzinfo=None)
    assert before <= naive <= after


def test_ingest_creates_source_file_record_with_correct_fields(
    initialized_db: Session,
) -> None:
    refs = [_ref("u0", date(2026, 4, 30))]
    payload_bytes = _payload("u0")
    source = _FakeSource(refs=refs, payloads={"u0": payload_bytes})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 1)})

    orch = Orchestrator(session=initialized_db)
    orch.ingest(_make_definition(source, parser), latest=True)

    sf = initialized_db.execute(select(SourceFile)).scalar_one()
    assert sf.source_uuid == "u0"
    assert sf.source_url == "https://example.gm/downloads-file/u0"
    assert sf.file_hash is not None
    assert len(sf.file_hash) == 64  # sha256 hex
    assert sf.file_size_bytes == len(payload_bytes)
    assert sf.link_text == "sample-u0"
    assert sf.downloaded_at is not None
    assert sf.parsed_at is not None


def test_ingest_computes_file_hash_as_sha256_hex(initialized_db: Session) -> None:
    import hashlib

    refs = [_ref("u0")]
    payload_bytes = _payload("u0")
    source = _FakeSource(refs=refs, payloads={"u0": payload_bytes})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 1)})

    orch = Orchestrator(session=initialized_db)
    orch.ingest(_make_definition(source, parser), latest=True)

    sf = initialized_db.execute(select(SourceFile)).scalar_one()
    assert sf.file_hash == hashlib.sha256(payload_bytes).hexdigest()


def test_ingest_stores_raw_file_to_disk_when_raw_data_dir_set(
    initialized_db: Session, tmp_path: Path
) -> None:
    refs = [_ref("u0", date(2026, 4, 30))]
    payload_bytes = _payload("u0")
    source = _FakeSource(refs=refs, payloads={"u0": payload_bytes})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 1)})

    raw_dir = tmp_path / "raw"
    orch = Orchestrator(session=initialized_db, raw_data_dir=raw_dir)
    orch.ingest(_make_definition(source, parser), latest=True)

    expected = raw_dir / "orchestrator-test" / "2026-04-30.pdf"
    assert expected.exists()
    assert expected.read_bytes() == payload_bytes

    sf = initialized_db.execute(select(SourceFile)).scalar_one()
    assert sf.local_path is not None
    assert sf.local_path.endswith("2026-04-30.pdf")


def test_ingest_skips_raw_file_storage_when_raw_data_dir_is_none(
    initialized_db: Session,
) -> None:
    refs = [_ref("u0")]
    source = _FakeSource(refs=refs, payloads={"u0": _payload("u0")})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 1)})

    orch = Orchestrator(session=initialized_db, raw_data_dir=None)
    orch.ingest(_make_definition(source, parser), latest=True)

    sf = initialized_db.execute(select(SourceFile)).scalar_one()
    assert sf.local_path is None


def test_ingest_logs_ingestion_success(initialized_db: Session) -> None:
    refs = [_ref("u0")]
    source = _FakeSource(refs=refs, payloads={"u0": _payload("u0")})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 4)})

    orch = Orchestrator(session=initialized_db)
    orch.ingest(_make_definition(source, parser), latest=True)

    log = initialized_db.execute(select(IngestionLog)).scalar_one()
    assert log.status is IngestionStatus.SUCCESS
    assert log.rows_added == 4
    assert log.finished_at is not None


def test_ingest_logs_ingestion_failure_on_parse_error(initialized_db: Session) -> None:
    refs = [_ref("u0")]
    source = _FakeSource(refs=refs, payloads={"u0": _payload("u0")})
    parser = _FakeParser(raise_on_uuid={"u0": ParseError})

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(_make_definition(source, parser), latest=True)

    assert summary.files_failed == 1
    assert summary.files_ingested == 0

    # Source file row IS created (we successfully fetched), data rows are NOT.
    sf = initialized_db.execute(select(SourceFile)).scalar_one()
    assert sf.source_uuid == "u0"
    data = initialized_db.execute(select(_FakeOrm)).scalars().all()
    assert data == []

    log = initialized_db.execute(select(IngestionLog)).scalar_one()
    assert log.status is IngestionStatus.FAILED
    assert log.error_message is not None and "fail" in log.error_message.lower()
    assert log.error_traceback is not None


def test_ingest_logs_ingestion_failure_on_fetch_error(initialized_db: Session) -> None:
    refs = [_ref("u0")]
    source = _FakeSource(refs=refs, payloads={}, fetch_error=httpx.HTTPStatusError)
    parser = _FakeParser()

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(_make_definition(source, parser), latest=True)

    assert summary.files_failed == 1
    # No source file (we never successfully downloaded), no data rows.
    assert initialized_db.execute(select(SourceFile)).scalars().all() == []
    assert initialized_db.execute(select(_FakeOrm)).scalars().all() == []
    log = initialized_db.execute(select(IngestionLog)).scalar_one()
    assert log.status is IngestionStatus.FAILED


def test_ingest_rolls_back_data_rows_on_partial_parse_failure(
    initialized_db: Session,
) -> None:
    """A duplicate-key insert during a file's batch must roll back ONLY that file."""
    refs = [_ref("u0", date(2026, 4, 30)), _ref("u1", date(2026, 4, 29))]
    payloads = {r.source_uuid: _payload(r.source_uuid) for r in refs}
    source = _FakeSource(refs=refs, payloads=payloads)
    # u0 produces a duplicate (snapshot_date, name) within its batch.
    bad_records = [
        _FakeRecord(snapshot_date=date(2026, 4, 30), name="dup", value=1),
        _FakeRecord(snapshot_date=date(2026, 4, 30), name="dup", value=2),
    ]
    good_records = _records(date(2026, 4, 29), 3)
    parser = _FakeParser(records_per_uuid={"u0": bad_records, "u1": good_records})

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(_make_definition(source, parser), latest=False)

    assert summary.files_failed == 1
    assert summary.files_ingested == 1
    assert summary.total_rows_added == 3

    # u1's 3 rows survive; u0's 0 rows survived.
    rows = initialized_db.execute(select(_FakeOrm)).scalars().all()
    assert len(rows) == 3
    assert all(r.snapshot_date == date(2026, 4, 29) for r in rows)


def test_ingest_is_idempotent(initialized_db: Session) -> None:
    refs = [_ref("u0", date(2026, 4, 30))]
    source = _FakeSource(refs=refs, payloads={"u0": _payload("u0")})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 5)})

    orch = Orchestrator(session=initialized_db)
    first = orch.ingest(_make_definition(source, parser), latest=True)
    second = orch.ingest(_make_definition(source, parser), latest=True)

    assert first.files_ingested == 1
    assert second.files_ingested == 0
    assert second.files_skipped == 1

    rows = initialized_db.execute(select(_FakeOrm)).scalars().all()
    assert len(rows) == 5  # not 10 — no duplicates


def test_ingest_with_backfill_from_date_filters_refs(initialized_db: Session) -> None:
    refs = [
        _ref("u0", date(2026, 3, 1)),
        _ref("u1", date(2026, 2, 1)),
        _ref("u2", date(2026, 1, 1)),
    ]
    source = _FakeSource(refs=refs, payloads={r.source_uuid: _payload(r.source_uuid) for r in refs})
    parser = _FakeParser(
        records_per_uuid={
            "u0": _records(date(2026, 3, 1), 1),
            "u1": _records(date(2026, 2, 1), 1),
            "u2": _records(date(2026, 1, 1), 1),
        }
    )

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(
        _make_definition(source, parser),
        latest=False,
        backfill_from=date(2026, 2, 1),
    )

    assert summary.files_ingested == 2  # u0 (Mar) and u1 (Feb), not u2 (Jan)


def test_ingest_returns_summary_dataclass(initialized_db: Session) -> None:
    refs = [_ref("u0")]
    source = _FakeSource(refs=refs, payloads={"u0": _payload("u0")})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 7)})

    orch = Orchestrator(session=initialized_db)
    summary = orch.ingest(_make_definition(source, parser), latest=True)

    assert isinstance(summary, IngestionSummary)
    assert summary.dataset_slug == "orchestrator-test"
    assert summary.files_discovered == 1
    assert summary.files_skipped == 0
    assert summary.files_ingested == 1
    assert summary.files_failed == 0
    assert summary.total_rows_added == 7
    assert summary.duration_seconds >= 0


def test_ingest_logs_structured_summary(initialized_db: Session) -> None:
    refs = [_ref("u0")]
    source = _FakeSource(refs=refs, payloads={"u0": _payload("u0")})
    parser = _FakeParser(records_per_uuid={"u0": _records(date(2026, 4, 30), 2)})

    orch = Orchestrator(session=initialized_db)
    with structlog.testing.capture_logs() as captured:
        orch.ingest(_make_definition(source, parser), latest=True)

    assert any(
        e.get("event") == "ingestion_complete"
        and e.get("dataset_slug") == "orchestrator-test"
        and e.get("files_ingested") == 1
        and e.get("total_rows_added") == 2
        for e in captured
    )


def test_ingest_skips_refs_without_date_hint_when_backfill_set(
    initialized_db: Session,
) -> None:
    """``backfill_from`` with refs lacking a date hint: those refs are skipped + warned."""
    refs = [
        _ref("u0", date(2026, 3, 1)),
        _ref("u1", None),  # no hint — must be skipped under backfill
    ]
    source = _FakeSource(refs=refs, payloads={r.source_uuid: _payload(r.source_uuid) for r in refs})
    parser = _FakeParser(
        records_per_uuid={
            "u0": _records(date(2026, 3, 1), 1),
            "u1": _records(date(2026, 1, 1), 1),
        }
    )

    orch = Orchestrator(session=initialized_db)
    with structlog.testing.capture_logs() as captured:
        summary = orch.ingest(
            _make_definition(source, parser),
            latest=False,
            backfill_from=date(2026, 1, 1),
        )

    assert summary.files_ingested == 1  # only u0
    assert any(
        e.get("event") == "ref_skipped_no_date_hint" and e.get("source_uuid") == "u1"
        for e in captured
    )
