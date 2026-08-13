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
    ) -> dict[str, object]:
        """Fetch earthquake data from the USGS FDSNWS API."""
        response = await self._client.get(
            "query",
            params={
                "format": "geojson",
                "starttime": str(starttime),
                "endtime": str(endtime),
                "minmagnitude": minmagnitude,
                "orderby": "time",
            },
        )
        response.raise_for_status()
        result: dict[str, object] = response.json()
        return result

    async def fetch_earthquake_by_id(self, event_id: str) -> dict[str, object]:
        raise NotImplementedError("stub — implement in the infrastructure story")
