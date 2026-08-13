"""
Shared pytest fixtures for Dark Factory tests.

Provides:
  - async_client: httpx.AsyncClient wired to the ASGI app via ASGITransport
  - FakeEarthquakeRepository: in-memory stub that satisfies the EarthquakeRepository port
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from dark_factory.domain.earthquake.entities import Earthquake
    from dark_factory.domain.earthquake.filters import EarthquakeFilter


# ---------------------------------------------------------------------------
# FakeEarthquakeRepository — satisfies the domain port without I/O
# ---------------------------------------------------------------------------

class FakeEarthquakeRepository:
    """In-memory fake that implements EarthquakeRepository for unit tests."""

    def __init__(self, earthquakes: list["Earthquake"] | None = None) -> None:
        self._store: list["Earthquake"] = earthquakes or []

    async def get_all(
        self, filters: "EarthquakeFilter | None" = None
    ) -> list["Earthquake"]:
        return list(self._store)

    async def get_by_id(self, earthquake_id: str) -> "Earthquake | None":
        for eq in self._store:
            if eq.id == earthquake_id:
                return eq
        return None


# ---------------------------------------------------------------------------
# ASGI async client fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
async def async_client():
    """
    Yield an httpx.AsyncClient bound to the ASGI app through ASGITransport.
    The fixture intentionally imports create_app at call time so that the
    import error surfaces at runtime, not at collection time.
    """
    import httpx
    from httpx import AsyncClient, ASGITransport
    from dark_factory.main import create_app  # ImportError expected until impl exists

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture()
def fake_repo() -> FakeEarthquakeRepository:
    """Return a fresh empty FakeEarthquakeRepository."""
    return FakeEarthquakeRepository()
