"""
Interface — FastAPI router for /api/v1/earthquakes endpoints.

All endpoints are stubs returning {"status": "stub"} until the
application + infrastructure stories are complete.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])


@router.get("/")
async def list_earthquakes() -> dict[str, str]:
    """List earthquakes with optional filters. (stub)"""
    return {"status": "stub"}


@router.get("/recent")
async def recent_earthquakes() -> dict[str, str]:
    """Return earthquakes from the last 24 h with magnitude >= 2.5. (stub)"""
    return {"status": "stub"}


@router.get("/{earthquake_id}")
async def get_earthquake_by_id(earthquake_id: str) -> dict[str, str]:
    """Return a single earthquake by its USGS event ID. (stub)"""
    return {"status": "stub"}
