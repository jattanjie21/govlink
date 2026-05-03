"""Abstract base class for dataset parsers.

A :class:`BaseParser` converts raw source bytes (typically PDF) into a
list of validated Pydantic records of a dataset-specific type ``R``.
Subclasses live in ``govlink/datasets/<slug>/parser.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog
from pydantic import BaseModel


class BaseParser[R: BaseModel](ABC):
    """Abstract parser parameterised over the record type ``R``.

    Parsers must be pure: same bytes in → same records out. They must
    NOT touch the database or filesystem — persistence is the
    orchestrator's concern.
    """

    def __init__(self) -> None:
        logger: Any = structlog.get_logger(self.__class__.__module__)
        self.logger: Any = logger.bind(parser=self.__class__.__name__)

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> list[R]:
        """Parse raw bytes into a list of validated records.

        Implementations should raise a clear exception (a subclass of
        :class:`ValueError`) on malformed input. Callers — typically the
        ingestion orchestrator — catch and log.
        """
