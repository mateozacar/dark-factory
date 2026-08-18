"""
Infrastructure — httpx.AsyncClient wrapper for the USGS FDSNWS API.
"""

from __future__ import annotations

import httpx


class USGSClient:
    """Thin wrapper around httpx.AsyncClient for USGS API calls."""

    def __init__(self, base_url: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url
        self._client = client

    async def query(
        self,
        starttime: str,
        endtime: str,
        minmagnitude: float,
        latitude: float | None = None,
        longitude: float | None = None,
        maxradiuskm: float | None = None,
        maxmagnitude: float | None = None,
    ) -> dict[str, object]:
        """Fetch earthquake data from the USGS FDSNWS API."""
        params: dict[str, str | float] = {
            "format": "geojson",
            "starttime": str(starttime),
            "endtime": str(endtime),
            "minmagnitude": minmagnitude,
            "orderby": "time",
        }
        if latitude is not None:
            params["latitude"] = latitude
        if longitude is not None:
            params["longitude"] = longitude
        if maxradiuskm is not None:
            params["maxradiuskm"] = maxradiuskm
        if maxmagnitude is not None:
            params["maxmagnitude"] = maxmagnitude
        response = await self._client.get("query", params=params)
        response.raise_for_status()
        result: dict[str, object] = response.json()
        return result

    async def fetch_earthquake_by_id(
        self, event_id: str
    ) -> dict[str, object] | None:
        """Fetch a single earthquake feature by its USGS event ID."""
        response = await self._client.get(
            "query",
            params={
                "format": "geojson",
                "eventid": event_id,
            },
        )
        response.raise_for_status()
        data: dict[str, object] = response.json()
        features = data.get("features", [])
        if not isinstance(features, list) or len(features) == 0:
            return None
        result: dict[str, object] = features[0]
        return result
