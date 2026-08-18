"""End-to-end state-transition tests for the canonical analytical request."""

from __future__ import annotations

import jwt
import pytest

from app.config import get_settings
from app.schemas.agent import AgentQueryRequest
from app.schemas.request_context import RequestContext
from app.services.agent_service import ConversationSupplierMismatchError
from tests.conftest import (
    FakeMcpClient,
    build_agent_service,
    make_interpreter_node,
    mcp_result,
    product_overview_success,
    rank_success,
    resolver_success,
    trend_success,
)


def _ctx(supplier: str = "NORDVALE") -> RequestContext:
    return RequestContext(
        user_id="DEV-USER-001",
        supplier_id=supplier,
        roles=["admin"],
    )


async def _ask(
    service,
    message: str,
    conversation_id: str,
    supplier: str = "NORDVALE",
):
    return await service.handle_query(
        AgentQueryRequest(
            message=message,
            conversation_id=conversation_id,
            language="sv",
        ),
        _ctx(supplier),
    )


async def test_backend_context_becomes_mcp_bearer_token():
    mcp = FakeMcpClient(
        call_results={"sales_rank": mcp_result(rank_success())}
    )
    service = build_agent_service(mcp)

    await _ask(service, "best product?", "conv-a")

    tokens = [token for token in mcp.tokens if token]
    assert tokens
    settings = get_settings()
    claims = jwt.decode(
        tokens[-1],
        settings.mcp_jwt_secret,
        algorithms=[settings.mcp_jwt_algorithm],
        issuer=settings.mcp_jwt_issuer,
        audience=settings.mcp_jwt_audience,
    )
    assert claims["supplier_id"] == "NORDVALE"
    assert claims["sub"] == "DEV-USER-001"


async def test_two_suppliers_receive_isolated_results():
    mcp = FakeMcpClient(
        supplier_data={
            "NORDVALE": rank_success(product_id="NORD-HOD-011"),
            "KIDS_CO": rank_success(product_id="KIDS-TOY-001"),
        }
    )
    service = build_agent_service(mcp)

    resp_a = await _ask(service, "best product?", "conv-a", supplier="NORDVALE")
    resp_b = await _ask(service, "best product?", "conv-b", supplier="KIDS_CO")

    id_a = resp_a.datasets[0].result["rows"][0]["entity"]["id"]
    id_b = resp_b.datasets[0].result["rows"][0]["entity"]["id"]
    assert id_a == "NORD-HOD-011"
    assert id_b == "KIDS-TOY-001"


async def test_cross_supplier_conversation_is_rejected():
    mcp = FakeMcpClient(
        call_results={"sales_rank": mcp_result(rank_success())}
    )
    service = build_agent_service(mcp)

    await _ask(service, "best product?", "shared", supplier="NORDVALE")
    with pytest.raises(ConversationSupplierMismatchError):
        await _ask(service, "same?", "shared", supplier="KIDS_CO")


async def test_online_then_physical_followups_preserve_trend_period_and_metrics():
    def decide(_message: str, turn: int):
        if turn == 1:
            return {
                "mode": "new_analysis",
                "operation": "trend",
                "metrics": ["units", "net_sales"],
                "grain": "month",
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
            }
        if turn == 2:
            return {
                "mode": "modify_analysis",
                "scope": {"channels": ["online"]},
            }
        return {
            "mode": "modify_analysis",
            # Deliberately omit the scope. The deterministic fallback must
            # recognize "fysiska butiker" and preserve the rest of the state.
        }

    mcp = FakeMcpClient(
        call_results={"sales_trend": mcp_result(trend_success())}
    )
    service = build_agent_service(
        mcp,
        interpreter=make_interpreter_node(decide=decide),
    )

    first = await _ask(
        service,
        "Visa sålda enheter och nettoomsättning månadsvis för 2026.",
        "conv-context",
    )
    second = await _ask(
        service,
        "Visa samma sak men bara online.",
        "conv-context",
    )
    third = await _ask(
        service,
        "Och fysiska butiker?",
        "conv-context",
    )

    trend_calls = [
        arguments
        for name, arguments in mcp.calls
        if name == "sales_trend"
    ]
    assert len(trend_calls) == 3

    for arguments in trend_calls:
        assert arguments["grain"] == "month"
        assert arguments["period_start"] == "2026-01-01"
        assert arguments["period_end"] == "2026-12-31"

    assert trend_calls[1]["scope"]["channels"] == ["online"]
    assert trend_calls[2]["scope"]["channels"] == ["physical"]


    assert first.visualizations[0].title == (
        "Sålda enheter och nettoomsättning – 2026"
    )
    assert second.visualizations[0].title == (
        "Sålda enheter och nettoomsättning – Online – 2026"
    )
    assert third.visualizations[0].title == (
        "Sålda enheter och nettoomsättning – Fysiska butiker – 2026"
    )


async def test_product_q1_misclassification_is_corrected_and_graph_reuses_overview():
    def decide(_message: str, turn: int):
        if turn == 1:
            return {
                # Reproduce the live failure: the model incorrectly treats Q1
                # as quarterly grain and turns a broad product-performance
                # request into a trend.
                "mode": "new_analysis",
                "operation": "trend",
                "metrics": ["net_sales"],
                "grain": "quarter",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "product_query": "windereaker",
            }
        return {
            # Even if the model mislabels this, deterministic presentation-only
            # detection must override it.
            "mode": "modify_analysis",
        }

    mcp = FakeMcpClient(
        call_results={
            "resolve_product": resolver_success(),
            "product_overview": mcp_result(
                product_overview_success()
            ),
        }
    )
    service = build_agent_service(
        mcp,
        interpreter=make_interpreter_node(decide=decide),
    )

    first = await _ask(
        service,
        "Hur har det gått under q1 för våran windereaker?",
        "conv-product",
    )
    calls_after_first = len(mcp.calls)

    assert [name for name, _ in mcp.calls] == [
        "resolve_product",
        "product_overview",
    ]
    assert first.visualizations[0].type == "metric_cards"
    assert "Windbreaker Jacket" in first.visualizations[0].title

    second = await _ask(
        service,
        "kan du grafa ut det?",
        "conv-product",
    )

    # Presentation-only follow-up reuses the rich product-overview result.
    assert len(mcp.calls) == calls_after_first
    assert second.visualizations[0].type == "line_chart"
    assert "Windbreaker Jacket" in second.visualizations[0].title

