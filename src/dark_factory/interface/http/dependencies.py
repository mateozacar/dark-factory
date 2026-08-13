"""
Interface — FastAPI dependency injection wiring.
"""

from __future__ import annotations

from fastapi import Request

from dark_factory.infrastructure.usgs.adapter import USGSAdapter


def get_earthquake_repository(request: Request) -> USGSAdapter:
    """Return a USGSAdapter wired with the lifespan-managed httpx.AsyncClient."""
    return USGSAdapter(client=request.app.state.http_client)
