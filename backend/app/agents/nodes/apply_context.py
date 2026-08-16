"""Deterministically apply persisted conversational context to a ToolPlan.

The planner decides *which* context dimensions the user intends to continue via
ToolPlan inheritance flags. This node performs the actual merge before MCP
execution.

This keeps semantic interpretation model-driven while making argument
propagation deterministic and preventing accidental loss of period, filters,
resolved product IDs, or analytical operation shape.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import StateKeys
from app.schemas.agent import PlannedToolCallDraft, ToolPlan


_CONTEXT_AWARE_TOOLS = {
    "sales_summary",
    "sales_rank",
    "sales_trend",
    "product_overview",
}

_FULL_SCOPE_KEYS = {
    "channels",
    "cities",
    "store_ids",
    "categories",
    "product_ids",
}

_PRODUCT_OVERVIEW_SCOPE_KEYS = {
    "channels",
    "cities",
    "store_ids",
}

_CONTEXT_ARGUMENT_KEYS = {
    "period_start",
    "period_end",
    "scope",
    "product",
}


def _coerce_plan(value: Any) -> ToolPlan:
    if isinstance(value, ToolPlan):
        return value
    if isinstance(value, dict):
        return ToolPlan.model_validate(value)
    if isinstance(value, str) and value.strip():
        return ToolPlan.model_validate_json(value)
    return ToolPlan()


def _load_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return deepcopy(value)
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _last_request_calls(state: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _load_json(
        state.get(StateKeys.CTX_LAST_REQUEST_JSON),
        {},
    )
    if not isinstance(payload, dict):
        return []

    calls = payload.get("tool_calls")
    if not isinstance(calls, list):
        return []

    return [call for call in calls if isinstance(call, dict)]


def _single_prior_product_id(state: dict[str, Any]) -> str | None:
    entities = _load_json(
        state.get(StateKeys.CTX_ENTITIES_JSON),
        [],
    )
    if not isinstance(entities, list):
        return None

    product_ids = [
        str(entity.get("id"))
        for entity in entities
        if isinstance(entity, dict)
        and entity.get("type") == "product"
        and entity.get("id")
    ]

    unique = list(dict.fromkeys(product_ids))
    return unique[0] if len(unique) == 1 else None


def _prior_period(state: dict[str, Any]) -> dict[str, Any]:
    period = _load_json(
        state.get(StateKeys.CTX_PERIOD_JSON),
        {},
    )
    return period if isinstance(period, dict) else {}


def _prior_scope(state: dict[str, Any]) -> dict[str, Any]:
    scope = _load_json(
        state.get(StateKeys.CTX_SCOPE_JSON),
        {},
    )
    return scope if isinstance(scope, dict) else {}


def _scope_keys_for_tool(tool_name: str) -> set[str]:
    if tool_name == "product_overview":
        return _PRODUCT_OVERVIEW_SCOPE_KEYS
    if tool_name in {"sales_summary", "sales_rank", "sales_trend"}:
        return _FULL_SCOPE_KEYS
    return set()


def _sanitize_scope(
    tool_name: str,
    scope: dict[str, Any],
) -> dict[str, Any]:
    allowed = _scope_keys_for_tool(tool_name)
    if not allowed:
        return {}
    return {
        key: deepcopy(value)
        for key, value in scope.items()
        if key in allowed
    }


def _operation_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return arguments that define analytical shape rather than context."""

    return {
        key: deepcopy(value)
        for key, value in arguments.items()
        if key not in _CONTEXT_ARGUMENT_KEYS
    }


def _context_arguments_for_tool(
    arguments: dict[str, Any],
    tool_name: str,
) -> dict[str, Any]:
    """Keep only context-like args that remain meaningful after tool override."""

    out: dict[str, Any] = {}

    if "period_start" in arguments:
        out["period_start"] = deepcopy(arguments["period_start"])
    if "period_end" in arguments:
        out["period_end"] = deepcopy(arguments["period_end"])

    if "scope" in arguments and isinstance(arguments["scope"], dict):
        out["scope"] = _sanitize_scope(
            tool_name,
            arguments["scope"],
        )

    if tool_name == "product_overview" and "product" in arguments:
        out["product"] = deepcopy(arguments["product"])

    return out


