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
