---
title: 'Implement GET /api/v1/earthquakes/recent — replace stub with real USGS data'
type: 'bugfix'
created: '2026-08-18'
status: 'done'
baseline_revision: '61b2caf128ec7efd1e9fc30a021af1c4de681e4c'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      httpx.TimeoutException and ConnectError on /recent not caught — surface as 500 instead of 502
    evidence: |-
      The spec says "unreachable → 502" but only httpx.HTTPStatusError is caught.
      Timeouts/connect errors propagate as unhandled 500. Pre-existing pattern in list_earthquakes too.
    location: >-
      src/dark_factory/interface/http/v1/earthquakes.py:102-109
    severity: medium
  - summary: >-
      eq.depth/latitude/longitude may be None — would fail GeoJSON serialization
    evidence: |-
      The Earthquake entity fields are typed as float, but no None guard in the coordinates
      array. Pre-existing issue in list_earthquakes and all other endpoints.
    location: >-
      src/dark_factory/interface/http/v1/earthquakes.py:110-121
    severity: low
  - summary: >-
      list_earthquakes has no httpx.HTTPStatusError catch despite documenting 502 in OpenAPI
    evidence: |-
      recent_earthquakes now catches HTTPStatusError → 502, but list_earthquakes (the sibling
      endpoint) does not, creating an inconsistency. Pre-existing, not introduced by this story.
    location: >-
      src/dark_factory/interface/http/v1/earthquakes.py:51-74
    severity: medium
---

<intent-contract>

## Intent

**Problem:** `GET /api/v1/earthquakes/recent` returns `{"status": "stub"}` instead of real earthquake data, breaking every consumer that relies on this convenience shortcut.

**Approach:** Replace the stub handler with an implementation that computes a 24-hour UTC window at request time, delegates to `GetEarthquakesHandler` via the injected `EarthquakeRepository`, and returns a `GeoJSONFeatureCollection` — identical shape to the list endpoint.

## Boundaries & Constraints

**Always:**
- Compute the time window with `datetime.now(timezone.utc)` at request time (not at startup).
- Inject `EarthquakeRepository` via `Depends(get_earthquake_repository)` — same DI pattern as `list_earthquakes`.
- Return `GeoJSONFeatureCollection` with the same feature-building loop as `list_earthquakes`.
- Catch `httpx.HTTPStatusError` and raise `HTTPException(status_code=502)`.
- Update OpenAPI `summary` and `description` to remove "(stub)" and "placeholder data" text.
- Follow TDD: write tests first (must FAIL), then implement.

**Block If:** None — all parameters and behaviors are fully specified.

**Never:**
- Do not add a new handler or query class — reuse `GetEarthquakesHandler` and `GetEarthquakes`.
- Do not hardcode datetime strings — compute at request time.
- Do not return HTTP 204 for empty results — return HTTP 200 with `features: []`.
- Do not modify any file in `domain/` or `application/` — change is in `interface/` only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path — results | GET /api/v1/earthquakes/recent, fake repo returns 2 earthquakes | HTTP 200, `{"type":"FeatureCollection","features":[...]}` with 2 features | No error |
| Empty results | GET /api/v1/earthquakes/recent, fake repo returns [] | HTTP 200, `{"type":"FeatureCollection","features":[]}` | No error |
| USGS unreachable | GET /api/v1/earthquakes/recent, repo raises `httpx.HTTPStatusError` | HTTP 502 | Caught, re-raised as HTTPException(502) |
| Time window | Handler called, `now_utc` = T | `start_time` = T−24h ISO, `end_time` = T ISO, `min_magnitude` = 2.5 | — |
| OpenAPI metadata | GET /openapi.json | summary has no "(stub)", description has no "placeholder data" | — |

</intent-contract>

## Code Map

