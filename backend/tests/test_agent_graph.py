"""Router/graph tests (offline: fake LLM nodes + fake MCP)."""

from __future__ import annotations

import json

from google.adk.models.lite_llm import LiteLlm

from app.agents.agents.analytics import build_analytics_agent
from app.agents.agents.planner import build_planner_agent
from app.agents.agents.router import build_router_agent
from app.agents.agents.visualization import build_visualization_agent
from app.agents.state import StateKeys
from app.schemas.agent import RouteDecision, ToolPlan
from app.schemas.visualization import VisualizationPlan
from tests.conftest import (
    FakeMcpClient,
    make_analytics_node,
    make_planner_node,
    make_router_node,
    make_visualization_node,
    rank_plan_args,
    rank_plan_call,
    rank_result,
    run_workflow,
    sales_rank_success,
)


def _model() -> LiteLlm:
    return LiteLlm(model="openai/gpt-4o-mini", api_key="test-not-used")


def _prior_overrides() -> dict:
    prior_calls = [{
        "call_id": "c1",
        "tool_name": "sales_rank",
        "arguments": {},
        "purpose": None,
        "status": "success",
        "result": sales_rank_success(),
        "error": None,
    }]
    return {
        StateKeys.HAS_PRIOR_RESULTS: True,
        StateKeys.CTX_HAS_RESULTS: True,
        StateKeys.CTX_TOOL_CALLS_JSON: prior_calls,
        StateKeys.CTX_RESULTS_JSON: json.dumps(
            [{"call_id": "c1", "tool_name": "sales_rank", "result": sales_rank_success()}]
        ),
    }


async def test_new_data_routes_through_mcp():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    state = await run_workflow(mcp=mcp, router=make_router_node("new_data"))
    assert len(mcp.calls) == 1
    assert any(d["status"] == "success" for d in state["response"]["datasets"])
    assert state["response"]["visualization_datasets"]


async def test_visualization_only_makes_zero_mcp_calls():
    mcp = FakeMcpClient()
    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("visualization_only"),
        visualization=make_visualization_node(
            [{
                "dataset": "c1:ranking",
                "type": "bar_chart",
                "title": "T",
                "x_key": "entity_name",
                "y_keys": ["units"],
            }]
        ),
        state_overrides=_prior_overrides(),
    )
    assert mcp.calls == []
    assert len(state["response"]["visualizations"]) == 1


async def test_analysis_only_makes_zero_mcp_calls():
    mcp = FakeMcpClient()
    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("analysis_only"),
        state_overrides=_prior_overrides(),
    )
    assert mcp.calls == []
    assert state["response"]["message"]


async def test_conversation_makes_zero_mcp_calls():
    mcp = FakeMcpClient()
    state = await run_workflow(mcp=mcp, router=make_router_node("conversation"))
    assert mcp.calls == []
    assert state["response"]["message"]
    assert state["response"]["datasets"] == []
    assert state["response"]["visualization_datasets"] == []


async def test_missing_prior_context_falls_back_to_new_data():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    state = await run_workflow(mcp=mcp, router=make_router_node("reuse_data"))
    assert len(mcp.calls) == 1
    assert state["effective_route"] == "new_data"


async def test_planner_retry_still_works():
    mcp = FakeMcpClient(
        call_results={
            "sales_rank": rank_result(structured=sales_rank_success() | {"rows": []})
        }
    )
    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node([rank_plan_call()]),
    )
    assert state["retry_count"] == 2
    assert state["_planner_calls"] == 2


async def test_supplier_id_never_in_tool_args():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    await run_workflow(mcp=mcp, router=make_router_node("new_data"))
    assert all("supplier_id" not in args for _, args in mcp.calls)
    assert mcp.calls[0][1] == rank_plan_args()


async def test_invalid_visualization_spec_is_dropped():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        visualization=make_visualization_node(
            [{
                "dataset": "c1:ranking",
                "type": "bar_chart",
                "title": "Broken",
                "x_key": "missing",
                "y_keys": ["units"],
            }]
        ),
    )
    assert state["response"]["visualizations"] == []



async def test_singular_ranking_is_finalized_before_mcp():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    deliberately_broad_call = {
        "call_id": "c1",
        "tool_name": "sales_rank",
        "arguments_json": json.dumps({
            "group_by": "product",
            "rank_by": "units",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "scope": {"channels": ["online"]},
            "limit": 10,
        }),
        "purpose": "find the best-selling product",
    }

    await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node([deliberately_broad_call]),
        user_message="What was our best-selling product online in Q1 2026?",
    )

    assert len(mcp.calls) == 1
    name, args = mcp.calls[0]
    assert name == "sales_rank"
    assert args["limit"] == 1
    assert args["order"] == "highest"
    assert args["scope"]["channels"] == ["online"]


