"""Abstract base class for dataset sources.

A :class:`BaseSource` knows how to discover available source files
(typically by scraping a listing page) and how to fetch the bytes of
any specific file. Subclasses live in
``govlink/datasets/<slug>/source.py`` and provide concrete behaviour.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

import structlog

from govlink.core.source_ref import SourceFileRef


class BaseSource(ABC):
    """Abstract source for a single dataset.

    Implementations must be safe to construct cheaply — no network or
    disk access in ``__init__``. All side-effecting work happens in
    :meth:`discover` and :meth:`fetch`.
    """

    def __init__(self) -> None:
        # ``structlog.get_logger`` returns a lazy proxy so binding works
        # even before configure_logging() has run (e.g. at import time).
        logger: Any = structlog.get_logger(self.__class__.__module__)
        self.logger: Any = logger.bind(source=self.__class__.__name__)

    @abstractmethod
    def discover(self) -> Iterable[SourceFileRef]:
        """Yield references to all currently-available source files.

        May be a generator (lazy) or return a list. Implementations
        should be idempotent — calling ``discover`` twice yields the
        same logical set unless the upstream source changed.
        """

    @abstractmethod
    def fetch(self, ref: SourceFileRef) -> bytes:
        """Download and return the raw bytes for a single source file."""
