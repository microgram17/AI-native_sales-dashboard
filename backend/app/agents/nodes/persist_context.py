"""Persist conversational analytical context after a new-data turn.

Raw reusable results represent the latest analytical turn only. Semantic context
(entity, period and scope) is retained across no_data/not_found/ambiguous
outcomes so a failed follow-up does not erase what the conversation was about.

The latest understood analytical request is persisted separately from result
data. This lets elliptical follow-ups preserve intent such as "monthly trend"
even when the latest query returned no data.
"""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ExecutedToolCall, StateKeys


_BUSINESS_STATUSES = {"success", "no_data", "not_found", "ambiguous"}


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


def _dedupe_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("id")
        name = entity.get("name")
        key = str(entity_id or name or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(entity)

    return out


def _extract_product_entities(
    successful: list[ExecutedToolCall],
) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []

    for call in successful:
        result = call.result or {}

        if call.tool_name == "product_overview":
            product = result.get("product")
            if isinstance(product, dict):
                entities.append(product)
            continue

        if (
            call.tool_name == "sales_rank"
            and call.arguments.get("group_by") == "product"
        ):
            rows = result.get("rows")
            if not isinstance(rows, list):
                continue

            for row in rows:
                if not isinstance(row, dict):
                    continue
                entity = row.get("entity")
                if isinstance(entity, dict) and entity.get("type") == "product":
                    entities.append(entity)

    return _dedupe_entities(entities)


def _first_success_value(
    successful: list[ExecutedToolCall],
    key: str,
) -> dict[str, Any] | None:
    for call in successful:
        value = (call.result or {}).get(key)
        if isinstance(value, dict):
            return value
    return None


def _entities_for_new_scope(
    previous_entities: list[dict[str, Any]],
    new_entities: list[dict[str, Any]],
    new_scope: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if new_entities:
        return new_entities

    if new_scope is None:
        return previous_entities

    product_ids = new_scope.get("product_ids")
    if not isinstance(product_ids, list) or not product_ids:
        return []

    previous_by_id = {
        str(entity.get("id")): entity
        for entity in previous_entities
        if isinstance(entity, dict) and entity.get("id")
    }

    resolved: list[dict[str, Any]] = []
    for product_id in product_ids:
        key = str(product_id)
        resolved.append(
            previous_by_id.get(
                key,
                {"type": "product", "id": key, "name": key},
            )
        )
    return _dedupe_entities(resolved)


def _last_request_payload(
    results: list[ExecutedToolCall],
) -> dict[str, Any] | None:
    calls = [
        {
            "tool_name": result.tool_name,
            "arguments": result.arguments,
            "purpose": result.purpose,
            "status": result.status,
        }
        for result in results
        if not result.failed and result.status in _BUSINESS_STATUSES
    ]
    if not calls:
        return None
    return {"tool_calls": calls}


def build_persist_context_node() -> BaseNode:
    def persist_context(
        ctx: Context,
        tool_results: list[dict] | None = None,
        successful_results_json: str = "[]",
    ) -> None:
        results = [
            ExecutedToolCall.model_validate(result)
            for result in (tool_results or [])
        ]
        successful = [result for result in results if result.is_success]

        previous_entities = _load_json(
            ctx.state.get(StateKeys.CTX_ENTITIES_JSON),
            [],
        )
        if not isinstance(previous_entities, list):
            previous_entities = []

        last_request = _last_request_payload(results)
        if last_request is not None:
            ctx.state[StateKeys.CTX_LAST_REQUEST_JSON] = json.dumps(last_request)

        # Reusable raw results always belong to the latest analytical turn.
        # A no-data turn therefore has no reusable result, but it must not wipe
        # the stable semantic context established by an earlier successful turn.
        ctx.state[StateKeys.CTX_HAS_RESULTS] = bool(successful)
        ctx.state[StateKeys.CTX_TOOL_CALLS_JSON] = [
            result.model_dump(mode="json") for result in results
        ]
        ctx.state[StateKeys.CTX_RESULTS_JSON] = (
            successful_results_json if successful else "[]"
        )

        if not successful:
            return

        new_entities = _extract_product_entities(successful)
        new_period = _first_success_value(successful, "effective_period")
        new_scope = _first_success_value(successful, "effective_scope")

        merged_entities = _entities_for_new_scope(
            previous_entities,
            new_entities,
            new_scope,
        )
        ctx.state[StateKeys.CTX_ENTITIES_JSON] = json.dumps(merged_entities)

        if new_period is not None:
            ctx.state[StateKeys.CTX_PERIOD_JSON] = json.dumps(new_period)

        if new_scope is not None:
            ctx.state[StateKeys.CTX_SCOPE_JSON] = json.dumps(new_scope)

    return node(persist_context, name="persist_context")
