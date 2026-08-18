---
id: SPEC-earthquake-aftershocks
companions: []
sources: []
---

> **Canonical contract.** This SPEC and its companions are the complete contract for what to build, test, and validate.
> Always verify alignment with the Product Brief and Architecture documents before implementation begins.

# Dark Factory — Aftershock Sequence Detection

## Description

Given a USGS earthquake event ID, detect its probable aftershock sequence: fetch the main event, compute a seismological search radius, query USGS for subsequent events within that radius, and return the aftershock list with statistics and a sequence activity assessment.

## What / Why

**What:** New endpoint `GET /api/v1/earthquakes/{earthquake_id}/aftershocks` that orchestrates two USGS calls — one to fetch the main event (implementing the existing stubs), one to retrieve events within the Wells–Coppersmith radius — and returns a structured response with stats and `sequence_assessment`.

**Why:** The list endpoint surfaces raw earthquake data, but gives no insight into whether a given event is part of an ongoing sequence. Aftershock detection is the first analytical layer on top of the proxy and unlocks meaningful use of the API for seismological monitoring.

## Capabilities

### CAP-1 — `Earthquake` entity gains `time` field

**Intent:** Add a `time` field (ISO-8601 string, e.g. `"2024-03-01T12:00:00Z"`) to the `Earthquake` domain entity so the application layer can split aftershocks by time window without external dependencies.

**Success:** `Earthquake.time` exists as an `str` field. `USGSMapper.feature_to_earthquake` populates it by converting the USGS `properties.time` millisecond-epoch integer to ISO-8601. All existing mapper and entity tests pass.

### CAP-2 — `EarthquakeFilter` extended with radius and magnitude-upper-bound fields

**Intent:** Add four optional fields to `EarthquakeFilter` — `latitude`, `longitude`, `max_radius_km`, `max_magnitude` — and thread them through `USGSClient.query` as `latitude`, `longitude`, `maxradiuskm`, `maxmagnitude` params.

**Success:** A filter with all four fields set causes `USGSClient.query` to include those params in the outbound USGS request. Existing calls without these fields are unaffected. `uv run mypy src/` reports 0 violations.

### CAP-3 — `GetAftershocksHandler` and `GetAftershocks` query in application layer

**Intent:** New `GetAftershocks` query dataclass (`earthquake_id: str`, `days: int = 30`) and `GetAftershocksHandler` that: (1) calls `repo.get_by_id(earthquake_id)` — raises `EarthquakeNotFound` if `None`; (2) computes `radius_km = 10 ** (0.5 * main.magnitude - 1.8)` and the time window `[main.time, main.time + days]`; (3) calls `repo.get_all(EarthquakeFilter(...))` with radius, magnitude bounds `[main_mag - 3.0, main_mag - 0.1]`, and time bounds; (4) computes `sequence_assessment`; (5) returns an `AftershockResult`.

**Success:** Unit tests pass for decaying sequence, active sequence, fewer than 3 aftershocks (`"insufficient_data"`), and main event not found. No direct infrastructure imports in the handler.

### CAP-4 — `AftershockResult` value object in domain layer

**Intent:** New stdlib dataclass `AftershockResult` in `domain/earthquake/` with fields: `main_event: Earthquake`, `aftershocks: list[Earthquake]`, `count: int`, `max_magnitude: float | None`, `avg_magnitude: float | None`, `largest_aftershock_id: str | None`, `sequence_assessment: str`.

**Success:** `AftershockResult` is importable from the domain layer with zero external dependencies. All fields are populated correctly by `GetAftershocksHandler` in tests.

### CAP-5 — `USGSClient.fetch_earthquake_by_id` and `USGSAdapter.get_by_id` implemented

**Intent:** Implement both stubs. `USGSClient.fetch_earthquake_by_id(event_id)` calls `GET /query?format=geojson&eventid={event_id}` and returns the first feature dict; returns `None` if the response `features` list is empty. `USGSAdapter.get_by_id(earthquake_id)` calls the client method and maps via `USGSMapper.feature_to_earthquake`, returning `None` when the client returns `None`.

