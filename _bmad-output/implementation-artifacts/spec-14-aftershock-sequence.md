---
title: 'Aftershock Sequence Detection Endpoint'
type: 'feature'
created: '2026-08-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      JSONDecodeError from response.json() is unhandled across the USGS client
    evidence: |-
      Pre-existing pattern in client.py (query method also unguarded). If USGS
      returns non-JSON, this propagates as an unhandled 500.
    location: >-
      src/dark_factory/infrastructure/usgs/client.py
    severity: low
  - summary: >-
      httpx.ConnectError and TimeoutException not caught, surface as 500
    evidence: |-
      Pre-existing pattern in the existing GET /earthquakes endpoint. Network-level
      failures should ideally return 502 to API consumers.
    location: >-
      src/dark_factory/interface/http/v1/earthquakes.py
    severity: medium
  - summary: >-
      sequence_assessment field typed as bare str; Literal or Enum would be safer
    evidence: |-
      AftershockResult.sequence_assessment accepts any string. Using
      Literal["decaying","active","insufficient_data"] would prevent invalid states.
    location: >-
      src/dark_factory/domain/earthquake/entities.py
    severity: low
  - summary: >-
      avg_magnitude not rounded; floating-point accumulation visible in API response
    evidence: |-
      sum(eq.magnitude for eq in aftershocks) / count can produce values like
      4.199999999999999. Spec does not specify rounding precision.
    location: >-
      src/dark_factory/application/earthquake/handlers.py
    severity: low
baseline_revision: 'df9143a7077c594e59d53be93ae4e6adf915ec6d'
---

<intent-contract>

## Intent

**Problem:** The API can list and retrieve individual earthquakes but provides no analytical layer. Consumers cannot determine whether a given event is a mainshock driving an ongoing aftershock sequence.

**Approach:** Implement `GET /api/v1/earthquakes/{earthquake_id}/aftershocks` end-to-end across all four clean-architecture layers: add `time` to the `Earthquake` entity, implement the two stubbed USGS methods, add a new `GetAftershocksHandler` that orchestrates the two-call sequence, and wire the route with a structured `AftershockResponse`.

## Boundaries & Constraints

**Always:**
- `Earthquake.time` is `str` (ISO-8601, e.g. `"2024-03-01T12:00:00Z"`). No `datetime` in the entity — ms-to-ISO conversion lives in the mapper (infrastructure).
- Domain layer (`domain/`) keeps zero external imports (stdlib only). `AftershockResult` and `EarthquakeNotFound` are both stdlib-only.
- Repository stays thin: no `get_aftershocks` method added to the port. All orchestration lives in `GetAftershocksHandler`.
- `EarthquakeFilter` source is `value_objects.py`; `filters.py` is a re-export shim — never edit `filters.py`.
- Wells–Coppersmith radius: `radius_km = 10 ** (0.5 * main.magnitude - 1.8)`.
- Sequence assessment: split the `[main_time, main_time + days]` window at its midpoint. Count aftershocks with time < midpoint (first half) and time ≥ midpoint (second half). `< 3` total → `"insufficient_data"`. `second_half_count < first_half_count` → `"decaying"`. Otherwise → `"active"`.
- TDD: tests written before implementation. They must fail (`FAILED`) before implementation, not `ERROR`.
- Quality gate: `uv run pytest tests/ -q` + `uv run ruff check .` + `uv run mypy src/` — all must pass with 0 failures/violations.

**Block If:**
- Any test that previously passed begins failing due to a change made here, and the failure is not directly caused by an intentional breakage (e.g. `test_earthquake_is_dataclass` checking 5 fields) — HALT with `blocking condition: regression`.

