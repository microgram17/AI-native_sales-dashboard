"""Mints the short-lived internal JWT the backend sends to the MCP server.

This token carries the trusted supplier context server-to-server. It is
infrastructure only: it never becomes an LLM prompt, an MCP tool argument, part
of a ToolPlan, or a model-visible field.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config import Settings


def mint_mcp_context_token(
    *, user_id: str, supplier_id: str, roles: list[str], settings: Settings
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "supplier_id": supplier_id,
        "roles": roles,
        "iss": settings.mcp_jwt_issuer,
        "aud": settings.mcp_jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.mcp_jwt_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.mcp_jwt_secret, algorithm=settings.mcp_jwt_algorithm)
