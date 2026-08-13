"""
Integration tests for OpenAPI metadata enrichment — spec-9-swagger-openapi-docs.

AC covered:
  - Given GET /openapi.json, when parsed, then `tags` array contains entries for
    "earthquakes" and "health", each with a non-empty `description`
  - Given GET /openapi.json, when parsed, then every operation object under `paths`
    has a non-empty `description` field (including health_check which currently has none)
  - Given GET /openapi.json, when parsed, then
    `paths["/api/v1/earthquakes"]["get"]["responses"]` contains key "502"
  - Given GET /openapi.json, when parsed, then
    `components.schemas.GeoJSONFeatureCollection` contains an `example` key with
    `type == "FeatureCollection"` and a non-empty `features` list

I/O & Edge-Case Matrix rows covered:
  - Tags have descriptions: GET /openapi.json → `tags` array includes entries for
    "earthquakes" and "health", each with non-empty `description` → Assert presence
  - All operations have description: GET /openapi.json → every operation object has a
    non-empty `description` field (including `health_check`) → Assert not absent/empty
  - Earthquakes list has 502: GET /openapi.json →
    `paths["/api/v1/earthquakes"]["get"]["responses"]` includes key "502" → Assert presence
  - Schema has example: GET /openapi.json →
    `components.schemas.GeoJSONFeatureCollection` includes an `example` key with a
    FeatureCollection shape → Assert presence and shape

TDD phase: RED — will fail until implementation adds openapi_tags, descriptions,
502 response, and json_schema_extra example.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# TestTagDescriptions
# ---------------------------------------------------------------------------


class TestTagDescriptions:
    """
    Given: GET /openapi.json is requested
    When:  the response is parsed
    Then:  the `tags` array contains entries for "earthquakes" and "health",
           each with a non-empty `description` field

    I/O Matrix row: Tags have descriptions
    """

    @pytest.mark.anyio
    async def test_tags_array_exists_in_openapi_json(self, async_client) -> None:
        """
        Given: the app is created via create_app()
        When:  GET /openapi.json
        Then:  response JSON contains a top-level "tags" key
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        assert "tags" in body, "openapi.json must contain a top-level 'tags' key"

    @pytest.mark.anyio
    async def test_earthquakes_tag_has_description(self, async_client) -> None:
        """
        Given: the app is created via create_app() with openapi_tags configured
        When:  GET /openapi.json
        Then:  the "tags" array contains an entry with name == "earthquakes"
               that has a non-empty "description" field

        I/O Matrix row: Tags have descriptions — "earthquakes" entry
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        tags: list[dict] = body.get("tags", [])

        earthquakes_tag = next(
            (t for t in tags if t.get("name") == "earthquakes"), None
        )
        assert earthquakes_tag is not None, (
            "tags array must contain an entry with name == 'earthquakes'"
        )
        description = earthquakes_tag.get("description", "")
        assert isinstance(description, str) and description.strip(), (
            "earthquakes tag must have a non-empty 'description' field"
        )

    @pytest.mark.anyio
    async def test_health_tag_has_description(self, async_client) -> None:
        """
        Given: the app is created via create_app() with openapi_tags configured
        When:  GET /openapi.json
        Then:  the "tags" array contains an entry with name == "health"
               that has a non-empty "description" field

        I/O Matrix row: Tags have descriptions — "health" entry
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        tags: list[dict] = body.get("tags", [])

        health_tag = next((t for t in tags if t.get("name") == "health"), None)
        assert health_tag is not None, (
            "tags array must contain an entry with name == 'health'"
        )
        description = health_tag.get("description", "")
        assert isinstance(description, str) and description.strip(), (
            "health tag must have a non-empty 'description' field"
        )

    @pytest.mark.anyio
    async def test_both_tags_present_in_tags_array(self, async_client) -> None:
        """
        Given: the app is created via create_app() with openapi_tags configured
        When:  GET /openapi.json
        Then:  both "earthquakes" and "health" are present in the tags array

        I/O Matrix row: Tags have descriptions — both entries present
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        tags: list[dict] = body.get("tags", [])
        tag_names = {t.get("name") for t in tags}

        assert "earthquakes" in tag_names, (
            "tags array must include an entry named 'earthquakes'"
        )
        assert "health" in tag_names, (
            "tags array must include an entry named 'health'"
        )


# ---------------------------------------------------------------------------
# TestOperationDescriptions
# ---------------------------------------------------------------------------


class TestOperationDescriptions:
    """
    Given: GET /openapi.json is requested
    When:  every operation object under `paths` is inspected
    Then:  each operation has a non-empty `description` field

    This will fail for the health_check endpoint which currently has no docstring
    and therefore no description in the OpenAPI spec.

    I/O Matrix row: All operations have description
    """

    _HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

    @pytest.mark.anyio
    async def test_every_operation_has_non_empty_description(
        self, async_client
    ) -> None:
        """
        Given: the OpenAPI spec is generated from the current app
        When:  all operation objects across all paths are collected
        Then:  every operation object has a non-empty "description" field

        I/O Matrix row: All operations have description — any missing triggers failure
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        paths: dict = body.get("paths", {})

        missing: list[str] = []
        for path, path_item in paths.items():
            for method in self._HTTP_METHODS:
                operation: dict | None = path_item.get(method)
                if operation is None:
                    continue
                description = operation.get("description", "")
                if not (isinstance(description, str) and description.strip()):
                    missing.append(f"{method.upper()} {path}")

        assert not missing, (
            f"The following operations are missing a non-empty 'description': "
            f"{missing}"
        )

    @pytest.mark.anyio
    async def test_health_check_operation_has_description(
        self, async_client
    ) -> None:
        """
        Given: the health_check route is defined inline inside create_app() and
               currently has no docstring (so its OpenAPI description is absent)
        When:  GET /openapi.json is parsed
        Then:  paths["/health"]["get"]["description"] is a non-empty string

        I/O Matrix row: All operations have description — health_check specifically
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        paths: dict = body.get("paths", {})

        health_operation = paths.get("/health", {}).get("get")
        assert health_operation is not None, (
            "paths must contain a GET /health operation"
        )
        description = health_operation.get("description", "")
        assert isinstance(description, str) and description.strip(), (
            "GET /health operation must have a non-empty 'description' field"
        )

    @pytest.mark.anyio
    async def test_list_earthquakes_operation_has_description(
        self, async_client
    ) -> None:
        """
        Given: the list_earthquakes route has a docstring today, but must also
               have an explicit description kwarg after enrichment
        When:  GET /openapi.json is parsed
        Then:  paths["/api/v1/earthquakes"]["get"]["description"] is non-empty

        I/O Matrix row: All operations have description — list_earthquakes
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        paths: dict = body.get("paths", {})

        operation = paths.get("/api/v1/earthquakes", {}).get("get")
        assert operation is not None, (
            "paths must contain a GET /api/v1/earthquakes operation"
        )
        description = operation.get("description", "")
        assert isinstance(description, str) and description.strip(), (
            "GET /api/v1/earthquakes operation must have a non-empty 'description' field"
        )

    @pytest.mark.anyio
    async def test_recent_earthquakes_operation_has_description(
        self, async_client
    ) -> None:
        """
        Given: the recent_earthquakes stub route
        When:  GET /openapi.json is parsed
        Then:  paths["/api/v1/earthquakes/recent"]["get"]["description"] is non-empty

        I/O Matrix row: All operations have description — recent_earthquakes stub
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        paths: dict = body.get("paths", {})

        operation = paths.get("/api/v1/earthquakes/recent", {}).get("get")
        assert operation is not None, (
            "paths must contain a GET /api/v1/earthquakes/recent operation"
        )
        description = operation.get("description", "")
        assert isinstance(description, str) and description.strip(), (
            "GET /api/v1/earthquakes/recent operation must have a non-empty "
            "'description' field"
        )

    @pytest.mark.anyio
    async def test_get_earthquake_by_id_operation_has_description(
        self, async_client
    ) -> None:
        """
        Given: the get_earthquake_by_id stub route
        When:  GET /openapi.json is parsed
        Then:  paths["/api/v1/earthquakes/{earthquake_id}"]["get"]["description"]
               is non-empty

        I/O Matrix row: All operations have description — get_earthquake_by_id stub
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        paths: dict = body.get("paths", {})

        operation = paths.get("/api/v1/earthquakes/{earthquake_id}", {}).get("get")
        assert operation is not None, (
            "paths must contain a GET /api/v1/earthquakes/{earthquake_id} operation"
        )
        description = operation.get("description", "")
        assert isinstance(description, str) and description.strip(), (
            "GET /api/v1/earthquakes/{earthquake_id} operation must have a non-empty "
            "'description' field"
        )