**Never:**
- Add `get_aftershocks` to `EarthquakeRepository` ABC.
- Import `httpx` in `domain/` or `application/` layers.
- Add `time` to the `GeoJSONFeatureProperties` response schema (that schema stays `{id, mag}`).
- Cache responses.
- Edit `filters.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path — decaying | Valid event ID, repo returns 4 aftershocks: 3 in first half, 1 in second | 200, `sequence_assessment="decaying"`, `count=4` | No error |
| Happy path — active | Valid event ID, repo returns 4 aftershocks: 1 in first half, 3 in second | 200, `sequence_assessment="active"`, `count=4` | No error |
| Insufficient data | Valid event ID, repo returns < 3 aftershocks | 200, `sequence_assessment="insufficient_data"` | No error |
| Zero aftershocks | Valid event ID, repo returns 0 aftershocks | 200, `sequence_assessment="insufficient_data"`, `count=0`, stats fields all `null` | No error |
| Main event not found | Unknown event ID | HTTP 404 | `EarthquakeNotFound` caught at router |
| USGS error on main event fetch | USGS returns non-404 HTTP error | HTTP 502 | `httpx.HTTPStatusError` caught at router |
| `days` out of range | `days=0` or `days=91` | HTTP 422 | FastAPI validation |
| Default `days` | No `days` param | Same as `days=30` | No error |

</intent-contract>

## Code Map

- `src/dark_factory/domain/earthquake/entities.py:8` — `Earthquake` dataclass; add `time: str = ""` at end; add `AftershockResult` dataclass below it
- `src/dark_factory/domain/earthquake/exceptions.py` — **NEW**: `EarthquakeNotFound(Exception)` with `event_id: str`
- `src/dark_factory/domain/earthquake/value_objects.py:28` — `EarthquakeFilter`; add `latitude: float | None = None`, `longitude: float | None = None`, `max_radius_km: float | None = None` (`max_magnitude` already exists at line 30)
- `src/dark_factory/infrastructure/usgs/mappers.py:18` — `feature_to_earthquake`: add `from datetime import datetime, timezone` at top; extract `properties.get("time")`, convert ms-epoch → ISO-8601 string, store in `Earthquake.time`
- `src/dark_factory/infrastructure/usgs/client.py:14` — `USGSClient.query`: add optional kwargs `latitude`, `longitude`, `maxradiuskm`, `maxmagnitude`; conditionally add to `params` dict only when not None
- `src/dark_factory/infrastructure/usgs/client.py:30` — `fetch_earthquake_by_id`: implement with `GET query?format=geojson&eventid={event_id}`; return `features[0]` or `None` if empty
- `src/dark_factory/infrastructure/usgs/adapter.py:25` — `get_all`: thread `filters.latitude`, `filters.longitude`, `filters.max_radius_km`, `filters.max_magnitude` through to `USGSClient.query`
- `src/dark_factory/infrastructure/usgs/adapter.py:35` — `get_by_id`: call `usgs_client.fetch_earthquake_by_id`; return `USGSMapper.feature_to_earthquake(feature)` or `None`; let non-404 `httpx.HTTPStatusError` propagate
- `src/dark_factory/application/earthquake/queries.py` — add `GetAftershocks(earthquake_id: str, days: int = 30)` dataclass
- `src/dark_factory/application/earthquake/handlers.py` — add `GetAftershocksHandler`; imports: `EarthquakeNotFound` from domain exceptions, `EarthquakeFilter` from value_objects, `AftershockResult` from entities, `datetime/timedelta/timezone` from stdlib
- `src/dark_factory/interface/http/v1/schemas.py` — add `AftershockMainEvent`, `AftershockStats`, `AftershockResponse` Pydantic models
- `src/dark_factory/interface/http/v1/earthquakes.py` — add `GET /{earthquake_id}/aftershocks` route; import `GetAftershocks`, `GetAftershocksHandler`, `EarthquakeNotFound`, `httpx`; catch exceptions; route must be defined AFTER the `/{earthquake_id}` stub route
- `tests/unit/domain/test_entities.py:42` — update `test_earthquake_is_dataclass` to expect `{"id", "magnitude", "depth", "latitude", "longitude", "time"}` (6 fields); add tests for `AftershockResult` and `EarthquakeNotFound`
- `tests/unit/infrastructure/test_mapper.py:105` — add `"time": 1709294400000` to `SAMPLE_FEATURE["properties"]`; add test `test_time_field_maps_to_iso8601`; update `test_all_five_fields_mapped_correctly_in_one_assertion` to include `time`
- `tests/unit/application/test_aftershock_handlers.py` — **NEW**: 4 handler unit tests (decaying, active, insufficient_data, not-found)
- `tests/integration/interface/test_earthquakes.py:673` — update `_make_sample_earthquakes()` to pass `time="2025-08-11T16:00:00Z"` and `time="2025-08-10T16:00:00Z"`; add `TestAftershocksEndpoint` class with 4 integration tests

## Tasks & Acceptance

**Execution (TDD order: tests first, then implementation):**

1. `tests/unit/domain/test_entities.py` -- UPDATE `test_earthquake_is_dataclass` to expect 6 fields including `time`; ADD `test_earthquake_time_field_defaults_to_empty_string`; ADD `test_aftershock_result_is_importable`; ADD `test_earthquake_not_found_exception_carries_event_id` -- establishes red for domain changes

2. `tests/unit/infrastructure/test_mapper.py` -- ADD `"time": 1709294400000` to `SAMPLE_FEATURE["properties"]`; ADD `test_time_field_maps_to_iso8601` asserting result is `"2024-03-01T12:00:00Z"`; UPDATE `test_all_five_fields_mapped_correctly_in_one_assertion` to include `time="2024-03-01T12:00:00Z"` in expected `Earthquake` -- establishes red for mapper change

3. `tests/unit/application/test_aftershock_handlers.py` -- NEW FILE: 4 handler tests using inline fake repo; import `GetAftershocksHandler`, `GetAftershocks`, `EarthquakeNotFound`, `Earthquake`, `AftershockResult` -- establishes red for handler

4. `tests/integration/interface/test_earthquakes.py` -- UPDATE `_make_sample_earthquakes()` to include `time` kwarg; ADD `TestAftershocksEndpoint` with: `test_aftershocks_returns_200_with_valid_id`, `test_aftershocks_returns_404_for_unknown_id`, `test_aftershocks_returns_422_for_days_out_of_range`, `test_aftershocks_response_has_required_fields` -- establishes red for route

5. `src/dark_factory/domain/earthquake/entities.py` -- ADD `time: str = ""` to `Earthquake`; ADD `AftershockResult` dataclass with fields: `main_event: Earthquake`, `aftershocks: list[Earthquake]`, `count: int`, `max_magnitude: float | None`, `avg_magnitude: float | None`, `largest_aftershock_id: str | None`, `sequence_assessment: str`

6. `src/dark_factory/domain/earthquake/exceptions.py` -- NEW: `class EarthquakeNotFound(Exception)` with `__init__(self, event_id: str)`

7. `src/dark_factory/domain/earthquake/value_objects.py` -- ADD `latitude: float | None = None`, `longitude: float | None = None`, `max_radius_km: float | None = None` to `EarthquakeFilter` (after existing fields; `max_magnitude` already exists)

8. `src/dark_factory/infrastructure/usgs/mappers.py` -- ADD `from datetime import datetime, timezone` import; EXTRACT `time_ms = properties.get("time")`; CONVERT to ISO-8601: `datetime.fromtimestamp(int(time_ms) / 1000, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')` if present else `""`; PASS `time=time_str` to `Earthquake()`

9. `src/dark_factory/infrastructure/usgs/client.py` -- EXTEND `query()` signature with optional `latitude: float | None = None`, `longitude: float | None = None`, `maxradiuskm: float | None = None`, `maxmagnitude: float | None = None`; add each to `params` dict only when `is not None`; IMPLEMENT `fetch_earthquake_by_id`: `GET query?format=geojson&eventid={event_id}`, return `features[0]` or `None`

10. `src/dark_factory/infrastructure/usgs/adapter.py` -- EXTEND `get_all` to pass `latitude`, `longitude`, `maxradiuskm`, `maxmagnitude` from filter to `usgs_client.query`; IMPLEMENT `get_by_id`: create `USGSClient`, call `fetch_earthquake_by_id`, map via `USGSMapper`, return `None` on `None` result, let non-404 HTTP errors propagate

11. `src/dark_factory/application/earthquake/queries.py` -- ADD `@dataclass class GetAftershocks: earthquake_id: str; days: int = 30`

12. `src/dark_factory/application/earthquake/handlers.py` -- ADD `GetAftershocksHandler.handle(query: GetAftershocks) -> AftershockResult`; logic: call `repo.get_by_id` → raise `EarthquakeNotFound` if None; compute `radius_km`, `end_dt`, `mid_dt`; build `EarthquakeFilter` with `start_time=main.time`, `end_time`, `min_magnitude=main.magnitude-3.0`, `max_magnitude=main.magnitude-0.1`, `latitude`, `longitude`, `max_radius_km=radius_km`; call `repo.get_all`; split by midpoint; compute stats; return `AftershockResult`

13. `src/dark_factory/interface/http/v1/schemas.py` -- ADD `AftershockMainEvent(BaseModel)` with `id, magnitude, depth, latitude, longitude, time: str`; ADD `AftershockStats(BaseModel)` with `count: int, max_magnitude: float | None, avg_magnitude: float | None, largest_aftershock_id: str | None`; ADD `AftershockResponse(BaseModel)` with `main_event: AftershockMainEvent, aftershocks: list[EarthquakeResponse], stats: AftershockStats, sequence_assessment: str`

14. `src/dark_factory/interface/http/v1/earthquakes.py` -- ADD `GET /{earthquake_id}/aftershocks` route: import `Query` from fastapi, `GetAftershocks/GetAftershocksHandler` from application, `EarthquakeNotFound` from domain exceptions, `httpx` for 502; handle `EarthquakeNotFound` → HTTP 404, `httpx.HTTPStatusError` → HTTP 502; build `AftershockResponse` from `AftershockResult`

**Acceptance Criteria:**
- Given a valid USGS event ID and at least 3 aftershocks where first-half rate > second-half rate, when `GET /aftershocks`, then response has `sequence_assessment="decaying"` and correct `count`
- Given a valid event ID and fewer than 3 aftershocks, when `GET /aftershocks`, then `sequence_assessment="insufficient_data"` and `stats.count < 3`
- Given an unknown event ID, when `GET /aftershocks`, then HTTP 404
- Given `days=91`, when `GET /aftershocks`, then HTTP 422
- Given a valid event ID, when `GET /aftershocks?days=30`, then response body contains `main_event`, `aftershocks`, `stats`, `sequence_assessment` fields
- Given the updated `Earthquake` entity, when `uv run pytest tests/unit/domain/ -q`, then 0 failures
- Given `uv run pytest tests/ -q && uv run ruff check . && uv run mypy src/`, then 0 failures and 0 violations

## Design Notes

**time conversion:** USGS `properties.time` is a millisecond-since-epoch integer. Conversion in mapper (infrastructure, can use stdlib datetime):
```python
from datetime import datetime, timezone
time_ms = properties.get("time")
time_str = (
    datetime.fromtimestamp(int(time_ms) / 1000, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if time_ms is not None else ""
)
```

**Handler half-window split:**
```python
from datetime import datetime, timedelta, timezone
main_dt = datetime.fromisoformat(main.time.replace('Z', '+00:00'))
end_dt = main_dt + timedelta(days=query.days)
mid_dt = main_dt + timedelta(days=query.days / 2)
start_time_str = main_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
end_time_str = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
first_half = [eq for eq in aftershocks if datetime.fromisoformat(eq.time.replace('Z', '+00:00')) < mid_dt]
second_half = [eq for eq in aftershocks if datetime.fromisoformat(eq.time.replace('Z', '+00:00')) >= mid_dt]
```

**Route exception handling pattern:**
```python
from fastapi import HTTPException
import httpx
from dark_factory.domain.earthquake.exceptions import EarthquakeNotFound
try:
    result = await handler.handle(query)
except EarthquakeNotFound:
    raise HTTPException(status_code=404, detail="Earthquake not found")
except httpx.HTTPStatusError as exc:
    raise HTTPException(status_code=502, detail=f"USGS upstream error: {exc.response.status_code}")
```

**USGSAdapter.get_by_id — USGSClient construction:** The adapter currently instantiates `USGSClient(base_url="", client=self._client)`. The actual base_url is configured on the httpx.AsyncClient at app startup (`settings.usgs_base_url`). Keep this pattern for `get_by_id` too.

## Verification

**Commands:**
- `uv run pytest tests/unit/domain/test_entities.py -v` -- expected: all entity tests pass, including new `time` field tests
- `uv run pytest tests/unit/infrastructure/test_mapper.py -v` -- expected: all mapper tests pass, including `test_time_field_maps_to_iso8601`
- `uv run pytest tests/unit/application/test_aftershock_handlers.py -v` -- expected: all 4 handler tests pass
- `uv run pytest tests/ -q` -- expected: 0 failures, 0 errors
- `uv run ruff check .` -- expected: 0 violations
- `uv run mypy src/` -- expected: 0 errors

## Auto Run Result

**Summary:** Full aftershock sequence detection feature implemented end-to-end across all four clean-architecture layers. The existing `get_by_id` and `fetch_earthquake_by_id` stubs were implemented; `Earthquake.time` was added to the domain entity; a new `GetAftershocksHandler` orchestrates the two-call sequence with Wells–Coppersmith radius and half-window sequence assessment; a new `GET /api/v1/earthquakes/{id}/aftershocks` endpoint was wired with full error handling.

**Files changed:**
- `src/dark_factory/domain/earthquake/entities.py` — added `time: str = ""` to `Earthquake`; added `AftershockResult` dataclass
- `src/dark_factory/domain/earthquake/exceptions.py` — new `EarthquakeNotFound` domain exception
- `src/dark_factory/domain/earthquake/value_objects.py` — added `latitude`, `longitude`, `max_radius_km` to `EarthquakeFilter`
- `src/dark_factory/infrastructure/usgs/mappers.py` — maps `properties.time` ms-epoch to ISO-8601 string
- `src/dark_factory/infrastructure/usgs/client.py` — extended `query()` with geo/mag params; implemented `fetch_earthquake_by_id`
- `src/dark_factory/infrastructure/usgs/adapter.py` — threads new filter fields through `get_all`; implements `get_by_id`
- `src/dark_factory/application/earthquake/queries.py` — added `GetAftershocks` dataclass
- `src/dark_factory/application/earthquake/handlers.py` — added `GetAftershocksHandler` with Wells–Coppersmith, half-window assessment, empty-time guards, min_magnitude clamp
- `src/dark_factory/interface/http/v1/schemas.py` — added `AftershockMainEvent`, `AftershockStats`, `AftershockResponse`
- `src/dark_factory/interface/http/v1/earthquakes.py` — added `GET /{earthquake_id}/aftershocks` route with 404/422/502 handling
- `tests/unit/domain/test_entities.py` — updated field-count assertion; added time/AftershockResult/EarthquakeNotFound tests
- `tests/unit/infrastructure/test_mapper.py` — added time to SAMPLE_FEATURE; added time mapping test
- `tests/unit/application/test_aftershock_handlers.py` — new file with 4 handler scenarios
- `tests/unit/infrastructure/test_adapter.py` — added spatial param test; added TestUSGSAdapterGetById (3 tests)
- `tests/integration/interface/test_earthquakes.py` — updated sample factories; added TestAftershocksEndpoint (5 scenarios)

**Review findings:** 6 patches applied (0 high, 4 medium, 2 low). 4 items deferred. 8 rejected as noise or false positives.

**Follow-up review recommended:** true (3×4 + 1×2 = 14 ≥ 5)

**Verification:**
- `uv run pytest tests/ -q` → 163 passed, 0 failures
- `uv run ruff check .` → All checks passed
- `uv run mypy src/` → Success: no issues found in 25 source files

**Residual risks:** Four deferred items: unhandled `JSONDecodeError` (pre-existing, low), `ConnectError`/`TimeoutException` surface as 500 (pre-existing, medium), `sequence_assessment` lacks `Literal` type constraint (low), `avg_magnitude` not rounded (low).

## Spec Change Log

## Review Triage Log

### 2026-08-18 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 4, low 2)
- defer: 4: (high 0, medium 1, low 3)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` Empty `main.time` guard: added `if not main.time: raise EarthquakeNotFound` before fromisoformat call (handlers.py)
  - `[medium]` `[patch]` Empty `eq.time` guard: filter aftershocks with empty time before half-window split to prevent ValueError (handlers.py)
  - `[medium]` `[patch]` USGSAdapter.get_by_id / USGSClient.fetch_earthquake_by_id untested at infra layer: added TestUSGSAdapterGetById class with 3 tests (eventid param, correct entity fields, None on empty features) in test_adapter.py
  - `[medium]` `[patch]` Spatial/magnitude params untested in adapter: added test_get_all_forwards_spatial_and_maxmagnitude_params to test_adapter.py
  - `[low]` `[patch]` min_magnitude can go negative for small mainshocks: clamped with max(0.0, ...) (handlers.py)
  - `[low]` `[patch]` Integration test only checked sequence_assessment key presence, not value: added assert body["sequence_assessment"] == "decaying" to test_aftershocks_response_has_required_fields
