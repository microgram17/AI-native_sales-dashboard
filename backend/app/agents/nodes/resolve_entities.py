"""Resolve a pending product query to canonical ID + name before analytics."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.request_state import coerce_request, request_to_json
from app.agents.state import (
    ROUTE_RESOLUTION_PROCEED,
    ROUTE_RESOLUTION_STOP,
    ExecutedToolCall,
    StateKeys,
)
from app.integrations.mcp.capabilities import CAP_PRODUCT_RESOLVER
from app.integrations.mcp.client import McpClient, McpClientError
from app.schemas.agent import CanonicalProduct


def _capabilities(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, str) and value.strip():
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
    return {}


def _set_resolution_outcome(
    ctx: Context,
    call: ExecutedToolCall,
) -> None:
    serialized = call.model_dump(mode="json")
    business = [
        {
            "call_id": call.call_id,
            "tool_name": call.tool_name,
            "result": call.result,
        }
    ]

    ctx.state[StateKeys.TOOL_RESULTS] = [serialized]
    ctx.state[StateKeys.BUSINESS_RESULTS_JSON] = json.dumps(
        business,
        ensure_ascii=False,
    )

    ctx.state[StateKeys.LAST_HAS_RESULTS] = False
    ctx.state[StateKeys.LAST_TOOL_RESULTS] = [serialized]
    ctx.state[StateKeys.LAST_BUSINESS_RESULTS_JSON] = json.dumps(
        business,
        ensure_ascii=False,
    )


def build_resolve_entities_node(mcp: McpClient) -> BaseNode:
    async def resolve_entities(
        ctx: Context,
        canonical_request_json: Any = "null",
        mcp_capabilities_json: Any = "{}",
        mcp_token: str | None = None,
    ) -> None:
        request = coerce_request(canonical_request_json)
        if request is None:
            raise RuntimeError("Canonical analytical request is missing.")

        query = (request.pending_product_query or "").strip()
        if not query:
            ctx.route = ROUTE_RESOLUTION_PROCEED
            return

        tool_name = _capabilities(mcp_capabilities_json).get(
            CAP_PRODUCT_RESOLVER
        )
        if not tool_name:
            raise RuntimeError(
                "The MCP product-resolution capability is unavailable."
            )

        try:
            outcome = await mcp.call_tool(
                tool_name,
                {"product": query},
                token=mcp_token,
            )
        except McpClientError as exc:
            raise RuntimeError(
                "Product resolution failed before analytics execution."
            ) from exc

        if outcome.is_error:
            raise RuntimeError(
                outcome.error_message
                or "Product resolution failed before analytics execution."
            )

        structured = outcome.structured or {}
        status = structured.get("status")

        if status == "success":
            product = structured.get("product")
            if (
                not isinstance(product, dict)
                or not product.get("id")
                or not product.get("name")
            ):
                raise RuntimeError(
                    "Product resolver returned success without a canonical product."
                )

            resolved = request.model_copy(
                update={
                    "entity": CanonicalProduct(
                        id=str(product["id"]),
                        name=str(product["name"]),
                    ),
                    "pending_product_query": None,
                }
            )
            ctx.state[StateKeys.CANONICAL_REQUEST_JSON] = request_to_json(resolved)
            ctx.route = ROUTE_RESOLUTION_PROCEED
            return

        if status in {"not_found", "ambiguous"}:
            call = ExecutedToolCall(
                call_id="__product_resolution__",
                tool_name=tool_name,
                arguments={"product": query},
                purpose="Resolve the named product before analytics.",
                status=status,
                result=structured,
            )
            _set_resolution_outcome(ctx, call)
            ctx.route = ROUTE_RESOLUTION_STOP
            return

        raise RuntimeError(
            f"Product resolver returned unsupported status {status!r}."
        )

    return node(resolve_entities, name="resolve_entities")
