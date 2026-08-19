from __future__ import annotations

from app.agents.state import StateKeys
from tests.conftest import (
    FakeMcpClient,
    make_analytics_node,
    make_conversation_node,
    make_interpreter_node,
    mcp_result,
    rank_success,
    run_workflow,
    trend_success,
)


async def test_new_trend_request_executes_trend_and_builds_line_chart():
    mcp = FakeMcpClient(
        call_results={"sales_trend": mcp_result(trend_success())}
    )

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node(
            {
                "mode": "new_analysis",
                "operation": "trend",
                "metrics": ["units", "net_sales"],
                "grain": "month",
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
            }
        ),
        user_message="Visa sålda enheter och nettoomsättning månadsvis för 2026.",
    )

    assert mcp.calls[0][0] == "sales_trend"
    assert mcp.calls[0][1]["grain"] == "month"

    response = state[StateKeys.RESPONSE]
    assert response["message"] == (
        "Här är den månatliga utvecklingen för sålda enheter och "
        "nettoomsättning under 2026."
    )
    assert response["visualizations"][0]["type"] == "line_chart"
    assert response["visualizations"][0]["secondary_y_keys"] == ["net_sales"]


async def test_ranking_gets_bar_chart_without_duplicate_analytics():
    first = rank_success()
    second = {
        **first["rows"][0],
        "rank": 2,
        "entity": {
            "type": "product",
            "id": "AURA-JKT-023",
            "name": "Oversized Blazer",
        },
    }
    ranking = {
        **first,
        "rank_by": "net_sales",
        "returned_rows_rank_metric_value": 300000.0,
        "rows": [first["rows"][0], second],
    }
    mcp = FakeMcpClient(
        call_results={"sales_rank": mcp_result(ranking)}
    )

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node(
            {
                "mode": "new_analysis",
                "operation": "ranking",
                "metrics": ["net_sales"],
                "group_by": "product",
                "rank_by": "net_sales",
                "rank_order": "highest",
                "limit": 5,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
            }
        ),
        analytics=make_analytics_node("SHOULD NOT APPEAR"),
        user_message="Vilka var våra 5 produkter med högst nettoomsättning under Q1 2026?",
    )

    response = state[StateKeys.RESPONSE]
    assert response["message"]
    assert response["message"] != "SHOULD NOT APPEAR"
    assert "Windbreaker Jacket" in response["message"]
    assert response["visualizations"][0]["type"] == "bar_chart"


async def test_conversation_branch_does_not_call_mcp():
    mcp = FakeMcpClient()

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node({"mode": "conversation"}),
        conversation=make_conversation_node("Hej."),
        user_message="Hej!",
    )

    assert mcp.calls == []
    assert state[StateKeys.RESPONSE]["message"] == "Hej."
