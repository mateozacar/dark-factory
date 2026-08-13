<!-- bmad:context -->
<!-- Verified 2026-08-13 against 2f91287. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## Dark-Factory

Stateless REST proxy for the USGS FDSNWS Earthquake API. Python 3.13, FastAPI, httpx, deployed on Render via GitHub Actions. Clean Architecture: four layers (domain → application → infrastructure → interface). Specs and planning docs live in `_bmad-output/`.

## Policy

- Never push to `main` directly — PRs only, base `main`.
- Branch naming: `{type}/DARK-{num}-{slug}` — type is `feature | bugfix | hotfix | chore`, num from the GitHub issue.
- Never modify `_bmad/` — managed by the BMad installer; read it, never write it.
- Never modify `.claude/settings.local.json` — contains credentials.

## Where things are

- HTTP router: `src/dark_factory/interface/http/v1/earthquakes.py`
- Domain port (the contract): `src/dark_factory/domain/earthquake/repositories.py`
- USGS adapter: `src/dark_factory/infrastructure/usgs/`
- Active specs: `_bmad-output/specs/`
- Architecture decisions: `_bmad-output/planning-artifacts/architecture/`
- Deferred work log: `_bmad-output/implementation-artifacts/deferred-work.md`

## Running and verifying

- Prefix all commands with `uv run` — bare `pytest`, `ruff`, `mypy` run outside the project environment and produce wrong results or silently test the wrong version.

## Conventions that differ from defaults

- `dark_factory/domain/` must have zero external imports — stdlib only. `tests/unit/domain/` enforces this contract; breaking it fails those tests.
- Dependency direction is strictly inward: `interface → application → domain`. `infrastructure` implements domain ports and is never imported by `application` or `domain`.
- `EarthquakeFilter` lives in `value_objects.py`; `filters.py` is a re-export shim — import from `value_objects`, not `filters`.

## Known pitfalls

- Three stubs are intentional and need a spec before implementation: `GET /api/v1/earthquakes/recent`, `GET /api/v1/earthquakes/{id}`, and `USGSClient.fetch_earthquake_by_id` — do not treat as bugs.
- `FakeEarthquakeRepository` in `tests/conftest.py` does not inherit from `EarthquakeRepository` ABC — mypy cannot catch injection type mismatches through it; use `app.dependency_overrides` to inject it in integration tests.

<!-- /bmad:context -->