async def test_explicit_top_n_is_finalized_before_mcp():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    deliberately_wrong_limit = {
        "call_id": "c1",
        "tool_name": "sales_rank",
        "arguments_json": json.dumps({
            "group_by": "product",
            "rank_by": "net_sales",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "limit": 10,
        }),
        "purpose": "rank products by revenue",
    }

    await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node([deliberately_wrong_limit]),
        user_message="What were our 5 highest-revenue products in Q1 2026?",
    )

    assert mcp.calls[0][1]["limit"] == 5
    assert mcp.calls[0][1]["order"] == "highest"


async def test_grouped_comparison_is_not_forced_to_one_row():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    comparison_call = {
        "call_id": "c1",
        "tool_name": "sales_rank",
        "arguments_json": json.dumps({
            "group_by": "channel",
            "rank_by": "net_sales",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "limit": 10,
        }),
        "purpose": "compare sales channels",
    }

    await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node([comparison_call]),
        user_message="Compare online and physical sales in Q1 2026.",
    )

    assert mcp.calls[0][1]["limit"] == 10




async def test_unresolved_product_id_retries_with_product_overview():
    bad_summary = {
        "status": "no_data",
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
        },
        "effective_scope": {
            "channels": [],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": ["OXFORD-BUTTON-DOWN"],
        },
        "current": None,
    }
    good_overview = {
        "status": "success",
        "product": {
            "type": "product",
            "id": "NORD-SHT-025",
            "name": "Oxford Button-Down",
        },
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
        },
        "effective_scope": {
            "channels": [],
            "cities": [],
            "store_ids": [],
        },
        "current": {
            "units": 62,
            "net_sales": 19322.44,
            "gross_sales": 20324.20,
            "discounts": 1001.76,
            "orders": 56,
            "average_selling_price": 311.65,
            "discount_rate": 0.0493,
        },
    }

    first_attempt = {
        "call_id": "c1",
        "tool_name": "sales_summary",
        "arguments_json": json.dumps({
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "scope": {
                "product_ids": ["OXFORD-BUTTON-DOWN"],
            },
        }),
        "purpose": "get Oxford Button-Down performance",
    }
    retry_attempt = {
        "call_id": "c2",
        "tool_name": "product_overview",
        "arguments_json": json.dumps({
            "product": "Oxford Button-Down",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
        }),
        "purpose": "resolve and summarize Oxford Button-Down",
    }

    def vary(attempt: int) -> list[dict]:
        return [first_attempt] if attempt == 1 else [retry_attempt]

    mcp = FakeMcpClient(
        call_results={
            "sales_summary": rank_result(structured=bad_summary),
            "resolve_product": rank_result(structured={
                "status": "success",
                "product": {
                    "type": "product",
                    "id": "NORD-SHT-025",
                    "name": "Oxford Button-Down",
                },
                "candidates": [],
            }),
            "product_overview": rank_result(structured=good_overview),
        }
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node(vary=vary),
        user_message="How did Oxford Button-Down perform in Q1 2026?",
    )

    assert [name for name, _ in mcp.calls] == [
        "sales_summary",
        "resolve_product",
        "product_overview",
    ]
    assert state["_planner_calls"] == 2
    assert "OXFORD-BUTTON-DOWN" in state["validation_errors_text"]
    assert (
        "Do not construct product IDs from product names"
        in state["validation_errors_text"]
    )
    assert state["response"]["tool_calls"][0]["tool_name"] == "product_overview"


async def test_previously_resolved_product_id_is_allowed():
    product_id = "NORD-KNT-022"
    trend_result = {
        "status": "success",
        "grain": "month",
        "split_by": None,
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
        },
        "effective_scope": {
            "channels": ["online"],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": [product_id],
        },
        "rows": [{
            "period_start": "2026-01-01",
            "period_label": "2026-01",
            "series_entity": None,
            "metrics": {
                "units": 10,
                "net_sales": 5092.57,
                "gross_sales": 5470.11,
                "discounts": 377.54,
                "orders": 10,
                "average_selling_price": 509.26,
                "discount_rate": 0.069,
            },
        }],
    }
    trend_call = {
        "call_id": "c1",
        "tool_name": "sales_trend",
        "arguments_json": json.dumps({
            "grain": "month",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "scope": {
                "channels": ["online"],
                "product_ids": [product_id],
            },
        }),
        "purpose": "show monthly sales for the resolved product",
    }

    mcp = FakeMcpClient(
        call_results={
            "sales_trend": rank_result(structured=trend_result),
        }
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node([trend_call]),
        user_message="Show me its monthly sales.",
        state_overrides={
            StateKeys.CTX_ENTITIES_JSON: json.dumps([
                {
                    "type": "product",
                    "id": product_id,
                    "name": "Wool-Blend Jumper",
                }
            ]),
        },
    )

    assert len(mcp.calls) == 1
    assert state["retry_count"] == 0
    assert state["last_validation_failed"] is False


