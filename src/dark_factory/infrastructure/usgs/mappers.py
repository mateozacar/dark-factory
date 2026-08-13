"""
Infrastructure — mapper: USGS GeoJSON → Earthquake domain entity.

Stub: intentionally unimplemented until the infrastructure story lands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dark_factory.domain.earthquake.entities import Earthquake


class USGSMapper:
    """Translates a USGS GeoJSON feature dict to an Earthquake domain entity.

    Not implemented in this story — raises NotImplementedError on use.
    """

    @staticmethod
    def feature_to_earthquake(feature: dict[str, object]) -> Earthquake:
        raise NotImplementedError("stub — implement in the infrastructure story")
