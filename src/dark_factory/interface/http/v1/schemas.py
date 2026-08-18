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


class AftershockMainEvent(BaseModel):
    """Wire-format representation of the main event in an aftershock response."""

    id: str
    magnitude: float
    depth: float
    latitude: float
    longitude: float
    time: str


class AftershockStats(BaseModel):
    """Statistics computed over the aftershock sequence."""

    count: int
    max_magnitude: float | None
    avg_magnitude: float | None
    largest_aftershock_id: str | None


class AftershockResponse(BaseModel):
    """Wire-format response for the GET /{earthquake_id}/aftershocks endpoint."""

    main_event: AftershockMainEvent
    aftershocks: list[EarthquakeResponse]
    stats: AftershockStats
    sequence_assessment: str


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
