"""Tests for govlink.api.exporters.csv — CSV export utilities."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from pydantic import BaseModel

from govlink.api.exporters.csv import create_csv_response, export_records_to_csv
from govlink.core.schemas import DecimalStr


class _SampleRecord(BaseModel):
    snapshot_date: date
    code: str
    value: DecimalStr
    extra: int


def _records() -> list[_SampleRecord]:
    return [
        _SampleRecord(
            snapshot_date=date(2026, 4, 30),
            code="USD",
            value=Decimal("72.39"),
            extra=1,
        ),
        _SampleRecord(
            snapshot_date=date(2026, 4, 30),
            code="JPY",
            value=Decimal("0.0082"),
            extra=100,
        ),
    ]


def test_export_csv_produces_valid_csv() -> None:
    text = export_records_to_csv(_records(), _SampleRecord)
    reader = csv.reader(StringIO(text))
    rows = list(reader)
    assert rows[0] == ["snapshot_date", "code", "value", "extra"]
    assert rows[1] == ["2026-04-30", "USD", "72.39", "1"]
    assert rows[2] == ["2026-04-30", "JPY", "0.0082", "100"]


def test_export_csv_empty_list_produces_headers_only() -> None:
    text = export_records_to_csv([], _SampleRecord)
    reader = csv.reader(StringIO(text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0] == ["snapshot_date", "code", "value", "extra"]


def test_export_csv_uses_schema_field_order() -> None:
    """Columns appear in the order the Pydantic schema declares them."""
    text = export_records_to_csv(_records(), _SampleRecord)
    header_line = text.splitlines()[0]
    assert header_line == "snapshot_date,code,value,extra"


def test_export_csv_handles_decimal_values() -> None:
    """Decimals render as plain numeric strings, not scientific notation."""
    record = _SampleRecord(
        snapshot_date=date(2026, 4, 30),
        code="GNF",
        value=Decimal("0.0000082"),  # would be 8.2E-6 in scientific notation
        extra=0,
    )
    text = export_records_to_csv([record], _SampleRecord)
    # Inspect the value column directly rather than scanning the whole row
    # (header contains 'date' which has an 'E' that would false-positive).
    reader = csv.DictReader(StringIO(text))
    row = next(reader)
    assert row["value"] == "0.0000082"
    assert "E" not in row["value"].upper()
    assert "e" not in row["value"]


def test_create_csv_response_has_correct_headers() -> None:
    """create_csv_response wraps content in a StreamingResponse with right headers."""
    response = create_csv_response("a,b,c\n1,2,3\n", filename="test.csv")
    assert response.media_type == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="test.csv"'


def test_export_csv_handles_thousands_value() -> None:
    """Values like 1132.65 render as plain '1132.65' (no thousands separator)."""
    record = _SampleRecord(
        snapshot_date=date(2026, 4, 30),
        code="DKK",
        value=Decimal("1132.65"),
        extra=100,
    )
    text = export_records_to_csv([record], _SampleRecord)
    assert "1132.65" in text
    assert "1,132.65" not in text
