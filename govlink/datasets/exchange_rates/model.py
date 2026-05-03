"""ORM model and Pydantic schemas for the exchange-rates dataset.

The single ``data_exchange_rates`` table is keyed on
``(snapshot_date, currency_code)``. The Pydantic ``ExchangeRateRecord`` is
what the parser produces (with ``rate_per_unit`` computed from
``rate / unit_multiplier``). The Pydantic ``ExchangeRateResponseItem`` is
the public-facing API representation, deliberately omitting internal
fields like ``id``, ``source_file_id``, and ``ingested_at``.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from sqlalchemy import (
    DECIMAL,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from govlink.core.schemas import DecimalStr
from govlink.db import Base

_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3,4}$")


def _utcnow() -> datetime:
    """UTC-aware ``datetime.now`` — the project's canonical clock source."""
    return datetime.now(UTC)


class ExchangeRate(Base):
    """One per-currency exchange rate row for a single snapshot date."""

    __tablename__ = "data_exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_date",
            "currency_code",
            name="uq_data_exchange_rates_snapshot_date_currency_code",
        ),
        Index(
            "ix_data_exchange_rates_snapshot_date_currency_code",
            "snapshot_date",
            "currency_code",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    currency_name: Mapped[str] = mapped_column(String(64), nullable=False)
    rate: Mapped[Decimal] = mapped_column(DECIMAL(18, 6), nullable=False)
    unit_multiplier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rate_per_unit: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ExchangeRate snapshot_date={self.snapshot_date.isoformat()} "
            f"code={self.currency_code} rate={self.rate}>"
        )


# Decimal field bounds chosen to mirror the ORM column precision. The
# DecimalStr serialisation alias from core.schemas ensures these values
# round-trip through JSON and CSV as plain strings, never floats.
_RateField = Annotated[
    DecimalStr,
    Field(gt=Decimal("0"), max_digits=18, decimal_places=6),
]


class ExchangeRateRecord(BaseModel):
    """The structured record produced by :class:`ExchangeRatesParser`.

    ``rate_per_unit`` is a computed field — derived from
    ``rate / unit_multiplier`` — so callers don't have to remember to
    divide. Frozen so records can't be mutated after the parser hands
    them off to the orchestrator.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_date: date
    currency_code: str = Field(min_length=3, max_length=8)
    currency_name: str = Field(min_length=1, max_length=64)
    rate: _RateField
    unit_multiplier: int = Field(ge=1)

    @field_validator("currency_code")
    @classmethod
    def _validate_currency_code(cls, v: str) -> str:
        if not _CURRENCY_CODE_PATTERN.fullmatch(v):
            raise ValueError(
                f"currency_code {v!r} must be 3 or 4 uppercase letters (e.g. 'USD', 'WAUA')"
            )
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rate_per_unit(self) -> DecimalStr:
        """GMD per single foreign-currency unit, normalising the multiplier."""
        return self.rate / Decimal(self.unit_multiplier)


class ExchangeRateResponseItem(BaseModel):
    """The public API representation of one exchange rate row.

    Deliberately omits internal fields (``id``, ``source_file_id``,
    ``ingested_at``) to keep the API surface clean. Built from an ORM
    instance via ``model_validate(orm_obj, from_attributes=True)``.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    snapshot_date: date
    currency_code: str
    currency_name: str
    rate: DecimalStr
    unit_multiplier: int
    rate_per_unit: DecimalStr

    @field_validator("rate", "rate_per_unit", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: Any) -> Any:
        # Pass-through; Pydantic handles Decimal → Decimal natively.
        return v
