"""Tests for govlink.core.definition — DatasetDefinition wiring model."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from govlink.core.base_parser import BaseParser
from govlink.core.base_source import BaseSource
from govlink.core.definition import DatasetDefinition
from govlink.core.models import DatasetFrequency
from govlink.core.source_ref import SourceFileRef
from govlink.db import Base


class _DefRecord(BaseModel):
    field_a: int


class _DefSource(BaseSource):
    def discover(self) -> Iterable[SourceFileRef]:
        return []

    def fetch(self, ref: SourceFileRef) -> bytes:
        return b""


class _DefParser(BaseParser[_DefRecord]):
    def parse(self, raw_bytes: bytes) -> list[_DefRecord]:
        return []


class _DefSchema(BaseModel):
    field_a: int


class _DefOrm(Base):
    __tablename__ = "data_definition_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_a: Mapped[str] = mapped_column(String(32), nullable=False)


def _make_definition(**overrides: Any) -> DatasetDefinition:
    base: dict[str, Any] = {
        "slug": "definition-test",
        "title": "Definition Test Dataset",
        "publisher": "Test Publisher",
        "source_url": "https://example.gm/test",
        "frequency": DatasetFrequency.DAILY,
        "source": _DefSource(),
        "parser": _DefParser(),
        "model_class": _DefOrm,
        "schema_class": _DefSchema,
    }
    base.update(overrides)
    return DatasetDefinition(**base)


def test_definition_construction_with_all_fields() -> None:
    """A DatasetDefinition with every field validates and exposes them."""
    d = _make_definition(description="A test dataset")
    assert d.slug == "definition-test"
    assert d.title == "Definition Test Dataset"
    assert d.description == "A test dataset"
    assert d.publisher == "Test Publisher"
    assert d.source_url == "https://example.gm/test"
    assert d.frequency is DatasetFrequency.DAILY
    assert isinstance(d.source, _DefSource)
    assert isinstance(d.parser, _DefParser)
    assert d.model_class is _DefOrm
    assert d.schema_class is _DefSchema


def test_definition_is_frozen() -> None:
    """Mutating a field after construction must raise."""
    d = _make_definition()
    with pytest.raises(ValidationError):
        d.slug = "other"  # type: ignore[misc]


def test_definition_rejects_extra_fields() -> None:
    """``extra='forbid'`` rejects unknown keys."""
    with pytest.raises(ValidationError):
        _make_definition(unexpected="value")


def test_definition_slug_must_match_pattern() -> None:
    """An invalid slug raises ValidationError at construction time."""
    with pytest.raises(ValidationError):
        _make_definition(slug="Bad Slug")
    with pytest.raises(ValidationError):
        _make_definition(slug="UPPERCASE")
    with pytest.raises(ValidationError):
        _make_definition(slug="under_score")


def test_definition_frequency_uses_dataset_frequency_enum() -> None:
    """A string from the enum is accepted; an invalid string is rejected."""
    d = _make_definition(frequency="weekly")
    assert d.frequency is DatasetFrequency.WEEKLY
    with pytest.raises(ValidationError):
        _make_definition(frequency="hourly")


def test_definition_source_must_be_base_source_instance() -> None:
    """Passing a non-BaseSource raises a clear validation error."""
    with pytest.raises(ValidationError):
        _make_definition(source="not-a-source")
    with pytest.raises(ValidationError):
        _make_definition(source=object())


def test_definition_parser_must_be_base_parser_instance() -> None:
    """Passing a non-BaseParser raises a clear validation error."""
    with pytest.raises(ValidationError):
        _make_definition(parser="not-a-parser")


def test_definition_model_class_must_be_subclass_of_base() -> None:
    """``model_class`` must be a subclass of govlink.db.Base."""

    class _NotBase:
        pass

    with pytest.raises(ValidationError):
        _make_definition(model_class=_NotBase)
    with pytest.raises(ValidationError):
        _make_definition(model_class="not-a-class")


def test_definition_schema_class_must_be_subclass_of_basemodel() -> None:
    """``schema_class`` must be a subclass of pydantic.BaseModel."""

    class _NotPydantic:
        pass

    with pytest.raises(ValidationError):
        _make_definition(schema_class=_NotPydantic)
    with pytest.raises(ValidationError):
        _make_definition(schema_class="not-a-class")


def test_definition_data_table_name_property_derived_from_slug() -> None:
    """``data_table_name`` is ``data_<slug_with_underscores>``."""
    d = _make_definition(slug="exchange-rates")
    assert d.data_table_name == "data_exchange_rates"
    d2 = _make_definition(slug="cpi")
    assert d2.data_table_name == "data_cpi"
    d3 = _make_definition(slug="multi-segment-slug")
    assert d3.data_table_name == "data_multi_segment_slug"


def test_definition_repr_includes_slug() -> None:
    """``repr`` surfaces the slug for debugging."""
    d = _make_definition(slug="repr-test")
    assert "repr-test" in repr(d)
    assert "DatasetDefinition" in repr(d)
