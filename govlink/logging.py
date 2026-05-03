"""structlog-based logging configuration.

Configures structured JSON logging for production and human-readable
console logging for development, based on the resolved environment.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor


def _shared_processors() -> list[Processor]:
    """Processors shared by structlog and the stdlib bridge formatter."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]


def configure_logging(env: str, log_level: str) -> None:
    """Configure structlog and the stdlib root logger.

    JSON output in production, coloured console output in development.
    Idempotent — calling this twice replaces (rather than duplicates)
    the configured handler so log records are emitted exactly once.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    shared: list[Processor] = _shared_processors()

    renderer: Processor
    if env == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level)

    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str, **initial_values: Any) -> structlog.stdlib.BoundLogger:
    """Return a named structlog ``BoundLogger`` (configures defaults if needed)."""
    if not logging.getLogger().handlers:
        configure_logging("development", "INFO")
    logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(name).bind(**initial_values)
    return logger