**Success:** `USGSAdapter.get_by_id` returns an `Earthquake` entity (with `time` populated) for a valid USGS event ID and `None` for an unknown ID. USGS non-404 HTTP errors propagate as `httpx.HTTPStatusError`. `spec-earthquake-by-id` CAP-2 and CAP-3 acceptance criteria are satisfied by this implementation.

### CAP-6 — `GET /api/v1/earthquakes/{earthquake_id}/aftershocks` endpoint

**Intent:** New FastAPI route accepting `days: int = Query(30, ge=1, le=90)`. On success returns `AftershockResponse` (see schema details in `response-schema.md`). Returns HTTP 404 when `EarthquakeNotFound` is raised. Returns HTTP 502 when USGS raises a non-404 HTTP error fetching the main event.

**Success:** `GET /api/v1/earthquakes/us6000tjl2/aftershocks` returns HTTP 200 with correct `AftershockResponse` shape. Unknown ID returns HTTP 404. `days=91` returns HTTP 422. All existing endpoint tests pass.

### CAP-7 — `AftershockResponse` Pydantic schema

**Intent:** New response schema in `interface/http/v1/schemas.py` with fields: `main_event` (id, magnitude, depth, latitude, longitude, time), `aftershocks` (list of `EarthquakeResponse`-shaped items), `stats` (count, max_magnitude, avg_magnitude, largest_aftershock_id), `sequence_assessment: str`.

**Success:** Schema validates and serializes correctly for all three `sequence_assessment` values. `EarthquakeResponse` either gains `time` or a new `AftershockEarthquakeResponse` schema is used — both approaches satisfy this capability.

### CAP-8 — Unit tests for `GetAftershocksHandler`

**Intent:** Four unit tests in `tests/unit/application/test_aftershock_handlers.py` using an inline fake repository: (1) decaying sequence (second half rate < first half), (2) active sequence (second half rate ≥ first half), (3) insufficient data (< 3 aftershocks → `"insufficient_data"`), (4) main event not found (raises `EarthquakeNotFound`). Follow the existing `test_handlers.py` pattern.

**Success:** All four tests pass with `uv run pytest tests/unit/application/test_aftershock_handlers.py -q`. No live network calls.

## Constraints

- **`Earthquake.time` conflict with spec-earthquake-by-id:** That spec's constraints explicitly exclude `time`; this spec requires it. The implementing developer must update `spec-earthquake-by-id`'s non-goals to remove the `time` exclusion, or document this as a deliberate supersession. This must be resolved before closing the GitHub issue. *(See open question OQ-1.)*
- **Domain purity (AD-2):** `Earthquake.time` is a plain `str` (ISO-8601). No `datetime` import in the entity. Conversion from ms-epoch lives in the mapper (infrastructure), not the entity or domain layer.
- **Thin repository port:** No `get_aftershocks` method on `EarthquakeRepository`. All orchestration lives in `GetAftershocksHandler`.
- **`sequence_assessment` algorithm:** Split the `days` window at its midpoint. Count aftershocks in `[main_time, midpoint)` (first half) and `[midpoint, end_time]` (second half). If total count < 3 → `"insufficient_data"`. If `second_half_count < first_half_count` → `"decaying"`. Otherwise → `"active"`.
- **`EarthquakeFilter` source file:** Extend `value_objects.py`, not `filters.py` (which is a re-export shim).
- **AD-8 stateless:** No caching. Each request to the aftershocks endpoint makes two outbound USGS calls.
- **AD-4 TDD:** Tests are written before or alongside implementation files.

## Non-goals

