from __future__ import annotations

from types import SimpleNamespace

from app.agents.agent import (
    LAST_ANALYTICS_RESULT,
    TURN_ANALYTICS_CALLED,
    TURN_ANALYTICS_RESULT,
    TURN_TOOL_CALLS,
    _headers,
    build_sales_agent,
    capture_tool_result,
)
from app.schemas.agent import AgentTurnOutput
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
import pytest

from app.config import Settings
from app.schemas.agent import AgentQueryRequest
from app.schemas.request_context import RequestContext
from app.services.agent_service import AgentService, ConversationSupplierMismatchError
from app.schemas.agent import AgentQueryResponse, DataView, DisplaySelection
from app.services.agent_service import (
    _coerce_result,
    _default_displays,
    _validate_displays,
)


def analytics_result() -> dict:
    return {
        "status": "success",
        "context": {
            "operation": "trend",
            "effective_period": {
                "start": "2026-01-01",
                "end": "2026-03-31",
                "label": "Q1 2026",
                "defaulted": False,
            },
            "effective_scope": {
                "channels": [],
                "cities": [],
                "store_ids": [],
                "categories": [],
                "product_ids": [],
            },
            "grain": "month",
            "group_by": None,
            "rank_by": None,
            "order": None,
            "split_by": None,
            "entity": None,
        },
        "warnings": [],
        "candidates": [],
        "views": [
            {
                "id": "trend",
                "kind": "timeseries",
                "rows": [
                    {"period_label": "2026-01", "net_sales": 100.0},
                    {"period_label": "2026-02", "net_sales": 120.0},
                ],
                "fields": [
                    {"key": "period_label", "role": "dimension", "format": "text"},
                    {"key": "net_sales", "role": "measure", "format": "currency_sek"},
                ],
                "primary_dimension": "period_label",
                "series_dimension": None,
                "default_measures": ["net_sales"],
                "default_visible": True,
            }
        ],
    }


def test_architecture_is_one_native_tool_enabled_agent() -> None:
    agent, toolset = build_sales_agent(
        LiteLlm(model="openai/gpt-4o-mini", api_key="test"),
        "http://localhost:8001/mcp",
    )
    assert agent.name == "sales_agent"
    assert agent.tools == [toolset]
    assert agent.output_schema is AgentTurnOutput
    assert agent.after_tool_callback is capture_tool_result


def test_mcp_header_comes_only_from_invocation_state() -> None:
    context = SimpleNamespace(state={"mcp_token": "secret-token"})
    assert _headers(context) == {"Authorization": "Bearer secret-token"}


def test_callback_captures_views_without_transforming_rows() -> None:
    state: dict = {TURN_TOOL_CALLS: []}
    context = SimpleNamespace(state=state, function_call_id="fc-1")
    tool = SimpleNamespace(name="sales_trend")
    result = analytics_result()

    # Match ADK's real callback invocation, which uses keyword arguments.
    capture_tool_result(
        tool=tool,
        args={"grain": "month"},
        tool_context=context,
        tool_response={"structuredContent": result, "isError": False},
    )

    assert state[TURN_ANALYTICS_CALLED] is True
    assert state[TURN_ANALYTICS_RESULT]["views"][0]["rows"] == result["views"][0]["rows"]
    assert state[LAST_ANALYTICS_RESULT] == result
    assert state[TURN_TOOL_CALLS][0]["arguments"] == {"grain": "month"}


def test_non_success_result_does_not_replace_reusable_views() -> None:
    previous = analytics_result()
    state: dict = {TURN_TOOL_CALLS: [], LAST_ANALYTICS_RESULT: previous}
    context = SimpleNamespace(state=state, function_call_id="fc-2")
    tool = SimpleNamespace(name="sales_summary")

    capture_tool_result(
        tool=tool,
        args={},
        tool_context=context,
        tool_response={
            "structuredContent": {
                **analytics_result(),
                "status": "no_data",
                "views": [],
            },
            "isError": False,
        },
    )

    assert state[TURN_ANALYTICS_RESULT]["status"] == "no_data"
    assert state[LAST_ANALYTICS_RESULT] == previous


