"""
Domain repository port: EarthquakeRepository.

Defines the abstract interface (port) that infrastructure adapters must implement.
Uses stdlib abc only — zero external imports (AD-2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dark_factory.domain.earthquake.entities import Earthquake
    from dark_factory.domain.earthquake.value_objects import EarthquakeFilter


class EarthquakeRepository(ABC):
    """Abstract repository port for earthquake data access."""

    @abstractmethod
    async def get_all(
        self, filters: EarthquakeFilter | None = None
    ) -> list[Earthquake]:
        """Return all earthquakes, optionally filtered."""
        ...

    @abstractmethod
    async def get_by_id(self, earthquake_id: str) -> Earthquake | None:
        """Return a single earthquake by its USGS event ID, or None."""
        ...
