"""
Unit tests for dark_factory.domain.earthquake.entities

AC covered:
  - Domain layer has zero external imports (AD-2 / mypy constraint)
  - Earthquake entity is a stdlib-only dataclass with the required fields

I/O & Edge-Case Matrix rows covered:
  - App cold start, default env: create_app() can construct a domain entity
    (indirectly asserts the import graph is correct)

TDD phase: RED — will fail with ImportError until entities.py is created.
"""

from __future__ import annotations

import pytest


class TestEarthquakeEntity:
    """
    Given the domain layer,
    when Earthquake is imported,
    then it is importable as a plain stdlib dataclass with no external deps.
    """

    def test_earthquake_can_be_imported(self) -> None:
        """
        Given: src/dark_factory/domain/earthquake/entities.py does not exist yet
        When:  we attempt to import Earthquake
        Then:  ImportError is raised (red phase — implementation missing)
        """
        from dark_factory.domain.earthquake.entities import Earthquake  # noqa: F401

    def test_earthquake_has_required_fields(self) -> None:
        """
        Given: Earthquake is a dataclass
        When:  an instance is constructed with all required fields
        Then:  each field stores the supplied value
        """
        from dark_factory.domain.earthquake.entities import Earthquake

        eq = Earthquake(
            id="us7000abc1",
            magnitude=5.2,
            depth=10.0,
            latitude=37.5,
            longitude=-122.1,
        )

        assert eq.id == "us7000abc1"
        assert eq.magnitude == 5.2
        assert eq.depth == 10.0
        assert eq.latitude == 37.5
        assert eq.longitude == -122.1

    def test_earthquake_is_dataclass(self) -> None:
        """
        Given: Earthquake is defined using @dataclasses.dataclass
        When:  dataclasses.fields() is called on it
        Then:  the six required field names are present (including time)
        """
        import dataclasses

        from dark_factory.domain.earthquake.entities import Earthquake

        field_names = {f.name for f in dataclasses.fields(Earthquake)}
        assert field_names == {"id", "magnitude", "depth", "latitude", "longitude", "time"}

    def test_earthquake_time_field_defaults_to_empty_string(self) -> None:
        """
        Given: Earthquake is constructed without a time argument
        When:  eq.time is accessed
        Then:  its value is "" (empty string default)
        """
        from dark_factory.domain.earthquake.entities import Earthquake

        eq = Earthquake(
            id="us7000abc1",
            magnitude=5.2,
            depth=10.0,
            latitude=37.5,
            longitude=-122.1,
        )
        assert eq.time == ""

    def test_aftershock_result_is_importable(self) -> None:
        """
        Given: entities.py is implemented with AftershockResult
        When:  AftershockResult is imported
        Then:  it is importable without error and is a dataclass
        """
        import dataclasses

        from dark_factory.domain.earthquake.entities import AftershockResult  # noqa: F401

        assert dataclasses.is_dataclass(AftershockResult)

    def test_earthquake_not_found_exception_carries_event_id(self) -> None:
        """
        Given: EarthquakeNotFound is defined with an event_id attribute
        When:  EarthquakeNotFound("us7000abc1") is raised and caught
        Then:  the exception's event_id attribute equals "us7000abc1"
        """
        from dark_factory.domain.earthquake.exceptions import EarthquakeNotFound

        exc = EarthquakeNotFound("us7000abc1")
        assert exc.event_id == "us7000abc1"

    def test_earthquake_domain_module_has_no_external_imports(self) -> None:
        """
        Given: the domain entities module is loaded
        When:  its __dict__ is inspected for banned external modules
        Then:  fastapi, httpx, and pydantic are NOT present as imports
        """
        import importlib
        import sys

        # Ensure fresh import
        mod_name = "dark_factory.domain.earthquake.entities"
        mod = importlib.import_module(mod_name)

        banned = {"fastapi", "httpx", "pydantic"}
        # Walk the module's global namespace for imported modules
        for name, obj in vars(mod).items():
            if hasattr(obj, "__module__") and obj.__module__:
                for banned_pkg in banned:
                    assert not obj.__module__.startswith(banned_pkg), (
                        f"Domain entity imports banned external package '{banned_pkg}' "
                        f"via symbol '{name}'"
                    )
