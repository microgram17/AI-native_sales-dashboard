"""Deterministic validator node. Routes back to the planner via ADK edges.

In addition to validating returned result structure, this node checks provenance
for product_ids used by the general analytics tools. A product ID is trusted
only when it was explicitly supplied by the user or was previously resolved and
persisted in conversational context.

This prevents the planner from silently constructing fake IDs from product
display names (for example "Oxford Button-Down" -> "OXFORD-BUTTON-DOWN").
"""

from __future__ import annotations

import json
import re
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ROUTE_PROCEED, ROUTE_RETRY, ExecutedToolCall, StateKeys
from app.schemas.agent import ToolPlan

MAX_RETRIES = 2

_RECOGNIZED_STATUSES = {"success", "no_data", "not_found", "ambiguous"}

_PRODUCT_SCOPE_TOOLS = {
    "sales_summary",
    "sales_rank",
    "sales_trend",
}


def _empty_plan() -> ToolPlan:
    return ToolPlan(
        tool_calls=[],
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


def _load_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _known_product_ids(state: Any) -> set[str]:
    entities = _load_json(
        state.get(StateKeys.CTX_ENTITIES_JSON),
        [],
    )
    if not isinstance(entities, list):
        return set()

    return {
        str(entity.get("id")).strip().casefold()
        for entity in entities
        if isinstance(entity, dict)
        and entity.get("type") == "product"
        and entity.get("id")
    }


def _user_explicitly_supplied_id(
    user_message: str,
    product_id: str,
) -> bool:
    """Return True only when the exact ID token appears in the user's message."""

    token = product_id.strip()
    if not token:
        return False

    # Treat letters, digits, underscores and hyphens as part of the ID token so
    # a partial substring cannot accidentally count as an explicit user-supplied
    # ID. Matching is case-insensitive.
    pattern = (
        rf"(?<![A-Za-z0-9_-])"
        rf"{re.escape(token)}"
        rf"(?![A-Za-z0-9_-])"
    )
    return re.search(
        pattern,
        user_message,
        flags=re.IGNORECASE,
    ) is not None


def _untrusted_product_ids(
    call: ExecutedToolCall,
    *,
    known_product_ids: set[str],
    user_message: str,
) -> list[str]:
    if call.tool_name not in _PRODUCT_SCOPE_TOOLS:
        return []

    scope = call.arguments.get("scope")
    if not isinstance(scope, dict):
        return []

    raw_product_ids = scope.get("product_ids")
    if not isinstance(raw_product_ids, list):
        return []

    untrusted: list[str] = []

    for value in raw_product_ids:
        product_id = str(value).strip()
        if not product_id:
            continue

        if product_id.casefold() in known_product_ids:
            continue

        if _user_explicitly_supplied_id(
            user_message,
            product_id,
        ):
            continue

        if product_id not in untrusted:
            untrusted.append(product_id)

    return untrusted


def _validate_product_id_provenance(
    call: ExecutedToolCall,
    *,
    known_product_ids: set[str],
    user_message: str,
) -> list[str]:
    untrusted = _untrusted_product_ids(
        call,
        known_product_ids=known_product_ids,
        user_message=user_message,
    )
    if not untrusted:
        return []

    rendered = ", ".join(repr(value) for value in untrusted)
    return [
        (
            f"{call.tool_name}: scope.product_ids contains unresolved product ID(s) "
            f"{rendered}. product_ids may only contain canonical product IDs "
            "explicitly supplied by the user or previously resolved in conversation "
            "context. Do not construct product IDs from product names. For a named "
            "single product, use product_overview with the product name so it can be "
            "resolved server-side."
        )
    ]


def _validate_call(call: ExecutedToolCall) -> list[str]:
    if call.failed:
        return [f"{call.tool_name}: execution failure ({call.error})."]
    if call.status not in _RECOGNIZED_STATUSES:
        return [f"{call.tool_name}: unrecognized status {call.status!r}."]
    if call.status != "success":
        return []

    result = call.result or {}

    if call.tool_name == "sales_rank" and not result.get("rows"):
        return ["sales_rank: success without ranking rows."]
    if call.tool_name == "sales_trend" and not result.get("rows"):
        return ["sales_trend: success without trend rows."]
    if call.tool_name == "product_overview" and not result.get("product"):
        return ["product_overview: success without a resolved product."]
    if call.tool_name == "sales_summary" and not result.get("current"):
        return ["sales_summary: success without summary metrics."]

    return []


def build_validate_results_node() -> BaseNode:
    def validate_results(
        ctx: Context,
        tool_plan: Any = None,
        tool_results: list[dict[str, Any]] | None = None,
        retry_count: int = 0,
    ) -> None:
        plan = _coerce_plan(tool_plan)
        results = [
            ExecutedToolCall.model_validate(result)
            for result in (tool_results or [])
        ]

        errors: list[str] = []

        if not plan.tool_calls:
            errors.append("Planner produced no tool calls.")

        executed_ids = {result.call_id for result in results}
        for call in plan.tool_calls:
            if call.call_id not in executed_ids:
                errors.append(
                    f"Tool call '{call.call_id}' did not execute."
                )

        known_product_ids = _known_product_ids(ctx.state)
        user_message = str(
            ctx.state.get(StateKeys.USER_MESSAGE, "") or ""
        )

        for call in results:
            errors.extend(
                _validate_product_id_provenance(
                    call,
                    known_product_ids=known_product_ids,
                    user_message=user_message,
                )
            )
            errors.extend(_validate_call(call))

        if errors:
            new_retry = retry_count + 1
            ctx.state[StateKeys.RETRY_COUNT] = new_retry
            ctx.state[StateKeys.LAST_VALIDATION_FAILED] = True

            previous = ctx.state.get(
                StateKeys.VALIDATION_ERRORS_TEXT,
                "",
            )
            ctx.state[StateKeys.VALIDATION_ERRORS_TEXT] = (
                f"{previous} {' ; '.join(errors)}".strip()
            )

            ctx.route = (
                ROUTE_RETRY
                if new_retry < MAX_RETRIES
                else ROUTE_PROCEED
            )
        else:
            ctx.state[StateKeys.LAST_VALIDATION_FAILED] = False
            ctx.route = ROUTE_PROCEED

    return node(
        validate_results,
        name="validate_results",
    )
