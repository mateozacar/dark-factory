"""
Domain filter dataclass: EarthquakeFilter (canonical domain definition).

This module re-exports the filter from value_objects so it is also importable
directly from dark_factory.domain.earthquake.filters, as expected by the story.
Uses stdlib only — zero external imports (AD-2).
"""

from __future__ import annotations

from dark_factory.domain.earthquake.value_objects import EarthquakeFilter

__all__ = ["EarthquakeFilter"]