# ---------------------------------------------------------------------------
# TestEarthquakesListResponses
# ---------------------------------------------------------------------------


class TestEarthquakesListResponses:
    """
    Given: GET /openapi.json is requested
    When:  paths["/api/v1/earthquakes"]["get"]["responses"] is inspected
    Then:  the responses object contains key "502"

    I/O Matrix row: Earthquakes list has 502
    """

    @pytest.mark.anyio
    async def test_earthquakes_list_responses_contains_502(
        self, async_client
    ) -> None:
        """
        Given: the list_earthquakes operation does not yet declare a 502 response
        When:  GET /openapi.json is parsed
        Then:  paths["/api/v1/earthquakes"]["get"]["responses"] contains key "502"

        I/O Matrix row: Earthquakes list has 502 — Assert presence
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        paths: dict = body.get("paths", {})

        operation = paths.get("/api/v1/earthquakes", {}).get("get")
        assert operation is not None, (
            "paths must contain a GET /api/v1/earthquakes operation"
        )
        responses: dict = operation.get("responses", {})
        assert "502" in responses, (
            "GET /api/v1/earthquakes responses must include a '502' entry for "
            "upstream USGS errors"
        )

    @pytest.mark.anyio
    async def test_earthquakes_list_502_response_has_description(
        self, async_client
    ) -> None:
        """
        Given: the list_earthquakes operation with a 502 responses entry
        When:  GET /openapi.json is parsed
        Then:  the "502" entry has a non-empty "description" field

        I/O Matrix row: Earthquakes list has 502 — Assert presence and shape
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        paths: dict = body.get("paths", {})

        operation = paths.get("/api/v1/earthquakes", {}).get("get", {})
        responses: dict = operation.get("responses", {})
        entry_502: dict | None = responses.get("502")
        assert entry_502 is not None, (
            "GET /api/v1/earthquakes responses must include a '502' entry"
        )
        description = entry_502.get("description", "")
        assert isinstance(description, str) and description.strip(), (
            "The '502' response entry must have a non-empty 'description' field"
        )


