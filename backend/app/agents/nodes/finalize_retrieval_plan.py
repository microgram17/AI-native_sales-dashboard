"""Deterministically enforce high-confidence retrieval invariants.

This node runs after conversational context has been applied and before MCP
execution. It intentionally has a narrow responsibility: correct ranking
cardinality and ranking direction when the user's wording makes those semantics
unambiguous.

It does NOT choose tools, metrics, periods, scopes, entities, or visualization
types. Those remain responsibilities of the planner/context/visualization
layers.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import StateKeys
from app.schemas.agent import PlannedToolCallDraft, ToolPlan


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

_COUNT_TOKEN = (
    r"(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty)"
)

_EXPLICIT_COUNT_PATTERNS = (
    # "top 5 products", "bottom five stores"
    re.compile(
        rf"\b(?:top|bottom)\s+(?P<count>{_COUNT_TOKEN})\b",
        re.IGNORECASE,
    ),
    # "5 highest-revenue products", "five worst selling products"
    re.compile(
        rf"\b(?P<count>{_COUNT_TOKEN})\s+"
        r"(?:highest|lowest|best|worst)"
        r"(?:[-\s][a-z]+){0,2}\s+"
        r"(?:products?|categories|category|stores?|cities|city|channels?)\b",
        re.IGNORECASE,
    ),
)

_LOW_ORDER_RE = re.compile(
    r"\b(?:worst(?:[-\s]selling)?|lowest|bottom|least)\b",
    re.IGNORECASE,
)
_HIGH_ORDER_RE = re.compile(
    r"\b(?:best(?:[-\s]selling)?|highest|top|most)\b",
    re.IGNORECASE,
)

_COMPARISON_RE = re.compile(
    r"\b(?:compare|comparison|versus|vs\.?|breakdown|break\s+down)\b",
    re.IGNORECASE,
)

_GROUP_SINGULAR = {
    "product": "product",
    "category": "category",
    "store": "store",
    "city": "city",
    "channel": "channel",
}

_RANK_CUE = (
    r"(?:best(?:[-\s]selling)?|worst(?:[-\s]selling)?|highest|lowest|"
    r"top|bottom|most|least)"
)


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


def _parse_count(token: str) -> int | None:
    value = token.strip().lower()

    if value.isdigit():
        count = int(value)
    else:
        count = _NUMBER_WORDS.get(value)

    if count is None or not 1 <= count <= 20:
        return None

    return count


def _explicit_requested_count(message: str) -> int | None:
    for pattern in _EXPLICIT_COUNT_PATTERNS:
        match = pattern.search(message)
        if match is None:
            continue

        count = _parse_count(match.group("count"))
        if count is not None:
            return count

    return None


def _requested_order(message: str) -> str | None:
    # Low-order language gets priority for phrases such as
    # "top 5 lowest-revenue products".
    if _LOW_ORDER_RE.search(message):
        return "lowest"

    if _HIGH_ORDER_RE.search(message):
        return "highest"

    return None


def _is_singular_superlative(
    message: str,
    group_by: Any,
) -> bool:
    """True only for a high-confidence singular ranking request.

    Examples:
    - "best-selling product"
    - "which city had the highest net sales?"
    - "store with the lowest revenue"

    Plural/list/breakdown requests are intentionally left to the planner.
    """

    if not isinstance(group_by, str):
        return False

    noun = _GROUP_SINGULAR.get(group_by)
    if noun is None:
        return False

    if _COMPARISON_RE.search(message):
        return False

    escaped_noun = re.escape(noun)

    cue_before_noun = re.search(
        rf"\b{_RANK_CUE}\b[^?.!\n]{{0,60}}\b{escaped_noun}\b",
        message,
        re.IGNORECASE,
    )
    noun_before_cue = re.search(
        rf"\b{escaped_noun}\b[^?.!\n]{{0,60}}\b{_RANK_CUE}\b",
        message,
        re.IGNORECASE,
    )

    return cue_before_noun is not None or noun_before_cue is not None


def _finalize_rank_arguments(
    arguments: dict[str, Any],
    user_message: str,
) -> dict[str, Any]:
    out = deepcopy(arguments)

    requested_count = _explicit_requested_count(user_message)
    if requested_count is not None:
        out["limit"] = requested_count
    elif _is_singular_superlative(
        user_message,
        out.get("group_by"),
    ):
        out["limit"] = 1

    requested_order = _requested_order(user_message)
    if requested_order is not None:
        out["order"] = requested_order

    return out


def finalize_retrieval_plan(
    plan: ToolPlan,
    user_message: str,
) -> ToolPlan:
    """Return a plan with deterministic retrieval invariants applied."""

    finalized_calls: list[PlannedToolCallDraft] = []

    for draft in plan.tool_calls:
        call = draft.to_call()
        arguments = deepcopy(call.arguments)

        if call.tool_name == "sales_rank":
            arguments = _finalize_rank_arguments(
                arguments,
                user_message,
            )

        finalized_calls.append(
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
        tool_calls=finalized_calls,
        inherit_period=plan.inherit_period,
        inherit_scope=plan.inherit_scope,
        inherit_entity=plan.inherit_entity,
        inherit_operation=plan.inherit_operation,
    )


def build_finalize_retrieval_plan_node() -> BaseNode:
    def finalize_retrieval(
        ctx: Context,
        tool_plan: Any = None,
        user_message: str = "",
    ) -> None:
        plan = _coerce_plan(tool_plan)
        finalized = finalize_retrieval_plan(
            plan,
            user_message,
        )
        ctx.state[StateKeys.TOOL_PLAN] = finalized.model_dump(
            mode="json"
        )

    return node(
        finalize_retrieval,
        name="finalize_retrieval_plan",
    )
