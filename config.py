"""
config.py

Central application settings, loaded from environment variables (and
optionally a .env file — see .env.example for the recognized keys).
Every other module that needs a configurable value (session TTL, CORS
origins, the database URL) should read it from here via get_settings()
rather than hardcoding it.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SQLAlchemy connection string. Defaults to a local PostgreSQL
    # instance; db/connection.py also supports sqlite:// URLs (used by
    # the test suite) via a conditional connect_args.
    database_url: str = "postgresql://cna_user:cna_password@localhost:5432/cna"

    # How long an issued session token stays valid (api/auth.py).
    session_ttl_hours: int = 8

    # Origins allowed to call the API with credentials — the dashboard
    # dev server's ports by default (see dashboard/vite.config.js).
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # PBKDF2 iteration count for password hashing (schema/user.py).
    # Kept here so it can be tuned without touching hashing code.
    pbkdf2_iterations: int = 260_000


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings instance, built once and cached.
    Safe to call repeatedly from anywhere — subsequent calls are free.
    """
    return Settings()
