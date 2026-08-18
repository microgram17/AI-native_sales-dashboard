from __future__ import annotations

import json

from app.agents.nodes.apply_context import apply_context_to_plan
from app.agents.state import StateKeys
from app.schemas.agent import PlannedToolCallDraft, ToolPlan


PRODUCT_ID = "NORD-KNT-022"


def _draft(
    tool_name: str,
    arguments: dict,
    call_id: str = "1",
) -> PlannedToolCallDraft:
    return PlannedToolCallDraft(
        call_id=call_id,
        tool_name=tool_name,
        arguments_json=json.dumps(arguments),
        purpose="test",
    )


def _state(
    *,
    period_start: str = "2026-01-01",
    period_end: str = "2026-03-31",
    channels: list[str] | None = None,
    product_ids: list[str] | None = None,
    last_tool: str = "sales_trend",
    last_arguments: dict | None = None,
) -> dict:
    scope = {
        "channels": ["online"] if channels is None else channels,
        "cities": [],
        "store_ids": [],
        "categories": [],
        "product_ids": (
            [PRODUCT_ID]
            if product_ids is None
            else product_ids
        ),
    }

    if last_arguments is None:
        last_arguments = {
            "grain": "month",
            "period_start": period_start,
            "period_end": period_end,
            "scope": scope,
        }

    return {
        StateKeys.CTX_ENTITIES_JSON: json.dumps(
            [
                {
                    "type": "product",
                    "id": PRODUCT_ID,
                    "name": "Wool-Blend Jumper",
                }
            ]
        ),
        StateKeys.CTX_PERIOD_JSON: json.dumps(
            {
                "start": period_start,
                "end": period_end,
            }
        ),
        StateKeys.CTX_SCOPE_JSON: json.dumps(scope),
        StateKeys.CTX_LAST_REQUEST_JSON: json.dumps(
            {
                "tool_calls": [
                    {
                        "tool_name": last_tool,
                        "arguments": last_arguments,
                        "purpose": "previous request",
                        "status": "success",
                    }
                ]
            }
        ),
    }


def _resolved_call(plan: ToolPlan, state: dict):
    resolved = apply_context_to_plan(plan, state)
    assert len(resolved.tool_calls) == 1
    return resolved.tool_calls[0].to_call()


def test_turn_2_inherits_q1_online_product_into_monthly_trend():
    plan = ToolPlan(
        tool_calls=[
            _draft(
                "sales_trend",
                {"grain": "month"},
            )
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=True,
        inherit_scope=True,
        inherit_entity=True,
        inherit_operation=False,
    )

    call = _resolved_call(plan, _state())

    assert call.tool_name == "sales_trend"
    assert call.arguments == {
        "grain": "month",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "scope": {
            "channels": ["online"],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": [PRODUCT_ID],
        },
    }


def test_turn_3_preserves_monthly_trend_even_if_draft_selects_summary():
    plan = ToolPlan(
        tool_calls=[
            _draft(
                "sales_summary",
                {
                    "period_start": "2026-01-01",
                    "period_end": "2026-06-30",
                    "scope": {
                        "product_ids": [PRODUCT_ID],
                    },
                },
            )
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=False,
        inherit_scope=True,
        inherit_entity=True,
        inherit_operation=True,
    )

    call = _resolved_call(plan, _state())

    assert call.tool_name == "sales_trend"
    assert call.arguments == {
        "grain": "month",
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "scope": {
            "channels": ["online"],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": [PRODUCT_ID],
        },
    }


def test_explicit_physical_channel_overrides_inherited_online():
    plan = ToolPlan(
        tool_calls=[
            _draft(
                "sales_trend",
                {
                    "scope": {
                        "channels": ["physical"],
                    }
                },
            )
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=True,
        inherit_scope=True,
        inherit_entity=True,
        inherit_operation=True,
    )

    call = _resolved_call(plan, _state())

    assert call.arguments["scope"]["channels"] == ["physical"]
    assert call.arguments["scope"]["product_ids"] == [PRODUCT_ID]
    assert call.arguments["period_start"] == "2026-01-01"
    assert call.arguments["period_end"] == "2026-03-31"
    assert call.arguments["grain"] == "month"


def test_explicit_empty_channels_clears_inherited_channel_filter():
    plan = ToolPlan(
        tool_calls=[
            _draft(
                "sales_trend",
                {
                    "scope": {
                        "channels": [],
                    }
                },
            )
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=True,
        inherit_scope=True,
        inherit_entity=True,
        inherit_operation=True,
    )

    call = _resolved_call(plan, _state())

    assert call.arguments["scope"]["channels"] == []
    assert call.arguments["scope"]["product_ids"] == [PRODUCT_ID]


def test_entity_can_be_inherited_without_other_scope_filters():
    plan = ToolPlan(
        tool_calls=[
            _draft(
                "sales_trend",
                {"grain": "month"},
            )
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=True,
        inherit_scope=False,
        inherit_entity=True,
        inherit_operation=False,
    )

    call = _resolved_call(plan, _state())

    assert call.arguments["scope"] == {
        "product_ids": [PRODUCT_ID],
    }


def test_unrelated_request_with_all_flags_false_is_unchanged():
    plan = ToolPlan(
        tool_calls=[
            _draft(
                "sales_summary",
                {
                    "period_start": "2026-04-01",
                    "period_end": "2026-06-30",
                },
            )
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=False,
        inherit_scope=False,
        inherit_entity=False,
        inherit_operation=False,
    )

    call = _resolved_call(plan, _state())

    assert call.tool_name == "sales_summary"
    assert call.arguments == {
        "period_start": "2026-04-01",
        "period_end": "2026-06-30",
    }


def test_product_overview_inherits_single_product_as_product_argument():
    plan = ToolPlan(
        tool_calls=[
            _draft(
                "product_overview",
                {},
            )
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=True,
        inherit_scope=True,
        inherit_entity=True,
        inherit_operation=False,
    )

    call = _resolved_call(plan, _state())

    assert call.tool_name == "product_overview"
    assert call.arguments["product"] == PRODUCT_ID
    assert call.arguments["period_start"] == "2026-01-01"
    assert call.arguments["period_end"] == "2026-03-31"
    assert call.arguments["scope"]["channels"] == ["online"]
    assert "product_ids" not in call.arguments["scope"]
    assert "categories" not in call.arguments["scope"]


def test_operation_inheritance_is_conservative_for_multi_call_plans():
    plan = ToolPlan(
        tool_calls=[
            _draft("sales_summary", {}, call_id="1"),
            _draft("sales_summary", {}, call_id="2"),
        ],
        product_query=None,
        requested_grain=None,
        inherit_period=False,
        inherit_scope=False,
        inherit_entity=False,
        inherit_operation=True,
    )

    resolved = apply_context_to_plan(plan, _state())

    assert [call.tool_name for call in resolved.tool_calls] == [
        "sales_summary",
        "sales_summary",
    ]
