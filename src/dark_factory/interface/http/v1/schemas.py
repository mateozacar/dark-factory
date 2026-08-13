"""
Interface — HTTP v1 Pydantic request/response schemas.

These are wire-format types; they translate to/from domain objects at
the handler boundary and must NOT leak into the domain layer.
"""

from __future__ import annotations

from pydantic import BaseModel


class EarthquakeResponse(BaseModel):
    """Wire-format representation of a single earthquake."""

    id: str
    magnitude: float
    depth: float
    latitude: float
    longitude: float


class EarthquakeListResponse(BaseModel):
    """Wire-format for a list of earthquakes."""

    items: list[EarthquakeResponse]
    total: int


class EarthquakeFilterParams(BaseModel):
    """Pydantic model for query-parameter based earthquake filtering."""

    min_magnitude: float | None = None
    max_magnitude: float | None = None
    min_depth: float | None = None
    max_depth: float | None = None
    start_time: str | None = None
    end_time: str | None = None
    limit: int | None = None
