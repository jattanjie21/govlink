"""Canonical mapping from CBG PDF currency name strings to ISO 4217 codes.

The Central Bank of The Gambia publishes currency names with various
typos, spacing inconsistencies, and parenthesised unit multipliers.
This module is the single source of truth for normalising those strings
into structured ``(currency_code, unit_multiplier)`` tuples.

Synthetic codes (not ISO 4217):

- ``WAUA``: West African Unit of Account
- ``XDR``:  IMF Special Drawing Rights (the official ISO 4217 alpha code;
  CBG abbreviates it as ``SDR`` which is not the ISO code)

If you encounter a currency name in a CBG PDF that this module does not
recognise, the parser raises :class:`UnknownCurrencyError` — fail-loud.
Update :data:`_MAPPING` and add a regression test.
"""

from __future__ import annotations

import re
from typing import Final


class UnknownCurrencyError(ValueError):
    """Raised when a currency name has no canonical mapping."""

    def __init__(self, raw_name: str) -> None:
        super().__init__(f"Unknown currency name: {raw_name!r}")
        self.raw_name = raw_name


# Map normalised name (uppercase, single-spaced, parens stripped) →
# ``(iso_code, default_multiplier)``. The default_multiplier is 1 for
# every entry; the actual multiplier comes from the parenthesised number
# in the raw input and is extracted in :func:`lookup`.
_MAPPING: Final[dict[str, tuple[str, int]]] = {
    "US DOLLAR": ("USD", 1),
    "EURO": ("EUR", 1),
    "GBP": ("GBP", 1),
    "SWISS FRANC": ("CHF", 1),
    "CFA FRANC": ("XOF", 1),  # multiplier (5000) comes from parens
    "EGYPTIAN POUND": ("EGP", 1),
    "GUINEAN FRANC": ("GNF", 1),
    "NEW GHANIAN CEDI": ("GHS", 1),  # CBG typo — should be 'Ghanaian'
    "NIGERIAN NAIRA": ("NGN", 1),
    "SIERRALEONE LEONE": ("SLL", 1),  # CBG typo — should be 'Sierra Leone'
    "SIERRA LEONE LEONE": ("SLL", 1),  # tolerate the fixed form too
    "SOUTH AFRICAN RAND": ("ZAR", 1),
    "WAUA": ("WAUA", 1),  # synthetic
    "SDR": ("XDR", 1),  # ISO is XDR; CBG calls it SDR
    "DANISH KRONE": ("DKK", 1),  # multiplier (100) comes from parens
    "NORWEGIAN KRONER": ("NOK", 1),  # multiplier (100) comes from parens
    "SWEDISH KRONA": ("SEK", 1),  # multiplier (100) comes from parens
    "CANADIAN DOLLAR": ("CAD", 1),
    "BRAZIL REAL": ("BRL", 1),
    "TURKISH LIRA": ("TRY", 1),
    "AUSTRALIAN DOLLAR": ("AUD", 1),
    "CHINA RENMINBI": ("CNY", 1),
    "HONG KONG DOLLAR": ("HKD", 1),
    "JAPANESE YEN": ("JPY", 1),  # multiplier (100) comes from parens
    "INDIAN RUPEE": ("INR", 1),
    "TAIWANESE DOLLAR": ("TWD", 1),
    "SINGAPORE DOLLAR": ("SGD", 1),
    "SRI LANKAN RUPEE": ("LKR", 1),
    "THAILAND BAHT": ("THB", 1),
    "U. A. E DIRHAM": ("AED", 1),
    "UAE DIRHAM": ("AED", 1),  # tolerate dropped periods
    "KUWAITI DINAR": ("KWD", 1),
    "SAUDI RIYAL": ("SAR", 1),
    "NEWZEALAND DOLLAR": ("NZD", 1),
    "NEW ZEALAND DOLLAR": ("NZD", 1),  # tolerate the fixed form
    "PHILLIPINE PESO": ("PHP", 1),  # CBG typo — should be 'Philippine'
    "PHILIPPINE PESO": ("PHP", 1),  # tolerate the fixed form
}

KNOWN_CURRENCY_NAMES: Final[frozenset[str]] = frozenset(_MAPPING.keys())
SYNTHETIC_CODES: Final[frozenset[str]] = frozenset({"WAUA", "XDR"})

_MULTIPLIER_PATTERN: Final[re.Pattern[str]] = re.compile(r"\((\d+)\)")
_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")


def _normalise(raw: str) -> tuple[str, int]:
    """Strip parenthesised multiplier (if present), collapse whitespace, uppercase."""
    multiplier = 1
    match = _MULTIPLIER_PATTERN.search(raw)
    if match:
        multiplier = int(match.group(1))
        raw = _MULTIPLIER_PATTERN.sub("", raw)
    cleaned = _WHITESPACE.sub(" ", raw).strip().upper()
    return cleaned, multiplier


def lookup(raw_name: str) -> tuple[str, int]:
    """Return ``(iso_code, unit_multiplier)`` for a CBG currency name.

    Raises :class:`UnknownCurrencyError` if the name has no canonical mapping.
    The multiplier in the parenthesised suffix wins over the per-entry default
    when both are present (the per-entry default is always 1, so this only
    matters when an entry not normally suffixed gains an explicit multiplier).
    """
    name_clean, multiplier = _normalise(raw_name)
    try:
        code, default_multiplier = _MAPPING[name_clean]
    except KeyError as e:
        raise UnknownCurrencyError(raw_name) from e
    return code, multiplier if multiplier != 1 else default_multiplier
