"""Tests for govlink.datasets.exchange_rates.source — discovery + fetch over httpx."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
import pytest
import structlog

from govlink.core.source_ref import SourceFileRef
from govlink.datasets.exchange_rates.source import ExchangeRatesSource


def _client_with_handler(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_discover_parses_real_listing_html_fixture(
    load_html_fixture: Callable[[str], str],
    load_html_expected: Callable[[str], dict[str, Any]],
) -> None:
    """Discovery against the real HTML fixture matches the JSON oracle for the first entries."""
    html = load_html_fixture("cbg_listing_2026-05.html")
    expected = load_html_expected("cbg_listing_2026-05")

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    src = ExchangeRatesSource(client=_client_with_handler(handler))
    refs = list(src.discover())
    src.close()

    by_uuid = {r.source_uuid: r for r in refs}
    for entry in expected["entries"][:10]:
        ref = by_uuid[entry["source_uuid"]]
        assert ref.url == entry["url"]
        assert ref.link_text == entry["link_text"]
        if entry["published_date_hint"] is None:
            assert ref.published_date_hint is None
        else:
            assert ref.published_date_hint == date.fromisoformat(entry["published_date_hint"])


def test_discover_extracts_source_uuid_from_url(
    load_html_fixture: Callable[[str], str],
) -> None:
    html = load_html_fixture("cbg_listing_2026-05.html")
    src = ExchangeRatesSource(
        client=_client_with_handler(lambda _req: httpx.Response(200, text=html))
    )
    refs = list(src.discover())
    src.close()
    for ref in refs[:10]:
        assert "/downloads-file/" in ref.url
        assert ref.url.split("/downloads-file/")[-1].startswith(ref.source_uuid)


def test_discover_skips_entries_without_pdf_extension_in_listing() -> None:
    """A listing entry whose link text doesn't mention 'pdf' is skipped with a warning."""
    html = (
        "<html><body>"
        '<a href="https://www.cbg.gm/downloads-file/01234567-aaaa-bbbb-cccc-deadbeefcafe">'
        "   01.05.2026 Some other document Type: docx</a>"
        "</body></html>"
    )
    src = ExchangeRatesSource(
        client=_client_with_handler(lambda _req: httpx.Response(200, text=html))
    )
    with structlog.testing.capture_logs() as captured:
        refs = list(src.discover())
    src.close()
    assert refs == []
    assert any(e.get("event") == "listing_entry_not_pdf" for e in captured)


def test_discover_parses_published_date_hint_from_link_text() -> None:
    html = (
        "<html><body>"
        '<a href="https://www.cbg.gm/downloads-file/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa">'
        "30.04.2026 Daily Valuation Type: pdf</a>"
        '<a href="https://www.cbg.gm/downloads-file/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb">'
        "29/04/2026 Daily Valuation Type: pdf</a>"
        '<a href="https://www.cbg.gm/downloads-file/cccccccc-cccc-cccc-cccc-cccccccccccc">'
        "28-04-2026 Daily Valuation Type: pdf</a>"
        '<a href="https://www.cbg.gm/downloads-file/dddddddd-dddd-dddd-dddd-dddddddddddd">'
        "16/13/2026 Daily Valuation Type: pdf</a>"
        "</body></html>"
    )
    src = ExchangeRatesSource(
        client=_client_with_handler(lambda _req: httpx.Response(200, text=html))
    )
    refs = list(src.discover())
    src.close()
    by_uuid = {r.source_uuid: r for r in refs}
    assert by_uuid["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"].published_date_hint == date(2026, 4, 30)
    assert by_uuid["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"].published_date_hint == date(2026, 4, 29)
    assert by_uuid["cccccccc-cccc-cccc-cccc-cccccccccccc"].published_date_hint == date(2026, 4, 28)
    # 16/13/2026 — month 13, must yield None, not crash
    assert by_uuid["dddddddd-dddd-dddd-dddd-dddddddddddd"].published_date_hint is None


def test_discover_handles_entry_with_unparseable_link_text() -> None:
    """Entry is still discovered if link text is unparseable; hint is None."""
    html = (
        "<html><body>"
        '<a href="https://www.cbg.gm/downloads-file/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee">'
        "Some wholly unparseable text Type: pdf</a>"
        "</body></html>"
    )
    src = ExchangeRatesSource(
        client=_client_with_handler(lambda _req: httpx.Response(200, text=html))
    )
    refs = list(src.discover())
    src.close()
    assert len(refs) == 1
    assert refs[0].source_uuid == "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    assert refs[0].published_date_hint is None


