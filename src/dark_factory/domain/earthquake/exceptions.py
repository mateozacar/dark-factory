"""
Domain exceptions for the earthquake bounded context.

Uses stdlib only — zero external imports (AD-2).
"""

from __future__ import annotations


class EarthquakeNotFound(Exception):
    """Raised when a requested earthquake event ID does not exist."""

    def __init__(self, event_id: str) -> None:
        super().__init__(f"Earthquake not found: {event_id}")
        self.event_id = event_id
