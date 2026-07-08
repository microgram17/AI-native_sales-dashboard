from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def mcp_call_tool(url: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Open a fresh stateless MCP session, call one tool, return the parsed result dict."""
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)

            if result.structuredContent is not None:
                return result.structuredContent  # type: ignore[return-value]

            if result.content:
                text = getattr(result.content[0], "text", None)
                if text is not None:
                    return json.loads(text)  # type: ignore[no-any-return]

            raise RuntimeError(f"MCP tool '{tool_name}' returned empty content")