# ---------------------------------------------------------------------------
# TestGeoJSONSchemaExample
# ---------------------------------------------------------------------------


class TestGeoJSONSchemaExample:
    """
    Given: GET /openapi.json is requested
    When:  components.schemas.GeoJSONFeatureCollection is inspected
    Then:  the schema contains an `example` key with `type == "FeatureCollection"`
           and a non-empty `features` list

    I/O Matrix row: Schema has example
    """

    @pytest.mark.anyio
    async def test_geojson_feature_collection_schema_has_example_key(
        self, async_client
    ) -> None:
        """
        Given: GeoJSONFeatureCollection has no json_schema_extra configured yet
        When:  GET /openapi.json is parsed
        Then:  components["schemas"]["GeoJSONFeatureCollection"] contains an "example" key

        I/O Matrix row: Schema has example — Assert presence
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        schemas: dict = body.get("components", {}).get("schemas", {})

        schema = schemas.get("GeoJSONFeatureCollection")
        assert schema is not None, (
            "components.schemas must contain 'GeoJSONFeatureCollection'"
        )
        assert "example" in schema, (
            "GeoJSONFeatureCollection schema must have an 'example' key "
            "(add json_schema_extra via ConfigDict)"
        )

    @pytest.mark.anyio
    async def test_geojson_feature_collection_example_type_is_feature_collection(
        self, async_client
    ) -> None:
        """
        Given: GeoJSONFeatureCollection schema has an example added via json_schema_extra
        When:  GET /openapi.json is parsed
        Then:  example["type"] == "FeatureCollection"

        I/O Matrix row: Schema has example — Assert shape: type == "FeatureCollection"
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        schemas: dict = body.get("components", {}).get("schemas", {})

        schema = schemas.get("GeoJSONFeatureCollection", {})
        example: dict = schema.get("example", {})
        assert example.get("type") == "FeatureCollection", (
            "GeoJSONFeatureCollection example must have type == 'FeatureCollection'"
        )

    @pytest.mark.anyio
    async def test_geojson_feature_collection_example_has_non_empty_features(
        self, async_client
    ) -> None:
        """
        Given: GeoJSONFeatureCollection schema has an example added via json_schema_extra
        When:  GET /openapi.json is parsed
        Then:  example["features"] is a non-empty list

        I/O Matrix row: Schema has example — Assert shape: non-empty features
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        schemas: dict = body.get("components", {}).get("schemas", {})

        schema = schemas.get("GeoJSONFeatureCollection", {})
        example: dict = schema.get("example", {})
        features = example.get("features")
        assert isinstance(features, list) and len(features) > 0, (
            "GeoJSONFeatureCollection example must have a non-empty 'features' list"
        )

    @pytest.mark.anyio
    async def test_geojson_feature_collection_example_feature_has_geometry(
        self, async_client
    ) -> None:
        """
        Given: GeoJSONFeatureCollection schema example has at least one feature
        When:  GET /openapi.json is parsed
        Then:  the first feature has a "geometry" key with type == "Point"
               and a "coordinates" list of three floats

        I/O Matrix row: Schema has example — Assert shape: feature geometry structure
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        schemas: dict = body.get("components", {}).get("schemas", {})

        schema = schemas.get("GeoJSONFeatureCollection", {})
        example: dict = schema.get("example", {})
        features: list = example.get("features", [])
        assert len(features) > 0, (
            "GeoJSONFeatureCollection example must have at least one feature"
        )

        first_feature = features[0]
        geometry = first_feature.get("geometry")
        assert geometry is not None, "Example feature must have a 'geometry' key"
        assert geometry.get("type") == "Point", (
            "Example feature geometry must have type == 'Point'"
        )
        coordinates = geometry.get("coordinates", [])
        assert isinstance(coordinates, list) and len(coordinates) == 3, (
            "Example feature geometry coordinates must be a list of 3 values "
            "[longitude, latitude, depth]"
        )

    @pytest.mark.anyio
    async def test_geojson_feature_collection_example_feature_has_properties(
        self, async_client
    ) -> None:
        """
        Given: GeoJSONFeatureCollection schema example has at least one feature
        When:  GET /openapi.json is parsed
        Then:  the first feature has a "properties" key containing "id" and "mag"

        I/O Matrix row: Schema has example — Assert shape: feature properties structure
        """
        response = await async_client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        schemas: dict = body.get("components", {}).get("schemas", {})

        schema = schemas.get("GeoJSONFeatureCollection", {})
        example: dict = schema.get("example", {})
        features: list = example.get("features", [])
        assert len(features) > 0, (
            "GeoJSONFeatureCollection example must have at least one feature"
        )

        first_feature = features[0]
        properties = first_feature.get("properties")
        assert properties is not None, "Example feature must have a 'properties' key"
        assert "id" in properties, (
            "Example feature properties must include an 'id' key"
        )
        assert "mag" in properties, (
            "Example feature properties must include a 'mag' key"
        )