- Implementing `GET /api/v1/earthquakes/recent` — separate stub, separate spec.
- Caching aftershock results or the main event lookup.
- Foreshock detection or bi-directional sequence analysis.
- Machine-learning-based sequence classification (the `sequence_assessment` enum is a simple count-ratio heuristic).
- Additional USGS event fields beyond `id`, `magnitude`, `depth`, `latitude`, `longitude`, `time`.
- Paginating the aftershock result set.

## Success Signal

`GET /api/v1/earthquakes/us6000tjl2/aftershocks` returns HTTP 200 with `sequence_assessment` as one of `"decaying"`, `"active"`, or `"insufficient_data"`, a populated `main_event` object, and a valid `stats` block. Unknown earthquake ID returns HTTP 404. `days=91` returns HTTP 422. `uv run pytest -q` reports 0 failures and 0 regressions. `uv run ruff check src/` and `uv run mypy src/` report 0 violations.

## Acceptance Criteria

- [ ] `Earthquake` entity has a `time: str` field; `USGSMapper` populates it from `properties.time` (ms-epoch → ISO-8601).
- [ ] `EarthquakeFilter` has `latitude`, `longitude`, `max_radius_km`, `max_magnitude` optional fields; `USGSClient.query` forwards them to USGS.
- [ ] `USGSClient.fetch_earthquake_by_id(event_id)` sends `eventid=<id>&format=geojson` and returns the feature dict or `None` when features list is empty.
- [ ] `USGSAdapter.get_by_id(earthquake_id)` returns a fully populated `Earthquake` (including `time`) or `None` on USGS 404.
- [ ] `GetAftershocksHandler` computes `radius_km = 10 ** (0.5 * main.magnitude - 1.8)`.
- [ ] `GetAftershocksHandler` calls `repo.get_all` with correct `start_time`, `end_time`, `latitude`, `longitude`, `max_radius_km`, `min_magnitude`, `max_magnitude` derived from the main event.
- [ ] `sequence_assessment` is `"decaying"` when second-half event count < first-half, `"active"` when ≥, and `"insufficient_data"` when total < 3.
- [ ] `GET /api/v1/earthquakes/{earthquake_id}/aftershocks` returns HTTP 200 with `AftershockResponse` on success.
- [ ] Returns HTTP 404 when the main event is not found; HTTP 502 on USGS upstream error; HTTP 422 when `days` is out of range.
- [ ] Unit tests cover all four `GetAftershocksHandler` scenarios (decaying, active, insufficient_data, not-found).
- [ ] `uv run pytest -q` passes with 0 failures; `uv run ruff check src/` and `uv run mypy src/` report 0 violations.
- [ ] `spec-earthquake-by-id` conflict on `Earthquake.time` resolved and documented.

## Definition of Ready

- [ ] Aligned with Architecture decisions (AD-2, AD-4, AD-5, AD-8)
- [ ] Acceptance Criteria are clear and testable
- [ ] `spec-earthquake-by-id` conflict on `Earthquake.time` acknowledged (OQ-1)
- [ ] GitHub issue created and linked

## Definition of Done

- [ ] All Acceptance Criteria met and verified
- [ ] Unit and integration tests written and passing
- [ ] Code reviewed and PR approved
- [ ] Merged to `main` and deployed successfully
- [ ] No regressions introduced

---

## Open Questions

- **OQ-1:** `spec-earthquake-by-id` constraint explicitly excludes `Earthquake.time` from v1. This spec requires it. Decision: update that spec's non-goals to remove the `time` exclusion, treating the aftershock feature as the driver for adding `time`.
- **OQ-2:** `USGSAdapter.get_all` currently ignores `lat/lon/radius` — does extending `EarthquakeFilter` and threading through `USGSClient.query` break any caller that relies on the current flat param set? (Low risk: all new filter fields are optional and default to `None`.)

---

## Cost Log

| Date (UTC) | Phase | Model | ~Input tkns | ~Output tkns | ~Cost USD |
|------------|-------|-------|-------------|--------------|-----------|
| 2026-08-18 | spec  | claude-sonnet-4-6 | 18000 | 2200 | $0.09 |
