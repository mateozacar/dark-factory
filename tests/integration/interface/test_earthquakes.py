"""
Integration tests for GET /api/v1/earthquakes

AC covered:
  - Given all three params present, when GET /api/v1/earthquakes?starttime=2026-08-06
    &endtime=2026-08-13&minmagnitude=4, then HTTP 200 with
    {"type":"FeatureCollection","features":[...]}
  - Given any required param missing, when GET /api/v1/earthquakes, then HTTP 422
  - Given any request, when get_earthquake_repository(request), then returns a
    USGSAdapter instance (not None)
  - Given a list of Earthquake entities, when serialized, then each is a GeoJSON
    Feature with Point geometry [lon, lat, depth] and mag in properties

I/O & Edge-Case Matrix rows covered:
  - Happy path: GET with all three params → HTTP 200, FeatureCollection with features
  - Missing required param (starttime absent) → HTTP 422
  - Missing required param (endtime absent) → HTTP 422
  - Missing required param (minmagnitude absent) → HTTP 422
  - All params missing → HTTP 422
  - USGS returns empty features: fake repo returns [] → HTTP 200,
    {"type":"FeatureCollection","features":[]}
  - GeoJSON Feature shape: geometry.coordinates=[lon,lat,depth], properties={id,mag}

TDD phase: RED — will fail until earthquakes.py, schemas.py, and dependencies.py
are implemented.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from dark_factory.domain.earthquake.entities import Earthquake
    from dark_factory.domain.earthquake.filters import EarthquakeFilter


# ---------------------------------------------------------------------------
# Inline fake repository (mirrors conftest.FakeEarthquakeRepository but
# pre-loaded with two sample earthquake entities matching the fixture)
# ---------------------------------------------------------------------------

class _FakeEarthquakeRepository:
    """In-memory fake that implements the EarthquakeRepository port."""

    def __init__(self, earthquakes: list["Earthquake"] | None = None) -> None:
        self._store: list["Earthquake"] = earthquakes or []

    async def get_all(self, filters: "EarthquakeFilter | None" = None) -> list["Earthquake"]:
        return list(self._store)

    async def get_by_id(self, earthquake_id: str) -> "Earthquake | None":
        for eq in self._store:
            if eq.id == earthquake_id:
                return eq
        return None


def _make_sample_earthquakes() -> list["Earthquake"]:
    """Return two Earthquake entities that match the fixture file."""
    from dark_factory.domain.earthquake.entities import Earthquake

    return [
        Earthquake(id="us7000abc1", magnitude=5.2, depth=10.0, latitude=37.5, longitude=-122.1),
        Earthquake(id="us7000def2", magnitude=4.8, depth=22.5, latitude=35.7, longitude=139.7),
    ]


# ---------------------------------------------------------------------------
# Helpers to build a patched ASGI client
# ---------------------------------------------------------------------------

async def _make_client_with_fake_repo(earthquakes: list["Earthquake"] | None = None):
    """
    Create an httpx.AsyncClient backed by ASGITransport with the DI overridden
    so that get_earthquake_repository returns a fake in-memory repo instead of
    triggering a live USGS call.

    Returns the client (caller must use it as an async context manager or close it).
    """
    import httpx
    from httpx import ASGITransport, AsyncClient

    from dark_factory.main import create_app
    from dark_factory.interface.http.dependencies import get_earthquake_repository

    fake_repo = _FakeEarthquakeRepository(earthquakes=earthquakes)
    app = create_app()
    app.dependency_overrides[get_earthquake_repository] = lambda: fake_repo

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver"), app


class TestListEarthquakesHappyPath:
    """
    Given: all three query params (starttime, endtime, minmagnitude) are present
    When:  GET /api/v1/earthquakes?starttime=2026-08-06&endtime=2026-08-13&minmagnitude=4
    Then:  HTTP 200 is returned with a GeoJSON FeatureCollection body
    """

    @pytest.mark.anyio
    async def test_happy_path_returns_200(self) -> None:
        """
        Given: DI overridden with a fake repo containing 2 earthquakes,
               and all three required params present
        When:  GET /api/v1/earthquakes with valid params
        Then:  HTTP 200
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={
                        "starttime": "2026-08-06",
                        "endtime": "2026-08-13",
                        "minmagnitude": "4",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_happy_path_returns_feature_collection_type(self) -> None:
        """
        Given: DI overridden with a fake repo containing 2 earthquakes,
               and all three required params present
        When:  GET /api/v1/earthquakes with valid params
        Then:  response JSON has "type" == "FeatureCollection"
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={
                        "starttime": "2026-08-06",
                        "endtime": "2026-08-13",
                        "minmagnitude": "4",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        body = response.json()
        assert body["type"] == "FeatureCollection"

    @pytest.mark.anyio
    async def test_happy_path_returns_non_empty_features_list(self) -> None:
        """
        Given: DI overridden with a fake repo containing 2 earthquakes
        When:  GET /api/v1/earthquakes with valid params
        Then:  response JSON has "features" as a non-empty list
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={
                        "starttime": "2026-08-06",
                        "endtime": "2026-08-13",
                        "minmagnitude": "4",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        body = response.json()
        assert "features" in body
        assert isinstance(body["features"], list)
        assert len(body["features"]) == 2

    @pytest.mark.anyio
    async def test_happy_path_feature_has_geojson_feature_type(self) -> None:
        """
        Given: DI overridden with a fake repo containing 2 earthquakes
        When:  GET /api/v1/earthquakes with valid params
        Then:  each item in "features" has type == "Feature"
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={
                        "starttime": "2026-08-06",
                        "endtime": "2026-08-13",
                        "minmagnitude": "4",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        body = response.json()
        for feature in body["features"]:
            assert feature["type"] == "Feature"

    @pytest.mark.anyio
    async def test_happy_path_feature_geometry_is_point_with_coordinates(self) -> None:
        """
        Given: a fake repo with an Earthquake(longitude=-122.1, latitude=37.5, depth=10.0)
        When:  GET /api/v1/earthquakes with valid params
        Then:  the first feature's geometry is {"type":"Point","coordinates":[-122.1,37.5,10.0]}

        I/O Matrix row: GeoJSON Feature shape
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={
                        "starttime": "2026-08-06",
                        "endtime": "2026-08-13",
                        "minmagnitude": "4",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        body = response.json()
        first_feature = body["features"][0]
        geometry = first_feature["geometry"]
        assert geometry["type"] == "Point"
        # coordinates order: [longitude, latitude, depth]
        coords = geometry["coordinates"]
        assert coords[0] == -122.1
        assert coords[1] == 37.5
        assert coords[2] == 10.0

    @pytest.mark.anyio
    async def test_happy_path_feature_properties_contain_id_and_mag(self) -> None:
        """
        Given: a fake repo with Earthquake(id="us7000abc1", magnitude=5.2)
        When:  GET /api/v1/earthquakes with valid params
        Then:  the first feature's properties contain {"id":"us7000abc1","mag":5.2}

        I/O Matrix row: GeoJSON Feature shape — properties={id, mag}
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={
                        "starttime": "2026-08-06",
                        "endtime": "2026-08-13",
                        "minmagnitude": "4",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        body = response.json()
        first_feature = body["features"][0]
        props = first_feature["properties"]
        assert props["id"] == "us7000abc1"
        assert props["mag"] == 5.2


class TestListEarthquakesMissingParams:
    """
    Given: one or more required query params (starttime, endtime, minmagnitude) are absent
    When:  GET /api/v1/earthquakes is called
    Then:  HTTP 422 Unprocessable Entity is returned

    I/O Matrix rows: Missing required param, All params missing
    """

    @pytest.mark.anyio
    async def test_missing_starttime_returns_422(self) -> None:
        """
        Given: endtime and minmagnitude are provided but starttime is absent
        When:  GET /api/v1/earthquakes?endtime=2026-08-13&minmagnitude=4
        Then:  HTTP 422

        I/O Matrix row: Missing required param (starttime absent)
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={"endtime": "2026-08-13", "minmagnitude": "4"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_missing_endtime_returns_422(self) -> None:
        """
        Given: starttime and minmagnitude are provided but endtime is absent
        When:  GET /api/v1/earthquakes?starttime=2026-08-06&minmagnitude=4
        Then:  HTTP 422

        I/O Matrix row: Missing required param (endtime absent)
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={"starttime": "2026-08-06", "minmagnitude": "4"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_missing_minmagnitude_returns_422(self) -> None:
        """
        Given: starttime and endtime are provided but minmagnitude is absent
        When:  GET /api/v1/earthquakes?starttime=2026-08-06&endtime=2026-08-13
        Then:  HTTP 422

        I/O Matrix row: Missing required param (minmagnitude absent)
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={"starttime": "2026-08-06", "endtime": "2026-08-13"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_all_params_missing_returns_422(self) -> None:
        """
        Given: no query params are provided
        When:  GET /api/v1/earthquakes (bare URL)
        Then:  HTTP 422

        I/O Matrix row: All params missing
        """
        client, app = await _make_client_with_fake_repo(_make_sample_earthquakes())
        try:
            async with client:
                response = await client.get("/api/v1/earthquakes")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 422


class TestListEarthquakesEmptyResult:
    """
    Given: the repository returns an empty list (USGS returned features: [])
    When:  GET /api/v1/earthquakes with all three required params
    Then:  HTTP 200 with {"type":"FeatureCollection","features":[]}

    I/O Matrix row: USGS returns empty features
    """

    @pytest.mark.anyio
    async def test_empty_repo_returns_200_with_empty_features(self) -> None:
        """
        Given: DI overridden with a fake repo containing NO earthquakes
        When:  GET /api/v1/earthquakes with valid params
        Then:  HTTP 200, body has type="FeatureCollection" and features=[]
        """
        client, app = await _make_client_with_fake_repo(earthquakes=[])
        try:
            async with client:
                response = await client.get(
                    "/api/v1/earthquakes",
                    params={
                        "starttime": "2026-08-06",
                        "endtime": "2026-08-13",
                        "minmagnitude": "4",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "FeatureCollection"
        assert body["features"] == []


class TestGetEarthquakeRepositoryDependency:
    """
    Given: any request arrives at the endpoint
    When:  get_earthquake_repository(request) is resolved by FastAPI DI
    Then:  the resolved value is a USGSAdapter instance (not None)

    AC: Given any request, when get_earthquake_repository(request),
        then returns a USGSAdapter instance (not None)
    """

    @pytest.mark.anyio
    async def test_get_earthquake_repository_returns_usgs_adapter(self) -> None:
        """
        Given: a FastAPI app created via create_app() with lifespan http_client
        When:  get_earthquake_repository(request) is called with a mock request
               that has app.state.http_client set
        Then:  the return value is a USGSAdapter instance, not None
        """
        import httpx
        from fastapi import Request
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter
        from dark_factory.interface.http.dependencies import get_earthquake_repository

        # Create a mock request with a fake app state containing an httpx client
        fake_client = httpx.AsyncClient()

        # Build a minimal mock request scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/earthquakes",
            "query_string": b"",
            "headers": [],
        }

        class _MockApp:
            class state:
                http_client = fake_client

        scope["app"] = _MockApp()
        request = Request(scope=scope)

        result = get_earthquake_repository(request=request)

        assert result is not None
        assert isinstance(result, USGSAdapter)

        await fake_client.aclose()