def test_display_validation_rejects_unknown_views_and_measures() -> None:
    _, views = _coerce_result(analytics_result())
    displays = _validate_displays(
        [
            DisplaySelection(
                view_id="trend",
                measure_keys=["made_up", "net_sales"],
            ),
            DisplaySelection(view_id="missing"),
        ],
        views,
    )
    assert len(displays) == 1
    assert displays[0].measure_keys == ["net_sales"]


def test_default_display_uses_semantic_view_defaults() -> None:
    _, views = _coerce_result(analytics_result())
    assert _default_displays(views) == [
        DisplaySelection(view_id="trend", measure_keys=["net_sales"])
    ]


def ranking_result(*, kind: str = "categorical") -> dict:
    result = analytics_result()
    result["context"].update(
        {
            "operation": "ranking",
            "grain": None,
            "group_by": "product",
            "rank_by": "net_sales",
            "order": "highest",
        }
    )
    result["views"] = [
        {
            "id": "ranking",
            "kind": kind,
            "rows": [
                {
                    "entity_name": "Hoodie",
                    "units": 40,
                    "net_sales": 1000.0,
                    "discount_rate": 0.05,
                },
                {
                    "entity_name": "Tee",
                    "units": 30,
                    "net_sales": 800.0,
                    "discount_rate": 0.04,
                },
            ],
            "fields": [
                {"key": "entity_name", "role": "dimension", "format": "text"},
                {"key": "units", "role": "measure", "format": "integer"},
                {
                    "key": "net_sales",
                    "role": "measure",
                    "format": "currency_sek",
                },
                {
                    "key": "discount_rate",
                    "role": "measure",
                    "format": "percentage_fraction",
                },
            ],
            "primary_dimension": "entity_name",
            "series_dimension": None,
            "default_measures": ["net_sales"],
            "default_visible": True,
        }
    ]
    return result


def test_multi_item_ranking_display_uses_only_the_ranked_measure() -> None:
    result = ranking_result()
    context, views = _coerce_result(result)

    displays = _validate_displays(
        [
            DisplaySelection(
                view_id="ranking",
                measure_keys=["units", "net_sales", "discount_rate"],
            )
        ],
        views,
        context,
    )

    assert displays[0].measure_keys == ["net_sales"]


def test_single_item_ranking_display_uses_all_default_metrics() -> None:
    result = ranking_result(kind="metrics")
    result["views"][0]["rows"] = result["views"][0]["rows"][:1]
    result["views"][0]["default_measures"] = [
        "units",
        "net_sales",
        "discount_rate",
    ]
    context, views = _coerce_result(result)

    displays = _validate_displays(
        [
            DisplaySelection(
                view_id="ranking",
                measure_keys=["net_sales"],
            )
        ],
        views,
        context,
    )

    assert displays[0].measure_keys == [
        "units",
        "net_sales",
        "discount_rate",
    ]


def test_http_response_has_only_one_data_payload() -> None:
    fields = set(AgentQueryResponse.model_fields)
    assert {"data_context", "data_views", "displays"}.issubset(fields)
    assert "datasets" not in fields
    assert "visualization_datasets" not in fields
    assert "visualizations" not in fields


def test_data_view_rows_are_flat_scalars() -> None:
    _, views = _coerce_result(analytics_result())
    view: DataView = views[0]
    assert all(
        not isinstance(value, (dict, list))
        for row in view.rows
        for value in row.values()
    )


@pytest.mark.asyncio
async def test_conversation_cannot_cross_supplier_boundary() -> None:
    sessions = InMemorySessionService()
    await sessions.create_session(
        app_name="test-agent",
        user_id="user-1",
        session_id="conversation-1",
        state={"supplier_id": "SUPPLIER-A", "user_id": "user-1"},
    )
    service = AgentService(
        runner=SimpleNamespace(),
        session_service=sessions,
        app_name="test-agent",
        settings=Settings(),
    )

    with pytest.raises(ConversationSupplierMismatchError):
        await service.handle_query(
            AgentQueryRequest(
                message="show sales",
                conversation_id="conversation-1",
                language="en",
            ),
            RequestContext(
                user_id="user-1",
                supplier_id="SUPPLIER-B",
                roles=["supplier"],
            ),
        )
