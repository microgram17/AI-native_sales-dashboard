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
    make_planner_node,
    make_router_node,
    make_visualization_node,
    rank_plan_args,
    rank_plan_call,
    rank_result,
    run_workflow,
    sales_rank_success,
    transport_failure,
)


def _model() -> LiteLlm:
    return LiteLlm(model="openai/gpt-4o-mini", api_key="test-not-used")


def _prior_overrides() -> dict:
    prior_calls = [{
        "call_id": "c1", "tool_name": "sales_rank", "arguments": {}, "purpose": None,
        "status": "success", "result": sales_rank_success(), "error": None,
    }]
    return {
        StateKeys.HAS_PRIOR_RESULTS: True,
        StateKeys.CTX_HAS_RESULTS: True,
        StateKeys.CTX_TOOL_CALLS_JSON: prior_calls,
        StateKeys.CTX_RESULTS_JSON: json.dumps(
            [{"call_id": "c1", "tool_name": "sales_rank", "result": sales_rank_success()}]
        ),
    }


# 10
async def test_new_data_routes_through_mcp():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    state = await run_workflow(mcp=mcp, router=make_router_node("new_data"))
    assert len(mcp.calls) == 1
    assert any(d["status"] == "success" for d in state["response"]["datasets"])


# 11
async def test_visualization_only_makes_zero_mcp_calls():
    mcp = FakeMcpClient()
    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("visualization_only"),
        visualization=make_visualization_node(
            [{"dataset": "c1", "type": "bar_chart", "title": "T", "y_keys": ["units"]}]
        ),
        state_overrides=_prior_overrides(),
    )
    assert mcp.calls == []
    assert len(state["response"]["visualizations"]) == 1


# 12
async def test_analysis_only_makes_zero_mcp_calls():
    mcp = FakeMcpClient()
    state = await run_workflow(
        mcp=mcp, router=make_router_node("analysis_only"), state_overrides=_prior_overrides()
    )
    assert mcp.calls == []
    assert state["response"]["message"]


# 13
async def test_conversation_makes_zero_mcp_calls():
    mcp = FakeMcpClient()
    state = await run_workflow(mcp=mcp, router=make_router_node("conversation"))
    assert mcp.calls == []
    assert state["response"]["message"]
    assert state["response"]["datasets"] == []


# 14
async def test_missing_prior_context_falls_back_to_new_data():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    # reuse route but no prior results -> fallback to new_data (MCP runs).
    state = await run_workflow(mcp=mcp, router=make_router_node("reuse_data"))
    assert len(mcp.calls) == 1
    assert state["effective_route"] == "new_data"


# 15
async def test_planner_retry_still_works():
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result(structured=sales_rank_success() | {"rows": []})}
    )
    state = await run_workflow(
        mcp=mcp, router=make_router_node("new_data"), planner=make_planner_node([rank_plan_call()])
    )
    assert state["retry_count"] == 2
    assert state["_planner_calls"] == 2


# 2 (graph-level)
async def test_supplier_id_never_in_tool_args():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    await run_workflow(mcp=mcp, router=make_router_node("new_data"))
    assert all("supplier_id" not in args for _, args in mcp.calls)
    assert mcp.calls[0][1] == rank_plan_args()


# structured-output schemas
def test_agents_expose_strict_output_schemas():
    assert build_router_agent(_model()).output_schema is RouteDecision
    assert build_planner_agent(_model()).output_schema is ToolPlan
    assert build_visualization_agent(_model()).output_schema is VisualizationPlan
    # analytics is free text (no output schema)
    assert build_analytics_agent(_model()).output_schema is None
