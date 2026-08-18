"""
Interface — FastAPI router for /api/v1/earthquakes endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from dark_factory.application.earthquake.handlers import GetEarthquakesHandler
from dark_factory.application.earthquake.queries import GetEarthquakes
from dark_factory.domain.earthquake.repositories import EarthquakeRepository
from dark_factory.domain.earthquake.value_objects import EarthquakeFilter
from dark_factory.interface.http.dependencies import get_earthquake_repository
from dark_factory.interface.http.v1.schemas import (
    EarthquakeFilterParams,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONFeatureProperties,
    GeoJSONGeometry,
)

router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])


@router.get(
    "",
    response_model=GeoJSONFeatureCollection,
    summary="List earthquakes",
    description=(
        "Filter and retrieve earthquakes from the USGS Earthquake Hazards API."
        " All three parameters are required."
        " Responses are returned as a GeoJSON FeatureCollection."
    ),
    responses={
        422: {"description": "Missing or invalid query parameters."},
        502: {"description": "USGS upstream unavailable or returned an error."},
    },
)
async def list_earthquakes(
    params: Annotated[EarthquakeFilterParams, Depends()],
    repo: Annotated[EarthquakeRepository, Depends(get_earthquake_repository)],
) -> GeoJSONFeatureCollection:
    """List earthquakes filtered by starttime, endtime, and minmagnitude."""
    earthquake_filter = EarthquakeFilter(
        start_time=params.starttime.isoformat(),
        end_time=params.endtime.isoformat(),
        min_magnitude=params.minmagnitude,
    )
    handler = GetEarthquakesHandler(repository=repo)
    earthquakes = await handler.handle(GetEarthquakes(filters=earthquake_filter))
    features = [
        GeoJSONFeature(
            type="Feature",
            geometry=GeoJSONGeometry(
                type="Point",
                coordinates=[eq.longitude, eq.latitude, eq.depth],
            ),
            properties=GeoJSONFeatureProperties(id=eq.id, mag=eq.magnitude),
        )
        for eq in earthquakes
    ]
    return GeoJSONFeatureCollection(type="FeatureCollection", features=features)


@router.get(
    "/recent",
    summary="Recent earthquakes (stub)",
    description=(
        "Shortcut for the last 24 hours with magnitude \u2265 2.5."
        " **Currently a stub** \u2014 returns placeholder data."
    ),
    responses={
        422: {"description": "Validation error (contract completeness)."},
    },
)
async def recent_earthquakes() -> dict[str, str]:
    """Return earthquakes from the last 24 h with magnitude >= 2.5. (stub)"""
    return {"status": "stub"}


@router.get(
    "/{earthquake_id}",
    summary="Get earthquake by ID (stub)",
    description=(
        "Retrieve a single earthquake event by its USGS event ID."
        " **Currently a stub** \u2014 returns placeholder data."
    ),
)
async def get_earthquake_by_id(earthquake_id: str) -> dict[str, str]:
    """Return a single earthquake by its USGS event ID. (stub)"""
    return {"status": "stub"}
