"""PDF parser for CBG daily valuation exchange rate publications.

The parser is pure: bytes in → records out. It does not touch the
database, the filesystem (other than reading the in-memory PDF stream),
or the network. All persistence is the orchestrator's job.

Failure-mode design:

- Empty input → :class:`ParseError`
- No date in body → :class:`ParseError`
- No currency rows → :class:`ParseError`
- Currency name absent from the canonical mapping →
  :class:`govlink.ingestion.currency_codes.UnknownCurrencyError` propagates
  (fail-loud, so we update the mapping rather than swallow unknowns).
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Final

import pdfplumber

from govlink.core.base_parser import BaseParser
from govlink.datasets.exchange_rates.model import ExchangeRateRecord
from govlink.ingestion.currency_codes import lookup as lookup_currency


class ParseError(ValueError):
    """Raised when a PDF cannot be parsed into a valid record set."""


# Currency line:
#   <name (uppercase, may include '.' '(' ')' digits, ends with letter or ')')>
#   <whitespace>
#   <rate (digits, optional thousands separators, optional decimals)>
_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
    ^\s*
    (?P<name>[A-Z][A-Z .()\d]*?[A-Z\)])
    \s+
    (?P<rate>[\d,]+(?:\.\d+)?)
    \s*$
    """,
    re.VERBOSE,
)

_DATE_FORMATS: Final[tuple[str, ...]] = (
    "%B %d, %Y",
    "%d %B %Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
)

_SKIP_PREFIXES: Final[tuple[str, ...]] = (
    "OFFICIAL EXCHANGE RATES",
    "SOURCE:",
    "EXCHANGE RATES FOR",
    "CENTRAL BANK OF",
)


class ExchangeRatesParser(BaseParser[ExchangeRateRecord]):
    """Parse CBG daily valuation PDFs into a list of :class:`ExchangeRateRecord`."""

    def parse(self, raw_bytes: bytes) -> list[ExchangeRateRecord]:
        """Parse a CBG daily valuation PDF into typed records.

        Raises :class:`ParseError` for empty input, missing snapshot date,
        or zero currency rows; raises
        :class:`govlink.ingestion.currency_codes.UnknownCurrencyError` if
        the PDF contains a currency name absent from the canonical mapping.
        """
        if not raw_bytes:
            raise ParseError("empty input bytes")
        text = self._extract_text(raw_bytes)
        snapshot_date = self._extract_date(text)
        records = self._extract_rows(text, snapshot_date)
        if not records:
            raise ParseError("no currency rows found in PDF body")
        self.logger.info(
            "parse_complete",
            snapshot_date=snapshot_date.isoformat(),
            row_count=len(records),
        )
        return records

    @staticmethod
    def _extract_text(raw_bytes: bytes) -> str:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            chunks = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(chunks)

    @staticmethod
    def _extract_date(text: str) -> date:
        # Look at the first 5 non-empty lines for a parseable date.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:5]:
            for fmt in _DATE_FORMATS:
                try:
                    return datetime.strptime(line, fmt).date()
                except ValueError:
                    continue
        raise ParseError("no snapshot date found in PDF body")

    @staticmethod
    def _extract_rows(text: str, snapshot_date: date) -> list[ExchangeRateRecord]:
        records: list[ExchangeRateRecord] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()
            if any(upper.startswith(p) for p in _SKIP_PREFIXES):
                continue
            match = _LINE_PATTERN.match(stripped)
            if not match:
                continue
            raw_name = match.group("name").strip()
            raw_rate = match.group("rate").replace(",", "")
            # The regex guarantees raw_rate is digits-only after comma stripping,
            # so Decimal() is total here.
            rate = Decimal(raw_rate)
            # lookup_currency raises UnknownCurrencyError; we let it propagate.
            code, multiplier = lookup_currency(raw_name)
            records.append(
                ExchangeRateRecord(
                    snapshot_date=snapshot_date,
                    currency_code=code,
                    currency_name=raw_name,
                    rate=rate,
                    unit_multiplier=multiplier,
                )
            )
        return records
