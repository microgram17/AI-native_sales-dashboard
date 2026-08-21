from __future__ import annotations

import json

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


async def test_broad_period_question_overrides_summary_to_line_chart():
    mcp = FakeMcpClient(
        call_results={"sales_trend": mcp_result(trend_success())}
    )

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node(
            {
                "mode": "new_analysis",
                "operation": "summary",
                "metrics": ["net_sales"],
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
            }
        ),
        user_message="Analyze net sales during Q1 2026.",
    )

    assert mcp.calls[0][0] == "sales_trend"
    assert state[StateKeys.RESPONSE]["visualizations"][0]["type"] == "line_chart"


async def test_widget_analysis_bootstraps_without_prior_conversation_results():
    mcp = FakeMcpClient(
        call_results={"sales_trend": mcp_result(trend_success())}
    )
    widget_request = {
        "operation": "trend",
        "metrics": ["net_sales"],
        "grain": "month",
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "interpretation_requested": True,
    }

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node({"mode": "analyze_existing"}),
        user_message="Analyze this widget.",
        state_overrides={
            StateKeys.WIDGET_ANALYSIS_REQUEST_JSON: json.dumps(widget_request),
        },
    )

    assert mcp.calls[0][0] == "sales_trend"
    assert state[StateKeys.RESPONSE]["message"] != (
        "Det finns ingen tidigare analys att återanvända ännu."
    )


async def test_current_dashboard_context_compiles_exact_store_trend():
    split_result = trend_success()
    split_result["split_by"] = "store"
    split_result["rows"] = [
        {
            **row,
            "series_entity": {
                "type": "store",
                "id": "ONLINE-SE",
                "name": "Online Store",
            },
        }
        for row in split_result["rows"]
    ]
    mcp = FakeMcpClient(
        call_results={"sales_trend": mcp_result(split_result)}
    )

    await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node(
            {
                "mode": "analyze_existing",
                "interpretation_requested": True,
            }
        ),
        user_message="Analyze the current dashboard view.",
        state_overrides={
            StateKeys.DASHBOARD_CONTEXT_JSON: json.dumps(
                {
                    "date_from": "2025-07-01",
                    "date_to": "2026-06-30",
                    "metric": "net_sales",
                    "grain": "month",
                    "group_by": "store",
                    "view": "trend",
                    "selected_group_ids": ["ONLINE-SE", "STO-001"],
                }
            )
        },
    )

    assert mcp.calls[0] == (
        "sales_trend",
        {
            "period_start": "2025-07-01",
            "period_end": "2026-06-30",
            "grain": "month",
            "scope": {
                "channels": [],
                "cities": [],
                "store_ids": ["ONLINE-SE", "STO-001"],
                "categories": [],
            },
            "series_limit": 2,
            "split_by": "store",
        },
    )


async def test_false_no_data_analysis_falls_back_to_validated_trend_facts():
    mcp = FakeMcpClient(
        call_results={"sales_trend": mcp_result(trend_success())}
    )
    widget_request = {
        "operation": "trend",
        "metrics": ["net_sales"],
        "grain": "month",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "interpretation_requested": True,
    }

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node({"mode": "analyze_existing"}),
        analytics=make_analytics_node(
            "There is no sales data available for the specified period."
        ),
        user_message="Analyze this widget.",
        state_overrides={
            StateKeys.WIDGET_ANALYSIS_REQUEST_JSON: json.dumps(widget_request),
            StateKeys.UI_LANGUAGE: "en",
        },
    )

    message = state[StateKeys.RESPONSE]["message"]
    assert "No data" not in message
    assert "577,975.25 SEK" in message


async def test_partial_false_no_data_and_markdown_image_fall_back_to_facts():
    mcp = FakeMcpClient(
        call_results={"sales_trend": mcp_result(trend_success())}
    )
    widget_request = {
        "operation": "trend",
        "metrics": ["net_sales"],
        "grain": "month",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "interpretation_requested": True,
    }

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node({"mode": "analyze_existing"}),
        analytics=make_analytics_node(
            "Februari: Data inte specifikt angiven.\n\n"
            "![Diagram](data:image/png;base64,unsafe)"
        ),
        user_message="Analysera den här widgeten.",
        state_overrides={
            StateKeys.WIDGET_ANALYSIS_REQUEST_JSON: json.dumps(widget_request),
            StateKeys.UI_LANGUAGE: "sv",
        },
    )

    message = state[StateKeys.RESPONSE]["message"]
    assert "inte specifikt angiven" not in message
    assert "![" not in message
    assert "data:image" not in message


async def test_ranking_percent_change_must_name_exact_comparison_period():
    mcp = FakeMcpClient(
        call_results={"sales_rank": mcp_result(rank_success())}
    )
    widget_request = {
        "operation": "ranking",
        "metrics": ["units"],
        "group_by": "product",
        "rank_by": "units",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "interpretation_requested": True,
    }

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node({"mode": "analyze_existing"}),
        analytics=make_analytics_node(
            "Windbreaker Jacket declined 31.75% from the previous period."
        ),
        user_message="Analyze this widget.",
        state_overrides={
            StateKeys.WIDGET_ANALYSIS_REQUEST_JSON: json.dumps(widget_request),
            StateKeys.UI_LANGUAGE: "en",
        },
    )

    message = state[StateKeys.RESPONSE]["message"]
    assert "2025-10-03" in message
    assert "2025-12-31" in message


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
