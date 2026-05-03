"""Registry-layer SQLAlchemy models.

These four tables describe *which* datasets exist in the system, what
their fields are, what raw files have been seen for each, and what
happened during each ingestion run. They are NOT data tables — the
per-dataset data tables live in ``govlink.datasets.<name>.model``.
"""

from __future__ import annotations

import enum
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from govlink.db import Base

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _utcnow() -> datetime:
    """UTC-aware ``datetime.now`` — the project's canonical clock source."""
    return datetime.now(UTC)


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Return the ``.value`` strings of an Enum class (for SQLAlchemy ``Enum``)."""
    return [member.value for member in enum_cls]


class DatasetFrequency(enum.StrEnum):
    """Publication cadence for a dataset."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    IRREGULAR = "irregular"


class IngestionStatus(enum.StrEnum):
    """Lifecycle states for an ingestion run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Dataset(Base):
    """A registered dataset (e.g. ``exchange-rates``)."""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    frequency: Mapped[DatasetFrequency] = mapped_column(
        Enum(
            DatasetFrequency,
            name="dataset_frequency",
            native_enum=False,
            length=32,
            create_constraint=True,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    last_ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    schema_definition: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    fields: Mapped[list[DatasetField]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    source_files: Mapped[list[SourceFile]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    ingestion_logs: Mapped[list[IngestionLog]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @validates("slug")
    def _validate_slug(self, _key: str, value: str) -> str:
        if not isinstance(value, str) or not _SLUG_PATTERN.match(value):
            raise ValueError(f"Invalid slug {value!r}: must match {_SLUG_PATTERN.pattern}")
        return value

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} slug={self.slug!r}>"


class DatasetField(Base):
    """A single field declared by a dataset's schema."""

    __tablename__ = "dataset_fields"
    __table_args__ = (UniqueConstraint("dataset_id", "field_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="fields")

    def __repr__(self) -> str:
        return (
            f"<DatasetField id={self.id} dataset_id={self.dataset_id} "
            f"field_name={self.field_name!r}>"
        )


class SourceFile(Base):
    """A raw artifact (typically a PDF) discovered upstream for a dataset."""

    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    link_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        nullable=False,
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="source_files")

    def __repr__(self) -> str:
        return (
            f"<SourceFile id={self.id} source_uuid={self.source_uuid!r} "
            f"dataset_id={self.dataset_id}>"
        )


class IngestionLog(Base):
    """One ingestion attempt, success or failure, for a dataset."""

    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_files.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(
            IngestionStatus,
            name="ingestion_status",
            native_enum=False,
            length=16,
            create_constraint=True,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rows_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="ingestion_logs")
    source_file: Mapped[SourceFile | None] = relationship()

    def __repr__(self) -> str:
        status_value = (
            self.status.value if isinstance(self.status, IngestionStatus) else self.status
        )
        return f"<IngestionLog id={self.id} dataset_id={self.dataset_id} status={status_value!r}>"
