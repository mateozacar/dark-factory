"""
Domain entity: Earthquake.

Uses stdlib dataclasses only — zero external imports (AD-2).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Earthquake:
    """Core domain entity representing a seismic event."""

    id: str
    magnitude: float
    depth: float
    latitude: float
    longitude: float
    time: str = ""


@dataclass
class AftershockResult:
    """Result of an aftershock sequence analysis for a given main event."""

    main_event: Earthquake
    aftershocks: list[Earthquake]
    count: int
    max_magnitude: float | None
    avg_magnitude: float | None
    largest_aftershock_id: str | None
    sequence_assessment: str
