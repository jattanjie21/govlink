"""Tests for govlink.core.registry — DatasetRegistry and global accessors."""

from __future__ import annotations

from collections.abc import Iterable
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest
import structlog
from pydantic import BaseModel
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from govlink.core.base_parser import BaseParser
from govlink.core.base_source import BaseSource
from govlink.core.definition import DatasetDefinition
from govlink.core.models import DatasetFrequency
from govlink.core.registry import (
    DatasetAlreadyRegisteredError,
    DatasetNotFoundError,
    DatasetRegistry,
    get_registry,
)
from govlink.core.source_ref import SourceFileRef
from govlink.db import Base


class _RegRecord(BaseModel):
    n: int


class _RegSource(BaseSource):
    def discover(self) -> Iterable[SourceFileRef]:
        return []

    def fetch(self, ref: SourceFileRef) -> bytes:
        return b""


class _RegParser(BaseParser[_RegRecord]):
    def parse(self, raw_bytes: bytes) -> list[_RegRecord]:
        return []


class _RegOrm(Base):
    __tablename__ = "data_registry_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    n: Mapped[str] = mapped_column(String(8), nullable=False)


class _RegSchema(BaseModel):
    n: int


def _definition(slug: str = "registry-test", title: str = "Registry Test") -> DatasetDefinition:
    return DatasetDefinition(
        slug=slug,
        title=title,
        publisher="Test Publisher",
        source_url="https://example.gm/x",
        frequency=DatasetFrequency.DAILY,
        source=_RegSource(),
        parser=_RegParser(),
        model_class=_RegOrm,
        schema_class=_RegSchema,
    )


def test_registry_starts_empty(fresh_registry: DatasetRegistry) -> None:
    """A freshly-constructed registry holds no definitions."""
    assert fresh_registry.list_all() == []
    assert fresh_registry.list_slugs() == []


def test_register_adds_definition(fresh_registry: DatasetRegistry) -> None:
    """``register`` makes a definition retrievable by its slug."""
    d = _definition(slug="alpha")
    fresh_registry.register(d)
    assert fresh_registry.get("alpha") is d


def test_register_duplicate_slug_raises(fresh_registry: DatasetRegistry) -> None:
    """Re-registering a slug raises ``DatasetAlreadyRegisteredError``."""
    fresh_registry.register(_definition(slug="dup"))
    with pytest.raises(DatasetAlreadyRegisteredError) as excinfo:
        fresh_registry.register(_definition(slug="dup"))
    assert "dup" in str(excinfo.value)
    assert excinfo.value.slug == "dup"


def test_register_returns_definition_for_chaining(fresh_registry: DatasetRegistry) -> None:
    """``register`` returns the registered definition (chain-friendly)."""
    d = _definition(slug="chain")
    returned = fresh_registry.register(d)
    assert returned is d


def test_get_unknown_slug_raises(fresh_registry: DatasetRegistry) -> None:
    """``get`` raises ``DatasetNotFoundError`` for an unknown slug."""
    with pytest.raises(DatasetNotFoundError) as excinfo:
        fresh_registry.get("nonexistent")
    assert "nonexistent" in str(excinfo.value)
    assert excinfo.value.slug == "nonexistent"


def test_get_returns_correct_definition(fresh_registry: DatasetRegistry) -> None:
    """With multiple registrations, ``get`` returns the matching one by slug."""
    a = _definition(slug="a")
    b = _definition(slug="b")
    fresh_registry.register(a)
    fresh_registry.register(b)
    assert fresh_registry.get("a") is a
    assert fresh_registry.get("b") is b


def test_list_all_returns_all_registered_in_insertion_order(
    fresh_registry: DatasetRegistry,
) -> None:
    """``list_all`` preserves registration order."""
    slugs = ["first", "second", "third"]
    for s in slugs:
        fresh_registry.register(_definition(slug=s))
    assert [d.slug for d in fresh_registry.list_all()] == slugs


