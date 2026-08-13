"""
Unit tests for dark_factory.application.earthquake.handlers

AC covered:
  - Given uv sync completed, when uv run pytest tests/ -q runs, then 0 failures
  - Application handler stubs return empty list / None without implementation
  - Handlers accept the repo port; domain is never bypassed

I/O & Edge-Case Matrix rows covered:
  - App cold start, default env: handler can be instantiated with a fake repo
  - pytest on stub suite: handler stub tests pass once implementation lands

TDD phase: RED — will fail with ImportError until handlers.py is created.
"""

from __future__ import annotations

import pytest


class TestGetEarthquakesHandler:
    """
    Given: a GetEarthquakesHandler and a FakeEarthquakeRepository
    When:  handle() is called with a GetEarthquakes query
    Then:  it returns an empty list (stub behaviour before USGS integration)
    """

    @pytest.mark.anyio
    async def test_get_earthquakes_handler_can_be_imported(self) -> None:
        from dark_factory.application.earthquake.handlers import (  # noqa: F401
            GetEarthquakesHandler,
        )

    @pytest.mark.anyio
    async def test_get_earthquakes_returns_list(self) -> None:
        """
        Given: a FakeEarthquakeRepository with zero items
        When:  GetEarthquakesHandler.handle() is awaited
        Then:  the result is a list (empty at stub stage)
        """
        from dark_factory.application.earthquake.handlers import GetEarthquakesHandler
        from dark_factory.application.earthquake.queries import GetEarthquakes

        class _FakeRepo:
            async def get_all(self, filters=None):
                return []

            async def get_by_id(self, earthquake_id: str):
                return None

        handler = GetEarthquakesHandler(repository=_FakeRepo())
        query = GetEarthquakes(filters=None)
        result = await handler.handle(query)

        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_get_earthquakes_with_empty_repo_returns_empty_list(self) -> None:
        """
        Given: a FakeEarthquakeRepository that stores no earthquakes
        When:  GetEarthquakesHandler.handle() is called
        Then:  the handler returns []
        """
        from dark_factory.application.earthquake.handlers import GetEarthquakesHandler
        from dark_factory.application.earthquake.queries import GetEarthquakes

        class _EmptyRepo:
            async def get_all(self, filters=None):
                return []

            async def get_by_id(self, earthquake_id: str):
                return None

        handler = GetEarthquakesHandler(repository=_EmptyRepo())
        result = await handler.handle(GetEarthquakes(filters=None))

        assert result == []


class TestGetEarthquakeByIdHandler:
    """
    Given: a GetEarthquakeByIdHandler and a FakeEarthquakeRepository
    When:  handle() is called with an ID that does not exist
    Then:  it returns None (stub behaviour)
    """

    @pytest.mark.anyio
    async def test_get_by_id_handler_can_be_imported(self) -> None:
        from dark_factory.application.earthquake.handlers import (  # noqa: F401
            GetEarthquakeByIdHandler,
        )

    @pytest.mark.anyio
    async def test_get_by_id_returns_none_for_unknown_id(self) -> None:
        """
        Given: a FakeEarthquakeRepository with no matching entry
        When:  GetEarthquakeByIdHandler.handle() is called with an unknown ID
        Then:  the result is None
        """
        from dark_factory.application.earthquake.handlers import GetEarthquakeByIdHandler
        from dark_factory.application.earthquake.queries import GetEarthquakeById

        class _EmptyRepo:
            async def get_all(self, filters=None):
                return []

            async def get_by_id(self, earthquake_id: str):
                return None

        handler = GetEarthquakeByIdHandler(repository=_EmptyRepo())
        result = await handler.handle(GetEarthquakeById(id="nonexistent-id"))

        assert result is None


class TestQueryDataclasses:
    """
    Given: the application queries module
    When:  GetEarthquakes and GetEarthquakeById are imported
    Then:  they are constructable dataclasses
    """

    def test_get_earthquakes_query_importable(self) -> None:
        from dark_factory.application.earthquake.queries import GetEarthquakes  # noqa: F401

    def test_get_earthquake_by_id_query_importable(self) -> None:
        from dark_factory.application.earthquake.queries import GetEarthquakeById  # noqa: F401

    def test_get_earthquakes_query_construction(self) -> None:
        import dataclasses

        from dark_factory.application.earthquake.queries import GetEarthquakes

        q = GetEarthquakes(filters=None)
        assert dataclasses.is_dataclass(q)

    def test_get_earthquake_by_id_query_construction(self) -> None:
        import dataclasses

        from dark_factory.application.earthquake.queries import GetEarthquakeById

        q = GetEarthquakeById(id="us7000abc1")
        assert q.id == "us7000abc1"
        assert dataclasses.is_dataclass(q)
