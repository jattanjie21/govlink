"""Dataset registry — process-global mapping of slug → DatasetDefinition.

Each ``govlink/datasets/<slug>/dataset.py`` module is expected to call
``get_registry().register(...)`` at import time. Application code
triggers that import in bulk via :meth:`DatasetRegistry.auto_discover`.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from govlink.core.definition import DatasetDefinition

_logger = structlog.get_logger(__name__)


class DatasetAlreadyRegisteredError(ValueError):
    """Raised when a slug is registered more than once on the same registry."""

    def __init__(self, slug: str) -> None:
        super().__init__(f"Dataset already registered: {slug!r}")
        self.slug = slug


class DatasetNotFoundError(KeyError):
    """Raised when ``get`` is called with a slug that was never registered."""

    def __init__(self, slug: str) -> None:
        super().__init__(slug)
        self.slug = slug

    def __str__(self) -> str:
        return f"Dataset not found: {self.slug!r}"


class DatasetRegistry:
    """In-memory mapping of slug → :class:`DatasetDefinition`.

    Tests should construct fresh instances. Production code uses the
    process-global instance via :func:`get_registry`.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, DatasetDefinition] = {}

    def register(self, definition: DatasetDefinition) -> DatasetDefinition:
        """Register a definition; raise if its slug is already taken."""
        if definition.slug in self._definitions:
            raise DatasetAlreadyRegisteredError(definition.slug)
        self._definitions[definition.slug] = definition
        _logger.info("dataset_registered", slug=definition.slug, title=definition.title)
        return definition

    def get(self, slug: str) -> DatasetDefinition:
        """Look up a definition by slug; raise ``DatasetNotFoundError`` if absent."""
        try:
            return self._definitions[slug]
        except KeyError as e:
            raise DatasetNotFoundError(slug) from e

    def list_all(self) -> list[DatasetDefinition]:
        """Return all registered definitions in insertion order."""
        return list(self._definitions.values())

    def list_slugs(self) -> list[str]:
        """Return all registered slugs in insertion order."""
        return list(self._definitions.keys())

    def __contains__(self, slug: object) -> bool:
        return isinstance(slug, str) and slug in self._definitions

    def clear(self) -> None:
        """Remove every registration. Test-only utility."""
        self._definitions.clear()

    def auto_discover(self, package: str = "govlink.datasets") -> None:
        """Import the ``dataset`` submodule of every immediate subpackage.

        Each ``govlink/datasets/<slug>/dataset.py`` is expected to call
        ``get_registry().register(...)`` at import time. Loose modules
        (non-package files directly under ``package``) are ignored.
        Import failures are wrapped in a :class:`RuntimeError` whose
        message identifies the offending module; the original exception
        is preserved via ``__cause__``.
        """
        pkg = importlib.import_module(package)
        if not hasattr(pkg, "__path__"):
            return  # leaf module — nothing to discover
        for module_info in pkgutil.iter_modules(pkg.__path__):
            if not module_info.ispkg:
                continue
            module_name = f"{package}.{module_info.name}.dataset"
            try:
                importlib.import_module(module_name)
            except Exception as e:
                _logger.error(
                    "dataset_discovery_failed",
                    module=module_name,
                    error=str(e),
                )
                raise RuntimeError(f"Failed to load dataset module {module_name!r}: {e}") from e
            _logger.debug("dataset_module_imported", module=module_name)


_global_registry: DatasetRegistry | None = None


def get_registry() -> DatasetRegistry:
    """Return the process-global registry, lazily constructed on first use."""
    global _global_registry
    if _global_registry is None:
        _global_registry = DatasetRegistry()
    return _global_registry


def _reset_global_registry_for_testing() -> None:
    """Reset the module-global registry. Test-only utility."""
    global _global_registry
    _global_registry = None
