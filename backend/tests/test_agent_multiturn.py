"""Multi-turn state + supplier propagation tests (AgentService, offline)."""

from __future__ import annotations

import jwt

from app.config import get_settings
from app.schemas.agent import AgentQueryRequest
from app.schemas.request_context import RequestContext
from app.services.agent_service import ConversationSupplierMismatchError
import pytest

from tests.conftest import (
    FakeMcpClient,
    build_agent_service,
    make_planner_node,
    make_router_node,
    rank_plan_call,
    rank_result,
    sales_rank_success,
)


def _ctx(supplier: str = "NORDVALE") -> RequestContext:
    return RequestContext(user_id="DEV-USER-001", supplier_id=supplier, roles=["admin"])


async def _ask(service, message: str, conversation_id: str, supplier: str = "NORDVALE"):
    return await service.handle_query(
        AgentQueryRequest(message=message, conversation_id=conversation_id), _ctx(supplier)
    )


# 1
async def test_backend_context_becomes_mcp_bearer_token():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    service = build_agent_service(mcp, router=make_router_node("new_data"))
    await _ask(service, "best product?", "conv-a")

    tokens = [t for t in mcp.tokens if t]
    assert tokens
    settings = get_settings()
    claims = jwt.decode(
        tokens[-1], settings.mcp_jwt_secret, algorithms=[settings.mcp_jwt_algorithm],
        issuer=settings.mcp_jwt_issuer, audience=settings.mcp_jwt_audience,
    )
    assert claims["supplier_id"] == "NORDVALE"
    assert claims["sub"] == "DEV-USER-001"


# 3
async def test_two_suppliers_receive_isolated_results():
    mcp = FakeMcpClient(
        supplier_data={
            "NORDVALE": sales_rank_success(product_id="NORD-HOD-011"),
            "KIDS_CO": sales_rank_success(product_id="KIDS-TOY-001"),
        }
    )
    service = build_agent_service(mcp, router=make_router_node("new_data"))
    resp_a = await _ask(service, "best product?", "conv-a", supplier="NORDVALE")
    resp_b = await _ask(service, "best product?", "conv-b", supplier="KIDS_CO")

    id_a = resp_a.datasets[0].result["rows"][0]["entity"]["id"]
    id_b = resp_b.datasets[0].result["rows"][0]["entity"]["id"]
    assert id_a == "NORD-HOD-011"
    assert id_b == "KIDS-TOY-001"


# 4
async def test_cross_supplier_conversation_is_rejected():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    service = build_agent_service(mcp, router=make_router_node("new_data"))
    await _ask(service, "best product?", "shared", supplier="NORDVALE")
    with pytest.raises(ConversationSupplierMismatchError):
        await _ask(service, "best product?", "shared", supplier="KIDS_CO")


# 5
async def test_conversation_id_reuses_session():
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    capture: dict = {}
    service = build_agent_service(
        mcp, router=make_router_node("new_data"),
        planner=make_planner_node([rank_plan_call()], capture=capture),
    )
    await _ask(service, "best product this year?", "conv-x")
    # Turn 2 in the same conversation sees persisted prior context.
    await _ask(service, "and what about it?", "conv-x")
    assert capture["prior_context_summary"]  # non-empty => session reused


# 6
async def test_transient_state_resets_between_turns():
    # Both turns fail validation (empty rows) -> retry_count reaches the cap each
    # turn. If transient state were NOT reset it would accumulate across turns.
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result(sales_rank_success() | {"rows": []})}
    )
    service = build_agent_service(
        mcp, router=make_router_node("new_data"), planner=make_planner_node([rank_plan_call()])
    )
    await _ask(service, "best product?", "conv-r")
    await _ask(service, "best product again?", "conv-r")
    session = await service._session_service.get_session(  # noqa: SLF001
        app_name=service._app_name, user_id="DEV-USER-001", session_id="conv-r"
    )
    assert session.state["retry_count"] == 2


# 7 + 8
async def test_followup_inherits_resolved_product_and_filter():
    mcp = FakeMcpClient(
        call_results={"sales_rank": rank_result(sales_rank_success(product_id="NORD-HOD-011", channel="online"))}
    )
    capture: dict = {}
    service = build_agent_service(
        mcp, router=make_router_node("new_data"),
        planner=make_planner_node([rank_plan_call()], capture=capture),
    )
    await _ask(service, "What is our best-selling product online this year?", "conv-c")
    await _ask(service, "Give me an overview of that product.", "conv-c")
    summary = capture["prior_context_summary"]
    assert "NORD-HOD-011" in summary
    assert "online" in summary


# 9
async def test_explicit_new_instruction_can_override_context():
    # Context is advisory: the planner receives it but is free to emit new args.
    mcp = FakeMcpClient(call_results={"sales_rank": rank_result()})
    capture: dict = {}
    service = build_agent_service(
        mcp, router=make_router_node("new_data"),
        planner=make_planner_node([rank_plan_call()], capture=capture),
    )
    await _ask(service, "best product online?", "conv-o")
    resp = await _ask(service, "now show all channels", "conv-o")
    assert capture["prior_context_summary"]  # prior context was provided
    assert resp.tool_calls[0].tool_name == "sales_rank"  # planner still drove the call