async def test_product_id_explicitly_typed_by_user_is_allowed():
    product_id = "NORD-KNT-022"
    trend_result = {
        "status": "success",
        "grain": "month",
        "split_by": None,
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
        },
        "effective_scope": {
            "channels": [],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": [product_id],
        },
        "rows": [{
            "period_start": "2026-01-01",
            "period_label": "2026-01",
            "series_entity": None,
            "metrics": {
                "units": 10,
                "net_sales": 5092.57,
                "gross_sales": 5470.11,
                "discounts": 377.54,
                "orders": 10,
                "average_selling_price": 509.26,
                "discount_rate": 0.069,
            },
        }],
    }
    trend_call = {
        "call_id": "c1",
        "tool_name": "sales_trend",
        "arguments_json": json.dumps({
            "grain": "month",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "scope": {
                "product_ids": [product_id],
            },
        }),
        "purpose": "show monthly sales for the supplied product ID",
    }

    mcp = FakeMcpClient(
        call_results={
            "sales_trend": rank_result(structured=trend_result),
        }
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node([trend_call]),
        user_message=(
            "Show monthly sales for NORD-KNT-022 in Q1 2026."
        ),
    )

    assert len(mcp.calls) == 1
    assert state["retry_count"] == 0
    assert state["last_validation_failed"] is False

def test_agents_expose_strict_output_schemas():
    assert build_router_agent(_model()).output_schema is RouteDecision
    assert build_planner_agent(_model()).output_schema is ToolPlan
    assert build_visualization_agent(_model()).output_schema is VisualizationPlan
    assert build_analytics_agent(_model()).output_schema is None


async def test_simple_visualization_backed_request_skips_analytics_prose():
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result()}
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        visualization=make_visualization_node(
            [{
                "dataset": "c1:ranking",
                "type": "bar_chart",
                "title": "Top products",
                "x_key": "entity_name",
                "y_keys": ["units"],
            }]
        ),
        analytics=make_analytics_node(
            "THIS SHOULD NOT BE RENDERED"
        ),
        user_message=(
            "What were our 5 best-selling products "
            "in Q1 2026?"
        ),
    )

    assert len(state["response"]["visualizations"]) == 1
    assert state["response"]["message"] == ""
    assert state.get(StateKeys.ANALYSIS) is None


async def test_swedish_simple_visualization_request_skips_analytics_prose():
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result()}
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        visualization=make_visualization_node(
            [{
                "dataset": "c1:ranking",
                "type": "bar_chart",
                "title": "Topp 5 produkter",
                "x_key": "entity_name",
                "y_keys": ["units"],
            }]
        ),
        analytics=make_analytics_node(
            "DETTA SKA INTE VISAS"
        ),
        user_message=(
            "Vilka var våra 5 bäst säljande produkter "
            "under Q1 2026?"
        ),
        state_overrides={
            StateKeys.UI_LANGUAGE: "sv",
        },
    )

    assert len(state["response"]["visualizations"]) == 1
    assert state["response"]["message"] == ""
    assert state.get(StateKeys.ANALYSIS) is None


async def test_explicit_interpretation_still_runs_analytics_with_visualization():
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result()}
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        visualization=make_visualization_node(
            [{
                "dataset": "c1:ranking",
                "type": "bar_chart",
                "title": "Top products",
                "x_key": "entity_name",
                "y_keys": ["units"],
            }]
        ),
        analytics=make_analytics_node(
            "The leading product stands out clearly."
        ),
        user_message=(
            "Why does the leading product stand out "
            "in Q1 2026?"
        ),
    )

    assert len(state["response"]["visualizations"]) == 1
    assert (
        state["response"]["message"]
        == "The leading product stands out clearly."
    )


async def test_swedish_interpretation_wording_runs_analytics():
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result()}
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        visualization=make_visualization_node(
            [{
                "dataset": "c1:ranking",
                "type": "bar_chart",
                "title": "Topp 5 produkter",
                "x_key": "entity_name",
                "y_keys": ["units"],
            }]
        ),
        analytics=make_analytics_node(
            "Den ledande produkten sticker ut."
        ),
        user_message=(
            "Varför sticker den ledande produkten ut "
            "under Q1 2026?"
        ),
        state_overrides={
            StateKeys.UI_LANGUAGE: "sv",
        },
    )

    assert (
        state["response"]["message"]
        == "Den ledande produkten sticker ut."
    )


async def test_missing_visualization_keeps_self_contained_analytics_answer():
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result()}
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        visualization=make_visualization_node([]),
        analytics=make_analytics_node(
            "Classic Denim Jacket was the leader."
        ),
        user_message=(
            "What was our best-selling product "
            "in Q1 2026?"
        ),
    )

    assert state["response"]["visualizations"] == []
    assert (
        state["response"]["message"]
        == "Classic Denim Jacket was the leader."
    )
