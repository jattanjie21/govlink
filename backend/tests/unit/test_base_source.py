"""Tests for govlink.core.base_source — BaseSource abstract class."""

from __future__ import annotations

from collections.abc import Iterable

import pytest
import structlog

from govlink.core.base_source import BaseSource
from govlink.core.source_ref import SourceFileRef


class _FakeSource(BaseSource):
    """A minimal in-memory source used only by these tests."""

    def __init__(self, refs: list[SourceFileRef], payloads: dict[str, bytes]) -> None:
        super().__init__()
        self._refs = refs
        self._payloads = payloads

    def discover(self) -> Iterable[SourceFileRef]:
        return list(self._refs)

    def fetch(self, ref: SourceFileRef) -> bytes:
        return self._payloads[ref.source_uuid]


class _MissingDiscover(BaseSource):
    def fetch(self, ref: SourceFileRef) -> bytes:
        return b""


class _MissingFetch(BaseSource):
    def discover(self) -> Iterable[SourceFileRef]:
        return []


def _ref(uuid: str = "u1", url: str = "https://a.gm/x.pdf") -> SourceFileRef:
    return SourceFileRef(source_uuid=uuid, url=url, link_text=None)


def test_base_source_cannot_be_instantiated_directly() -> None:
    """BaseSource is abstract — direct instantiation must raise TypeError."""
    with pytest.raises(TypeError):
        BaseSource()  # type: ignore[abstract]


def test_subclass_must_implement_discover() -> None:
    """A subclass missing ``discover`` must not be instantiable."""
    with pytest.raises(TypeError):
        _MissingDiscover()  # type: ignore[abstract]


def test_subclass_must_implement_fetch() -> None:
    """A subclass missing ``fetch`` must not be instantiable."""
    with pytest.raises(TypeError):
        _MissingFetch()  # type: ignore[abstract]


def test_concrete_subclass_can_be_instantiated_and_used() -> None:
    """A subclass implementing both methods is constructible and callable."""
    src = _FakeSource(refs=[_ref()], payloads={"u1": b"hello"})
    refs = list(src.discover())
    assert len(refs) == 1
    assert src.fetch(refs[0]) == b"hello"


def test_discover_returns_iterable_of_source_file_refs() -> None:
    """``discover`` produces an iterable of SourceFileRef instances."""
    src = _FakeSource(
        refs=[_ref("u1"), _ref("u2", url="https://a.gm/2.pdf")],
        payloads={},
    )
    out = list(src.discover())
    assert len(out) == 2
    assert all(isinstance(r, SourceFileRef) for r in out)


def test_fetch_returns_bytes() -> None:
    """``fetch`` produces ``bytes`` for a given ref."""
    src = _FakeSource(refs=[_ref()], payloads={"u1": b"\x00\x01\x02"})
    body = src.fetch(_ref())
    assert isinstance(body, bytes)
    assert body == b"\x00\x01\x02"


def test_source_has_logger_attribute() -> None:
    """Each instance has a structlog logger bound with the source class name.

    Asserted behaviourally via ``structlog.testing.capture_logs`` rather
    than poking at a private ``_context`` attribute.
    """
    src = _FakeSource(refs=[], payloads={})
    assert src.logger is not None
    with structlog.testing.capture_logs() as captured:
        src.logger.info("smoke")
    assert any(
        event.get("source") == "_FakeSource" and event.get("event") == "smoke" for event in captured
    )
