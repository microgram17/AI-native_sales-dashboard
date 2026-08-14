"""Minimal MCP integration for the agent.

Responsible only for connecting to the existing MCP server, listing tools and
calling tools by name via the MCP SDK. It contains no prompts, no analytics
interpretation, no visualization decisions and no supplier selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class McpClientError(Exception):
    """A transport or protocol failure while talking to the MCP server."""


@dataclass(frozen=True)
class McpToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class McpToolResult:
    """Outcome of a tool call. is_error marks a tool/protocol error (not a
    business outcome); structured holds the tool's structuredContent."""

    structured: dict[str, Any] | None
    is_error: bool
    error_message: str | None = None


class McpClient:
    def __init__(self, url: str) -> None:
        # Strip a trailing slash to avoid a 307 redirect on POST.
        self._url = url.rstrip("/")

    @staticmethod
    def _headers(token: str | None) -> dict[str, str] | None:
        # Per-call header so concurrent requests for different suppliers stay isolated.
        return {"Authorization": f"Bearer {token}"} if token else None

    async def list_tools(self, token: str | None = None) -> list[McpToolDefinition]:
        try:
            async with streamablehttp_client(self._url, headers=self._headers(token)) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
        except Exception as exc:  # noqa: BLE001 - normalize any transport failure
            raise McpClientError(f"Failed to list MCP tools: {exc}") from exc

        return [
            McpToolDefinition(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.inputSchema or {},
            )
            for tool in result.tools
        ]

    async def call_tool(
        self, name: str, arguments: dict[str, Any], token: str | None = None
    ) -> McpToolResult:
        try:
            async with streamablehttp_client(self._url, headers=self._headers(token)) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
        except Exception as exc:  # noqa: BLE001 - normalize any transport failure
            raise McpClientError(f"MCP tool call failed for '{name}': {exc}") from exc

        error_message = None
        if result.isError:
            error_message = _first_text(result) or "Tool reported an error."
        return McpToolResult(
            structured=result.structuredContent,
            is_error=bool(result.isError),
            error_message=error_message,
        )


def _first_text(result: Any) -> str | None:
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            return text
    return None
