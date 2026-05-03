"""Shared Pydantic v2 schemas used across datasets and API responses.

Provides the response envelope (:class:`Response`), pagination
parameters (:class:`PaginationParams`), the metadata block
(:class:`Meta`), and the error structures (:class:`ErrorDetail`,
:class:`ErrorResponse`). Per-dataset response models live next to the
dataset they describe.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    """Pagination knobs accepted by list endpoints."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Meta(BaseModel):
    """Response envelope metadata block."""

    model_config = ConfigDict(extra="forbid")

    dataset: str | None = None
    count: int = Field(ge=0)
    total: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=0)
    offset: int | None = Field(default=None, ge=0)
    snapshot_date: date | None = None
    generated_at: datetime = Field(default_factory=_utcnow)


class Response[T](BaseModel):
    """Generic response envelope wrapping a typed ``data`` payload."""

    model_config = ConfigDict(extra="forbid")

    data: T
    meta: Meta


class ErrorDetail(BaseModel):
    """Machine-readable error details emitted under :attr:`ErrorResponse.error`."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Top-level error envelope returned by failed API requests."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
