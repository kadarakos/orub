"""Settings loaded from the environment / .env. See design doc §2, §8.

pydantic is used here because environment variables are untrusted-boundary
input, same as Discogs API responses and FastAPI request bodies -- once
loaded, a Settings instance is just plain validated data.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    discogs_token: str
    discogs_user_agent: str = "orub/0.1"
    database_url: str = "sqlite:///orub.db"