def _inherit_operation(
    plan: ToolPlan,
    current_tool_name: str,
    current_arguments: dict[str, Any],
    state: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Preserve the previous analytical operation when safely one-to-one.

    Operation inheritance is deliberately conservative. It is applied only
    when both the current and previous analytical request contain exactly one
    tool call. Multi-call plans remain planner-controlled.
    """

    if not plan.inherit_operation or len(plan.tool_calls) != 1:
        return current_tool_name, deepcopy(current_arguments)

    previous_calls = _last_request_calls(state)
    if len(previous_calls) != 1:
        return current_tool_name, deepcopy(current_arguments)

    previous = previous_calls[0]
    previous_tool_name = previous.get("tool_name")
    previous_arguments = previous.get("arguments")

    if (
        previous_tool_name not in _CONTEXT_AWARE_TOOLS
        or not isinstance(previous_arguments, dict)
    ):
        return current_tool_name, deepcopy(current_arguments)

    previous_operation = _operation_arguments(previous_arguments)

    if current_tool_name == previous_tool_name:
        # Same operation: inherit omitted shape args, while allowing explicit
        # changes such as month -> week.
        merged = {
            **previous_operation,
            **deepcopy(current_arguments),
        }
        return previous_tool_name, merged

    # Planner chose a different tool even though it declared that the previous
    # operation should continue. Preserve the previous operation and carry only
    # the current turn's explicit context changes across to that operation.
    current_context = _context_arguments_for_tool(
        current_arguments,
        previous_tool_name,
    )
    return previous_tool_name, {
        **previous_operation,
        **current_context,
    }


def _apply_period(
    arguments: dict[str, Any],
    state: dict[str, Any],
    *,
    inherit: bool,
) -> None:
    if not inherit:
        return

    period = _prior_period(state)

    if "period_start" not in arguments and period.get("start"):
        arguments["period_start"] = period["start"]

    if "period_end" not in arguments and period.get("end"):
        arguments["period_end"] = period["end"]


def _apply_scope(
    tool_name: str,
    arguments: dict[str, Any],
    state: dict[str, Any],
    *,
    inherit: bool,
) -> None:
    allowed = _scope_keys_for_tool(tool_name)
    if not allowed:
        arguments.pop("scope", None)
        return

    current_scope_present = "scope" in arguments
    current_scope = (
        deepcopy(arguments.get("scope"))
        if isinstance(arguments.get("scope"), dict)
        else {}
    )

    if inherit:
        previous = _prior_scope(state)

        # Product identity is controlled independently by inherit_entity.
        previous.pop("product_ids", None)

        merged = _sanitize_scope(tool_name, previous)
        merged.update(_sanitize_scope(tool_name, current_scope))
        arguments["scope"] = merged
        return

    if current_scope_present:
        arguments["scope"] = _sanitize_scope(
            tool_name,
            current_scope,
        )


def _apply_entity(
    tool_name: str,
    arguments: dict[str, Any],
    state: dict[str, Any],
    *,
    inherit: bool,
) -> None:
    if not inherit:
        return

    product_id = _single_prior_product_id(state)
    if not product_id:
        return

    if tool_name == "product_overview":
        arguments.setdefault("product", product_id)
        return

    if tool_name not in {
        "sales_summary",
        "sales_rank",
        "sales_trend",
    }:
        return

    scope = arguments.get("scope")
    if not isinstance(scope, dict):
        scope = {}

    # An explicitly supplied product_ids field wins, including [] when the user
    # explicitly clears the product restriction.
    if "product_ids" not in scope:
        scope["product_ids"] = [product_id]

    arguments["scope"] = _sanitize_scope(tool_name, scope)


def _sanitize_arguments(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    out = deepcopy(arguments)

    if tool_name not in _CONTEXT_AWARE_TOOLS:
        return out

    if tool_name != "product_overview":
        out.pop("product", None)

    if "scope" in out:
        if isinstance(out["scope"], dict):
            out["scope"] = _sanitize_scope(
                tool_name,
                out["scope"],
            )
        else:
            out.pop("scope", None)

    return out


def apply_context_to_plan(
    plan: ToolPlan,
    state: dict[str, Any],
) -> ToolPlan:
    """Return a new ToolPlan with selected prior context applied."""

    resolved_calls: list[PlannedToolCallDraft] = []

    for draft in plan.tool_calls:
        call = draft.to_call()

        tool_name, arguments = _inherit_operation(
            plan,
            call.tool_name,
            call.arguments,
            state,
        )

        if tool_name in _CONTEXT_AWARE_TOOLS:
            _apply_period(
                arguments,
                state,
                inherit=plan.inherit_period,
            )
            _apply_scope(
                tool_name,
                arguments,
                state,
                inherit=plan.inherit_scope,
            )
            _apply_entity(
                tool_name,
                arguments,
                state,
                inherit=plan.inherit_entity,
            )

        arguments = _sanitize_arguments(
            tool_name,
            arguments,
        )

        resolved_calls.append(
            PlannedToolCallDraft(
                call_id=call.call_id,
                tool_name=tool_name,
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
        inherit_period=plan.inherit_period,
        inherit_scope=plan.inherit_scope,
        inherit_entity=plan.inherit_entity,
        inherit_operation=plan.inherit_operation,
    )


def build_apply_context_node() -> BaseNode:
    def apply_context(
        ctx: Context,
        tool_plan: Any = None,
    ) -> None:
        plan = _coerce_plan(tool_plan)
        resolved = apply_context_to_plan(
            plan,
            ctx.state,
        )
        ctx.state[StateKeys.TOOL_PLAN] = resolved.model_dump(
            mode="json"
        )

    return node(apply_context, name="apply_context")
