# Deferred Work

Entries appended by bmad-build review passes. Do not modify existing entries.

---

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: FakeEarthquakeRepository in tests/conftest.py does not inherit from EarthquakeRepository ABC.
  evidence: Test file is human-owned and locked; duck typing works for stubs, but mypy cannot catch type mismatches when the fake is injected as a port. Infra story should either update conftest or use a Protocol-typed fake.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: get_repository() in dependencies.py does not inject the app-level httpx.AsyncClient from app.state.
  evidence: USGSAdapter is a stub raising NotImplementedError; wiring the shared client (app.state.http_client) into the DI function is the infrastructure story's responsibility to avoid a separate unmanaged client per request.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: EarthquakeFilterParams in schemas.py only exposes min_magnitude/max_magnitude; all other Brief filter params are absent.
  evidence: Intentional stub; full schema (depth, lat/lon bounds, time range, limit) belongs in the endpoint implementation story.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: I/O matrix row "Settings missing required var → ValidationError" has no test and no triggerable code path (Settings has no required-without-default fields).
  evidence: Aspirational row describing behavior that matters when required config fields are added; covering test belongs in the config hardening or secrets story.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: Domain dataclasses (Earthquake, Magnitude, Depth, Coordinates) are mutable; EarthquakeFilter time fields typed as str instead of datetime.
  evidence: Domain hardening concern; frozen=True and datetime typing improve correctness but are not required by the scaffold spec. Deferred to domain validation story.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: Settings.usgs_base_url has no empty-string or URL-format validation; trailing slash could produce malformed USGS request URLs.
  evidence: Config hardening; acceptable for scaffold where no real USGS calls are made. Deferred to infrastructure story.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: httpx.AsyncClient in lifespan has no timeout set; health endpoint does not probe USGS reachability.
  evidence: Operational hardening for production readiness; acceptable for stub scaffold. Deferred to infrastructure/deployment story.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: EarthquakeResponse schema missing place, time, and url fields that USGS returns and API consumers expect.
  evidence: Response schema is a stub; full field set is the endpoint implementation story's responsibility.

- source_spec: `_bmad-output/specs/spec-project-setup/stories/1-project-scaffold-setup.md`
  summary: CI job has no timeout-minutes; a hung integration test could occupy the runner for up to GitHub's 6-hour hard limit.
  evidence: Operational hardening; no integration tests with live network calls exist yet. Add timeout-minutes when USGS integration tests are introduced.
