"""API tests for POST /agent/query (auth + supplier isolation)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_service, get_authentication_service, get_request_context
from app.main import app
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.schemas.request_context import RequestContext


class CapturingAgentService:
    def __init__(self) -> None:
        self.seen_context: RequestContext | None = None
        self.seen_request: AgentQueryRequest | None = None

    async def handle_query(self, request, context) -> AgentQueryResponse:
        self.seen_context = context
        self.seen_request = request
        return AgentQueryResponse(
            conversation_id="conv", message=f"supplier={context.supplier_id}"
        )


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


# 1
def test_agent_query_requires_authentication():
    # Avoid the real auth DB chain and the real agent service.
    app.dependency_overrides[get_authentication_service] = lambda: object()
    app.dependency_overrides[get_agent_service] = lambda: CapturingAgentService()
    client = TestClient(app)

    response = client.post("/agent/query", json={"message": "hello"})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# 2
def test_supplier_id_is_not_accepted_from_request_body():
    assert "supplier_id" not in AgentQueryRequest.model_fields

    fake = CapturingAgentService()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user_id="DEV-USER-001", supplier_id="NORDVALE", roles=["admin"]
    )
    app.dependency_overrides[get_agent_service] = lambda: fake
    client = TestClient(app)

    response = client.post(
        "/agent/query", json={"message": "hi", "supplier_id": "HACKED"}
    )
    assert response.status_code == 422
    assert fake.seen_context is None


def test_only_canonical_agent_query_route_is_published():
    paths = app.openapi()["paths"]
    assert "/agent/query" in paths
    assert "/agent/query-v2" not in paths


def test_dashboard_context_is_accepted_without_affecting_supplier_scope():
    fake = CapturingAgentService()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user_id="DEV-USER-001", supplier_id="NORDVALE", roles=["admin"]
    )
    app.dependency_overrides[get_agent_service] = lambda: fake
    client = TestClient(app)

    response = client.post(
        "/agent/query",
        json={
            "message": "What stands out?",
            "dashboard_context": {
                "date_from": "2026-01-01",
                "date_to": "2026-06-30",
                "metric": "net_sales",
                "group_by": "store",
            },
        },
    )

    assert response.status_code == 200
    assert fake.seen_request.dashboard_context.date_from.isoformat() == "2026-01-01"
    assert fake.seen_context.supplier_id == "NORDVALE"


def test_widget_analysis_is_validated_as_a_scoped_new_request():
    fake = CapturingAgentService()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user_id="DEV-USER-001", supplier_id="NORDVALE", roles=["admin"]
    )
    app.dependency_overrides[get_agent_service] = lambda: fake
    client = TestClient(app)

    response = client.post(
        "/agent/query",
        json={
            "message": "Analyze this sales trend.",
            "widget_analysis": {
                "widget": "sales_trend",
                "operation": "trend",
                "metrics": ["net_sales"],
                "period_start": "2026-01-01",
                "period_end": "2026-06-30",
                "grain": "month",
            },
        },
    )

    assert response.status_code == 200
    widget = fake.seen_request.widget_analysis
    assert widget.widget == "sales_trend"
    assert widget.operation == "trend"
    assert widget.metrics == ["net_sales"]
    assert fake.seen_context.supplier_id == "NORDVALE"


def test_performance_trend_requires_selected_widget_series():
    fake = CapturingAgentService()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user_id="DEV-USER-001", supplier_id="NORDVALE", roles=["admin"]
    )
    app.dependency_overrides[get_agent_service] = lambda: fake
    client = TestClient(app)

    response = client.post(
        "/agent/query",
        json={
            "message": "Analyze this performance trend.",
            "widget_analysis": {
                "widget": "performance",
                "operation": "trend",
                "metrics": ["net_sales"],
                "period_start": "2025-07-01",
                "period_end": "2026-06-30",
                "grain": "month",
                "split_by": "store",
                "series_limit": 3,
                "scope": {},
            },
        },
    )

    assert response.status_code == 422
