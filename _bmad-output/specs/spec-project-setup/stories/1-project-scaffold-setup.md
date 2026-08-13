---
title: 'Project Scaffold Setup — Dark Factory'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'f7405c5296b577c1a9e2d93d1dbb47b2d9f8e8cf'
context:
  - _bmad-output/planning-artifacts/architecture/architecture-Dark-Factory-2026-08-13/ARCHITECTURE-SPINE.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Dark Factory repository has no application code, no package tooling, and no CI pipeline. No feature story can begin until the four-layer architecture boundaries are instantiated, the dependency toolchain is locked, and CI gates are enforcing quality.

**Approach:** Create the complete repository scaffold — `pyproject.toml` with locked deps, `src/dark_factory/` four-layer module structure with zero-import-domain enforcement, `tests/` mirroring that structure with TDD stubs, the FastAPI app factory, the pydantic-settings config class, and `.github/workflows/ci.yml` — so `uv sync && uv run pytest` passes on the first run.

## Boundaries & Constraints

**Always:**
- Python 3.13 (`requires-python = ">=3.13"`); `uv` is the sole package manager — no pip, no requirements.txt
- `src/dark_factory/domain/` has zero imports of `fastapi`, `httpx`, or `pydantic` — enforced by mypy
- All config flows through `pydantic-settings` `Settings` class + env vars; no hardcoded URLs or secrets
- TDD discipline: every test stub file is created before its corresponding implementation file

**Ask First:**
- Any dependency version that deviates from the Architecture Spine (AD-1, AD-11)
- Adding any dependency not listed in the Architecture Spine's key-dependencies block

**Never:**
- USGS integration (USGSAdapter logic, live httpx calls to USGS) — deferred to infrastructure story
- Functional HTTP endpoint handlers (query execution, response bodies beyond stubs) — deferred
- `deploy.yml` CI workflow — deferred to deployment story
- Response-format negotiation (JSON vs GeoJSON `Accept` header handling) — deferred
- Rate limiting, auth, caching — explicitly out of scope for v1

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| App cold start, default env | No `.env` file; `Settings.usgs_base_url` has default | `create_app()` returns FastAPI instance; `/docs` → HTTP 200 | N/A |
| Settings missing required var | Required env var absent, no default | `pydantic ValidationError` raised at startup | Process exits before binding port; error names the missing var |
| pytest on stub suite | `tests/` with stubs, no impl logic | `pytest` exits 0, 0 failures, 0 errors | N/A |

</frozen-after-approval>

## Code Map

- `pyproject.toml` -- to be created; single source of truth for deps, tool config (ruff, mypy), and Python version pin
- `src/dark_factory/domain/earthquake/` -- to be created; entities.py, value_objects.py, repositories.py, filters.py — zero external imports
- `src/dark_factory/application/earthquake/` -- to be created; queries.py, handlers.py — depends only on domain ports
- `src/dark_factory/infrastructure/usgs/` -- to be created; adapter.py, client.py, mappers.py stubs — implements domain port
- `src/dark_factory/interface/http/v1/` -- to be created; earthquakes.py (router), schemas.py (Pydantic I/O) — depends only on application
- `src/dark_factory/interface/http/dependencies.py` -- to be created; DI wiring stub
- `src/dark_factory/config.py` -- to be created; `Settings(BaseSettings)` with `usgs_base_url` defaulting to USGS API URL
- `src/dark_factory/main.py` -- to be created; `create_app()` factory, mounts router at `/api/v1`, `/health` stub, httpx lifespan
- `tests/conftest.py` -- to be created; `AsyncClient` fixture via `ASGITransport`, `FakeEarthquakeRepository` stub
- `tests/unit/domain/` -- to be created; `test_entities.py`, `test_value_objects.py` stubs
- `tests/unit/application/` -- to be created; `test_handlers.py` stub
- `tests/integration/infrastructure/` -- to be created; empty stub
- `tests/integration/interface/` -- to be created; `test_health.py` stub
- `.env.example` -- to be created; documents every Settings field
- `.github/workflows/ci.yml` -- to be created; runs ruff, mypy, pytest on PRs targeting main
- `uv.lock` -- to be committed after running `uv sync`

## Tasks & Acceptance

