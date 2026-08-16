from __future__ import annotations

import json

from app.agents.nodes.finalize_retrieval_plan import finalize_retrieval_plan
from app.schemas.agent import PlannedToolCallDraft, ToolPlan


def _plan(
    *,
    tool_name: str = "sales_rank",
    arguments: dict,
) -> ToolPlan:
    return ToolPlan(
        tool_calls=[
            PlannedToolCallDraft(
                call_id="1",
                tool_name=tool_name,
                arguments_json=json.dumps(arguments),
                purpose="test",
            )
        ],
        inherit_period=False,
        inherit_scope=False,
        inherit_entity=False,
        inherit_operation=False,
    )


def _args(plan: ToolPlan) -> dict:
    assert len(plan.tool_calls) == 1
    return plan.tool_calls[0].to_call().arguments


def test_best_selling_singular_overrides_broad_default_limit():
    plan = _plan(
        arguments={
            "group_by": "product",
            "rank_by": "units",
            "limit": 10,
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "What was our best-selling product online in Q1 2026?",
    )

    assert _args(finalized)["limit"] == 1
    assert _args(finalized)["order"] == "highest"


def test_worst_selling_singular_sets_limit_one_and_lowest_order():
    plan = _plan(
        arguments={
            "group_by": "product",
            "rank_by": "units",
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "What was our worst-selling product by units in Q1 2026?",
    )

    assert _args(finalized)["limit"] == 1
    assert _args(finalized)["order"] == "lowest"


def test_which_city_had_highest_sets_limit_one():
    plan = _plan(
        arguments={
            "group_by": "city",
            "rank_by": "net_sales",
            "limit": 10,
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "Which city had the highest net sales in Q1 2026?",
    )

    assert _args(finalized)["limit"] == 1
    assert _args(finalized)["order"] == "highest"


def test_explicit_top_five_overrides_wrong_limit():
    plan = _plan(
        arguments={
            "group_by": "product",
            "rank_by": "net_sales",
            "limit": 10,
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "What were our top 5 products by revenue in Q1 2026?",
    )

    assert _args(finalized)["limit"] == 5
    assert _args(finalized)["order"] == "highest"


def test_written_number_highest_revenue_is_supported():
    plan = _plan(
        arguments={
            "group_by": "product",
            "rank_by": "net_sales",
            "limit": 10,
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "Show the five highest-revenue products in Q1 2026.",
    )

    assert _args(finalized)["limit"] == 5
    assert _args(finalized)["order"] == "highest"


def test_bottom_three_sets_lowest_order():
    plan = _plan(
        arguments={
            "group_by": "store",
            "rank_by": "net_sales",
            "limit": 10,
            "order": "highest",
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "Show the bottom 3 stores by net sales.",
    )

    assert _args(finalized)["limit"] == 3
    assert _args(finalized)["order"] == "lowest"


def test_grouped_comparison_does_not_force_singular_limit():
    plan = _plan(
        arguments={
            "group_by": "channel",
            "rank_by": "net_sales",
            "limit": 10,
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "Compare online and physical sales in Q1 2026.",
    )

    assert _args(finalized)["limit"] == 10


def test_plural_ranking_without_explicit_count_is_left_unchanged():
    plan = _plan(
        arguments={
            "group_by": "store",
            "rank_by": "net_sales",
            "limit": 10,
        }
    )

    finalized = finalize_retrieval_plan(
        plan,
        "Which stores sell the least?",
    )

    assert _args(finalized)["limit"] == 10
    assert _args(finalized)["order"] == "lowest"


def test_non_rank_tool_is_unchanged():
    arguments = {
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
    }
    plan = _plan(
        tool_name="sales_summary",
        arguments=arguments,
    )

    finalized = finalize_retrieval_plan(
        plan,
        "How are our sales doing from January to June 2026?",
    )

    assert _args(finalized) == arguments


def test_inheritance_flags_are_preserved():
    plan = ToolPlan(
        tool_calls=[
            PlannedToolCallDraft(
                call_id="1",
                tool_name="sales_rank",
                arguments_json=json.dumps({
                    "group_by": "product",
                    "rank_by": "units",
                    "limit": 10,
                }),
                purpose="test",
            )
        ],
        inherit_period=True,
        inherit_scope=True,
        inherit_entity=True,
        inherit_operation=True,
    )

    finalized = finalize_retrieval_plan(
        plan,
        "What was the best-selling product?",
    )

    assert finalized.inherit_period is True
    assert finalized.inherit_scope is True
    assert finalized.inherit_entity is True
    assert finalized.inherit_operation is True
