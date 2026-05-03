"""Tests for govlink.logging — structlog configuration."""

from __future__ import annotations

import json
import logging
import re

import pytest
import structlog

from govlink.logging import configure_logging, get_logger


def _read_json_lines(text: str) -> list[dict[str, object]]:
    """Parse a multi-line JSON log capture into a list of records."""
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]


def test_configure_logging_returns_bound_logger(capsys: pytest.CaptureFixture[str]) -> None:
    """After ``configure_logging``, ``get_logger`` returns a usable bound logger."""
    configure_logging("development", "INFO")
    log = get_logger("test")
    assert isinstance(log, structlog.stdlib.BoundLogger)
    log.info("smoke")
    captured = capsys.readouterr()
    assert "smoke" in captured.out


def test_logger_emits_json_in_production(capsys: pytest.CaptureFixture[str]) -> None:
    """Production env emits valid JSON log records."""
    configure_logging("production", "INFO")
    log = get_logger("svc")
    log.info("hello", action="ping", count=3)
    captured = capsys.readouterr()
    records = _read_json_lines(captured.out)
    assert len(records) == 1
    record = records[0]
    assert record["event"] == "hello"
    assert record["action"] == "ping"
    assert record["count"] == 3
    assert record["level"] == "info"
    assert record["logger"] == "svc"


def test_logger_emits_console_in_development(capsys: pytest.CaptureFixture[str]) -> None:
    """Development env emits human-readable output, not JSON."""
    configure_logging("development", "INFO")
    log = get_logger("svc")
    log.info("hello", action="ping")
    captured = capsys.readouterr()
    assert "hello" in captured.out
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.out.strip().splitlines()[0])


def test_logger_includes_timestamp_in_iso_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every log record carries an ISO 8601 UTC timestamp."""
    configure_logging("production", "INFO")
    log = get_logger("svc")
    log.info("ts-check")
    captured = capsys.readouterr()
    record = _read_json_lines(captured.out)[0]
    assert "timestamp" in record
    iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
    assert re.match(iso_pattern, str(record["timestamp"])) is not None


def test_logger_respects_log_level(capsys: pytest.CaptureFixture[str]) -> None:
    """Setting log_level=ERROR suppresses INFO records."""
    configure_logging("production", "ERROR")
    log = get_logger("svc")
    log.info("should-be-suppressed")
    log.error("should-appear")
    captured = capsys.readouterr()
    assert "should-be-suppressed" not in captured.out
    assert "should-appear" in captured.out


def test_get_logger_returns_distinct_named_loggers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``get_logger("a")`` and ``get_logger("b")`` produce distinct named loggers."""
    configure_logging("production", "INFO")
    get_logger("alpha").info("first")
    get_logger("beta").info("second")
    captured = capsys.readouterr()
    records = _read_json_lines(captured.out)
    assert {r["logger"] for r in records} == {"alpha", "beta"}


def test_configure_logging_is_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    """Calling ``configure_logging`` twice must not duplicate handlers."""
    configure_logging("production", "INFO")
    configure_logging("production", "INFO")
    log = get_logger("svc")
    log.info("once")
    captured = capsys.readouterr()
    records = _read_json_lines(captured.out)
    assert len(records) == 1


def test_configure_logging_bridges_stdlib_loggers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Third-party stdlib loggers (e.g. uvicorn) flow through structlog."""
    configure_logging("production", "INFO")
    stdlib_log = logging.getLogger("third.party")
    stdlib_log.info("from-stdlib")
    captured = capsys.readouterr()
    records = _read_json_lines(captured.out)
    assert any(r["event"] == "from-stdlib" for r in records)


def test_get_logger_lazy_configures_when_root_has_no_handlers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Calling ``get_logger`` before ``configure_logging`` must auto-configure defaults."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    log = get_logger("lazy")
    log.info("lazy-init")
    captured = capsys.readouterr()
    assert "lazy-init" in captured.out