**Execution (TDD order — test stubs before implementation):**
- [x] `pyproject.toml` -- create -- project metadata, `requires-python = ">=3.13"`, all prod and dev deps per Architecture Spine AD-1/AD-11, ruff and mypy tool sections; run `uv sync` to generate `uv.lock`
- [x] `tests/conftest.py`, `tests/unit/domain/__init__.py`, `tests/unit/application/__init__.py`, `tests/integration/infrastructure/__init__.py`, `tests/integration/interface/__init__.py` -- create -- test package markers and shared fixtures (AsyncClient + FakeEarthquakeRepository stubs)
- [x] `tests/unit/domain/test_entities.py`, `tests/unit/domain/test_value_objects.py` -- create stubs -- placeholder `test_placeholder` that passes; red phase before domain impl
- [x] `tests/unit/application/test_handlers.py` -- create stub -- placeholder test with mocked repo; red phase before application impl
- [x] `tests/integration/interface/test_health.py` -- create stub -- placeholder test for `GET /health` via `ASGITransport`; red phase before interface impl
- [x] `src/dark_factory/__init__.py`, all layer `__init__.py` files (domain/earthquake, application/earthquake, infrastructure/usgs, interface/http, interface/http/v1) -- create -- empty package markers
- [x] `src/dark_factory/domain/earthquake/entities.py` -- create stub -- `Earthquake` dataclass with `id: str`, `magnitude: float`, `depth: float`, `latitude: float`, `longitude: float`; stdlib only
- [x] `src/dark_factory/domain/earthquake/value_objects.py` -- create stub -- `Magnitude`, `Depth`, `Coordinates`, `EarthquakeFilter` dataclasses; stdlib only
- [x] `src/dark_factory/domain/earthquake/repositories.py` -- create stub -- `EarthquakeRepository(ABC)` with abstract `get_all` and `get_by_id`; stdlib only
- [x] `src/dark_factory/domain/earthquake/filters.py` -- create stub -- `EarthquakeFilter` dataclass with optional filter fields matching Brief params; stdlib only
- [x] `src/dark_factory/application/earthquake/queries.py`, `handlers.py` -- create stubs -- `GetEarthquakes` / `GetEarthquakeById` query dataclasses; handler stubs that accept repo port and query, return empty list / None
- [x] `src/dark_factory/infrastructure/usgs/adapter.py`, `client.py`, `mappers.py` -- create stubs -- `USGSAdapter(EarthquakeRepository)` skeleton; httpx client wrapper skeleton; mapper stub; intentionally unimplemented (`raise NotImplementedError`)
- [x] `src/dark_factory/interface/http/v1/earthquakes.py`, `schemas.py`, `../dependencies.py` -- create stubs -- router with stub endpoints returning `{"status": "stub"}`; Pydantic response schemas; DI wiring returning stub adapter
- [x] `src/dark_factory/config.py` -- create -- `Settings(BaseSettings)` with `usgs_base_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"` and `model_config = SettingsConfigDict(env_file=".env")`
- [x] `src/dark_factory/main.py` -- create -- `create_app()` wires lifespan (httpx.AsyncClient), mounts `/api/v1` router, adds `GET /health` returning `{"status": "ok"}`; `app = create_app()`
- [x] `.env.example` -- create -- documents `USGS_BASE_URL` and any other Settings fields with example values and descriptions
- [x] `.github/workflows/ci.yml` -- create -- triggers on PRs to main; steps: checkout, setup Python 3.13, install uv, `uv sync --frozen`, `uv run ruff check .`, `uv run mypy src/`, `uv run pytest tests/ -q`
- [x] `uv.lock` -- commit -- run `uv sync` to generate and commit the lock file for reproducible builds

**Acceptance Criteria:**
- Given a clean clone, when `uv sync` runs, then all packages install and exit 0
- Given `uv sync` completed, when `uv run pytest tests/ -q` runs, then 0 failures and 0 errors
- Given `src/dark_factory/domain/` exists, when `uv run mypy src/dark_factory/domain/ --strict` runs, then zero external-import violations
- Given the app is started with `uvicorn dark_factory.main:app`, when `GET /docs` is requested, then HTTP 200 is returned
- Given a `.env` with `USGS_BASE_URL` overriding the default, when `Settings()` is called, then the overridden value is returned by `settings.usgs_base_url`
- Given `ci.yml` exists and the branch is pushed, when a PR is opened targeting `main`, then all CI steps (ruff, mypy, pytest) pass

