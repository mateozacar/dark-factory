"""
Application query handlers: GetEarthquakesHandler, GetEarthquakeByIdHandler.

Handlers depend only on the domain repository port — never on infrastructure
or interface layers (AD-2).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from dark_factory.application.earthquake.queries import (
    GetAftershocks,
    GetEarthquakeById,
    GetEarthquakes,
)
from dark_factory.domain.earthquake.entities import AftershockResult, Earthquake
from dark_factory.domain.earthquake.exceptions import EarthquakeNotFound
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


class GetAftershocksHandler:
    """Handles the GetAftershocks query: fetches main event and analyses sequence."""

    def __init__(self, repository: EarthquakeRepository) -> None:
        self._repository = repository

    async def handle(self, query: GetAftershocks) -> AftershockResult:
        """Fetch the main event, retrieve aftershocks, and assess the sequence."""
        main = await self._repository.get_by_id(query.earthquake_id)
        if main is None:
            raise EarthquakeNotFound(query.earthquake_id)

        if not main.time:
            raise EarthquakeNotFound(query.earthquake_id)

        # Compute time window
        main_dt = datetime.fromisoformat(main.time.replace("Z", "+00:00"))
        end_dt = main_dt + timedelta(days=query.days)
        mid_dt = main_dt + timedelta(days=query.days / 2)

        start_time_str = main_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Wells–Coppersmith radius
        radius_km = 10 ** (0.5 * main.magnitude - 1.8)

        aftershock_filter = EarthquakeFilter(
            start_time=start_time_str,
            end_time=end_time_str,
            min_magnitude=max(0.0, main.magnitude - 3.0),
            max_magnitude=main.magnitude - 0.1,
            latitude=main.latitude,
            longitude=main.longitude,
            max_radius_km=radius_km,
        )

        aftershocks = await self._repository.get_all(aftershock_filter)

        count = len(aftershocks)

        # Compute stats
        if count == 0:
            max_magnitude: float | None = None
            avg_magnitude: float | None = None
            largest_aftershock_id: str | None = None
        else:
            max_magnitude = max(eq.magnitude for eq in aftershocks)
            avg_magnitude = sum(eq.magnitude for eq in aftershocks) / count
            largest = max(aftershocks, key=lambda eq: eq.magnitude)
            largest_aftershock_id = largest.id

        # Sequence assessment
        if count < 3:
            sequence_assessment = "insufficient_data"
        else:
            timed = [eq for eq in aftershocks if eq.time]
            first_half = [
                eq
                for eq in timed
                if datetime.fromisoformat(eq.time.replace("Z", "+00:00")) < mid_dt
            ]
            second_half = [
                eq
                for eq in timed
                if datetime.fromisoformat(eq.time.replace("Z", "+00:00")) >= mid_dt
            ]
            if len(second_half) < len(first_half):
                sequence_assessment = "decaying"
            else:
                sequence_assessment = "active"

        return AftershockResult(
            main_event=main,
            aftershocks=aftershocks,
            count=count,
            max_magnitude=max_magnitude,
            avg_magnitude=avg_magnitude,
            largest_aftershock_id=largest_aftershock_id,
            sequence_assessment=sequence_assessment,
        )
