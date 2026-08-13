---
title: 'Dark Factory — USGS Earthquake Query Endpoint'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'fc45e86c66d76d5fc616461d623f9770c04660f2'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The infrastructure and interface layers are fully stubbed — `USGSClient`, `USGSMapper`, `USGSAdapter`, `EarthquakeFilterParams`, and the earthquake router all raise `NotImplementedError` or return placeholder data; no earthquake data reaches consumers.

**Approach:** Wire the complete data path across all four layers: implement `USGSClient.query()`, `USGSMapper.feature_to_earthquake()`, and `USGSAdapter.get_all()`; fix the DI to inject a live `USGSAdapter`; extend `EarthquakeFilterParams` with required `starttime`, `endtime`, and `minmagnitude` fields; update `GET /api/v1/earthquakes` to return a GeoJSON FeatureCollection. TDD: tests written and approved before implementation.

## Boundaries & Constraints

**Always:**
- Four-layer dependency rule (AD-2): `interface → application → domain`; `infrastructure` implements domain ports only.
- `USGSAdapter.get_all()` returns `List[Earthquake]`; no raw GeoJSON dict crosses the domain boundary (AD-5).
- `starttime`, `endtime`, and `minmagnitude` are required query params; missing any one returns HTTP 422.
- GeoJSON FeatureCollection is the unconditional response format (Accept-header negotiation is deferred per AD-6).
- `app.state.http_client` (lifespan-managed `httpx.AsyncClient`) is the only HTTP client injected into `USGSAdapter`.
- TDD mandate: write test files before implementation files in each phase.

**Ask First:**
- Any change to `Earthquake` domain entity fields or `EarthquakeRepository` ABC.

**Never:**
- Caching or persisting USGS responses (AD-8).
- Exposing USGS fields beyond `id`, `mag`, `depth`, `lat`, `lon`.
- Calling USGS directly from `application/` or `domain/`.
- Implementing `GET /api/v1/earthquakes/recent` or `GET /api/v1/earthquakes/{id}` (remain stubs).
- Depth, geographic bounds, or `limit` filters in this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `GET /api/v1/earthquakes?starttime=2026-08-06&endtime=2026-08-13&minmagnitude=4` | HTTP 200, `{"type":"FeatureCollection","features":[...]}` | N/A |
| Missing required param | Any one of `starttime`, `endtime`, `minmagnitude` absent | HTTP 422 Unprocessable Entity | FastAPI query-param validation |
| All params missing | `GET /api/v1/earthquakes` | HTTP 422 | FastAPI query-param validation |
| USGS returns empty features | USGS `features: []` | HTTP 200, `{"type":"FeatureCollection","features":[]}` | N/A |
| Mapper happy path | USGS feature dict with `id`, `properties.mag`, `geometry.coordinates[lon,lat,depth]` | `Earthquake(id, magnitude, depth, latitude, longitude)` all set correctly | N/A |

</frozen-after-approval>

## Code Map

