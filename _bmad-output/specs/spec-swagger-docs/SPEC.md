---
id: SPEC-swagger-docs
companions: []
sources: []
---

> **Canonical contract.** This SPEC and its companions are the complete contract for what to build, test, and validate.
> Always verify alignment with the Product Brief and Architecture documents before implementation begins.

# Dark Factory — Swagger / OpenAPI Documentation Enrichment

## Description

Enrich the existing auto-generated OpenAPI metadata so that `/docs` is a complete, self-service API reference where any developer can discover, understand, and execute every endpoint without reading source code.

## What / Why

**What:** Add endpoint-level summaries, descriptions, response examples, error response entries (422, 502), and tag group descriptions to the FastAPI application. No new packages. No functional changes.

**Why:** FastAPI already generates Swagger UI at `/docs` and ReDoc at `/redoc` from type annotations (AD-1 — no extra packages needed). The current implementation exposes minimal metadata: docstrings are sparse, there are no response examples, and error responses beyond 422 are undocumented. A developer hitting `/docs` today cannot tell what the endpoints return, what a real response looks like, or what happens when USGS is unreachable.

## Acceptance Criteria

- [ ] `GET /openapi.json` — every operation (`/api/v1/earthquakes`, `/api/v1/earthquakes/recent`, `/api/v1/earthquakes/{id}`, `/health`) contains a non-empty `summary` and `description` field.
- [ ] `GET /openapi.json` — every operation documents at least HTTP 200 and HTTP 422 responses.
- [ ] `GET /openapi.json` — `GET /api/v1/earthquakes` documents an HTTP 502 response (upstream USGS unavailable).
- [ ] `GET /docs` — the `GET /api/v1/earthquakes` 200 response section renders a populated GeoJSON FeatureCollection example.
- [ ] `GET /docs` — tag groups ("earthquakes", "health") render a visible description above their endpoint list.
- [ ] `uv run ruff check src/` — 0 violations after changes.
- [ ] `uv run mypy src/` — 0 errors after changes.
- [ ] `uv run pytest -q` — 0 regressions (existing tests continue to pass).

## Definition of Ready

- [ ] Aligned with Product Brief
- [ ] Consistent with Architecture decisions (AD-1: FastAPI built-ins only; no extra packages)
- [ ] Acceptance Criteria are clear and testable
- [ ] No unresolved blocking dependencies
- [ ] GitHub issue created and linked

## Definition of Done

- [ ] All Acceptance Criteria met and verified
- [ ] Unit and integration tests written and passing
- [ ] Code reviewed and PR approved
- [ ] Merged to `main` and deployed successfully
- [ ] No regressions introduced

---

## Capabilities

### CAP-1 — Endpoint metadata completeness

**Intent:** Every public endpoint exposes a `summary`, `description`, and documented HTTP responses in the OpenAPI spec.

**Scope:** `GET /api/v1/earthquakes`, `GET /api/v1/earthquakes/recent`, `GET /api/v1/earthquakes/{id}`, `GET /health`.

**Success:** `GET /openapi.json` returns an object where every operation has a non-empty `summary`, a non-empty `description`, and at least 200 and 422 listed under `responses`.

---

### CAP-2 — Response example on earthquake list

**Intent:** Add a concrete GeoJSON FeatureCollection example to the 200 response schema of `GET /api/v1/earthquakes`.

**Success:** Swagger UI renders an example response body under the "200 Successful Response" section for `GET /api/v1/earthquakes`.

---

### CAP-3 — Upstream error response documented

**Intent:** Document HTTP 502 on endpoints that proxy USGS, so consumers know what to expect when the upstream is unavailable.

**Scope:** `GET /api/v1/earthquakes` (only implemented proxy endpoint in this scope; stubs are excluded).

**Success:** `GET /openapi.json` includes a `502` entry under the responses for `GET /api/v1/earthquakes`.

---

### CAP-4 — Tag group descriptions

**Intent:** Add `openapi_tags` metadata to the FastAPI app factory so tag groups render with a visible description in the Swagger UI.

**Tags in scope:** `earthquakes`, `health`.

**Success:** `GET /docs` shows a description paragraph above each tag group's endpoint list.

---

## Constraints

- **No new packages.** All metadata is added via FastAPI built-ins: `summary`, `description`, `responses`, `openapi_extra`, and `openapi_tags` in `create_app()`. Installing any additional schema or documentation library violates AD-1.
- **No functional changes.** Endpoint signatures, response structures, status codes returned at runtime, and HTTP behavior must be identical before and after. This spec modifies only what the OpenAPI spec *documents*, not what the endpoints *do*.
- **OpenAPI 3.1.0 validity.** `GET /openapi.json` must remain parseable by standard OpenAPI 3.1.0 validators after changes.

## Non-Goals

- No custom Swagger UI theme, favicon, or JavaScript customization.
- No ReDoc-specific customization.
- No access restriction or authentication on `/docs` or `/redoc`.
- No expansion of the stubs (`GET /api/v1/earthquakes/recent`, `GET /api/v1/earthquakes/{id}`) — they remain stubs; only their stub status is documented.
- No per-field validation examples beyond what Pydantic already generates from type annotations.

## Success Signal

A developer opens `/docs` on the running API, reads each endpoint's description, expands `GET /api/v1/earthquakes`, sees a populated GeoJSON FeatureCollection example response, and can execute the request directly from the browser — no curl, no README, no source code required.

---

## Cost Log

| Date (UTC) | Phase | Model | ~Input tkns | ~Output tkns | ~Cost USD |
|------------|-------|-------|-------------|--------------|-----------|
| 2026-08-13 | spec  | claude-sonnet-4-6 | 14500 | 1800 | $0.07 |
