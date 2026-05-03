"""Source: scrape the CBG daily exchange rate listing page and fetch PDFs.

``discover()`` is tolerant of bad rows — listing entries without a UUID
or with non-PDF link text are skipped with a warning log. ``fetch()`` is
strict — any HTTP failure (4xx, 5xx, timeout) propagates so the caller
can decide retry policy.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Final

import httpx
from bs4 import BeautifulSoup, Tag

from govlink.core.base_source import BaseSource
from govlink.core.source_ref import SourceFileRef

_LISTING_URL: Final[str] = "https://www.cbg.gm/daily-valuation-exchange-rate"
_DEFAULT_USER_AGENT: Final[str] = "govlink/0.1 (+https://github.com/TODO/govlink)"
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0

_DOWNLOAD_URL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"/downloads-file/(?P<uuid>[0-9a-f-]{30,})"
)
_DATE_HINT_FORMATS: Final[tuple[str, ...]] = (
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
)


class ExchangeRatesSource(BaseSource):
    """Source for CBG daily valuation exchange rate PDFs."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        listing_url: str = _LISTING_URL,
        user_agent: str = _DEFAULT_USER_AGENT,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__()
        self._listing_url = listing_url
        self._user_agent = user_agent
        self._timeout_seconds = timeout_seconds
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        )

    def discover(self) -> Iterable[SourceFileRef]:
        """Scrape the CBG listing page and yield one ref per PDF entry.

        Anchors that don't reference ``/downloads-file/<uuid>`` or whose
        link text doesn't mention ``pdf`` are silently skipped (with a
        warning log). HTTP errors propagate.
        """
        response = self._client.get(self._listing_url)
        response.raise_for_status()
        refs = list(self._parse_listing(response.text))
        self.logger.info("discover_complete", discovered_count=len(refs))
        return refs

    def fetch(self, ref: SourceFileRef) -> bytes:
        """Download and return the bytes of a single source file.

        HTTP non-2xx responses raise :class:`httpx.HTTPStatusError`;
        timeouts raise :class:`httpx.TimeoutException`. Both propagate so
        the caller (the orchestrator) decides retry policy.
        """
        # If the source was constructed with a caller-supplied client that
        # doesn't carry our User-Agent header, attach it on a per-request
        # basis so test transports still see it.
        headers: dict[str, str] = {"User-Agent": self._user_agent}
        response = self._client.get(ref.url, headers=headers)
        response.raise_for_status()
        return response.content

    def _parse_listing(self, html: str) -> Iterable[SourceFileRef]:
        soup = BeautifulSoup(html, "html.parser")
        for raw_anchor in soup.find_all("a", href=True):
            anchor: Tag = raw_anchor  # bs4 returns Tag for matched anchors
            ref = self._anchor_to_ref(anchor)
            if ref is not None:
                yield ref

    def _anchor_to_ref(self, anchor: Tag) -> SourceFileRef | None:
        # ``find_all("a", href=True)`` only yields anchors whose href is a
        # string, so the get() result is always a str — no runtime check.
        href_value: str = str(anchor.get("href", ""))
        match = _DOWNLOAD_URL_PATTERN.search(href_value)
        if not match:
            return None
        text = anchor.get_text(" ", strip=True)
        if "pdf" not in text.lower():
            self.logger.warning("listing_entry_not_pdf", href=href_value, text=text[:80])
            return None
        url = href_value if href_value.startswith("http") else f"https://www.cbg.gm{href_value}"
        return SourceFileRef(
            source_uuid=match.group("uuid"),
            url=url,
            link_text=text[:512] or None,
            published_date_hint=self._parse_date_hint(text),
        )

    @staticmethod
    def _parse_date_hint(link_text: str) -> date | None:
        for token in link_text.split():
            for fmt in _DATE_HINT_FORMATS:
                try:
                    return datetime.strptime(token, fmt).date()
                except ValueError:
                    continue
        return None

    def close(self) -> None:
        """Close the underlying HTTP client *only* if we own it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> ExchangeRatesSource:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
