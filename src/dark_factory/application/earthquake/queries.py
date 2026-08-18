"""
Application query dataclasses: GetEarthquakes, GetEarthquakeById.

Stdlib dataclasses only — no external deps at this layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dark_factory.domain.earthquake.value_objects import EarthquakeFilter


@dataclass
class GetEarthquakes:
    """Query: retrieve a (filtered) list of earthquakes."""

    filters: EarthquakeFilter | None = None


@dataclass
class GetEarthquakeById:
    """Query: retrieve a single earthquake by its USGS event ID."""

    id: str


@dataclass
class GetAftershocks:
    """Query: retrieve the aftershock sequence for a given mainshock event."""

    earthquake_id: str
    days: int = 30
