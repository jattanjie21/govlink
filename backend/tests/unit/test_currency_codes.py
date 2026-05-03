"""Tests for govlink.ingestion.currency_codes — canonical CBG currency mapping."""

from __future__ import annotations

import re

import pytest

from govlink.ingestion.currency_codes import (
    KNOWN_CURRENCY_NAMES,
    SYNTHETIC_CODES,
    UnknownCurrencyError,
    lookup,
)


def test_lookup_us_dollar_returns_usd_with_multiplier_1() -> None:
    assert lookup("US DOLLAR") == ("USD", 1)


def test_lookup_handles_parenthesised_multiplier() -> None:
    assert lookup("DANISH KRONE (100)") == ("DKK", 100)


def test_lookup_handles_cfa_franc_5000() -> None:
    assert lookup("CFA FRANC (5000)") == ("XOF", 5000)


def test_lookup_normalises_whitespace() -> None:
    assert lookup("  US  DOLLAR  ") == ("USD", 1)


def test_lookup_case_insensitive() -> None:
    assert lookup("us dollar") == ("USD", 1)


def test_lookup_handles_known_typos() -> None:
    """CBG ships several typos verbatim; the mapping accepts them as canonical."""
    assert lookup("PHILLIPINE PESO") == ("PHP", 1)
    assert lookup("NEW GHANIAN CEDI") == ("GHS", 1)
    assert lookup("SIERRALEONE LEONE") == ("SLL", 1)


def test_lookup_handles_synthetic_codes() -> None:
    assert lookup("WAUA") == ("WAUA", 1)
    assert lookup("SDR") == ("XDR", 1)


def test_lookup_handles_uae_dirham_with_periods() -> None:
    assert lookup("U. A. E DIRHAM") == ("AED", 1)


def test_lookup_handles_jpy_per_100() -> None:
    assert lookup("JAPANESE YEN (100)") == ("JPY", 100)


def test_lookup_unknown_raises_unknown_currency_error() -> None:
    with pytest.raises(UnknownCurrencyError):
        lookup("DRACHMAS OF ATLANTIS")


def test_unknown_currency_error_includes_input_string() -> None:
    with pytest.raises(UnknownCurrencyError) as excinfo:
        lookup("DRACHMAS OF ATLANTIS")
    assert "DRACHMAS OF ATLANTIS" in str(excinfo.value)
    assert excinfo.value.raw_name == "DRACHMAS OF ATLANTIS"


def test_all_known_codes_present() -> None:
    """Snapshot test: at least 33 canonical names (matches the reference PDFs)."""
    assert isinstance(KNOWN_CURRENCY_NAMES, frozenset)
    assert len(KNOWN_CURRENCY_NAMES) >= 33


def test_all_iso_codes_are_valid_format() -> None:
    """Every ISO output is exactly 3 uppercase letters; synthetic codes excepted."""
    iso_pattern = re.compile(r"^[A-Z]{3}$")
    for name in KNOWN_CURRENCY_NAMES:
        code, _ = lookup(name)
        if code in SYNTHETIC_CODES:
            assert code.isupper()
            assert 3 <= len(code) <= 4
        else:
            assert iso_pattern.match(code), f"{name!r} → {code!r} is not 3 uppercase letters"


def test_known_synthetic_codes_documented() -> None:
    """``SYNTHETIC_CODES`` lists the non-ISO outputs so they're discoverable."""
    assert isinstance(SYNTHETIC_CODES, frozenset)
    assert "WAUA" in SYNTHETIC_CODES
    assert "XDR" in SYNTHETIC_CODES


def test_lookup_parens_with_explicit_multiplier_overrides_default() -> None:
    """If a name with default-multiplier=1 carries an explicit (N), N wins."""
    # Hypothetical: SWISS FRANC (10) — multiplier 10 should be used, not the default 1.
    assert lookup("SWISS FRANC (10)") == ("CHF", 10)
