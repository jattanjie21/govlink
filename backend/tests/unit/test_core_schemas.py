"""Tests for govlink.core.schemas — shared API response schemas."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from govlink.core.schemas import (
    ErrorDetail,
    ErrorResponse,
    Meta,
    PaginationParams,
    Response,
)


def test_pagination_params_defaults() -> None:
    """Default PaginationParams must be (limit=100, offset=0)."""
    p = PaginationParams()
    assert p.limit == 100
    assert p.offset == 0


def test_pagination_params_max_limit() -> None:
    """A limit above 1000 must raise ValidationError."""
    with pytest.raises(ValidationError):
        PaginationParams(limit=10000)


def test_pagination_params_min_offset() -> None:
    """A negative offset must raise ValidationError."""
    with pytest.raises(ValidationError):
        PaginationParams(offset=-1)


def test_pagination_params_min_limit() -> None:
    """A limit of zero or below must raise ValidationError."""
    with pytest.raises(ValidationError):
        PaginationParams(limit=0)


def test_meta_serialises_with_iso_timestamp() -> None:
    """Meta.generated_at serialises to an ISO 8601 timestamp with timezone."""
    m = Meta(count=5)
    payload = m.model_dump(mode="json")
    assert "generated_at" in payload
    iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:\d{2})$"
    assert re.match(iso_pattern, payload["generated_at"]) is not None


def test_meta_default_generated_at_is_utc() -> None:
    """``generated_at`` defaults to a timezone-aware UTC datetime."""
    m = Meta(count=0)
    assert isinstance(m.generated_at, datetime)
    assert m.generated_at.tzinfo is not None
    assert m.generated_at.utcoffset() == UTC.utcoffset(None)


def test_meta_optional_fields_default_to_none() -> None:
    """Optional Meta fields default to None unless provided."""
    m = Meta(count=10)
    assert m.dataset is None
    assert m.total is None
    assert m.limit is None
    assert m.offset is None
    assert m.snapshot_date is None


def test_meta_serialises_snapshot_date() -> None:
    """``snapshot_date`` (a ``date``) serialises to ISO 8601 ``YYYY-MM-DD``."""
    m = Meta(count=1, snapshot_date=date(2026, 5, 3))
    payload = m.model_dump(mode="json")
    assert payload["snapshot_date"] == "2026-05-03"


def test_response_envelope_generic_typed() -> None:
    """``Response[list[int]]`` correctly types the data field."""
    resp = Response[list[int]](data=[1, 2, 3], meta=Meta(count=3))
    assert resp.data == [1, 2, 3]
    assert resp.meta.count == 3


def test_response_envelope_serializes_to_expected_shape() -> None:
    """A serialised Response has exactly the keys ``data`` and ``meta``."""
    resp = Response[list[str]](data=["a", "b"], meta=Meta(count=2))
    payload = resp.model_dump(mode="json")
    assert set(payload.keys()) == {"data", "meta"}
    assert payload["data"] == ["a", "b"]
    assert payload["meta"]["count"] == 2
    # And it round-trips through JSON cleanly.
    json.dumps(payload)


def test_error_response_structure() -> None:
    """``ErrorResponse`` exposes ``error.code``, ``error.message``, optional ``error.details``."""
    err = ErrorResponse(
        error=ErrorDetail(
            code="dataset_not_found",
            message="No dataset with that slug.",
            details={"slug": "missing"},
        )
    )
    payload = err.model_dump(mode="json")
    assert payload["error"]["code"] == "dataset_not_found"
    assert payload["error"]["message"] == "No dataset with that slug."
    assert payload["error"]["details"] == {"slug": "missing"}


def test_error_detail_details_optional() -> None:
    """``ErrorDetail.details`` defaults to None when omitted."""
    detail = ErrorDetail(code="x", message="y")
    assert detail.details is None
