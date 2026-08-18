"""
Unit tests for dark_factory.infrastructure.usgs.adapter.USGSAdapter

AC covered:
  - Given a mocked USGS transport, when USGSAdapter.get_all(filters), then the
    outbound request includes format=geojson, orderby=time, and the three filter
    values (starttime, endtime, minmagnitude)
  - Given a mocked USGS transport returning two features, when USGSAdapter.get_all(filters),
    then a List[Earthquake] of length 2 is returned

I/O & Edge-Case Matrix rows covered:
  - Happy path: USGS returns 2 features → List[Earthquake] with correct values
  - USGS returns empty features: USGS features=[] → get_all returns []
  - Correct URL params: outbound request carries format, orderby, starttime, endtime,
    minmagnitude

TDD phase: RED — will fail with NotImplementedError until adapter.py is implemented.
"""

from __future__ import annotations

import json
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Load shared fixture
# ---------------------------------------------------------------------------

_FIXTURE_PATH = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "usgs_response.json"


def _load_fixture() -> dict:
    return json.loads(_FIXTURE_PATH.read_text())


# ---------------------------------------------------------------------------
# Helper: build an EarthquakeFilter with the three required fields
# ---------------------------------------------------------------------------

def _make_filter(
    start_time: str = "2026-08-06",
    end_time: str = "2026-08-13",
    min_magnitude: float = 4.0,
):
    from dark_factory.domain.earthquake.value_objects import EarthquakeFilter

    return EarthquakeFilter(
        start_time=start_time,
        end_time=end_time,
        min_magnitude=min_magnitude,
    )


class TestUSGSAdapterGetAll:
    """
    Given: a USGSAdapter wired with an httpx.AsyncClient backed by MockTransport
    When:  get_all(filters) is awaited
    Then:  the outbound request carries the correct USGS query params, and the
           returned value is a List[Earthquake]
    """

    @pytest.mark.anyio
    async def test_get_all_returns_list_of_earthquake_entities(self) -> None:
        """
        Given: a mock transport that returns the 2-feature USGS fixture
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the result is a list of Earthquake objects with length 2
        """
        import httpx
        from dark_factory.domain.earthquake.entities import Earthquake
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        result = await adapter.get_all(_make_filter())

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(eq, Earthquake) for eq in result)

    @pytest.mark.anyio
    async def test_get_all_maps_first_earthquake_correctly(self) -> None:
        """
        Given: a mock transport returning the fixture where the first feature
               has id="us7000abc1", mag=5.2, coordinates=[-122.1, 37.5, 10.0]
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the first Earthquake in the list has id="us7000abc1",
               magnitude=5.2, depth=10.0, latitude=37.5, longitude=-122.1
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        result = await adapter.get_all(_make_filter())

        first = result[0]
        assert first.id == "us7000abc1"
        assert first.magnitude == 5.2
        assert first.depth == 10.0
        assert first.latitude == 37.5
        assert first.longitude == -122.1

    @pytest.mark.anyio
    async def test_get_all_sends_format_geojson_param(self) -> None:
        """
        Given: a mock transport that captures the outbound request
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the outbound request URL contains format=geojson
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        await adapter.get_all(_make_filter())

        assert len(captured_requests) == 1
        params = dict(captured_requests[0].url.params)
        assert params.get("format") == "geojson"

    @pytest.mark.anyio
    async def test_get_all_sends_orderby_time_param(self) -> None:
        """
        Given: a mock transport that captures the outbound request
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the outbound request URL contains orderby=time
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        await adapter.get_all(_make_filter())

        params = dict(captured_requests[0].url.params)
        assert params.get("orderby") == "time"

    @pytest.mark.anyio
    async def test_get_all_sends_starttime_param(self) -> None:
        """
        Given: a mock transport that captures the outbound request,
               and filters.start_time = "2026-08-06"
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the outbound request URL contains starttime=2026-08-06
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        await adapter.get_all(_make_filter(start_time="2026-08-06"))

        params = dict(captured_requests[0].url.params)
        assert params.get("starttime") == "2026-08-06"

    @pytest.mark.anyio
    async def test_get_all_sends_endtime_param(self) -> None:
        """
        Given: a mock transport that captures the outbound request,
               and filters.end_time = "2026-08-13"
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the outbound request URL contains endtime=2026-08-13
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        await adapter.get_all(_make_filter(end_time="2026-08-13"))

        params = dict(captured_requests[0].url.params)
        assert params.get("endtime") == "2026-08-13"

    @pytest.mark.anyio
    async def test_get_all_sends_minmagnitude_param(self) -> None:
        """
        Given: a mock transport that captures the outbound request,
               and filters.min_magnitude = 4.0
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the outbound request URL contains minmagnitude=4.0 (or 4)
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        await adapter.get_all(_make_filter(min_magnitude=4.0))

        params = dict(captured_requests[0].url.params)
        assert "minmagnitude" in params
        assert float(params["minmagnitude"]) == 4.0

    @pytest.mark.anyio
    async def test_get_all_with_empty_features_returns_empty_list(self) -> None:
        """
        Given: a mock transport returning an empty USGS FeatureCollection
               (features: [])
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the result is an empty list []

        I/O Matrix row: USGS returns empty features
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        empty_response = {"type": "FeatureCollection", "features": [], "metadata": {"count": 0}}

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=empty_response)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        result = await adapter.get_all(_make_filter())

        assert result == []

    @pytest.mark.anyio
    async def test_get_all_sends_all_three_filter_params_together(self) -> None:
        """
        Given: a mock transport that captures the outbound request,
               and filters with starttime="2026-08-06", endtime="2026-08-13",
               minmagnitude=4.0
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the outbound request includes ALL of: format=geojson, orderby=time,
               starttime, endtime, minmagnitude
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        await adapter.get_all(
            _make_filter(
                start_time="2026-08-06",
                end_time="2026-08-13",
                min_magnitude=4.0,
            )
        )

        params = dict(captured_requests[0].url.params)
        assert params.get("format") == "geojson"
        assert params.get("orderby") == "time"
        assert params.get("starttime") == "2026-08-06"
        assert params.get("endtime") == "2026-08-13"
        assert float(params["minmagnitude"]) == 4.0

    @pytest.mark.anyio
    async def test_get_all_forwards_spatial_and_maxmagnitude_params(self) -> None:
        """
        Given: an EarthquakeFilter with latitude, longitude, max_radius_km, max_magnitude set
        When:  USGSAdapter.get_all(filters) is awaited
        Then:  the outbound request includes latitude, longitude, maxradiuskm, maxmagnitude

        I/O Matrix row: spatial/magnitude filter params forwarded to USGS
        """
        import httpx
        from dark_factory.domain.earthquake.value_objects import EarthquakeFilter
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        fixture = _load_fixture()
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=fixture)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        spatial_filter = EarthquakeFilter(
            start_time="2026-08-06",
            end_time="2026-08-13",
            min_magnitude=2.5,
            max_magnitude=5.9,
            latitude=37.5,
            longitude=-122.1,
            max_radius_km=25.0,
        )
        adapter = USGSAdapter(client=client)
        await adapter.get_all(spatial_filter)

        params = dict(captured_requests[0].url.params)
        assert float(params["latitude"]) == 37.5
        assert float(params["longitude"]) == -122.1
        assert float(params["maxradiuskm"]) == 25.0
        assert float(params["maxmagnitude"]) == 5.9


