from __future__ import annotations

from app.agents.state import StateKeys
from tests.conftest import (
    FakeMcpClient,
    make_interpreter_node,
    mcp_result,
    product_overview_success,
    resolver_success,
    run_workflow,
)


async def test_named_product_is_resolved_and_canonical_id_is_injected():
    """Broad named-product performance requests normalize to product_overview.

    The interpreter fixture deliberately emits operation="summary" to verify
    that the deterministic semantic layer still recognizes the actual user
    wording ("Hur har det gått ... för ...") as a broad product-performance
    request.
    """

    mcp = FakeMcpClient(
        call_results={
            "resolve_product": resolver_success(),
            "product_overview": mcp_result(
                product_overview_success()
            ),
        }
    )

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node(
            {
                "mode": "new_analysis",
                "operation": "summary",
                "metrics": ["units", "net_sales"],
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "product_query": "windereaker",
            }
        ),
        user_message="Hur har det gått under q1 för våran windereaker?",
    )

    assert mcp.calls[0] == (
        "resolve_product",
        {"product": "windereaker"},
    )

    # The semantic layer intentionally upgrades this broad single-product
    # performance question from the interpreter's summary guess to
    # product_overview.
    assert mcp.calls[1][0] == "product_overview"
    assert mcp.calls[1][1]["product"] == "AURA-JKT-025"
    assert mcp.calls[1][1]["period_start"] == "2026-01-01"
    assert mcp.calls[1][1]["period_end"] == "2026-03-31"

    request_json = state[StateKeys.CANONICAL_REQUEST_JSON]
    assert '"operation":"product_overview"' in request_json
    assert "AURA-JKT-025" in request_json
    assert "Windbreaker Jacket" in request_json


async def test_not_found_stops_before_analytics_query():
    mcp = FakeMcpClient(
        call_results={
            "resolve_product": mcp_result(
                {
                    "status": "not_found",
                    "product": None,
                    "candidates": [],
                }
            )
        }
    )

    state = await run_workflow(
        mcp=mcp,
        interpreter=make_interpreter_node(
            {
                "mode": "new_analysis",
                "operation": "summary",
                "product_query": "not a real product",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
            }
        ),
        user_message="How did not a real product do?",
    )

    assert [name for name, _ in mcp.calls] == ["resolve_product"]
    assert state[StateKeys.LAST_HAS_RESULTS] is False
