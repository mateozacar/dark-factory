"""
Interface — HTTP v1 Pydantic request/response schemas.

These are wire-format types; they translate to/from domain objects at
the handler boundary and must NOT leak into the domain layer.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class EarthquakeResponse(BaseModel):
    """Wire-format representation of a single earthquake."""

    id: str
    magnitude: float
    depth: float
    latitude: float
    longitude: float


class EarthquakeListResponse(BaseModel):
    """Wire-format for a list of earthquakes."""

    items: list[EarthquakeResponse]
    total: int


class EarthquakeFilterParams(BaseModel):
    """Pydantic model for query-parameter based earthquake filtering."""

    starttime: date
    endtime: date
    minmagnitude: float


class GeoJSONGeometry(BaseModel):
    """GeoJSON Point geometry."""

    type: str = "Point"
    coordinates: list[float]


class GeoJSONFeatureProperties(BaseModel):
    """Properties embedded in a GeoJSON Feature."""

    id: str
    mag: float


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature wrapping a single earthquake."""

    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: GeoJSONFeatureProperties


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection wrapping a list of earthquake features."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [-122.1, 37.5, 10.0],
                        },
                        "properties": {"id": "us7000abc1", "mag": 5.2},
                    }
                ],
            }
        }
    )

    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]
