---
id: SPEC-project-setup
companions:
  - ../../../../_bmad-output/planning-artifacts/architecture/architecture-Dark-Factory-2026-08-13/ARCHITECTURE-SPINE.md
sources:
  - ../../../../_bmad-output/planning-artifacts/briefs/brief-Dark-Factory-2026-08-13/brief.md
---

> **Canonical contract.** This SPEC and its companions are the complete contract for what to build, test, and validate.
> Always verify alignment with the Product Brief and Architecture documents before implementation begins.

# Dark Factory — Project Scaffold Setup

## Description

Initialize the Dark Factory repository with the full four-layer clean architecture scaffold, toolchain configuration, and GitHub Actions CI so every subsequent feature story has a verified, runnable base.

## What / Why

**What:** Create the source directory structure, `pyproject.toml` with all production and dev dependencies, the FastAPI app factory, the pydantic-settings config class, empty module stubs for each architectural layer, mirroring test stubs under `tests/`, and a `ci.yml` GitHub Actions workflow that runs `ruff`, `mypy`, and `pytest` on every PR.

**Why:** No development story can begin until the repository compiles, the dependency toolchain is locked, the four-layer module boundaries are in place, and CI gates are enforcing them. This story is the prerequisite for every subsequent implementation story.

## Acceptance Criteria

- [ ] `uv sync` installs all production and dev dependencies and exits 0 with no errors.
- [ ] `src/dark_factory/` contains `domain/earthquake/`, `application/earthquake/`, `infrastructure/usgs/`, and `interface/http/v1/` directories, each with an `__init__.py`.
- [ ] `domain/` contains zero imports of `fastapi`, `httpx`, or `pydantic` (verified by `mypy --strict` or `ruff`).
- [ ] `dark_factory.main.create_app()` returns a FastAPI instance; `uvicorn dark_factory.main:app` starts without errors.
- [ ] `dark_factory.config.Settings` instantiates from environment variables (with a `.env` sourced from `.env.example` as baseline); all required vars documented in `.env.example`.
- [ ] `tests/` mirrors `src/dark_factory/` with `unit/domain/`, `unit/application/`, `integration/infrastructure/`, and `integration/interface/` subdirectories; `conftest.py` exists at root.
- [ ] `pytest` discovers all test stubs and exits 0 (0 failures, 0 errors).
- [ ] `.github/workflows/ci.yml` runs `ruff check .`, `mypy src/`, and `pytest` on pull requests targeting `main`; workflow passes on this branch.
- [ ] `pyproject.toml` specifies `requires-python = ">=3.13"` and lists all deps from AD-1 and AD-11 (fastapi ≥0.141.1, pydantic-settings ≥2.0, httpx ≥0.28.1, uvicorn[standard] ≥0.30; dev: pytest ≥8.0, anyio[trio] ≥4.0, pytest-anyio, ruff ≥0.5, mypy ≥1.10).
- [ ] `uv.lock` is committed and reproducible: `uv sync --frozen` exits 0.

## Capabilities

- **CAP-1** — Developer installs all project dependencies via `uv sync`.
  - **intent:** A developer can clone the repo and install the full dependency set with a single command.
  - **success:** `uv sync` exits 0; all packages in `pyproject.toml` are importable.

- **CAP-2** — Four-layer directory scaffold exists and respects architectural boundaries.
  - **intent:** The repository exposes `domain/`, `application/`, `infrastructure/`, and `interface/` as importable modules with correct internal boundaries.
  - **success:** All four layers are importable; `mypy --strict src/dark_factory/domain/` reports zero errors related to external imports.

- **CAP-3** — FastAPI app factory returns a runnable ASGI app.
  - **intent:** `create_app()` in `main.py` wires FastAPI with the versioned router mount and returns a ready-to-serve ASGI app.
  - **success:** `uvicorn dark_factory.main:app` starts without import or configuration errors; `/docs` and `/redoc` return HTTP 200.

- **CAP-4** — pydantic-settings `Settings` class loads configuration from environment variables.
  - **intent:** All runtime configuration (USGS base URL, app metadata) is read from environment variables through a single `Settings` class.
  - **success:** `Settings()` instantiates with environment variables sourced from `.env.example`; accessing any documented setting returns the expected value.

- **CAP-5** — GitHub Actions CI validates the scaffold on every pull request.
  - **intent:** `ci.yml` runs the full quality gate (`ruff`, `mypy`, `pytest`) automatically on PRs targeting `main`.
  - **success:** The CI workflow completes with all steps green on the initial scaffold branch.

## Constraints

- Python 3.13 only (`requires-python = ">=3.13"`). Bends CI runner image and any runtime assumptions.
- `uv` is the sole package manager. No `pip install`, no `requirements.txt`, no `poetry`. Bends all install commands in CI and developer docs.
- `domain/` has zero external dependencies. No `import fastapi`, `import httpx`, or `import pydantic` inside `domain/`. Bends module structure and what may be placed in which layer.
- All configuration must flow through pydantic-settings + env vars. No hardcoded URLs, tokens, or magic strings in source. Bends how `Settings` is written and what `.env.example` must document.
- TDD discipline: test stub files are created before implementation stubs. Bends the order in which files are written within this story.

## Non-goals

- USGS integration (`USGSAdapter`, `httpx` calls to USGS endpoints) — deferred to the infrastructure story.
- Functional HTTP endpoint handlers (`GET /earthquakes`, `GET /health` logic) — the router mount point exists but returns a stub; full handlers are subsequent stories.
- Render deployment and `deploy.yml` workflow — deferred until endpoints are implemented and validated.
- Response-format negotiation (JSON vs GeoJSON via `Accept` header) — deferred to the endpoint story.
- Rate limiting, auth, or caching — explicitly out of scope for v1 per the Product Brief.

## Success Signal

`uv sync && uv run pytest tests/ -q` passes with 0 failures and 0 errors, and `uv run uvicorn dark_factory.main:app` starts the server. The CI workflow runs green on a PR. The four-layer boundary is verifiable: `domain/` imports no external packages.

## Definition of Ready

- [ ] Aligned with Product Brief
- [ ] Consistent with Architecture Spine decisions (AD-1 through AD-11)
- [ ] Acceptance Criteria are clear and testable
- [ ] No unresolved blocking dependencies
- [ ] GitHub issue created and linked

## Definition of Done

- [ ] All Acceptance Criteria met and verified
- [ ] Unit and integration test stubs written first (TDD — red before green)
- [ ] `ruff`, `mypy`, and `pytest` all pass locally and in CI
- [ ] Code reviewed and PR approved
- [ ] Merged to `main` and CI green on `main`
- [ ] No regressions introduced
