"""
Unit tests for dark_factory.infrastructure.usgs.mappers.USGSMapper

AC covered:
  - Given a sample USGS feature, when USGSMapper.feature_to_earthquake(feature),
    then returns correct Earthquake with all five fields

I/O & Edge-Case Matrix rows covered:
  - Mapper happy path: USGS feature dict with id, properties.mag,
    geometry.coordinates[lon, lat, depth] → Earthquake(id, magnitude, depth, latitude, longitude)
    all set correctly

TDD phase: RED — will fail with NotImplementedError until mappers.py is implemented.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Minimal sample USGS GeoJSON feature (mirrors fixture at tests/fixtures/usgs_response.json)
# ---------------------------------------------------------------------------

SAMPLE_FEATURE: dict = {
    "type": "Feature",
    "id": "us7000abc1",
    "geometry": {
        "type": "Point",
        "coordinates": [-122.1, 37.5, 10.0],
    },
    "properties": {
        "mag": 5.2,
        "place": "10km N of Test City, CA",
        "time": 1709294400000,
    },
}

SECOND_FEATURE: dict = {
    "type": "Feature",
    "id": "us7000def2",
    "geometry": {
        "type": "Point",
        "coordinates": [139.7, 35.7, 22.5],
    },
    "properties": {
        "mag": 4.8,
        "place": "15km E of Tokyo, Japan",
    },
}


class TestUSGSMapperFeatureToEarthquake:
    """
    Given: a USGS GeoJSON feature dict
    When:  USGSMapper.feature_to_earthquake(feature) is called
    Then:  an Earthquake domain entity is returned with all five fields correctly mapped
    """

    def test_mapper_can_be_imported(self) -> None:
        """
        Given: the infrastructure usgs mappers module exists
        When:  USGSMapper is imported
        Then:  it is importable without error
        """
        from dark_factory.infrastructure.usgs.mappers import USGSMapper  # noqa: F401

    def test_feature_to_earthquake_returns_earthquake_instance(self) -> None:
        """
        Given: a valid USGS feature dict
        When:  USGSMapper.feature_to_earthquake() is called
        Then:  the returned object is an Earthquake domain entity
        """
        from dark_factory.domain.earthquake.entities import Earthquake
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        assert isinstance(result, Earthquake)

    def test_feature_id_maps_to_earthquake_id(self) -> None:
        """
        Given: a USGS feature with id="us7000abc1"
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the resulting Earthquake.id equals "us7000abc1"
        """
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        assert result.id == "us7000abc1"

    def test_properties_mag_maps_to_magnitude(self) -> None:
        """
        Given: a USGS feature with properties.mag = 5.2
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the resulting Earthquake.magnitude equals 5.2
        """
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        assert result.magnitude == 5.2

    def test_coordinates_index_2_maps_to_depth(self) -> None:
        """
        Given: a USGS feature with geometry.coordinates = [lon, lat, depth]
               where depth (index 2) is 10.0
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the resulting Earthquake.depth equals 10.0
        """
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        assert result.depth == 10.0

    def test_coordinates_index_1_maps_to_latitude(self) -> None:
        """
        Given: a USGS feature with geometry.coordinates = [lon, lat, depth]
               where latitude (index 1) is 37.5
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the resulting Earthquake.latitude equals 37.5
        """
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        assert result.latitude == 37.5

    def test_coordinates_index_0_maps_to_longitude(self) -> None:
        """
        Given: a USGS feature with geometry.coordinates = [lon, lat, depth]
               where longitude (index 0) is -122.1
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the resulting Earthquake.longitude equals -122.1
        """
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        assert result.longitude == -122.1

    def test_all_five_fields_mapped_correctly_in_one_assertion(self) -> None:
        """
        Given: a USGS feature with id="us7000abc1", mag=5.2,
               coordinates=[-122.1, 37.5, 10.0], and time=1709294400000
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the Earthquake entity has id="us7000abc1", magnitude=5.2,
               depth=10.0, latitude=37.5, longitude=-122.1, time="2024-03-01T12:00:00Z"
        """
        from dark_factory.domain.earthquake.entities import Earthquake
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        expected = Earthquake(
            id="us7000abc1",
            magnitude=5.2,
            depth=10.0,
            latitude=37.5,
            longitude=-122.1,
            time="2024-03-01T12:00:00Z",
        )
        assert result == expected

    def test_time_field_maps_to_iso8601(self) -> None:
        """
        Given: a USGS feature with properties.time = 1709294400000 (ms epoch)
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the resulting Earthquake.time equals "2024-03-01T12:00:00Z"

        I/O Matrix row: time ms-epoch → ISO-8601 UTC string
        """
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SAMPLE_FEATURE)

        assert result.time == "2024-03-01T12:00:00Z"

    def test_second_feature_maps_all_five_fields_correctly(self) -> None:
        """
        Given: a second USGS feature with id="us7000def2", mag=4.8,
               and coordinates=[139.7, 35.7, 22.5]
        When:  USGSMapper.feature_to_earthquake(feature) is called
        Then:  the Earthquake entity has id="us7000def2", magnitude=4.8,
               depth=22.5, latitude=35.7, longitude=139.7
        """
        from dark_factory.domain.earthquake.entities import Earthquake
        from dark_factory.infrastructure.usgs.mappers import USGSMapper

        result = USGSMapper.feature_to_earthquake(SECOND_FEATURE)

        expected = Earthquake(
            id="us7000def2",
            magnitude=4.8,
            depth=22.5,
            latitude=35.7,
            longitude=139.7,
        )
        assert result == expected