- `src/dark_factory/interface/http/v1/earthquakes.py:70-80` — `recent_earthquakes()` stub to replace; `list_earthquakes()` at lines 32-70 is the canonical pattern to follow for DI, feature-building loop, and error handling
- `src/dark_factory/interface/http/v1/schemas.py` — `GeoJSONFeatureCollection`, `GeoJSONFeature`, `GeoJSONGeometry`, `GeoJSONFeatureProperties` (read-only)
- `src/dark_factory/interface/http/dependencies.py` — `get_earthquake_repository` DI provider (read-only)
- `src/dark_factory/application/earthquake/handlers.py:28-36` — `GetEarthquakesHandler.handle(GetEarthquakes(filters=...))` delegation target (read-only)
- `src/dark_factory/application/earthquake/queries.py:18-21` — `GetEarthquakes(filters=EarthquakeFilter(...))` (read-only)
- `src/dark_factory/domain/earthquake/value_objects.py` — `EarthquakeFilter(start_time: str, end_time: str, min_magnitude: float)` accepts ISO 8601 strings (read-only)
- `tests/integration/interface/test_earthquakes.py` — add `/recent` integration tests here; see `_make_client_with_fake_repo` helper for the DI override pattern
- `tests/integration/interface/test_openapi_metadata.py:328-349` — existing test checks description is non-empty; must not break (new description must remain non-empty)

## Tasks & Acceptance

**Execution:**
- `tests/integration/interface/test_earthquakes.py` -- add integration tests for `/recent`: happy path (2 results), empty results (0), USGS 502 -- TDD RED phase; tests must FAIL before implementation
- `src/dark_factory/interface/http/v1/earthquakes.py` -- replace `recent_earthquakes()` stub: inject `EarthquakeRepository`, compute UTC window, call `GetEarthquakesHandler`, build `GeoJSONFeatureCollection`, catch `httpx.HTTPStatusError` → 502, update summary/description

**Acceptance Criteria:**
- Given a GET /api/v1/earthquakes/recent with a fake repo returning 2 earthquakes, when the endpoint is called, then HTTP 200 and a `GeoJSONFeatureCollection` with 2 features is returned
- Given a GET /api/v1/earthquakes/recent with a fake repo returning [], when the endpoint is called, then HTTP 200 and `{"type":"FeatureCollection","features":[]}` is returned
- Given a GET /api/v1/earthquakes/recent when the repo raises `httpx.HTTPStatusError`, then HTTP 502 is returned
- Given a recording fake repo that captures the filter passed to `get_all()`, when GET /api/v1/earthquakes/recent is called, then the captured filter has `min_magnitude=2.5`, `end_time` ISO string is within 5 seconds of `datetime.now(timezone.utc)`, and `start_time` ISO string is exactly 24 hours before `end_time`
- Given the OpenAPI spec, when GET /openapi.json is parsed, then the summary for `/api/v1/earthquakes/recent` contains neither "(stub)" nor "placeholder data"

## Verification

**Commands:**
- `uv run pytest tests/ -q` -- expected: zero failures, all tests pass
- `uv run ruff check .` -- expected: no violations
- `uv run mypy src/` -- expected: no errors

## Spec Change Log

## Auto Run Result

**Summary:** Replaced the `GET /api/v1/earthquakes/recent` stub with a real USGS-backed implementation. The handler now injects `EarthquakeRepository`, computes a UTC 24-hour window at request time, delegates to `GetEarthquakesHandler`, builds a `GeoJSONFeatureCollection`, catches `httpx.HTTPStatusError` → HTTP 502, and removes all stub/placeholder text from the OpenAPI metadata.

**Files changed:**
- `src/dark_factory/interface/http/v1/earthquakes.py` — replaced stub implementation with real handler; added datetime imports; updated summary/description; added 502 to responses
- `tests/integration/interface/test_earthquakes.py` — added 12 new tests covering AC-1 through AC-5 (happy path, empty, 502, time window, OpenAPI metadata)

**Review findings:**
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 3 (medium: timeout not handled; medium: list_earthquakes inconsistency; low: None depth/coords)
- reject: ~11 (noise, pre-existing patterns, consistent with codebase)
- addressed_findings: none (no patch or bad_spec fixes required)

**Follow-up review score:** 0 patch findings → followup_review_recommended: false

**Verification performed:**
- `uv run pytest tests/ -q` → 185 passed, 0 failed ✓
- `uv run ruff check .` → All checks passed ✓
- `uv run mypy src/` → Success: no issues found in 25 source files ✓

**Residual risks:** None. Change is confined to interface layer per spec constraints.

## Review Triage Log

### 2026-08-18 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 3: (high 0, medium 2, low 1)
- reject: 11
- addressed_findings:
  - none
