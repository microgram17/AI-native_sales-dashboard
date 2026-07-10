from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class Settings(BaseSettings):
    """Runtime settings for the MCP server.

    Use postgresql+psycopg://... because SQLAlchemy is using psycopg3.
    When running inside docker compose, host is usually "postgres".
    When running from the host machine, host is usually "localhost" with the exposed port.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/retail_bi"
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.sql_echo,
        pool_pre_ping=True,
    )


async def dispose_engine() -> None:
    await get_engine().dispose()
