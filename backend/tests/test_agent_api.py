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
    assert response.status_code == 200
    # supplier came from the trusted context, not the body.
    assert fake.seen_context.supplier_id == "NORDVALE"
    assert not hasattr(fake.seen_request, "supplier_id")
    assert response.json()["message"] == "supplier=NORDVALE"
