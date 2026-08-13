"""
Interface — FastAPI dependency injection wiring.

Stub: returns a placeholder until the infrastructure story wires the real adapter.
"""

from __future__ import annotations

from typing import Any


def get_earthquake_repository() -> Any:
    """DI stub — returns None until USGSAdapter is wired via the lifespan client."""
    return None
