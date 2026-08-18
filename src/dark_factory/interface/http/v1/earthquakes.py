"""
Interface — FastAPI router for /api/v1/earthquakes endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from dark_factory.application.earthquake.handlers import (
    GetAftershocksHandler,
    GetEarthquakesHandler,
)
from dark_factory.application.earthquake.queries import GetAftershocks, GetEarthquakes
from dark_factory.domain.earthquake.exceptions import EarthquakeNotFound
from dark_factory.domain.earthquake.value_objects import EarthquakeFilter
from dark_factory.interface.http.dependencies import get_earthquake_repository
from dark_factory.interface.http.v1.schemas import (
    AftershockMainEvent,
    AftershockResponse,
    AftershockStats,
    EarthquakeFilterParams,
    EarthquakeResponse,
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
                coordinates=[eq.longitude or 0.0, eq.latitude or 0.0, eq.depth or 0.0],
            ),
            properties=GeoJSONFeatureProperties(id=eq.id, mag=eq.magnitude),
        )
        for eq in earthquakes
    ]
    return GeoJSONFeatureCollection(type="FeatureCollection", features=features)


@router.get(
    "/recent",
    response_model=GeoJSONFeatureCollection,
    summary="Recent earthquakes",
    description=(
        "Shortcut for the last 24 hours with magnitude \u2265 2.5."
        " Computes the time window at request time and returns"
        " a GeoJSON FeatureCollection."
    ),
    responses={
        422: {"description": "Validation error (contract completeness)."},
        502: {"description": "USGS upstream unavailable or returned an error."},
    },
)
async def recent_earthquakes(
    repo: Annotated[EarthquakeRepository, Depends(get_earthquake_repository)],
) -> GeoJSONFeatureCollection:
    """Return earthquakes from the last 24 h with magnitude >= 2.5."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=24)
    earthquake_filter = EarthquakeFilter(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        min_magnitude=2.5,
    )
    try:
        handler = GetEarthquakesHandler(repository=repo)
        earthquakes = await handler.handle(GetEarthquakes(filters=earthquake_filter))
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"USGS upstream error: {str(exc)}",
        )
    features = [
        GeoJSONFeature(
            type="Feature",
            geometry=GeoJSONGeometry(
                type="Point",
                coordinates=[eq.longitude or 0.0, eq.latitude or 0.0, eq.depth or 0.0],
            ),
            properties=GeoJSONFeatureProperties(id=eq.id, mag=eq.magnitude),
        )
        for eq in earthquakes
    ]
    return GeoJSONFeatureCollection(type="FeatureCollection", features=features)


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


@router.get(
    "/{earthquake_id}/aftershocks",
    response_model=AftershockResponse,
    summary="Get aftershock sequence for an earthquake",
    description=(
        "Retrieve and analyse the aftershock sequence for a given mainshock event."
        " Returns sequence statistics and an assessment of whether the sequence"
        " is decaying, active, or has insufficient data."
    ),
    responses={
        404: {"description": "Earthquake event not found."},
        422: {"description": "Validation error (e.g. days out of range)."},
        502: {"description": "USGS upstream unavailable or returned an error."},
    },
)
async def get_aftershocks(
    earthquake_id: str,
    repo: Annotated[EarthquakeRepository, Depends(get_earthquake_repository)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> AftershockResponse:
    """Return the aftershock sequence and statistics for a mainshock event."""
    query = GetAftershocks(earthquake_id=earthquake_id, days=days)
    handler = GetAftershocksHandler(repository=repo)
    try:
        result = await handler.handle(query)
    except EarthquakeNotFound:
        raise HTTPException(status_code=404, detail="Earthquake not found")
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"USGS upstream error: {str(exc)}",
        )
    main = result.main_event
    return AftershockResponse(
        main_event=AftershockMainEvent(
            id=main.id,
            magnitude=main.magnitude,
            depth=main.depth,
            latitude=main.latitude,
            longitude=main.longitude,
            time=main.time,
        ),
        aftershocks=[
            EarthquakeResponse(
                id=eq.id,
                magnitude=eq.magnitude,
                depth=eq.depth,
                latitude=eq.latitude,
                longitude=eq.longitude,
            )
            for eq in result.aftershocks
        ],
        stats=AftershockStats(
            count=result.count,
            max_magnitude=result.max_magnitude,
            avg_magnitude=result.avg_magnitude,
            largest_aftershock_id=result.largest_aftershock_id,
        ),
        sequence_assessment=result.sequence_assessment,
    )