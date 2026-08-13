"""
Application query handlers: GetEarthquakesHandler, GetEarthquakeByIdHandler.

Handlers depend only on the domain repository port — never on infrastructure
or interface layers (AD-2).
"""

from __future__ import annotations

from dark_factory.application.earthquake.queries import (
    GetEarthquakeById,
    GetEarthquakes,
)
from dark_factory.domain.earthquake.entities import Earthquake
from dark_factory.domain.earthquake.repositories import EarthquakeRepository
from dark_factory.domain.earthquake.value_objects import EarthquakeFilter


class GetEarthquakesHandler:
    """Handles the GetEarthquakes query by delegating to the repository port."""

    def __init__(self, repository: EarthquakeRepository) -> None:
        self._repository = repository

    async def handle(self, query: GetEarthquakes) -> list[Earthquake]:
        """Execute the query and return matching earthquakes."""
        filters: EarthquakeFilter | None = query.filters
        return await self._repository.get_all(filters)


class GetEarthquakeByIdHandler:
    """Handles the GetEarthquakeById query by delegating to the repository port."""

    def __init__(self, repository: EarthquakeRepository) -> None:
        self._repository = repository

    async def handle(self, query: GetEarthquakeById) -> Earthquake | None:
        """Execute the query and return the earthquake, or None if not found."""
        return await self._repository.get_by_id(query.id)
