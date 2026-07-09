from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_server_url: str = "http://mcp_server:8000/mcp"
    cors_origins: list[str] = ["*"]
    agent_model: str = "openai/gpt-4.1-mini"
    openai_api_key: str | None = None
    google_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
