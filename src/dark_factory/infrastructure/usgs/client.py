"""
Infrastructure — httpx.AsyncClient wrapper for the USGS FDSNWS API.

Stub: intentionally unimplemented until the infrastructure story lands.
"""

from __future__ import annotations


class USGSClient:
    """Thin wrapper around httpx.AsyncClient for USGS API calls.

    Not implemented in this story — raises NotImplementedError on use.
    """

    def __init__(self, base_url: str, client: object) -> None:
        self._base_url = base_url
        self._client = client

    async def fetch_earthquakes(self, params: dict[str, object]) -> dict[str, object]:
        raise NotImplementedError("stub — implement in the infrastructure story")

    async def fetch_earthquake_by_id(self, event_id: str) -> dict[str, object]:
        raise NotImplementedError("stub — implement in the infrastructure story")
