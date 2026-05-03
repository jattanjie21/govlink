"""Tests for govlink.core.base_parser — BaseParser abstract class."""

from __future__ import annotations

import pytest
import structlog
from pydantic import BaseModel

from govlink.core.base_parser import BaseParser


class _FakeRecord(BaseModel):
    value: int


class _FakeParser(BaseParser[_FakeRecord]):
    """A minimal parser that decodes ASCII-digit bytes into _FakeRecord rows."""

    def parse(self, raw_bytes: bytes) -> list[_FakeRecord]:
        return [_FakeRecord(value=int(b)) for b in raw_bytes.decode().split(",")]


class _MissingParse(BaseParser[_FakeRecord]):
    pass


def test_base_parser_cannot_be_instantiated_directly() -> None:
    """BaseParser is abstract — direct instantiation must raise TypeError."""
    with pytest.raises(TypeError):
        BaseParser()  # type: ignore[abstract]


def test_subclass_must_implement_parse() -> None:
    """A subclass missing ``parse`` must not be instantiable."""
    with pytest.raises(TypeError):
        _MissingParse()  # type: ignore[abstract]


def test_concrete_parser_returns_typed_records() -> None:
    """A concrete parser returns a list of the parameterised record type."""
    parser = _FakeParser()
    out = parser.parse(b"1,2,3")
    assert all(isinstance(r, _FakeRecord) for r in out)
    assert [r.value for r in out] == [1, 2, 3]


def test_parse_accepts_bytes_input() -> None:
    """The contract is bytes — strings or paths are not the parser's job."""
    parser = _FakeParser()
    parser.parse(b"42")  # bytes works
    with pytest.raises((TypeError, AttributeError, ValueError)):
        parser.parse("42")  # type: ignore[arg-type]


def test_parser_has_logger_attribute() -> None:
    """Each instance has a structlog logger bound with the parser class name."""
    parser = _FakeParser()
    assert parser.logger is not None
    with structlog.testing.capture_logs() as captured:
        parser.logger.info("smoke")
    assert any(
        event.get("parser") == "_FakeParser" and event.get("event") == "smoke" for event in captured
    )


def test_parse_result_is_a_list_not_iterator() -> None:
    """The return type is a concrete list — callers can iterate it twice."""
    parser = _FakeParser()
    result = parser.parse(b"7,8")
    assert isinstance(result, list)
    # Iterating twice must not exhaust the result.
    first = [r.value for r in result]
    second = [r.value for r in result]
    assert first == second == [7, 8]
