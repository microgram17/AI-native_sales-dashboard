"""Resolve named product references before analytical MCP execution.

The planner supplies semantic product_query text. This node is responsible for
turning that text into a supplier-scoped canonical product identity through the
MCP resolve_product capability and injecting the canonical ID into the
analytical plan.

If resolution is ambiguous or fails to find a product, analytical execution is
stopped. This intentionally prevents an unresolved named-product request from
falling back to an unscoped supplier-wide query.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import (
    PRODUCT_RESOLVER_TOOL_NAME,
    ROUTE_RESOLUTION_PROCEED,
    ROUTE_RESOLUTION_STOP,
    ExecutedToolCall,
    StateKeys,
)
from app.integrations.mcp.client import McpClient, McpClientError
from app.schemas.agent import PlannedToolCallDraft, ToolPlan


_PRODUCT_SCOPED_TOOLS = {
    "sales_summary",
    "sales_rank",
    "sales_trend",
}


def _empty_plan() -> ToolPlan:
    return ToolPlan(
        tool_calls=[],
        product_query=None,
        requested_grain=None,
        inherit_period=False,
        inherit_scope=False,
        inherit_entity=False,
        inherit_operation=False,
    )


def _coerce_plan(value: Any) -> ToolPlan:
    if isinstance(value, ToolPlan):
        return value
    if isinstance(value, dict):
        return ToolPlan.model_validate(value)
    if isinstance(value, str) and value.strip():
        return ToolPlan.model_validate_json(value)
    return _empty_plan()


def _product_query(plan: ToolPlan) -> str | None:
    if isinstance(plan.product_query, str) and plan.product_query.strip():
        return plan.product_query.strip()

    # Safety for older/faulty planner output: product_overview's product
    # argument is still an explicit single-product reference.
    for draft in plan.tool_calls:
        call = draft.to_call()
        if call.tool_name != "product_overview":
            continue
        product = call.arguments.get("product")
        if isinstance(product, str) and product.strip():
            return product.strip()

    return None


def _inject_product(
    plan: ToolPlan,
    product_id: str,
) -> ToolPlan:
    resolved_calls: list[PlannedToolCallDraft] = []

    for draft in plan.tool_calls:
        call = draft.to_call()
        arguments = deepcopy(call.arguments)

        if call.tool_name == "product_overview":
            arguments["product"] = product_id

        elif call.tool_name in _PRODUCT_SCOPED_TOOLS:
            scope = arguments.get("scope")
            if not isinstance(scope, dict):
                scope = {}
            else:
                scope = deepcopy(scope)

            # An explicitly resolved current-turn product always wins over an
            # empty, guessed, or stale draft product_ids value.
            scope["product_ids"] = [product_id]
            arguments["scope"] = scope

        resolved_calls.append(
            PlannedToolCallDraft(
                call_id=call.call_id,
                tool_name=call.tool_name,
                arguments_json=json.dumps(
                    arguments,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ),
                purpose=call.purpose,
            )
        )

    return ToolPlan(
        tool_calls=resolved_calls,
        product_query=plan.product_query,
        requested_grain=plan.requested_grain,
        inherit_period=plan.inherit_period,
        inherit_scope=plan.inherit_scope,
        inherit_entity=plan.inherit_entity,
        inherit_operation=plan.inherit_operation,
    )


def _resolution_payload(
    query: str,
    structured: dict[str, Any],
) -> ExecutedToolCall:
    return ExecutedToolCall(
        call_id="__resolve_product__",
        tool_name=PRODUCT_RESOLVER_TOOL_NAME,
        arguments={"product": query},
        purpose="Resolve the named product before analytics.",
        status=structured.get("status"),
        result=structured,
    )


def build_resolve_entities_node(mcp: McpClient) -> BaseNode:
    async def resolve_entities(
        ctx: Context,
        tool_plan: Any = None,
        available_tool_names: list[str] | None = None,
        mcp_token: str | None = None,
    ) -> None:
        plan = _coerce_plan(tool_plan)
        query = _product_query(plan)

        if query is None:
            ctx.route = ROUTE_RESOLUTION_PROCEED
            return

        if PRODUCT_RESOLVER_TOOL_NAME not in set(available_tool_names or []):
            # Never proceed unscoped when a named product cannot be resolved.
            raise RuntimeError(
                "The MCP product resolver capability is unavailable."
            )

        try:
            outcome = await mcp.call_tool(
                PRODUCT_RESOLVER_TOOL_NAME,
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

            canonical = {
                "type": "product",
                "id": str(product["id"]),
                "name": str(product["name"]),
            }
            ctx.state[StateKeys.RESOLVED_PRODUCT_JSON] = json.dumps(
                canonical,
                ensure_ascii=False,
            )
            resolved_plan = _inject_product(
                plan,
                canonical["id"],
            )
            ctx.state[StateKeys.TOOL_PLAN] = resolved_plan.model_dump(
                mode="json"
            )
            ctx.route = ROUTE_RESOLUTION_PROCEED
            return

        if status in {"not_found", "ambiguous"}:
            result = _resolution_payload(query, structured)
            serialized_result = result.model_dump(mode="json")
            ctx.state[StateKeys.TOOL_RESULTS] = [serialized_result]
            ctx.state[StateKeys.SUCCESSFUL_RESULTS_JSON] = json.dumps(
                [
                    {
                        "call_id": result.call_id,
                        "tool_name": result.tool_name,
                        "result": result.result,
                    }
                ],
                ensure_ascii=False,
            )

            # The current turn explicitly changed product identity but could not
            # resolve it. Do not leave older product data/entity context marked
            # as reusable, otherwise a later elliptical follow-up could
            # accidentally operate on the previous product.
            ctx.state[StateKeys.CTX_HAS_RESULTS] = False
            ctx.state[StateKeys.CTX_RESULTS_JSON] = "[]"
            ctx.state[StateKeys.CTX_TOOL_CALLS_JSON] = [serialized_result]
            ctx.state[StateKeys.CTX_ENTITIES_JSON] = "[]"

            ctx.route = ROUTE_RESOLUTION_STOP
            return

        raise RuntimeError(
            f"Product resolver returned unsupported status {status!r}."
        )

    return node(
        resolve_entities,
        name="resolve_entities",
    )
