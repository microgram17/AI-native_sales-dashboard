from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.inbound.api.dependencies import get_chat_service, get_user_context
from app.application.services.chat_service import ChatService
from app.domain.chat import ChatRequest, ChatResponse
from app.domain.user_context import UserContext

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    request: ChatRequest,
    user: UserContext = Depends(get_user_context),
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return await service.chat(user=user, message=request.message)
