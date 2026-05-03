"""DatasetDefinition — the unit of registration.

A :class:`DatasetDefinition` bundles the identity, data flow, and
storage classes for a single dataset into one immutable, validated
object. This is what each ``govlink/datasets/<slug>/dataset.py`` builds
and hands to :meth:`govlink.core.registry.DatasetRegistry.register`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from govlink.core.base_parser import BaseParser
from govlink.core.base_source import BaseSource
from govlink.core.models import DatasetFrequency
from govlink.db import Base

# Reuse the same slug pattern enforced on the ORM Dataset.slug column so
# that ``Dataset.slug`` and ``DatasetDefinition.slug`` accept exactly the
# same set of values.
_SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class DatasetDefinition(BaseModel):
    """Self-contained definition of a registered dataset.

    Wires together identity (``slug``, ``title``, ``publisher``, …), the
    data flow (``source``, ``parser``), and storage (``model_class``,
    ``schema_class``). Frozen — definitions must not mutate after they
    are registered.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    slug: str = Field(min_length=1, max_length=64, pattern=_SLUG_PATTERN)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    publisher: str = Field(min_length=1, max_length=255)
    source_url: str = Field(min_length=1, max_length=1024)
    frequency: DatasetFrequency
    source: BaseSource
    parser: BaseParser[Any]
    model_class: type[Base]
    schema_class: type[BaseModel]

    # ``mode="before"`` so the explicit isinstance/issubclass checks run
    # ahead of Pydantic's own arbitrary-type validation. That gives us a
    # single, clearly-worded error message regardless of input shape.

    @field_validator("source", mode="before")
    @classmethod
    def _source_is_base_source(cls, v: Any) -> BaseSource:
        if not isinstance(v, BaseSource):
            raise ValueError("source must be an instance of BaseSource")
        return v

    @field_validator("parser", mode="before")
    @classmethod
    def _parser_is_base_parser(cls, v: Any) -> BaseParser[Any]:
        if not isinstance(v, BaseParser):
            raise ValueError("parser must be an instance of BaseParser")
        return v

    @field_validator("model_class", mode="before")
    @classmethod
    def _model_is_orm_class(cls, v: Any) -> type[Base]:
        if not (isinstance(v, type) and issubclass(v, Base)):
            raise ValueError("model_class must be a subclass of govlink.db.Base")
        return v

    @field_validator("schema_class", mode="before")
    @classmethod
    def _schema_is_pydantic_class(cls, v: Any) -> type[BaseModel]:
        if not (isinstance(v, type) and issubclass(v, BaseModel)):
            raise ValueError("schema_class must be a subclass of pydantic.BaseModel")
        return v

    @property
    def data_table_name(self) -> str:
        """The expected SQL table name for this dataset's data: ``data_<slug>``."""
        return f"data_{self.slug.replace('-', '_')}"

    def __repr__(self) -> str:
        return f"<DatasetDefinition slug={self.slug!r}>"
