"""Tests for govlink.datasets.exchange_rates.parser — fixture-driven."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import structlog

from govlink.datasets.exchange_rates.model import ExchangeRateRecord
from govlink.datasets.exchange_rates.parser import ExchangeRatesParser, ParseError
from govlink.ingestion.currency_codes import UnknownCurrencyError

# --- helpers --------------------------------------------------------------


def _make_fake_pdf_with_text(text: str) -> Any:
    """Return a context manager that mimics ``pdfplumber.open`` returning ``text``."""
    page = MagicMock()
    page.extract_text.return_value = text
    pdf = MagicMock()
    pdf.pages = [page]
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=pdf)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _check_oracle(
    stem: str,
    load_pdf_fixture: Callable[[str], bytes],
    load_pdf_expected: Callable[[str], dict[str, Any]],
) -> None:
    """Reusable assertion: parse(stem) matches the JSON oracle exactly."""
    raw = load_pdf_fixture(stem)
    expected = load_pdf_expected(stem)

    parser = ExchangeRatesParser()
    actual = parser.parse(raw)

    expected_records = expected["records"]
    expected_date = date.fromisoformat(expected["snapshot_date"])

    assert len(actual) == len(
        expected_records
    ), f"Row count mismatch for {stem}: parsed={len(actual)}, oracle={len(expected_records)}"
    assert all(r.snapshot_date == expected_date for r in actual)

    for parsed, expected_row in zip(actual, expected_records, strict=True):
        assert parsed.currency_code == expected_row["currency_code"]
        assert parsed.currency_name == expected_row["currency_name"]
        assert parsed.rate == Decimal(expected_row["rate"])
        assert parsed.unit_multiplier == expected_row["unit_multiplier"]


# --- fixture-driven tests against real PDFs ------------------------------


def test_parse_2026_04_30_returns_expected_records(
    load_pdf_fixture: Callable[[str], bytes],
    load_pdf_expected: Callable[[str], dict[str, Any]],
) -> None:
    _check_oracle("2026-04-30", load_pdf_fixture, load_pdf_expected)


def test_parse_2025_12_15_returns_expected_records(
    load_pdf_fixture: Callable[[str], bytes],
    load_pdf_expected: Callable[[str], dict[str, Any]],
) -> None:
    _check_oracle("2025-12-15", load_pdf_fixture, load_pdf_expected)


def test_parse_2025_08_25_returns_expected_records(
    load_pdf_fixture: Callable[[str], bytes],
    load_pdf_expected: Callable[[str], dict[str, Any]],
) -> None:
    _check_oracle("2025-08-25", load_pdf_fixture, load_pdf_expected)


def test_parse_2025_04_30_returns_expected_records(
    load_pdf_fixture: Callable[[str], bytes],
    load_pdf_expected: Callable[[str], dict[str, Any]],
) -> None:
    _check_oracle("2025-04-30", load_pdf_fixture, load_pdf_expected)


def test_parse_extracts_snapshot_date_from_pdf_body(
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    """The date returned must come from the PDF body, not from any external hint."""
    parser = ExchangeRatesParser()
    records = parser.parse(load_pdf_fixture("2026-04-30"))
    assert records[0].snapshot_date == date(2026, 4, 30)
    records = parser.parse(load_pdf_fixture("2025-08-25"))
    assert records[0].snapshot_date == date(2025, 8, 25)


def test_parse_handles_thousands_separator_in_rate(
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    """The 2026-04-30 fixture's 'DANISH KRONE (100) 1,132.65' parses to Decimal('1132.65')."""
    parser = ExchangeRatesParser()
    records = parser.parse(load_pdf_fixture("2026-04-30"))
    dkk = next(r for r in records if r.currency_code == "DKK")
    assert dkk.rate == Decimal("1132.65")
    assert dkk.unit_multiplier == 100


