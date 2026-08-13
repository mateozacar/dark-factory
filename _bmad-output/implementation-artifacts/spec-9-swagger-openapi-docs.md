---
title: 'Dark Factory — Swagger / OpenAPI Documentation Enrichment'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'e7f4a671a5065d2565e6e9f6bd78419d79246d81'
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Stub endpoints /recent and /{earthquake_id} lack response_model and error-response documentation
    evidence: |-
      Both stubs return dict[str,str] with no response_model; 502 and 404 are undocumented.
      Surfaced by Blind Hunter. Will be addressed when stubs are implemented.
    location: >-
      src/dark_factory/interface/http/v1/earthquakes.py:64-91
    severity: low
  - summary: >-
      health_check lacks response_model and 503 unhealthy-state documentation
    evidence: |-
      /health has no response_model and no documented 503 response.
      The health check does not probe USGS upstream reachability — it only returns {"status":"ok"}.
      Surfaced by Blind Hunter and Edge Case Hunter.
    location: >-
      src/dark_factory/main.py:69-72
    severity: low
  - summary: >-
      No temporal ordering validation: starttime after endtime passes through to USGS unchecked
    evidence: |-
      EarthquakeFilterParams accepts starttime > endtime without raising 422.
      USGS may return an empty or error response silently.
      Surfaced by Edge Case Hunter.
    location: >-
      src/dark_factory/interface/http/v1/schemas.py:32-38
    severity: medium
  - summary: >-
      minmagnitude accepts negative values and extreme floats without domain validation
    evidence: |-
      EarthquakeFilterParams.minmagnitude has no Field(ge=0.0, le=10.0) constraint.
      Nonsensical values are forwarded to the USGS API.
      Surfaced by Edge Case Hunter.
    location: >-
      src/dark_factory/interface/http/v1/schemas.py:37
    severity: medium
  - summary: >-
      API version hardcoded as "0.1.0" in create_app rather than derived from package metadata
    evidence: |-
      FastAPI(version="0.1.0") will silently drift from pyproject.toml as the project evolves.
      Should derive from importlib.metadata.version("dark-factory") or pydantic-settings.
      Surfaced by Blind Hunter.
    location: >-
      src/dark_factory/main.py:42
    severity: low
---

<intent-contract>

## Intent

**Problem:** FastAPI auto-generates `/docs` and `/redoc` but the current implementation delivers minimal metadata: `health_check` has no docstring so its OpenAPI `description` is absent; no endpoint documents a 502 upstream-error response; `GeoJSONFeatureCollection` has no schema example; tag groups have no descriptions. Developers hitting `/docs` cannot tell what each endpoint does, what a real response looks like, or what happens when USGS is unreachable.

**Approach:** Enrich OpenAPI metadata across three files using only FastAPI built-ins — no new packages. Add `openapi_tags` to `create_app()`, add explicit `summary`/`description`/`responses` to each route decorator, add `json_schema_extra` example to `GeoJSONFeatureCollection`. TDD: write failing tests against `GET /openapi.json` before touching implementation files.

## Boundaries & Constraints

**Always:**
- Use only FastAPI built-ins: `summary`, `description`, `responses`, `openapi_extra`, `openapi_tags` — no additional packages (AD-1).
- No changes to endpoint signatures, response structures, status codes returned at runtime, or existing test assertions — documentation-only changes.
- TDD mandate: test file must be written and confirmed failing before any implementation file is touched.
- `GET /openapi.json` must remain valid OpenAPI 3.1.0 after all changes.

**Block If:**
- Any change requires modifying an existing endpoint's return type, path, or HTTP method.

**Never:**
- Custom Swagger UI theme, favicon, or JavaScript customization.
- Access restriction or authentication on `/docs` or `/redoc`.
- Expanding the stubs (`/recent`, `/{id}`) beyond documenting their stub status.
- Installing new Python packages.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tags have descriptions | `GET /openapi.json` | `tags` array includes entries for "earthquakes" and "health", each with non-empty `description` | Assert presence |
| All operations have description | `GET /openapi.json` | Every operation object has a non-empty `description` field (including `health_check`) | Assert not absent/empty |
| Earthquakes list has 502 | `GET /openapi.json` | `paths["/api/v1/earthquakes"]["get"]["responses"]` includes key `"502"` | Assert presence |
| Schema has example | `GET /openapi.json` | `components.schemas.GeoJSONFeatureCollection` includes an `example` key with a FeatureCollection shape | Assert presence and shape |

</intent-contract>

## Code Map

- `src/dark_factory/main.py:32` — `create_app()` — add `openapi_tags` list with "earthquakes" and "health" entries; read-only: existing lifespan, router prefix `/api/v1`, health route path `/health`
- `src/dark_factory/main.py:45` — `health_check` inline route — add `summary` and `description` kwargs to `@app.get` decorator; no docstring exists so description is absent from current OpenAPI spec
- `src/dark_factory/interface/http/v1/earthquakes.py:27` — `@router.get("")` decorator on `list_earthquakes` — add `summary`, `description`, `responses={422: ..., 502: ...}`; `response_model=GeoJSONFeatureCollection` already generates 200; FastAPI auto-adds 422 for query params but it must be in `responses` explicitly to satisfy test
- `src/dark_factory/interface/http/v1/earthquakes.py:54` — `@router.get("/recent")` on `recent_earthquakes` — add `summary`, `description`
- `src/dark_factory/interface/http/v1/earthquakes.py:60` — `@router.get("/{earthquake_id}")` on `get_earthquake_by_id` — add `summary`, `description`
- `src/dark_factory/interface/http/v1/schemas.py:62` — `GeoJSONFeatureCollection` — add `model_config = ConfigDict(json_schema_extra={"example": {...}})` with a single-feature FeatureCollection; import `ConfigDict` from `pydantic`
- `tests/integration/interface/test_openapi_metadata.py` — NEW — TDD tests against `GET /openapi.json` for tags, descriptions, 502, and schema example; must fail before implementation
- `tests/conftest.py:46` — `async_client` fixture (read-only) — reuse as-is; all metadata tests hit `/openapi.json` which requires no DI override