## Spec Change Log

## Design Notes

- `Settings.usgs_base_url` carries a default (`https://earthquake.usgs.gov/fdsnws/event/1/query`) so the app starts without a `.env` file. This is safe because the URL is public; only override in tests or when pointing at a mock.
- Domain layer (`entities.py`, `value_objects.py`, `repositories.py`, `filters.py`) uses `dataclasses.dataclass` and `abc.ABC` exclusively — no external package imports. Pydantic belongs in `interface/http/v1/schemas.py` only.
- `EarthquakeFilter` may appear in both `domain/earthquake/filters.py` and be mirrored in `interface/http/v1/schemas.py` as a Pydantic model for request validation. They are separate types; the interface schema maps to the domain filter at the handler boundary.
- Infrastructure stubs (`USGSAdapter`) deliberately raise `NotImplementedError` — the test stubs must pass before any real implementation lands, confirming the TDD constraint.

## Verification

**Commands:**
- `uv sync` -- expected: exit 0, no package errors
- `uv run pytest tests/ -q` -- expected: exit 0, 0 failures, 0 errors
- `uv run ruff check .` -- expected: exit 0, no violations
- `uv run mypy src/dark_factory/domain/ --strict` -- expected: exit 0 or only `error: Cannot find implementation or library stub` for stdlib ABCs (not external import violations)
- `uv run uvicorn dark_factory.main:app --host 0.0.0.0 --port 8000` -- expected: server starts, `GET /docs` → HTTP 200

## Suggested Review Order

**Application wiring — start here to grasp the design**

- `create_app()` factory: wires lifespan, mounts `/api/v1` router, adds `/health` stub
  [`main.py:32`](../../../../src/dark_factory/main.py#L32)

- `lifespan()`: creates shared `httpx.AsyncClient` stored on `app.state`
  [`main.py:23`](../../../../src/dark_factory/main.py#L23)

- `Settings`: pydantic-settings loads from env; `usgs_base_url` has safe public default
  [`config.py:13`](../../../../src/dark_factory/config.py#L13)

- router stub: `/earthquakes`, `/recent`, `/{id}` — all return `{"status":"stub"}`
  [`earthquakes.py:1`](../../../../src/dark_factory/interface/http/v1/earthquakes.py#L1)

- DI stub: `get_repository()` returns `USGSAdapter()` — httpx wiring deferred to infra story
  [`dependencies.py:1`](../../../../src/dark_factory/interface/http/dependencies.py#L1)

**Domain layer — verify zero external imports (AD-2)**

- `EarthquakeRepository` ABC: pure stdlib port; all infra must implement this interface
  [`repositories.py:18`](../../../../src/dark_factory/domain/earthquake/repositories.py#L18)

- `Earthquake` entity: five-field stdlib dataclass; no fastapi/httpx/pydantic imports
  [`entities.py:13`](../../../../src/dark_factory/domain/earthquake/entities.py#L13)

- `EarthquakeFilter` and sibling value objects: all stdlib, all fields optional
  [`value_objects.py:1`](../../../../src/dark_factory/domain/earthquake/value_objects.py#L1)

**Application layer — handlers depend only on the domain port**

- `GetEarthquakesHandler`: delegates to `EarthquakeRepository.get_all`; no infra import
  [`handlers.py:19`](../../../../src/dark_factory/application/earthquake/handlers.py#L19)

**Infrastructure stub — intentionally unimplemented**

- `USGSAdapter`: inherits `EarthquakeRepository`; both methods raise `NotImplementedError`
  [`adapter.py:18`](../../../../src/dark_factory/infrastructure/usgs/adapter.py#L18)

**Tests & config**

- `FakeEarthquakeRepository` + `async_client` fixture via `ASGITransport`
  [`conftest.py:24`](../../../../tests/conftest.py#L24)

- Integration tests: `/health` → 200, `/docs` → 200, `Settings` default + env-var override
  [`test_health.py:1`](../../../../tests/integration/interface/test_health.py#L1)

- Deps, ruff (line-length 88), mypy strict, pytest config
  [`pyproject.toml:1`](../../../../pyproject.toml#L1)

- CI: ruff + mypy + pytest on PR and push to `main`
  [`ci.yml:1`](../../../../.github/workflows/ci.yml#L1)
