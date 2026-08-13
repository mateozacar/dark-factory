"""
Application factory: create_app().

Wires the FastAPI instance with:
  - httpx.AsyncClient lifespan (shared client for the lifetime of the process)
  - /api/v1 router
  - /health endpoint
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from dark_factory.config import Settings
from dark_factory.interface.http.v1.earthquakes import router as earthquakes_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage the shared httpx.AsyncClient across the application lifetime."""
    settings = Settings()
    async with httpx.AsyncClient(base_url=settings.usgs_base_url) as client:
        app.state.http_client = client
        yield
    # client is closed automatically on context-manager exit


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    openapi_tags = [
        {
            "name": "earthquakes",
            "description": (
                "Query real-time global earthquake data proxied"
                " from the USGS Earthquake Hazards API."
            ),
        },
        {
            "name": "health",
            "description": "Service health and upstream availability check.",
        },
    ]

    app = FastAPI(
        title="Dark Factory — Earthquake API",
        description="Stateless USGS earthquake proxy built with Clean Architecture.",
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=openapi_tags,
    )

    # /api/v1 versioned router
    app.include_router(earthquakes_router, prefix="/api/v1")

    # /health — lives outside the versioned prefix
    @app.get(
        "/health",
        tags=["health"],
        summary="Service health check",
        description=(
            "Confirms the service is running."
            " Returns 200 when the application is healthy."
        ),
    )
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


# Module-level app instance for uvicorn/gunicorn entry point
app = create_app()