- `src/dark_factory/infrastructure/usgs/client.py:10` — `USGSClient` — replace `fetch_earthquakes(params)` stub with `query(starttime, endtime, minmagnitude)` that builds USGS params and calls `await self._client.get("", params=...)`; `_client` is `httpx.AsyncClient` already set to `base_url=usgs_base_url`
- `src/dark_factory/infrastructure/usgs/mappers.py:15` — `USGSMapper.feature_to_earthquake(feature)` — implement mapping: `feature["id"]` → `id`; `feature["properties"]["mag"]` → `magnitude`; `feature["geometry"]["coordinates"][2]` → `depth`; `[0]` → `longitude`; `[1]` → `latitude`
- `src/dark_factory/infrastructure/usgs/adapter.py:18` — `USGSAdapter` — implement `get_all(filters)`: create `USGSClient(base_url="", client=self._client)`, call `.query(filters.start_time, filters.end_time, filters.min_magnitude)`, map each feature via `USGSMapper`, return `List[Earthquake]`
- `src/dark_factory/interface/http/dependencies.py:12` — `get_earthquake_repository()` — add `request: Request` param; return `USGSAdapter(client=request.app.state.http_client)` instead of `None`
- `src/dark_factory/interface/http/v1/schemas.py:30` — `EarthquakeFilterParams` — add `starttime: date`, `endtime: date`, `minmagnitude: float` as required fields; add `GeoJSONFeature` and `GeoJSONFeatureCollection` Pydantic schemas for response
- `src/dark_factory/interface/http/v1/earthquakes.py:15` — `list_earthquakes()` — inject `EarthquakeFilterParams = Depends()`, instantiate handler with repo dep, map params → `EarthquakeFilter`, await handler, return serialized `GeoJSONFeatureCollection`
- `src/dark_factory/domain/earthquake/value_objects.py:35` — `EarthquakeFilter` has `start_time: str|None`, `end_time: str|None`, `min_magnitude: float|None` — read-only; interface maps `EarthquakeFilterParams.starttime` → `EarthquakeFilter.start_time` (ISO string)
- `src/dark_factory/domain/earthquake/entities.py:12` — `Earthquake(id, magnitude, depth, latitude, longitude)` — read-only
- `src/dark_factory/main.py:23` — lifespan sets `app.state.http_client = httpx.AsyncClient(base_url=settings.usgs_base_url)` — read-only
- `src/dark_factory/config.py:22` — `usgs_base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"` — read-only
- `tests/conftest.py:46` — `async_client` fixture via `ASGITransport`; integration tests override DI with mocked adapter
- `tests/unit/infrastructure/` — new directory; mapper unit test + adapter unit test
- `tests/integration/interface/test_earthquakes.py` — new; endpoint integration test using recorded fixture

## Tasks & Acceptance

**Execution (TDD — Phase 1: tests first; Phase 2: implementation after approval):**

**Phase 1 — Tests (write before implementation):**
- [x] `tests/unit/infrastructure/__init__.py` -- create empty init -- pytest discovery
- [x] `tests/fixtures/usgs_response.json` -- create minimal valid USGS GeoJSON fixture (2 features) -- used by integration test to avoid live network calls
- [x] `tests/unit/infrastructure/test_mapper.py` -- unit test: `USGSMapper.feature_to_earthquake(sample_feature)` asserts all five fields map correctly -- red phase
- [x] `tests/unit/infrastructure/test_adapter.py` -- unit test: `USGSAdapter.get_all(filters)` with `httpx.MockTransport` asserts correct URL params and returns `List[Earthquake]` -- red phase
- [x] `tests/integration/interface/test_earthquakes.py` -- integration test: override DI to use mock USGS; `GET /earthquakes?starttime=...&endtime=...&minmagnitude=4` asserts HTTP 200, `type=="FeatureCollection"`, non-empty features; missing-param case asserts HTTP 422 -- red phase

**Phase 2 — Implementation (after human approves test contract):**
- [x] `src/dark_factory/infrastructure/usgs/client.py` -- implement `query(starttime, endtime, minmagnitude)` replacing stub; `params={"format":"geojson","starttime":str(starttime),"endtime":str(endtime),"minmagnitude":minmagnitude,"orderby":"time"}`; return `response.json()`
- [x] `src/dark_factory/infrastructure/usgs/mappers.py` -- implement `feature_to_earthquake(feature)`; extract all five fields from the feature dict; remove `NotImplementedError`
- [x] `src/dark_factory/infrastructure/usgs/adapter.py` -- implement `get_all(filters)`; guard against `None` filters; delegate to `USGSClient.query()`; map via `USGSMapper`; return `List[Earthquake]`
- [x] `src/dark_factory/interface/http/dependencies.py` -- implement `get_earthquake_repository(request: Request) -> USGSAdapter`; import `Request` from fastapi
- [x] `src/dark_factory/interface/http/v1/schemas.py` -- add `starttime: date`, `endtime: date`, `minmagnitude: float` to `EarthquakeFilterParams`; add `GeoJSONFeature` and `GeoJSONFeatureCollection` response models
- [x] `src/dark_factory/interface/http/v1/earthquakes.py` -- implement `list_earthquakes()`: accept `EarthquakeFilterParams = Depends()`, inject repo dep, build `EarthquakeFilter`, call `GetEarthquakesHandler`, return `GeoJSONFeatureCollection`

