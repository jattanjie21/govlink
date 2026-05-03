"""Value object representing a discovered source file.

A :class:`SourceFileRef` is what :meth:`govlink.core.base_source.BaseSource.discover`
yields — a transport-independent description of one upstream artifact.
``source_uuid`` must be globally unique within a dataset and stable
across re-discoveries of the same logical file.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceFileRef(BaseModel):
    """A reference to a single source file discoverable from a dataset's source.

    This is a value object — frozen, hashable, equality by value.
    The ``published_date_hint`` is intentionally a hint; never trust it
    as authoritative, since publishers' link-text dates are unreliable.
    Authoritative snapshot dates must come from parsing file contents.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_uuid: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1, max_length=1024)
    link_text: str | None = Field(default=None, max_length=512)
    published_date_hint: date | None = None

    @field_validator("url")
    @classmethod
    def _url_must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v