class TestUSGSAdapterGetById:
    """
    Given: a USGSAdapter wired with a MockTransport
    When:  get_by_id(event_id) is awaited
    Then:  the outbound request carries eventid and format=geojson params,
           the returned Earthquake has correct fields, and None is returned
           when features list is empty.
    """

    @pytest.mark.anyio
    async def test_get_by_id_sends_eventid_and_format_params(self) -> None:
        """
        Given: a mock transport that captures the outbound request
        When:  USGSAdapter.get_by_id("us7000abc1") is awaited
        Then:  the request URL contains eventid=us7000abc1 and format=geojson
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        single_feature_response = {
            "type": "FeatureCollection",
            "features": [_load_fixture()["features"][0]],
            "metadata": {"count": 1},
        }
        captured_requests: list[httpx.Request] = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json=single_feature_response)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        await adapter.get_by_id("us7000abc1")

        assert len(captured_requests) == 1
        params = dict(captured_requests[0].url.params)
        assert params.get("eventid") == "us7000abc1"
        assert params.get("format") == "geojson"

    @pytest.mark.anyio
    async def test_get_by_id_returns_earthquake_entity_with_correct_fields(self) -> None:
        """
        Given: a mock transport returning a single-feature GeoJSON with
               id="us7000abc1", mag=5.2, coordinates=[-122.1, 37.5, 10.0], time=1754956800000
        When:  USGSAdapter.get_by_id("us7000abc1") is awaited
        Then:  the returned Earthquake has id="us7000abc1", magnitude=5.2,
               depth=10.0, latitude=37.5, longitude=-122.1
        """
        import httpx
        from dark_factory.domain.earthquake.entities import Earthquake
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        single_feature_response = {
            "type": "FeatureCollection",
            "features": [_load_fixture()["features"][0]],
            "metadata": {"count": 1},
        }

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=single_feature_response)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        result = await adapter.get_by_id("us7000abc1")

        assert isinstance(result, Earthquake)
        assert result.id == "us7000abc1"
        assert result.magnitude == 5.2
        assert result.depth == 10.0
        assert result.latitude == 37.5
        assert result.longitude == -122.1

    @pytest.mark.anyio
    async def test_get_by_id_returns_none_when_features_empty(self) -> None:
        """
        Given: a mock transport returning an empty features list
        When:  USGSAdapter.get_by_id("unknown-id") is awaited
        Then:  the result is None
        """
        import httpx
        from dark_factory.infrastructure.usgs.adapter import USGSAdapter

        empty_response = {"type": "FeatureCollection", "features": [], "metadata": {"count": 0}}

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=empty_response)

        transport = httpx.MockTransport(handler=mock_handler)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="https://earthquake.usgs.gov/fdsnws/event/1/query",
        )

        adapter = USGSAdapter(client=client)
        result = await adapter.get_by_id("unknown-id-9999")

        assert result is None
