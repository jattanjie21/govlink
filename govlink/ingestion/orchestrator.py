"""Ingestion orchestrator — drives the source → parse → store pipeline.

The :class:`Orchestrator` is dataset-agnostic. Given a
:class:`govlink.core.definition.DatasetDefinition`, it discovers source
files, filters out already-ingested ones (idempotency keyed on
``source_uuid``), fetches new bytes, parses them, and stores both the
raw-file metadata and the parsed records inside per-file SAVEPOINTs so
one file's failure cannot poison another's success.

Convention assumed by ``latest=True``: sources return their refs in
newest-first order. ``BaseSource.discover`` documents this contract.
"""

from __future__ import annotations

import hashlib
import time
import traceback
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from govlink.core.models import (
    Dataset,
    IngestionLog,
    IngestionStatus,
    SourceFile,
)
from govlink.core.source_ref import SourceFileRef

if TYPE_CHECKING:
    from govlink.core.definition import DatasetDefinition

_logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class IngestionSummary:
    """Aggregate result of one :meth:`Orchestrator.ingest` invocation."""

    dataset_slug: str
    files_discovered: int
    files_skipped: int
    files_ingested: int
    files_failed: int
    total_rows_added: int
    duration_seconds: float


class Orchestrator:
    """Drive the full ingestion cycle for a single dataset.

    Each file is processed inside a SAVEPOINT (``session.begin_nested``)
    so failure on one file rolls back only that file's writes — earlier
    successful files remain committed at the outer-transaction level.
    """

    def __init__(self, session: Session, raw_data_dir: Path | None = None) -> None:
        self._session = session
        self._raw_data_dir = raw_data_dir

    def ingest(
        self,
        definition: DatasetDefinition,
        *,
        latest: bool = True,
        backfill_from: date | None = None,
    ) -> IngestionSummary:
        """Run one ingestion cycle for the given dataset definition.

        ``latest=True`` (default) takes only the first ref returned by
        ``definition.source.discover()`` — sources are expected to yield
        in newest-first order. ``latest=False`` processes every ref,
        optionally filtered by ``backfill_from`` (refs without a
        ``published_date_hint`` are skipped under that filter, with a
        warning log).
        """
        started_monotonic = time.monotonic()
        dataset_row = self._upsert_dataset(definition)

        all_refs = list(definition.source.discover())
        candidates = self._select_candidates(all_refs, latest=latest, backfill_from=backfill_from)

        files_skipped = 0
        files_ingested = 0
        files_failed = 0
        total_rows_added = 0

        for ref in candidates:
            existing = self._session.execute(
                select(SourceFile).where(SourceFile.source_uuid == ref.source_uuid)
            ).scalar_one_or_none()
            if existing is not None:
                files_skipped += 1
                _logger.info(
                    "ref_skipped_already_ingested",
                    source_uuid=ref.source_uuid,
                    dataset_slug=definition.slug,
                )
                continue

            outcome = self._process_one(definition, dataset_row, ref)
            if outcome.success:
                files_ingested += 1
                total_rows_added += outcome.rows_added
            else:
                files_failed += 1

        if files_ingested > 0:
            dataset_row.last_ingested_at = datetime.now(UTC)
            self._session.commit()

        duration = time.monotonic() - started_monotonic
        summary = IngestionSummary(
            dataset_slug=definition.slug,
            files_discovered=len(all_refs),
            files_skipped=files_skipped,
            files_ingested=files_ingested,
            files_failed=files_failed,
            total_rows_added=total_rows_added,
            duration_seconds=duration,
        )
        _logger.info(
            "ingestion_complete",
            dataset_slug=summary.dataset_slug,
            files_discovered=summary.files_discovered,
            files_skipped=summary.files_skipped,
            files_ingested=summary.files_ingested,
            files_failed=summary.files_failed,
            total_rows_added=summary.total_rows_added,
            duration_seconds=round(summary.duration_seconds, 4),
        )
        return summary

    # --- internals -----------------------------------------------------

    def _upsert_dataset(self, definition: DatasetDefinition) -> Dataset:
        ds = self._session.execute(
            select(Dataset).where(Dataset.slug == definition.slug)
        ).scalar_one_or_none()
        if ds is None:
            ds = Dataset(
                slug=definition.slug,
                title=definition.title,
                description=definition.description,
                publisher=definition.publisher,
                source_url=definition.source_url,
                frequency=definition.frequency,
            )
            self._session.add(ds)
            self._session.commit()
        return ds

    def _select_candidates(
        self,
        refs: list[SourceFileRef],
        *,
        latest: bool,
        backfill_from: date | None,
    ) -> list[SourceFileRef]:
        if latest:
            return refs[:1]
        if backfill_from is None:
            return refs
        kept: list[SourceFileRef] = []
        for ref in refs:
            if ref.published_date_hint is None:
                _logger.warning(
                    "ref_skipped_no_date_hint",
                    source_uuid=ref.source_uuid,
                    backfill_from=backfill_from.isoformat(),
                )
                continue
            if ref.published_date_hint >= backfill_from:
                kept.append(ref)
        return kept

    def _process_one(
        self,
        definition: DatasetDefinition,
        dataset_row: Dataset,
        ref: SourceFileRef,
    ) -> _FileOutcome:
        log = IngestionLog(dataset_id=dataset_row.id, status=IngestionStatus.PENDING)
        self._session.add(log)
        self._session.commit()

        # 1) Fetch — failures here mean we never created a SourceFile row.
        try:
            log.status = IngestionStatus.RUNNING
            self._session.commit()
            raw_bytes = definition.source.fetch(ref)
        except Exception as e:
            self._record_failure(log, e)
            return _FileOutcome(success=False, rows_added=0)

        # 2) Commit SourceFile up front. The fetch succeeded, so we want the
        #    metadata persisted regardless of whether the parse step succeeds.
        sf = self._build_source_file(dataset_row, ref, raw_bytes, definition.slug)
        self._session.add(sf)
        self._session.commit()
        log.source_file_id = sf.id
        self._session.commit()

        # 3) Parse + insert data rows inside a SAVEPOINT. A parse error or
        #    unique-constraint violation rolls back ONLY the data rows for
        #    this file; the SourceFile row above survives.
        nested = self._session.begin_nested()
        rows_added = 0
        try:
            records = definition.parser.parse(raw_bytes)
            sf.parsed_at = datetime.now(UTC)
            orm_rows = [
                definition.model_class(**rec.model_dump(), source_file_id=sf.id) for rec in records
            ]
            self._session.add_all(orm_rows)
            self._session.flush()  # surfaces unique-constraint violations now
            rows_added = len(orm_rows)
            nested.commit()
        except Exception as e:
            nested.rollback()
            self._record_failure(log, e)
            return _FileOutcome(success=False, rows_added=0)

        log.status = IngestionStatus.SUCCESS
        log.rows_added = rows_added
        log.finished_at = datetime.now(UTC)
        self._session.commit()
        return _FileOutcome(success=True, rows_added=rows_added)

    def _build_source_file(
        self,
        dataset_row: Dataset,
        ref: SourceFileRef,
        raw_bytes: bytes,
        slug: str,
    ) -> SourceFile:
        local_path: str | None = None
        if self._raw_data_dir is not None:
            local_path = self._write_raw_bytes(slug, ref, raw_bytes)
        return SourceFile(
            dataset_id=dataset_row.id,
            source_uuid=ref.source_uuid,
            source_url=ref.url,
            local_path=local_path,
            file_hash=hashlib.sha256(raw_bytes).hexdigest(),
            file_size_bytes=len(raw_bytes),
            link_text=ref.link_text,
            downloaded_at=datetime.now(UTC),
        )

    def _write_raw_bytes(self, slug: str, ref: SourceFileRef, raw_bytes: bytes) -> str:
        assert self._raw_data_dir is not None  # guarded by caller
        stem = (
            ref.published_date_hint.isoformat()
            if ref.published_date_hint is not None
            else ref.source_uuid
        )
        target = self._raw_data_dir / slug / f"{stem}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw_bytes)
        return str(target)

    def _record_failure(self, log: IngestionLog, exc: Exception) -> None:
        log.status = IngestionStatus.FAILED
        log.error_message = str(exc) or exc.__class__.__name__
        log.error_traceback = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log.finished_at = datetime.now(UTC)
        self._session.commit()


@dataclass(frozen=True)
class _FileOutcome:
    success: bool
    rows_added: int


# Re-export for callers that want the dataclass without importing the helper.
__all__: list[Any] = ["IngestionSummary", "Orchestrator"]
