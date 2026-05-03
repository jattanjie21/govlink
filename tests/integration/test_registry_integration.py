"""End-to-end tests for the dataset registry pattern.

Exercises the full machinery — DatasetDefinition construction, registration,
retrieval, and auto-discovery from a real on-disk subpackage — using
realistic-shaped fakes. No real PDF parsing or HTTP traffic.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from pydantic import BaseModel
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from govlink.core.base_parser import BaseParser
from govlink.core.base_source import BaseSource
from govlink.core.definition import DatasetDefinition
from govlink.core.models import DatasetFrequency
from govlink.core.registry import DatasetRegistry, get_registry
from govlink.core.source_ref import SourceFileRef
from govlink.db import Base

# --- Module-level fakes shared across tests + the temporary auto-discover dataset.py.


class _IntRecord(BaseModel):
    """Pydantic record produced by ``_IntParser`` and validated against ``_IntSchema``."""

    field_a: int


class _IntSource(BaseSource):
    """A source returning a single fixed ref with stable bytes."""

    def discover(self) -> Iterable[SourceFileRef]:
        return [
            SourceFileRef(
                source_uuid="int-uuid-1",
                url="https://example.gm/int.pdf",
                link_text="Integration sample",
            )
        ]

    def fetch(self, ref: SourceFileRef) -> bytes:
        return b"sample-bytes"


class _IntParser(BaseParser[_IntRecord]):
    """A parser that produces a single _IntRecord regardless of input."""

    def parse(self, raw_bytes: bytes) -> list[_IntRecord]:
        return [_IntRecord(field_a=42)]


class _IntSchema(BaseModel):
    field_a: int


class _IntOrm(Base):
    __tablename__ = "data_integration_main"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_a: Mapped[str] = mapped_column(String(8), nullable=False)


class _MyTestOrm(Base):
    __tablename__ = "data_my_test_dataset"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_a: Mapped[str] = mapped_column(String(8), nullable=False)


class _AlphaOrm(Base):
    __tablename__ = "data_alpha_int"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class _BetaOrm(Base):
    __tablename__ = "data_beta_int"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class _TempOrm(Base):
    __tablename__ = "data_temp_test_dataset"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


def _make_temp_definition(slug: str) -> DatasetDefinition:
    """Build a DatasetDefinition for the on-disk auto-discover fixture."""
    return DatasetDefinition(
        slug=slug,
        title="Temporary Test Dataset",
        publisher="Integration Test",
        source_url="https://example.gm/temp",
        frequency=DatasetFrequency.IRREGULAR,
        source=_IntSource(),
        parser=_IntParser(),
        model_class=_TempOrm,
        schema_class=_IntSchema,
    )


# --- Tests.


def test_full_registration_flow(fresh_registry: DatasetRegistry) -> None:
    """Constructing, registering, and retrieving a definition round-trips fully."""
    definition = DatasetDefinition(
        slug="integration-main",
        title="Integration Main",
        description="A dataset built end-to-end from fakes.",
        publisher="Integration Test Publisher",
        source_url="https://example.gm/int",
        frequency=DatasetFrequency.DAILY,
        source=_IntSource(),
        parser=_IntParser(),
        model_class=_IntOrm,
        schema_class=_IntSchema,
    )
    fresh_registry.register(definition)
    fetched = fresh_registry.get("integration-main")

    assert fetched is definition
    assert fetched.slug == "integration-main"
    assert fetched.title == "Integration Main"
    assert fetched.description == "A dataset built end-to-end from fakes."
    assert fetched.publisher == "Integration Test Publisher"
    assert fetched.source_url == "https://example.gm/int"
    assert fetched.frequency is DatasetFrequency.DAILY
    assert isinstance(fetched.source, _IntSource)
    assert isinstance(fetched.parser, _IntParser)
    assert fetched.model_class is _IntOrm
    assert fetched.schema_class is _IntSchema

    # The data flow contracts hold end-to-end.
    refs = list(fetched.source.discover())
    assert len(refs) == 1
    body = fetched.source.fetch(refs[0])
    records = fetched.parser.parse(body)
    assert records == [_IntRecord(field_a=42)]


def test_definition_data_table_name_matches_orm_model_tablename(
    fresh_registry: DatasetRegistry,
) -> None:
    """``data_table_name`` derived from the slug matches the ORM ``__tablename__``."""
    definition = DatasetDefinition(
        slug="my-test-dataset",
        title="My Test Dataset",
        publisher="Test",
        source_url="https://example.gm/x",
        frequency=DatasetFrequency.MONTHLY,
        source=_IntSource(),
        parser=_IntParser(),
        model_class=_MyTestOrm,
        schema_class=_IntSchema,
    )
    fresh_registry.register(definition)
    assert definition.data_table_name == "data_my_test_dataset"
    assert definition.data_table_name == _MyTestOrm.__tablename__


def test_two_definitions_for_different_datasets_coexist(
    fresh_registry: DatasetRegistry,
) -> None:
    """Two distinct slugs both register and remain independently retrievable."""
    alpha = DatasetDefinition(
        slug="alpha-int",
        title="Alpha",
        publisher="Test",
        source_url="https://example.gm/a",
        frequency=DatasetFrequency.WEEKLY,
        source=_IntSource(),
        parser=_IntParser(),
        model_class=_AlphaOrm,
        schema_class=_IntSchema,
    )
    beta = DatasetDefinition(
        slug="beta-int",
        title="Beta",
        publisher="Test",
        source_url="https://example.gm/b",
        frequency=DatasetFrequency.QUARTERLY,
        source=_IntSource(),
        parser=_IntParser(),
        model_class=_BetaOrm,
        schema_class=_IntSchema,
    )
    fresh_registry.register(alpha)
    fresh_registry.register(beta)

    assert fresh_registry.get("alpha-int") is alpha
    assert fresh_registry.get("beta-int") is beta
    assert fresh_registry.list_slugs() == ["alpha-int", "beta-int"]
    assert fresh_registry.get("alpha-int").model_class is _AlphaOrm
    assert fresh_registry.get("beta-int").model_class is _BetaOrm


def test_auto_discover_with_temporary_dataset_subpackage(
    isolated_global_registry: DatasetRegistry,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Writing a real subpackage on disk and pointing auto_discover at it works.

    The temporary ``dataset.py`` imports shared fakes from this test module
    (which is importable as ``tests.integration.test_registry_integration``
    because ``tests/__init__.py`` exists), constructs a real
    ``DatasetDefinition``, and calls ``get_registry().register(...)`` at
    import time — exactly mirroring the real plugin pattern.
    """
    pkg_root = tmp_path / "temp_disco_pkg"
    sub_pkg = pkg_root / "temp_test_dataset"
    sub_pkg.mkdir(parents=True)
    (pkg_root / "__init__.py").write_text("")
    (sub_pkg / "__init__.py").write_text("")
    (sub_pkg / "dataset.py").write_text(
        "from tests.integration.test_registry_integration import _make_temp_definition\n"
        "from govlink.core.registry import get_registry\n"
        "\n"
        "get_registry().register(_make_temp_definition('temp-test-dataset'))\n"
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    isolated_global_registry.auto_discover(package="temp_disco_pkg")

    assert "temp-test-dataset" in get_registry()
    fetched = get_registry().get("temp-test-dataset")
    assert fetched.slug == "temp-test-dataset"
    assert fetched.title == "Temporary Test Dataset"
    assert fetched.frequency is DatasetFrequency.IRREGULAR
    assert fetched.model_class is _TempOrm