def test_discover_logs_summary(load_html_fixture: Callable[[str], str]) -> None:
    html = load_html_fixture("cbg_listing_2026-05.html")
    src = ExchangeRatesSource(
        client=_client_with_handler(lambda _req: httpx.Response(200, text=html))
    )
    with structlog.testing.capture_logs() as captured:
        list(src.discover())
    src.close()
    assert any(
        e.get("event") == "discover_complete" and isinstance(e.get("discovered_count"), int)
        for e in captured
    )


def test_discover_raises_on_http_error() -> None:
    """A 500 response on the listing fetch must surface, not silently return []."""

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    src = ExchangeRatesSource(client=_client_with_handler(handler))
    with pytest.raises(httpx.HTTPStatusError):
        list(src.discover())
    src.close()


def test_fetch_returns_bytes_on_200() -> None:
    pdf_bytes = b"%PDF-1.7 fake bytes"

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=pdf_bytes)

    src = ExchangeRatesSource(client=_client_with_handler(handler))
    ref = SourceFileRef(
        source_uuid="x",
        url="https://www.cbg.gm/downloads-file/x.pdf",
        link_text=None,
    )
    out = src.fetch(ref)
    src.close()
    assert isinstance(out, bytes)
    assert out == pdf_bytes


def test_fetch_raises_on_404() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    src = ExchangeRatesSource(client=_client_with_handler(handler))
    ref = SourceFileRef(
        source_uuid="x",
        url="https://www.cbg.gm/downloads-file/x.pdf",
        link_text=None,
    )
    with pytest.raises(httpx.HTTPStatusError):
        src.fetch(ref)
    src.close()


def test_fetch_raises_on_timeout() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout")

    src = ExchangeRatesSource(client=_client_with_handler(handler))
    ref = SourceFileRef(
        source_uuid="x",
        url="https://www.cbg.gm/downloads-file/x.pdf",
        link_text=None,
    )
    with pytest.raises(httpx.TimeoutException):
        src.fetch(ref)
    src.close()


def test_fetch_uses_user_agent_header() -> None:
    captured_headers: dict[str, str] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured_headers.update({k.lower(): v for k, v in req.headers.items()})
        return httpx.Response(200, content=b"ok")

    src = ExchangeRatesSource(client=_client_with_handler(handler))
    ref = SourceFileRef(
        source_uuid="x",
        url="https://www.cbg.gm/downloads-file/x.pdf",
        link_text=None,
    )
    src.fetch(ref)
    src.close()
    ua = captured_headers.get("user-agent", "")
    assert "govlink" in ua.lower()


def test_fetch_follows_redirects() -> None:
    pdf_bytes = b"%PDF-final"

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/redirect"):
            return httpx.Response(302, headers={"location": "https://example.gm/final.pdf"})
        return httpx.Response(200, content=pdf_bytes)

    src = ExchangeRatesSource(client=_client_with_handler(handler))
    ref = SourceFileRef(
        source_uuid="x",
        url="https://example.gm/redirect",
        link_text=None,
    )
    out = src.fetch(ref)
    src.close()
    assert out == pdf_bytes


def test_source_default_timeout_is_30_seconds() -> None:
    src = ExchangeRatesSource()
    try:
        timeout = src._client.timeout
        assert timeout.connect == 30.0
        assert timeout.read == 30.0
    finally:
        src.close()


def test_source_accepts_custom_httpx_client() -> None:
    """A caller-supplied client is used as-is and is NOT closed by the source."""
    transport = httpx.MockTransport(lambda _r: httpx.Response(200, content=b""))
    custom = httpx.Client(transport=transport)
    src = ExchangeRatesSource(client=custom)
    src.close()
    # The client should still be usable — source did not close what it didn't open.
    response = custom.get("https://example.gm/x")
    assert response.status_code == 200
    custom.close()


def test_source_works_as_context_manager() -> None:
    """``with ExchangeRatesSource() as src:`` enters and exits cleanly."""
    src = ExchangeRatesSource(
        client=_client_with_handler(lambda _r: httpx.Response(200, content=b""))
    )
    with src as ctx:
        assert ctx is src


def test_discover_handles_relative_href() -> None:
    """A relative href on the listing is resolved to an absolute URL."""
    html = (
        "<html><body>"
        '<a href="/downloads-file/ffffffff-ffff-ffff-ffff-ffffffffffff">'
        "01.05.2026 Daily Valuation Type: pdf</a>"
        "</body></html>"
    )
    src = ExchangeRatesSource(
        client=_client_with_handler(lambda _req: httpx.Response(200, text=html))
    )
    refs = list(src.discover())
    src.close()
    assert len(refs) == 1
    assert refs[0].url.startswith("https://www.cbg.gm/")