def test_list_slugs_returns_just_slug_strings(fresh_registry: DatasetRegistry) -> None:
    """``list_slugs`` returns the slug strings in registration order."""
    fresh_registry.register(_definition(slug="one"))
    fresh_registry.register(_definition(slug="two"))
    assert fresh_registry.list_slugs() == ["one", "two"]


def test_contains_supports_in_operator(fresh_registry: DatasetRegistry) -> None:
    """The ``in`` operator works for slug membership."""
    fresh_registry.register(_definition(slug="present"))
    assert "present" in fresh_registry
    assert "absent" not in fresh_registry
    assert 42 not in fresh_registry  # non-string keys are never present


def test_clear_resets_registry(fresh_registry: DatasetRegistry) -> None:
    """``clear`` removes all registrations."""
    fresh_registry.register(_definition(slug="x"))
    fresh_registry.register(_definition(slug="y"))
    fresh_registry.clear()
    assert fresh_registry.list_all() == []


def test_global_registry_singleton_returns_same_instance(
    isolated_global_registry: DatasetRegistry,
) -> None:
    """``get_registry`` returns the same instance across calls."""
    assert get_registry() is get_registry()
    assert get_registry() is isolated_global_registry


def test_global_registry_distinct_from_fresh_instances(
    isolated_global_registry: DatasetRegistry,
) -> None:
    """A new ``DatasetRegistry()`` is NOT the global one."""
    fresh = DatasetRegistry()
    assert fresh is not get_registry()