**Acceptance Criteria:**
- Given all three params present, when `GET /api/v1/earthquakes?starttime=2026-08-06&endtime=2026-08-13&minmagnitude=4`, then HTTP 200 with `{"type":"FeatureCollection","features":[...]}`
- Given any required param missing, when `GET /api/v1/earthquakes`, then HTTP 422
- Given a sample USGS feature, when `USGSMapper.feature_to_earthquake(feature)`, then returns correct `Earthquake` with all five fields
- Given a mocked USGS transport, when `USGSAdapter.get_all(filters)`, then the outbound request includes `format=geojson`, `orderby=time`, and the three filter values
- Given any request, when `get_earthquake_repository(request)`, then returns a `USGSAdapter` instance (not `None`)
- Given a list of `Earthquake` entities, when serialized, then each is a GeoJSON `Feature` with `Point` geometry `[lon, lat, depth]` and `mag` in `properties`
- Given all code changes, when `uv run ruff check src/` and `uv run mypy src/`, then 0 violations

## Spec Change Log

## Design Notes

**GeoJSON FeatureCollection shape (router output):**
```python
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [eq.longitude, eq.latitude, eq.depth]},
            "properties": {"id": eq.id, "mag": eq.magnitude},
        }
        for eq in earthquakes
    ],
}
```

**USGS httpx call (USGSClient.query):**
```python
response = await self._client.get("", params={
    "format": "geojson", "starttime": str(starttime),
    "endtime": str(endtime), "minmagnitude": minmagnitude, "orderby": "time",
})
return response.json()
```

**DI wiring (dependencies.py):**
```python
from fastapi import Request
def get_earthquake_repository(request: Request) -> USGSAdapter:
    return USGSAdapter(client=request.app.state.http_client)
```

## Verification

**Commands:**
- `uv run pytest tests/unit/infrastructure/ -v` -- expected: all mapper and adapter unit tests pass
- `uv run pytest tests/integration/interface/test_earthquakes.py -v` -- expected: endpoint test passes
- `uv run pytest -q` -- expected: 0 failures, no regressions
- `uv run ruff check src/` -- expected: no violations
- `uv run mypy src/` -- expected: no errors

## Suggested Review Order

**Entry point — HTTP interface**

- Router: `list_earthquakes()` wires params → filter → handler → GeoJSON response
  [`earthquakes.py:28`](../../../src/dark_factory/interface/http/v1/earthquakes.py#L28)

- Schemas: required query params and GeoJSON response models added here
  [`schemas.py:32`](../../../src/dark_factory/interface/http/v1/schemas.py#L32)

**DI wiring**

- DI: `get_earthquake_repository` now returns live `USGSAdapter` via `app.state`
  [`dependencies.py:12`](../../../src/dark_factory/interface/http/dependencies.py#L12)

**Infrastructure — data path**

- Adapter: `get_all` delegates to `USGSClient`, maps features → domain entities
  [`adapter.py:22`](../../../src/dark_factory/infrastructure/usgs/adapter.py#L22)

- Client: `query` builds USGS params (`format`, `orderby`, three filters) and returns raw JSON
  [`client.py:17`](../../../src/dark_factory/infrastructure/usgs/client.py#L17)

- Mapper: `feature_to_earthquake` extracts all five fields with explicit type guards
  [`mappers.py:14`](../../../src/dark_factory/infrastructure/usgs/mappers.py#L14)

**Tests**

- Integration: happy path 200 + FeatureCollection shape; missing-param 422
  [`test_earthquakes.py:1`](../../../tests/integration/interface/test_earthquakes.py#L1)

- Adapter unit: `MockTransport` asserts correct outbound USGS query params
  [`test_adapter.py:1`](../../../tests/unit/infrastructure/test_adapter.py#L1)

- Mapper unit: verifies all five field mappings from raw feature dict
  [`test_mapper.py:1`](../../../tests/unit/infrastructure/test_mapper.py#L1)

- Fixture: minimal 2-feature USGS GeoJSON used by integration + adapter tests
  [`usgs_response.json:1`](../../../tests/fixtures/usgs_response.json#L1)
