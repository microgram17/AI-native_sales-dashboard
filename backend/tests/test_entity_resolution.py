from __future__ import annotations

import json

from app.agents.state import StateKeys
from tests.conftest import (
    FakeMcpClient,
    make_planner_node,
    make_router_node,
    rank_result,
    run_workflow,
)


def resolved_product(
    product_id: str = "NORD-SHT-025",
    product_name: str = "Oxford Button-Down",
) -> dict:
    return {
        "status": "success",
        "product": {
            "type": "product",
            "id": product_id,
            "name": product_name,
        },
        "candidates": [],
    }


def q1_product_summary(
    *,
    product_id: str = "NORD-SHT-025",
    status: str = "success",
) -> dict:
    base = {
        "status": status,
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
        "warnings": [],
    }
    if status == "success":
        base["current"] = {
            "units": 62,
            "net_sales": 19322.44,
            "gross_sales": 20324.20,
            "discounts": 1001.76,
            "orders": 56,
            "average_selling_price": 311.65,
            "discount_rate": 0.0493,
        }
    else:
        base["current"] = None
    return base


async def test_named_product_is_resolved_before_summary_and_canonical_id_is_injected():
    draft = {
        "call_id": "c1",
        "tool_name": "sales_summary",
        "arguments_json": json.dumps({
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "scope": {"product_ids": []},
        }),
        "purpose": "get Oxford Button-Down performance",
    }
    mcp = FakeMcpClient(
        call_results={
            "resolve_product": rank_result(structured=resolved_product()),
            "sales_summary": rank_result(structured=q1_product_summary()),
        }
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node(
            [draft],
            product_query="Oxford Button-Down",
        ),
        user_message="Hur gick Oxford Button-Down under Q1 2026?",
    )

    assert [name for name, _ in mcp.calls] == [
        "resolve_product",
        "sales_summary",
    ]
    assert mcp.calls[0][1] == {"product": "Oxford Button-Down"}
    assert mcp.calls[1][1]["scope"]["product_ids"] == ["NORD-SHT-025"]
    assert state["retry_count"] == 0
    assert state["last_validation_failed"] is False

    entities = json.loads(state[StateKeys.CTX_ENTITIES_JSON])
    assert entities == [{
        "type": "product",
        "id": "NORD-SHT-025",
        "name": "Oxford Button-Down",
    }]


async def test_ambiguous_product_stops_before_analytical_query():
    draft = {
        "call_id": "c1",
        "tool_name": "sales_summary",
        "arguments_json": json.dumps({
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
        }),
        "purpose": "get product performance",
    }
    ambiguous = {
        "status": "ambiguous",
        "product": None,
        "candidates": [
            {
                "type": "product",
                "id": "P1",
                "name": "Logo Hoodie",
            },
            {
                "type": "product",
                "id": "P2",
                "name": "Zip Hoodie",
            },
        ],
    }
    mcp = FakeMcpClient(
        call_results={
            "resolve_product": rank_result(structured=ambiguous),
            "sales_summary": rank_result(structured=q1_product_summary()),
        }
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node(
            [draft],
            product_query="Hoodie",
        ),
        user_message="Hur går Hoodie?",
        state_overrides={
            StateKeys.CTX_HAS_RESULTS: True,
            StateKeys.CTX_RESULTS_JSON: '[{"old":"data"}]',
            StateKeys.CTX_ENTITIES_JSON: json.dumps([
                {
                    "type": "product",
                    "id": "OLD-1",
                    "name": "Previous Product",
                }
            ]),
        },
    )

    assert [name for name, _ in mcp.calls] == ["resolve_product"]
    business = json.loads(state[StateKeys.SUCCESSFUL_RESULTS_JSON])
    assert business[0]["result"]["status"] == "ambiguous"
    assert state["response"]["datasets"] == []
    assert state[StateKeys.CTX_HAS_RESULTS] is False
    assert state[StateKeys.CTX_RESULTS_JSON] == "[]"
    assert json.loads(state[StateKeys.CTX_ENTITIES_JSON]) == []


async def test_resolved_product_is_persisted_even_when_period_has_no_sales():
    draft = {
        "call_id": "c1",
        "tool_name": "sales_summary",
        "arguments_json": json.dumps({
            "period_start": "2020-01-01",
            "period_end": "2020-03-31",
        }),
        "purpose": "get product performance",
    }
    no_data = q1_product_summary(status="no_data")
    no_data["effective_period"] = {
        "start": "2020-01-01",
        "end": "2020-03-31",
    }

    mcp = FakeMcpClient(
        call_results={
            "resolve_product": rank_result(structured=resolved_product()),
            "sales_summary": rank_result(structured=no_data),
        }
    )

    state = await run_workflow(
        mcp=mcp,
        router=make_router_node("new_data"),
        planner=make_planner_node(
            [draft],
            product_query="Oxford Button-Down",
        ),
        user_message="Hur gick Oxford Button-Down under Q1 2020?",
    )

    business = json.loads(state[StateKeys.SUCCESSFUL_RESULTS_JSON])
    assert business[0]["result"]["status"] == "no_data"

    entities = json.loads(state[StateKeys.CTX_ENTITIES_JSON])
    assert entities[0]["id"] == "NORD-SHT-025"
    period = json.loads(state[StateKeys.CTX_PERIOD_JSON])
    assert period["start"] == "2020-01-01"
    assert period["end"] == "2020-03-31"
