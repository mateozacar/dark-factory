"""
Infrastructure — USGSAdapter: implements the EarthquakeRepository port.
"""

from __future__ import annotations

import httpx

from dark_factory.domain.earthquake.entities import Earthquake
from dark_factory.domain.earthquake.repositories import EarthquakeRepository
from dark_factory.domain.earthquake.value_objects import EarthquakeFilter
from dark_factory.infrastructure.usgs.client import USGSClient
from dark_factory.infrastructure.usgs.mappers import USGSMapper


class USGSAdapter(EarthquakeRepository):
    """Concrete adapter that satisfies the EarthquakeRepository port via USGS."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_all(
        self, filters: EarthquakeFilter | None = None
    ) -> list[Earthquake]:
        """Fetch earthquakes from USGS and return as domain entities."""
        if filters is None:
            return []
        usgs_client = USGSClient(base_url="", client=self._client)
        raw = await usgs_client.query(
            starttime=filters.start_time or "",
            endtime=filters.end_time or "",
            minmagnitude=filters.min_magnitude or 0.0,
            latitude=filters.latitude,
            longitude=filters.longitude,
            maxradiuskm=filters.max_radius_km,
            maxmagnitude=filters.max_magnitude,
        )
        features = raw.get("features", [])
        if not isinstance(features, list):
            raise TypeError(
                f"Expected list for 'features', got {type(features).__name__}"
            )
        return [USGSMapper.feature_to_earthquake(f) for f in features]

    async def get_by_id(self, earthquake_id: str) -> Earthquake | None:
        """Fetch a single earthquake by its USGS event ID."""
        usgs_client = USGSClient(base_url="", client=self._client)
        feature = await usgs_client.fetch_earthquake_by_id(earthquake_id)
        if feature is None:
            return None
        return USGSMapper.feature_to_earthquake(feature)
