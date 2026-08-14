from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend runtime settings loaded from environment or backend/.env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/retail_bi"

    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    # Streamable-HTTP URL of the MCP analytics server. A trailing slash is
    # stripped by the client to avoid a 307 redirect on POST.
    mcp_server_url: str = "http://localhost:8001/mcp"

    # Short-lived context token minted for MCP (must match the MCP server's
    # MCP_JWT_* settings). The secret is a non-production placeholder.
    mcp_jwt_secret: str = "dev-mcp-shared-secret-change-me-please"
    mcp_jwt_algorithm: str = "HS256"
    mcp_jwt_issuer: str = "retail-bi-backend"
    mcp_jwt_audience: str = "retail-bi-mcp"
    mcp_jwt_ttl_seconds: int = 180

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
