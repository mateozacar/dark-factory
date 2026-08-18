"""
Unit tests for dark_factory.application.earthquake.handlers.GetAftershocksHandler

AC covered:
  - Given a valid event ID and aftershocks with first-half rate > second-half rate,
    when GetAftershocksHandler.handle() is called, then AftershockResult.sequence_assessment
    == "decaying" and count is correct
  - Given a valid event ID and aftershocks with second-half rate >= first-half rate,
    when GetAftershocksHandler.handle() is called, then sequence_assessment == "active"
  - Given a valid event ID and fewer than 3 aftershocks,
    when GetAftershocksHandler.handle() is called, then sequence_assessment == "insufficient_data"
  - Given an unknown event ID (repo.get_by_id returns None),
    when GetAftershocksHandler.handle() is called, then EarthquakeNotFound is raised

I/O & Edge-Case Matrix rows covered:
  - Happy path — decaying: 4 aftershocks, 3 in first half, 1 in second
  - Happy path — active:   4 aftershocks, 1 in first half, 3 in second
  - Insufficient data:     < 3 aftershocks
  - Main event not found:  repo.get_by_id returns None → EarthquakeNotFound

TDD phase: RED — will fail with ImportError/AttributeError until
  GetAftershocksHandler, GetAftershocks, EarthquakeNotFound, and AftershockResult
  are implemented.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Timeline constants used across all handler tests
#
# Main event: 2025-01-01T00:00:00Z
# Window (days=30):  ends   2025-01-31T00:00:00Z
#                    mid    2025-01-16T00:00:00Z  (days/2 = 15 days later)
#
# First-half timestamps  (time < midpoint):
#   A: 2025-01-05T00:00:00Z
#   B: 2025-01-08T00:00:00Z
#   C: 2025-01-12T00:00:00Z
#
# Second-half timestamps (time >= midpoint):
#   D: 2025-01-20T00:00:00Z
# ---------------------------------------------------------------------------

_MAIN_TIME = "2025-01-01T00:00:00Z"

_AFTERSHOCK_FIRST_HALF_A = "2025-01-05T00:00:00Z"
_AFTERSHOCK_FIRST_HALF_B = "2025-01-08T00:00:00Z"
_AFTERSHOCK_FIRST_HALF_C = "2025-01-12T00:00:00Z"
_AFTERSHOCK_SECOND_HALF  = "2025-01-20T00:00:00Z"

# ---------------------------------------------------------------------------
# Inline fake repository (no conftest dependency)
# ---------------------------------------------------------------------------


class _FakeRepo:
    """
    Minimal in-memory fake that satisfies both get_by_id and get_all without
    importing or depending on the real EarthquakeRepository ABC.
    """

    def __init__(
        self,
        main_event: object,
        aftershocks: list[object],
    ) -> None:
        self._main = main_event
        self._aftershocks = aftershocks

    async def get_by_id(self, earthquake_id: str) -> object:
        return self._main

    async def get_all(self, filters: object = None) -> list[object]:
        return list(self._aftershocks)


class _FakeEmptyRepo:
    """Repo that returns None from get_by_id (simulates unknown event ID)."""

    async def get_by_id(self, earthquake_id: str) -> None:
        return None

    async def get_all(self, filters: object = None) -> list[object]:
        return []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetAftershocksHandlerDecaying:
    """
    Given: a valid main event and 4 aftershocks where 3 fall in the first half
           of the time window and 1 falls in the second half
    When:  GetAftershocksHandler.handle(GetAftershocks(...)) is awaited
    Then:  AftershockResult.sequence_assessment == "decaying"
           and AftershockResult.count == 4
    """

    @pytest.mark.anyio
    async def test_decaying_sequence_assessment_and_count(self) -> None:
        """
        I/O Matrix row: Happy path — decaying (3 first-half, 1 second-half)
        """
        from dark_factory.application.earthquake.handlers import GetAftershocksHandler
        from dark_factory.application.earthquake.queries import GetAftershocks
        from dark_factory.domain.earthquake.entities import AftershockResult, Earthquake

        main = Earthquake(
            id="us7000main",
            magnitude=6.0,
            depth=15.0,
            latitude=37.5,
            longitude=-122.1,
            time=_MAIN_TIME,
        )

        aftershocks = [
            Earthquake(id="as001", magnitude=3.1, depth=10.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_FIRST_HALF_A),
            Earthquake(id="as002", magnitude=2.9, depth=11.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_FIRST_HALF_B),
            Earthquake(id="as003", magnitude=3.3, depth=12.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_FIRST_HALF_C),
            Earthquake(id="as004", magnitude=2.7, depth=13.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_SECOND_HALF),
        ]

        repo = _FakeRepo(main_event=main, aftershocks=aftershocks)
        handler = GetAftershocksHandler(repository=repo)
        query = GetAftershocks(earthquake_id="us7000main", days=30)

        result = await handler.handle(query)

        assert isinstance(result, AftershockResult)
        assert result.sequence_assessment == "decaying"
        assert result.count == 4


class TestGetAftershocksHandlerActive:
    """
    Given: a valid main event and 4 aftershocks where 1 falls in the first half
           of the time window and 3 fall in the second half
    When:  GetAftershocksHandler.handle(GetAftershocks(...)) is awaited
    Then:  AftershockResult.sequence_assessment == "active"
           and AftershockResult.count == 4
    """

    @pytest.mark.anyio
    async def test_active_sequence_assessment_and_count(self) -> None:
        """
        I/O Matrix row: Happy path — active (1 first-half, 3 second-half)
        """
        from dark_factory.application.earthquake.handlers import GetAftershocksHandler
        from dark_factory.application.earthquake.queries import GetAftershocks
        from dark_factory.domain.earthquake.entities import AftershockResult, Earthquake

        main = Earthquake(
            id="us7000main",
            magnitude=6.0,
            depth=15.0,
            latitude=37.5,
            longitude=-122.1,
            time=_MAIN_TIME,
        )

        # Three timestamps in the second half: Jan 17, 20, 25 (all >= mid Jan 16)
        aftershocks = [
            Earthquake(id="as011", magnitude=3.0, depth=10.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_FIRST_HALF_A),
            Earthquake(id="as012", magnitude=2.8, depth=11.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_SECOND_HALF),
            Earthquake(id="as013", magnitude=2.6, depth=12.0, latitude=37.5, longitude=-122.1, time="2025-01-17T00:00:00Z"),
            Earthquake(id="as014", magnitude=2.5, depth=13.0, latitude=37.5, longitude=-122.1, time="2025-01-25T00:00:00Z"),
        ]

        repo = _FakeRepo(main_event=main, aftershocks=aftershocks)
        handler = GetAftershocksHandler(repository=repo)
        query = GetAftershocks(earthquake_id="us7000main", days=30)

        result = await handler.handle(query)

        assert isinstance(result, AftershockResult)
        assert result.sequence_assessment == "active"
        assert result.count == 4


class TestGetAftershocksHandlerInsufficientData:
    """
    Given: a valid main event and fewer than 3 aftershocks
    When:  GetAftershocksHandler.handle(GetAftershocks(...)) is awaited
    Then:  AftershockResult.sequence_assessment == "insufficient_data"
           and AftershockResult.count < 3

    I/O Matrix rows covered:
      - Insufficient data: < 3 aftershocks → "insufficient_data"
      - Zero aftershocks:  count=0, stats fields all None (or null)
    """

    @pytest.mark.anyio
    async def test_two_aftershocks_gives_insufficient_data(self) -> None:
        """Fewer than 3 total aftershocks → insufficient_data."""
        from dark_factory.application.earthquake.handlers import GetAftershocksHandler
        from dark_factory.application.earthquake.queries import GetAftershocks
        from dark_factory.domain.earthquake.entities import AftershockResult, Earthquake

        main = Earthquake(
            id="us7000main",
            magnitude=6.0,
            depth=15.0,
            latitude=37.5,
            longitude=-122.1,
            time=_MAIN_TIME,
        )

        aftershocks = [
            Earthquake(id="as021", magnitude=3.0, depth=10.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_FIRST_HALF_A),
            Earthquake(id="as022", magnitude=2.8, depth=11.0, latitude=37.5, longitude=-122.1, time=_AFTERSHOCK_FIRST_HALF_B),
        ]

        repo = _FakeRepo(main_event=main, aftershocks=aftershocks)
        handler = GetAftershocksHandler(repository=repo)
        query = GetAftershocks(earthquake_id="us7000main", days=30)

        result = await handler.handle(query)

        assert isinstance(result, AftershockResult)
        assert result.sequence_assessment == "insufficient_data"
        assert result.count < 3

    @pytest.mark.anyio
    async def test_zero_aftershocks_gives_insufficient_data_and_null_stats(self) -> None:
        """
        I/O Matrix row: Zero aftershocks → insufficient_data, count=0,
        stats fields (max_magnitude, avg_magnitude, largest_aftershock_id) all None.
        """
        from dark_factory.application.earthquake.handlers import GetAftershocksHandler
        from dark_factory.application.earthquake.queries import GetAftershocks
        from dark_factory.domain.earthquake.entities import AftershockResult, Earthquake

        main = Earthquake(
            id="us7000main",
            magnitude=6.0,
            depth=15.0,
            latitude=37.5,
            longitude=-122.1,
            time=_MAIN_TIME,
        )

        repo = _FakeRepo(main_event=main, aftershocks=[])
        handler = GetAftershocksHandler(repository=repo)
        query = GetAftershocks(earthquake_id="us7000main", days=30)

        result = await handler.handle(query)

        assert isinstance(result, AftershockResult)
        assert result.sequence_assessment == "insufficient_data"
        assert result.count == 0
        assert result.max_magnitude is None
        assert result.avg_magnitude is None
        assert result.largest_aftershock_id is None


class TestGetAftershocksHandlerNotFound:
    """
    Given: the repository returns None for get_by_id (unknown event ID)
    When:  GetAftershocksHandler.handle(GetAftershocks(...)) is awaited
    Then:  EarthquakeNotFound is raised with the correct event_id

    I/O Matrix row: Main event not found → EarthquakeNotFound → HTTP 404
    """

    @pytest.mark.anyio
    async def test_unknown_event_id_raises_earthquake_not_found(self) -> None:
        """
        Given: repo.get_by_id returns None
        When:  handler.handle() is awaited with the same unknown ID
        Then:  EarthquakeNotFound is raised and its event_id matches the query
        """
        from dark_factory.application.earthquake.handlers import GetAftershocksHandler
        from dark_factory.application.earthquake.queries import GetAftershocks
        from dark_factory.domain.earthquake.exceptions import EarthquakeNotFound

        repo = _FakeEmptyRepo()
        handler = GetAftershocksHandler(repository=repo)
        query = GetAftershocks(earthquake_id="unknown-id-9999", days=30)

        with pytest.raises(EarthquakeNotFound) as exc_info:
            await handler.handle(query)

        assert exc_info.value.event_id == "unknown-id-9999"