def test_auto_discover_imports_each_dataset_subpackage(
    isolated_global_registry: DatasetRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``auto_discover`` imports the ``dataset`` submodule of each subpackage."""
    fake_root = ModuleType("fake_pkg")
    fake_root.__path__ = ["/fake/path"]  # type: ignore[attr-defined]

    fake_modules = [
        MagicMock(name="alpha", ispkg=True),
        MagicMock(name="beta", ispkg=True),
        MagicMock(name="loose", ispkg=False),  # must be skipped
    ]
    fake_modules[0].name = "alpha"
    fake_modules[1].name = "beta"
    fake_modules[2].name = "loose"

    imported: list[str] = []

    def fake_import_module(name: str) -> Any:
        imported.append(name)
        if name == "fake_pkg":
            return fake_root
        return MagicMock()

    monkeypatch.setattr("govlink.core.registry.importlib.import_module", fake_import_module)
    monkeypatch.setattr("govlink.core.registry.pkgutil.iter_modules", lambda _path: fake_modules)

    isolated_global_registry.auto_discover(package="fake_pkg")
    assert "fake_pkg" in imported
    assert "fake_pkg.alpha.dataset" in imported
    assert "fake_pkg.beta.dataset" in imported
    assert "fake_pkg.loose.dataset" not in imported


def test_auto_discover_logs_each_discovered_dataset(
    isolated_global_registry: DatasetRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each successful import emits a structured log line."""
    fake_root = ModuleType("fake_pkg")
    fake_root.__path__ = ["/fake/path"]  # type: ignore[attr-defined]

    fake_module = MagicMock(ispkg=True)
    fake_module.name = "alpha"

    def fake_import_module(name: str) -> Any:
        return fake_root if name == "fake_pkg" else MagicMock()

    monkeypatch.setattr("govlink.core.registry.importlib.import_module", fake_import_module)
    monkeypatch.setattr("govlink.core.registry.pkgutil.iter_modules", lambda _path: [fake_module])

    with structlog.testing.capture_logs() as captured:
        isolated_global_registry.auto_discover(package="fake_pkg")

    assert any(
        e.get("event") == "dataset_module_imported" and e.get("module") == "fake_pkg.alpha.dataset"
        for e in captured
    )


def test_auto_discover_raises_if_dataset_module_import_fails(
    isolated_global_registry: DatasetRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a dataset module raises during import, the failure propagates with context."""
    fake_root = ModuleType("fake_pkg")
    fake_root.__path__ = ["/fake/path"]  # type: ignore[attr-defined]

    fake_module = MagicMock(ispkg=True)
    fake_module.name = "broken"

    def fake_import_module(name: str) -> Any:
        if name == "fake_pkg":
            return fake_root
        raise ImportError(f"simulated failure in {name}")

    monkeypatch.setattr("govlink.core.registry.importlib.import_module", fake_import_module)
    monkeypatch.setattr("govlink.core.registry.pkgutil.iter_modules", lambda _path: [fake_module])

    with pytest.raises(RuntimeError) as excinfo:
        isolated_global_registry.auto_discover(package="fake_pkg")
    msg = str(excinfo.value)
    assert "broken" in msg
    assert "fake_pkg.broken.dataset" in msg
    assert isinstance(excinfo.value.__cause__, ImportError)


def test_auto_discover_idempotent(
    isolated_global_registry: DatasetRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling ``auto_discover`` twice imports modules twice but does not error."""
    fake_root = ModuleType("fake_pkg")
    fake_root.__path__ = ["/fake/path"]  # type: ignore[attr-defined]

    fake_module = MagicMock(ispkg=True)
    fake_module.name = "alpha"

    call_count: dict[str, int] = {}

    def fake_import_module(name: str) -> Any:
        call_count[name] = call_count.get(name, 0) + 1
        return fake_root if name == "fake_pkg" else MagicMock()

    monkeypatch.setattr("govlink.core.registry.importlib.import_module", fake_import_module)
    monkeypatch.setattr("govlink.core.registry.pkgutil.iter_modules", lambda _path: [fake_module])

    isolated_global_registry.auto_discover(package="fake_pkg")
    isolated_global_registry.auto_discover(package="fake_pkg")
    assert call_count.get("fake_pkg.alpha.dataset", 0) == 2
    # Registry remains empty because the fake import doesn't actually register.
    assert isolated_global_registry.list_all() == []


def test_auto_discover_skips_when_package_has_no_path(
    isolated_global_registry: DatasetRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the resolved package has no ``__path__``, auto_discover returns silently."""
    not_a_package = ModuleType("not_a_pkg")  # no __path__ assigned

    def fake_import_module(name: str) -> Any:
        return not_a_package

    iter_called = False

    def fake_iter_modules(_p: Any) -> Any:
        nonlocal iter_called
        iter_called = True
        return iter([])

    monkeypatch.setattr("govlink.core.registry.importlib.import_module", fake_import_module)
    monkeypatch.setattr("govlink.core.registry.pkgutil.iter_modules", fake_iter_modules)

    isolated_global_registry.auto_discover(package="not_a_pkg")
    assert iter_called is False


def test_dataset_already_registered_error_str_contains_slug() -> None:
    """The error stringification surfaces the offending slug."""
    err = DatasetAlreadyRegisteredError("foo")
    assert "foo" in str(err)
    assert err.slug == "foo"


def test_dataset_not_found_error_str_contains_slug() -> None:
    """The error stringification surfaces the missing slug."""
    err = DatasetNotFoundError("missing-slug")
    assert "missing-slug" in str(err)
    assert err.slug == "missing-slug"


def test_dataset_already_registered_error_is_value_error() -> None:
    """Subclass relationship enables generic ``except ValueError`` handlers."""
    assert issubclass(DatasetAlreadyRegisteredError, ValueError)


def test_dataset_not_found_error_is_key_error() -> None:
    """Subclass relationship enables generic ``except KeyError`` handlers."""
    assert issubclass(DatasetNotFoundError, KeyError)


def test_get_registry_lazy_init_constructs_on_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``get_registry`` constructs the global on first use and caches it."""
    from govlink.core import registry as _reg_mod

    monkeypatch.setattr(_reg_mod, "_global_registry", None)
    first = get_registry()
    assert isinstance(first, DatasetRegistry)
    assert first is get_registry()


def test_reset_global_registry_for_testing_clears_global(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The test-only reset helper sets the module-global back to None."""
    from govlink.core import registry as _reg_mod

    # Set a sentinel and then reset.
    monkeypatch.setattr(_reg_mod, "_global_registry", DatasetRegistry())
    assert _reg_mod._global_registry is not None
    _reg_mod._reset_global_registry_for_testing()
    assert _reg_mod._global_registry is None
