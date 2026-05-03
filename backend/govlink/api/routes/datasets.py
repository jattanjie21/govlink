"""Generic dataset endpoints — every route works for any registered dataset.

Routes are parameterised by ``{slug}``. The handler looks up the
:class:`DatasetDefinition` from the registry and queries the dataset's
ORM ``model_class`` dynamically. There is no per-dataset route code.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from govlink.api.deps import (
    get_db_session,
    get_pagination,
    get_registry_dep,
    limiter,
)
from govlink.api.exporters.csv import create_csv_response, export_records_to_csv
from govlink.core.registry import DatasetNotFoundError, DatasetRegistry
from govlink.core.schemas import ErrorDetail, ErrorResponse, Meta, PaginationParams

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _not_found(slug: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=ErrorResponse(
            error=ErrorDetail(
                code="dataset_not_found",
                message=f"Dataset {slug!r} not found",
            )
        ).model_dump(),
    )


def _resolve_definition(registry: DatasetRegistry, slug: str) -> Any:
    try:
        return registry.get(slug)
    except DatasetNotFoundError as e:
        raise _not_found(slug) from e


@router.get("")
async def list_datasets(
    registry: Annotated[DatasetRegistry, Depends(get_registry_dep)],
) -> dict[str, Any]:
    """List every registered dataset's metadata."""
    items = [
        {
            "slug": d.slug,
            "title": d.title,
            "description": d.description,
            "publisher": d.publisher,
            "source_url": d.source_url,
            "frequency": d.frequency.value,
        }
        for d in registry.list_all()
    ]
    return {"data": items, "meta": Meta(count=len(items)).model_dump(mode="json")}


@router.get("/{slug}")
async def get_dataset(
    slug: str,
    registry: Annotated[DatasetRegistry, Depends(get_registry_dep)],
) -> dict[str, Any]:
    """Return metadata for one registered dataset."""
    definition = _resolve_definition(registry, slug)
    fields = [
        {
            "name": fname,
            "type": str(finfo.annotation),
        }
        for fname, finfo in definition.schema_class.model_fields.items()
    ]
    return {
        "data": {
            "slug": definition.slug,
            "title": definition.title,
            "description": definition.description,
            "publisher": definition.publisher,
            "source_url": definition.source_url,
            "frequency": definition.frequency.value,
            "data_table_name": definition.data_table_name,
            "fields": fields,
        },
        "meta": Meta(count=1, dataset=definition.slug).model_dump(mode="json"),
    }


@router.get("/{slug}/latest")
@limiter.limit("60/minute")
async def latest(
    request: Request,  # required by slowapi
    slug: str,
    registry: Annotated[DatasetRegistry, Depends(get_registry_dep)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    """Return all records from the most recent snapshot for a dataset."""
    definition = _resolve_definition(registry, slug)
    model = definition.model_class

    latest_date = session.execute(select(func.max(model.snapshot_date))).scalar()
    if latest_date is None:
        return {
            "data": [],
            "meta": Meta(count=0, dataset=definition.slug, snapshot_date=None).model_dump(
                mode="json"
            ),
        }

    rows = session.execute(select(model).where(model.snapshot_date == latest_date)).scalars().all()
    items = [
        definition.schema_class.model_validate(r, from_attributes=True).model_dump(mode="json")
        for r in rows
    ]
    return {
        "data": items,
        "meta": Meta(
            count=len(items),
            dataset=definition.slug,
            snapshot_date=latest_date,
        ).model_dump(mode="json"),
    }


@router.get("/{slug}/historical")
@limiter.limit("60/minute")
async def historical(
    request: Request,  # required by slowapi
    slug: str,
    registry: Annotated[DatasetRegistry, Depends(get_registry_dep)],
    session: Annotated[Session, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    currency: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Return paginated, filterable historical records for a dataset."""
    definition = _resolve_definition(registry, slug)
    model = definition.model_class

    base = select(model)
    if from_date is not None:
        base = base.where(model.snapshot_date >= from_date)
    if to_date is not None:
        base = base.where(model.snapshot_date <= to_date)
    if currency is not None and hasattr(model, "currency_code"):
        base = base.where(model.currency_code == currency.upper())

    total = session.execute(select(func.count()).select_from(base.subquery())).scalar() or 0

    page_query = (
        base.order_by(model.snapshot_date.desc()).limit(pagination.limit).offset(pagination.offset)
    )
    rows = session.execute(page_query).scalars().all()
    items = [
        definition.schema_class.model_validate(r, from_attributes=True).model_dump(mode="json")
        for r in rows
    ]
    return {
        "data": items,
        "meta": Meta(
            count=len(items),
            total=total,
            dataset=definition.slug,
            limit=pagination.limit,
            offset=pagination.offset,
        ).model_dump(mode="json"),
    }


@router.get("/{slug}/csv")
@limiter.limit("60/minute")
async def csv_export(
    request: Request,  # required by slowapi
    slug: str,
    registry: Annotated[DatasetRegistry, Depends(get_registry_dep)],
    session: Annotated[Session, Depends(get_db_session)],
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    currency: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
    """Stream a CSV of all records (filterable by from/to/currency)."""
    definition = _resolve_definition(registry, slug)
    model = definition.model_class

    query = select(model)
    if from_date is not None:
        query = query.where(model.snapshot_date >= from_date)
    if to_date is not None:
        query = query.where(model.snapshot_date <= to_date)
    if currency is not None and hasattr(model, "currency_code"):
        query = query.where(model.currency_code == currency.upper())

    query = query.order_by(model.snapshot_date.desc())
    rows = session.execute(query).scalars().all()
    records = [definition.schema_class.model_validate(r, from_attributes=True) for r in rows]
    csv_text = export_records_to_csv(records, definition.schema_class)
    filename = f"{slug}.csv"
    return create_csv_response(csv_text, filename=filename)