## Tasks & Acceptance

**Execution (TDD — Phase 1: tests first; Phase 2: implementation after tests confirmed failing):**

**Phase 1 — Tests (write before implementation):**
- `tests/integration/interface/test_openapi_metadata.py` -- create with four test classes: `TestTagDescriptions`, `TestOperationDescriptions`, `TestEarthquakesListResponses`, `TestGeoJSONSchemaExample` -- must fail (RED) before implementation; each test hits `GET /openapi.json` via `async_client`

**Phase 2 — Implementation (after RED confirmed):**
- `src/dark_factory/interface/http/v1/schemas.py` -- add `from pydantic import ConfigDict` import and `model_config = ConfigDict(json_schema_extra={"example": {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-122.1, 37.5, 10.0]}, "properties": {"id": "us7000abc1", "mag": 5.2}}]}})` to `GeoJSONFeatureCollection` -- makes `test_geojson_schema_has_example` go GREEN
- `src/dark_factory/interface/http/v1/earthquakes.py` -- add `summary`, `description`, and `responses` kwargs to all three `@router.get(...)` decorators -- makes `TestOperationDescriptions` and `TestEarthquakesListResponses` go GREEN
- `src/dark_factory/main.py` -- add `openapi_tags = [{"name": "earthquakes", "description": "..."}, {"name": "health", "description": "..."}]` to `create_app()` and pass to `FastAPI(..., openapi_tags=openapi_tags)`; add `summary` and `description` to the `health_check` inline route decorator -- makes `TestTagDescriptions` and missing-description tests go GREEN

**Acceptance Criteria:**
- Given `GET /openapi.json`, when parsed, then `tags` array contains entries for "earthquakes" and "health" each with a non-empty `description`
- Given `GET /openapi.json`, when parsed, then every operation object under `paths` has a non-empty `description` field
- Given `GET /openapi.json`, when parsed, then `paths["/api/v1/earthquakes"]["get"]["responses"]` contains key `"502"`
- Given `GET /openapi.json`, when parsed, then `components["schemas"]["GeoJSONFeatureCollection"]` contains an `"example"` key with `type == "FeatureCollection"` and a non-empty `features` list
- Given all changes applied, when `uv run pytest tests/ -q`, then 0 failures and no regressions
- Given all changes applied, when `uv run ruff check .`, then 0 violations
- Given all changes applied, when `uv run mypy src/`, then 0 errors

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 5: (high 0, medium 2, low 3)
- reject: 11 (noise, diff-construction artefact, or out-of-scope per intent)
- addressed_findings:
  - none

## Auto Run Result

**Status:** done

**Summary:** Added OpenAPI metadata enrichment across three files — `openapi_tags` with descriptions, explicit `summary`/`description`/`responses` on all route decorators (including the 502 upstream-error entry on `list_earthquakes`), and a `GeoJSONFeatureCollection` schema example.

**Files changed:**
- `src/dark_factory/main.py` — added `openapi_tags` (earthquakes + health descriptions), `summary` and `description` on `health_check`
- `src/dark_factory/interface/http/v1/earthquakes.py` — added `summary`, `description`, and `responses` (422 + 502) to `list_earthquakes`; added `summary` and `description` to `recent_earthquakes` and `get_earthquake_by_id`
- `src/dark_factory/interface/http/v1/schemas.py` — added `ConfigDict` import and `json_schema_extra` example to `GeoJSONFeatureCollection`
- `tests/integration/interface/test_openapi_metadata.py` — NEW: 13 test functions (26 runs with asyncio+trio backends) covering all 4 matrix rows

**Review findings:** 0 patch, 5 deferred (pre-existing validation gaps and version drift), 11 rejected (noise/out-of-scope).

**Follow-up review:** `false` — 0 patched findings; score 0.

**Verification:**
- `uv run pytest tests/ -q` → 125 passed, 0 failures
- `uv run ruff check .` → 0 violations
- `uv run mypy src/` → 0 errors
- All 4 I/O matrix rows covered by passing tests

**Residual risks:** None introduced by this change. Pre-existing gaps captured in `deferred`.

## Design Notes

**FastAPI `responses` parameter merges with auto-generated entries.** Adding `responses={422: {"description": "..."}, 502: {"description": "..."}}` to a decorator does not suppress the auto-generated 200; it only adds or overrides the listed codes.

**`GeoJSONFeatureCollection` example placement.** `model_config = ConfigDict(json_schema_extra={"example": {...}})` places the example at the schema level in `components/schemas`, which is what the Swagger UI renders under the 200 response section.

**`openapi_tags` order.** FastAPI renders tags in the order listed in `openapi_tags`. List "earthquakes" first, "health" second.

**Inline `health_check` route.** It is defined as a closure inside `create_app()`, not in the router file. Add `summary` and `description` as keyword args to `@app.get("/health", tags=["health"], summary="...", description="...")`.

## Verification

**Commands:**
- `uv run pytest tests/integration/interface/test_openapi_metadata.py -v` -- expected: all 4+ tests RED before implementation; all GREEN after
- `uv run pytest tests/ -q` -- expected: 0 failures, no regressions
- `uv run ruff check .` -- expected: 0 violations
- `uv run mypy src/` -- expected: 0 errors
