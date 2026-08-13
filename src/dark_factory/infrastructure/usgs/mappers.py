"""
Infrastructure — mapper: USGS GeoJSON → Earthquake domain entity.
"""

from __future__ import annotations

from dark_factory.domain.earthquake.entities import Earthquake


class USGSMapper:
    """Translates a USGS GeoJSON feature dict to an Earthquake domain entity."""

    @staticmethod
    def feature_to_earthquake(feature: dict[str, object]) -> Earthquake:
        """Map a USGS GeoJSON feature dict to an Earthquake domain entity."""
        earthquake_id = str(feature["id"])
        properties = feature["properties"]
        if not isinstance(properties, dict):
            raise TypeError(
                f"Expected dict for 'properties', got {type(properties).__name__}"
            )
        mag = properties["mag"]
        magnitude = float(mag)
        geometry = feature["geometry"]
        if not isinstance(geometry, dict):
            raise TypeError(
                f"Expected dict for 'geometry', got {type(geometry).__name__}"
            )
        coordinates = geometry["coordinates"]
        if not isinstance(coordinates, list):
            raise TypeError(
                f"Expected list for 'coordinates', got {type(coordinates).__name__}"
            )
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
        depth = float(coordinates[2])
        return Earthquake(
            id=earthquake_id,
            magnitude=magnitude,
            depth=depth,
            latitude=latitude,
            longitude=longitude,
        )
