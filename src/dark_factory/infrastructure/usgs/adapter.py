"""
Infrastructure — USGSAdapter: implements the EarthquakeRepository port.

Stub: intentionally unimplemented until the infrastructure story lands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dark_factory.domain.earthquake.repositories import EarthquakeRepository

if TYPE_CHECKING:
    from dark_factory.domain.earthquake.entities import Earthquake
    from dark_factory.domain.earthquake.value_objects import EarthquakeFilter


class USGSAdapter(EarthquakeRepository):
    """Concrete adapter that satisfies the EarthquakeRepository port via USGS.

    Not implemented in this story — all methods raise NotImplementedError.
    """

    def __init__(self, client: object) -> None:
        self._client = client

    async def get_all(
        self, filters: EarthquakeFilter | None = None
    ) -> list[Earthquake]:
        raise NotImplementedError("stub — implement in the infrastructure story")

    async def get_by_id(self, earthquake_id: str) -> Earthquake | None:
        raise NotImplementedError("stub — implement in the infrastructure story")
