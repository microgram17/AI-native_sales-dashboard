from fastapi import APIRouter, Depends

from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent_service import AgentService

router = APIRouter()


def get_agent_service() -> AgentService:
    return AgentService()


@router.post("/chat")
async def chat(
    request: AgentRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    result = await service.answer(request.message)
    return AgentResponse.model_validate(result)