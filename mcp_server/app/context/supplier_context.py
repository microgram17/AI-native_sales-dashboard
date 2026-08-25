"""Trusted supplier context resolution for MCP tools.

The supplier identity is NEVER a model-visible tool argument. For authenticated
requests it is extracted from a short-lived JWT that the backend mints after it
resolves the trusted supplier membership, sent as ``Authorization: Bearer``.
Every environment requires this authenticated context.
"""

from __future__ import annotations

from typing import Protocol

import jwt
from mcp.server.fastmcp import Context

from app.db.engine import get_settings


class SupplierContextError(Exception):
    """Raised when a trusted supplier context cannot be established."""


class SupplierResolver(Protocol):
    """Trusted supplier source used by MCP tool registration."""

    def resolve(self, ctx: Context) -> str: ...


def _bearer_token(ctx: Context) -> str | None:
    try:
        request_context = ctx.request_context
    except Exception:  # noqa: BLE001 - no active HTTP request context
        return None
    request = getattr(request_context, "request", None)
    headers = getattr(request, "headers", None)
    if not headers:
        return None
    raw = headers.get("authorization") or headers.get("Authorization")
    if not raw:
        return None
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise SupplierContextError("Malformed Authorization header; expected Bearer token.")
    return token.strip()


class SupplierContextResolver:
    """Resolves the trusted supplier_id for the current MCP request."""

    def __init__(
        self,
        *,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        jwt_issuer: str | None = None,
        jwt_audience: str | None = None,
    ) -> None:
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._jwt_issuer = jwt_issuer
        self._jwt_audience = jwt_audience

    def resolve(self, ctx: Context) -> str:
        token = _bearer_token(ctx)
        if token is not None:
            return self._supplier_from_token(token)

        raise SupplierContextError(
            "No authenticated supplier context. A valid Authorization: Bearer "
            "token is required."
        )

    def _supplier_from_token(self, token: str) -> str:
        options = {"require": ["exp"], "verify_aud": self._jwt_audience is not None}
        try:
            claims = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
                issuer=self._jwt_issuer,
                audience=self._jwt_audience,
                options=options,
            )
        except jwt.PyJWTError as exc:
            raise SupplierContextError(f"Invalid MCP context token: {exc}") from exc

        supplier_id = claims.get("supplier_id")
        if not supplier_id:
            raise SupplierContextError("MCP context token is missing supplier_id.")
        return str(supplier_id)


def build_supplier_context_resolver() -> SupplierContextResolver:
    settings = get_settings()
    return SupplierContextResolver(
        jwt_secret=settings.mcp_jwt_secret,
        jwt_algorithm=settings.mcp_jwt_algorithm,
        jwt_issuer=settings.mcp_jwt_issuer,
        jwt_audience=settings.mcp_jwt_audience,
    )
