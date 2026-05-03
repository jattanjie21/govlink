"""Tests for govlink.core.source_ref — SourceFileRef value object."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from govlink.core.source_ref import SourceFileRef


def _make_ref(**overrides: object) -> SourceFileRef:
    """Build a minimally valid SourceFileRef with overridable fields."""
    base: dict[str, object] = {
        "source_uuid": "01f3604a-4474-11f1-8725-02e599c15748",
        "url": "https://www.cbg.gm/files/example.pdf",
        "link_text": "Daily exchange rates — 2026-05-01",
    }
    base.update(overrides)
    return SourceFileRef(**base)  # type: ignore[arg-type]


def test_source_file_ref_construction_with_required_fields() -> None:
    """Can construct with the documented required fields."""
    ref = SourceFileRef(
        source_uuid="abc-123",
        url="https://example.gm/x.pdf",
        link_text="Example PDF",
    )
    assert ref.source_uuid == "abc-123"
    assert ref.url == "https://example.gm/x.pdf"
    assert ref.link_text == "Example PDF"


def test_source_file_ref_is_frozen() -> None:
    """Mutating a field after construction must raise ValidationError."""
    ref = _make_ref()
    with pytest.raises(ValidationError):
        ref.url = "https://other.example.com/y.pdf"  # type: ignore[misc]


def test_source_file_ref_rejects_extra_fields() -> None:
    """Unknown keys must be rejected (extra='forbid')."""
    with pytest.raises(ValidationError):
        SourceFileRef(  # type: ignore[call-arg]
            source_uuid="x",
            url="https://example.gm/x.pdf",
            link_text=None,
            unexpected_field=42,
        )


def test_source_file_ref_source_uuid_required_non_empty() -> None:
    """An empty ``source_uuid`` must raise ValidationError."""
    with pytest.raises(ValidationError):
        _make_ref(source_uuid="")


def test_source_file_ref_url_must_be_http_or_https() -> None:
    """``url`` must use the http:// or https:// scheme."""
    with pytest.raises(ValidationError):
        _make_ref(url="ftp://example.com/x.pdf")
    with pytest.raises(ValidationError):
        _make_ref(url="file:///etc/passwd")
    with pytest.raises(ValidationError):
        _make_ref(url="//example.com/x.pdf")
    # Both http and https are accepted.
    assert _make_ref(url="http://a.gm/x.pdf").url.startswith("http://")
    assert _make_ref(url="https://a.gm/x.pdf").url.startswith("https://")


def test_source_file_ref_published_date_hint_optional() -> None:
    """``published_date_hint`` is optional and defaults to None."""
    ref = _make_ref()
    assert ref.published_date_hint is None


def test_source_file_ref_published_date_hint_must_be_date_not_datetime() -> None:
    """Field type is ``date`` — datetime values must not silently survive as datetimes."""
    ref = _make_ref(published_date_hint=date(2026, 5, 1))
    assert isinstance(ref.published_date_hint, date)
    assert not isinstance(ref.published_date_hint, datetime)

    # A datetime input must either be rejected or coerced to a plain date.
    try:
        ref2 = _make_ref(published_date_hint=datetime(2026, 5, 1, 12, 30, tzinfo=UTC))
    except ValidationError:
        return
    assert ref2.published_date_hint is not None
    assert isinstance(ref2.published_date_hint, date)
    assert not isinstance(ref2.published_date_hint, datetime)


def test_source_file_ref_equality_by_value() -> None:
    """Two refs with identical fields must compare equal."""
    a = _make_ref(source_uuid="same", url="https://a.gm/x.pdf", link_text="t")
    b = _make_ref(source_uuid="same", url="https://a.gm/x.pdf", link_text="t")
    assert a == b


def test_source_file_ref_hashable() -> None:
    """Frozen refs must be hashable and usable in sets / dict keys."""
    a = _make_ref(source_uuid="u1", url="https://a.gm/1.pdf")
    b = _make_ref(source_uuid="u2", url="https://a.gm/2.pdf")
    bag = {a, b, a}
    assert len(bag) == 2
    lookup = {a: "one", b: "two"}
    assert lookup[a] == "one"
