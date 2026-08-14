from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AgentServiceDep, RequestContextDep
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.services.agent_service import ConversationSupplierMismatchError

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
async def query(
    request: AgentQueryRequest,
    context: RequestContextDep,
    service: AgentServiceDep,
) -> AgentQueryResponse:
    try:
        return await service.handle_query(request, context)
    except ConversationSupplierMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
