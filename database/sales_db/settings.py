from __future__ import annotations

from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database tooling settings.

    Use SQLAlchemy URLs for migrations/query tooling:
    postgresql+psycopg://user:password@host:port/db
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/retail_bi"

    @cached_property
    def psycopg_url(self) -> str:
        """Return a psycopg-compatible DSN.

        psycopg.connect() expects postgresql://..., while SQLAlchemy uses
        postgresql+psycopg://... for the psycopg3 dialect.
        """
        return self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)


settings = DatabaseSettings()