def test_parse_handles_parenthesised_multiplier(
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    parser = ExchangeRatesParser()
    records = parser.parse(load_pdf_fixture("2026-04-30"))
    by_code = {r.currency_code: r for r in records}
    assert by_code["XOF"].unit_multiplier == 5000
    assert by_code["JPY"].unit_multiplier == 100
    assert by_code["DKK"].unit_multiplier == 100
    assert by_code["NOK"].unit_multiplier == 100
    assert by_code["SEK"].unit_multiplier == 100


def test_parse_skips_header_and_footer_lines(
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    parser = ExchangeRatesParser()
    records = parser.parse(load_pdf_fixture("2026-04-30"))
    names = {r.currency_name for r in records}
    assert not any("OFFICIAL" in n for n in names)
    assert not any("SOURCE" in n for n in names)
    assert not any("CENTRAL BANK" in n for n in names)


# --- error-path tests using mocked pdfplumber -----------------------------


def test_parse_raises_on_empty_pdf_bytes() -> None:
    parser = ExchangeRatesParser()
    with pytest.raises(ParseError, match="empty"):
        parser.parse(b"")


def test_parse_raises_on_pdf_with_no_currency_rows() -> None:
    parser = ExchangeRatesParser()
    fake_pdf = _make_fake_pdf_with_text(
        "OFFICIAL EXCHANGE RATES FOR VALUATION PURPOSES\n"
        "April 30, 2026\n"
        "SOURCE: CENTRAL BANK OF THE GAMBIA\n"
    )
    with (
        patch("pdfplumber.open", return_value=fake_pdf),
        pytest.raises(ParseError, match="no currency rows"),
    ):
        parser.parse(b"%PDF-fake")


def test_parse_raises_on_unknown_currency() -> None:
    parser = ExchangeRatesParser()
    fake_pdf = _make_fake_pdf_with_text("April 30, 2026\nFAKE CURRENCY 99.99\n")
    with (
        patch("pdfplumber.open", return_value=fake_pdf),
        pytest.raises(UnknownCurrencyError) as excinfo,
    ):
        parser.parse(b"%PDF-fake")
    assert "FAKE CURRENCY" in str(excinfo.value)


def test_parse_raises_on_missing_date() -> None:
    parser = ExchangeRatesParser()
    fake_pdf = _make_fake_pdf_with_text(
        "OFFICIAL EXCHANGE RATES FOR VALUATION PURPOSES\nUS DOLLAR 72.39\n"
    )
    with (
        patch("pdfplumber.open", return_value=fake_pdf),
        pytest.raises(ParseError, match="no snapshot date"),
    ):
        parser.parse(b"%PDF-fake")


def test_parse_returns_a_list_not_iterator(
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    parser = ExchangeRatesParser()
    result = parser.parse(load_pdf_fixture("2026-04-30"))
    assert isinstance(result, list)
    assert all(isinstance(r, ExchangeRateRecord) for r in result)
    # Iterable twice (would fail for a generator).
    first = [r.currency_code for r in result]
    second = [r.currency_code for r in result]
    assert first == second


def test_parser_logs_parsed_record_count(
    load_pdf_fixture: Callable[[str], bytes],
) -> None:
    parser = ExchangeRatesParser()
    with structlog.testing.capture_logs() as captured:
        parser.parse(load_pdf_fixture("2026-04-30"))
    assert any(e.get("event") == "parse_complete" and e.get("row_count") == 33 for e in captured)


def test_parse_accepts_alternate_date_formats() -> None:
    """The body date can appear in several formats — the parser tolerates them."""
    parser = ExchangeRatesParser()
    for body_date in ("30 April 2026", "30/04/2026", "30-04-2026", "30.04.2026"):
        fake_pdf = _make_fake_pdf_with_text(f"{body_date}\nUS DOLLAR 72.39\n")
        with patch("pdfplumber.open", return_value=fake_pdf):
            records = parser.parse(b"%PDF-fake")
        assert records[0].snapshot_date == date(2026, 4, 30)


def test_parse_skips_noise_lines_that_dont_match_the_pattern() -> None:
    """Lines that are blank, mid-page noise, or otherwise unmatched are skipped."""
    parser = ExchangeRatesParser()
    fake_pdf = _make_fake_pdf_with_text(
        "April 30, 2026\n"
        "\n"  # blank — exercises the `if not stripped: continue` path
        "Some random midpage text — possibly an annotation\n"
        "US DOLLAR 72.39\n"
    )
    with patch("pdfplumber.open", return_value=fake_pdf):
        records = parser.parse(b"%PDF-fake")
    assert len(records) == 1
    assert records[0].currency_code == "USD"


def test_parse_handles_rate_without_thousands_separator() -> None:
    """The 92 KB era fixtures use rates like '1131.27' (no comma); must parse equally."""
    parser = ExchangeRatesParser()
    fake_pdf = _make_fake_pdf_with_text("April 30, 2026\nDANISH KRONE (100) 1131.27\n")
    with patch("pdfplumber.open", return_value=fake_pdf):
        records = parser.parse(b"%PDF-fake")
    assert records[0].rate == Decimal("1131.27")
