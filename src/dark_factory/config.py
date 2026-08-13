"""
Application configuration via pydantic-settings.

All config flows through this module; env vars override defaults.
A .env file is loaded automatically if present.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Dark Factory.

    Fields can be overridden by environment variables (case-insensitive).
    For example, USGS_BASE_URL=https://... will override usgs_base_url.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    usgs_base_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
