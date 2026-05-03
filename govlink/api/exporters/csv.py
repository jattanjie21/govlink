"""CSV export utilities.

Generic across any Pydantic record schema. Column order follows the
schema's field order. Decimal values are serialised via the schema's
own ``model_dump(mode="json")``, so the project's :data:`DecimalStr`
alias guarantees plain-string output (no scientific notation, no float
drift).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from fastapi.responses import StreamingResponse
from pydantic import BaseModel


def export_records_to_csv(
    records: Sequence[BaseModel],
    schema_class: type[BaseModel],
) -> str:
    """Serialise a sequence of Pydantic records to a CSV string.

    Column order matches ``schema_class.model_fields`` followed by
    ``model_computed_fields`` (so derived values like ``rate_per_unit``
    appear). Empty input still produces a header row.
    """
    fieldnames = [
        *schema_class.model_fields.keys(),
        *schema_class.model_computed_fields.keys(),
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow(record.model_dump(mode="json"))
    return output.getvalue()


def create_csv_response(csv_content: str, filename: str) -> StreamingResponse:
    """Wrap CSV text in a :class:`StreamingResponse` with download headers."""
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
