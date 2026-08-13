"""
Domain value objects: Magnitude, Depth, Coordinates, EarthquakeFilter.

Uses stdlib dataclasses only — zero external imports (AD-2).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Magnitude:
    """Represents a seismic magnitude reading."""

    value: float


@dataclass
class Depth:
    """Represents the depth of a seismic event in kilometres."""

    km: float


@dataclass
class Coordinates:
    """Geographic coordinates for a seismic event."""

    latitude: float
    longitude: float


@dataclass
class EarthquakeFilter:
    """Optional query filter passed down to the repository port.

    All fields default to None, representing an unfiltered query.
    """

    min_magnitude: float | None = None
    max_magnitude: float | None = None
    min_depth: float | None = None
    max_depth: float | None = None
    min_latitude: float | None = None
    max_latitude: float | None = None
    min_longitude: float | None = None
    max_longitude: float | None = None
    start_time: str | None = None
    end_time: str | None = None
    limit: int | None = None
