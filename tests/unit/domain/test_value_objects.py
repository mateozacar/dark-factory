"""
Unit tests for dark_factory.domain.earthquake.value_objects

AC covered:
  - Domain layer has zero external imports (AD-2)
  - Magnitude, Depth, Coordinates, EarthquakeFilter are stdlib-only dataclasses

I/O & Edge-Case Matrix rows covered:
  - App cold start, default env: value objects constructable from defaults
  - Settings missing required var: EarthquakeFilter with all-None optional fields
    does not raise, i.e. filtering is gracefully optional

TDD phase: RED — will fail with ImportError until value_objects.py is created.
"""

from __future__ import annotations

import dataclasses

import pytest


class TestMagnitude:
    """
    Given the domain layer,
    when Magnitude value object is imported and constructed,
    then it stores the supplied numeric value.
    """

    def test_magnitude_can_be_imported(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Magnitude  # noqa: F401

    def test_magnitude_stores_value(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Magnitude

        m = Magnitude(value=5.2)
        assert m.value == 5.2

    def test_magnitude_is_dataclass(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Magnitude

        assert dataclasses.is_dataclass(Magnitude)


class TestDepth:
    """
    Given the domain layer,
    when Depth value object is imported and constructed,
    then it stores the supplied numeric value.
    """

    def test_depth_can_be_imported(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Depth  # noqa: F401

    def test_depth_stores_value(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Depth

        d = Depth(km=35.0)
        assert d.km == 35.0

    def test_depth_is_dataclass(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Depth

        assert dataclasses.is_dataclass(Depth)


class TestCoordinates:
    """
    Given the domain layer,
    when Coordinates value object is imported and constructed,
    then latitude and longitude are stored correctly.
    """

    def test_coordinates_can_be_imported(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Coordinates  # noqa: F401

    def test_coordinates_stores_lat_lon(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Coordinates

        c = Coordinates(latitude=37.5, longitude=-122.1)
        assert c.latitude == 37.5
        assert c.longitude == -122.1

    def test_coordinates_is_dataclass(self) -> None:
        from dark_factory.domain.earthquake.value_objects import Coordinates

        assert dataclasses.is_dataclass(Coordinates)


class TestEarthquakeFilter:
    """
    Given the domain layer,
    when EarthquakeFilter is constructed with all-None optional fields,
    then it does not raise and represents an unfiltered state.
    """

    def test_earthquake_filter_can_be_imported(self) -> None:
        from dark_factory.domain.earthquake.value_objects import EarthquakeFilter  # noqa: F401

    def test_earthquake_filter_all_none_defaults(self) -> None:
        """
        Given: EarthquakeFilter has optional fields
        When:  it is constructed with no arguments
        Then:  all fields default to None (unfiltered query)
        """
        from dark_factory.domain.earthquake.value_objects import EarthquakeFilter

        f = EarthquakeFilter()
        # All filter fields should be None by default (unfiltered)
        for field in dataclasses.fields(f):
            assert getattr(f, field.name) is None, (
                f"Expected field '{field.name}' to default to None"
            )

    def test_earthquake_filter_is_dataclass(self) -> None:
        from dark_factory.domain.earthquake.value_objects import EarthquakeFilter

        assert dataclasses.is_dataclass(EarthquakeFilter)

    def test_value_objects_module_has_no_external_imports(self) -> None:
        """
        Given: the value_objects module is loaded
        When:  its global namespace is inspected
        Then:  fastapi, httpx, and pydantic are NOT imported
        """
        import importlib

        mod = importlib.import_module("dark_factory.domain.earthquake.value_objects")
        banned = {"fastapi", "httpx", "pydantic"}
        for name, obj in vars(mod).items():
            if hasattr(obj, "__module__") and obj.__module__:
                for banned_pkg in banned:
                    assert not obj.__module__.startswith(banned_pkg), (
                        f"Domain value_objects imports banned package '{banned_pkg}' "
                        f"via symbol '{name}'"
                    )
