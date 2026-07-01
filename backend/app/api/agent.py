from fastapi import APIRouter, Depends, HTTPException

from app.adapters.mcp_sales_client import McpSalesClient
from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent_service import AgentService
from app.schemas.auth import CurrentUserContext
from app.dependencies.current_user import get_current_user_context

router = APIRouter()


def get_agent_service() -> AgentService:
    return AgentService(sales_analytics=McpSalesClient())


def _check_supplier_access(supplier_code: str, user_ctx: CurrentUserContext) -> None:
    if supplier_code not in user_ctx.allowed_supplier_codes:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: supplier {supplier_code!r} not in your allowed list",
        )


@router.post("/ask")
async def ask_question(
    request: AgentRequest,
    service: AgentService = Depends(get_agent_service),
    user_ctx: CurrentUserContext = Depends(get_current_user_context),
) -> AgentResponse:
    _check_supplier_access(request.supplier_code, user_ctx)
    result = await service.answer_question(
        supplier_code=request.supplier_code,
        question=request.question,
    )
    return AgentResponse.model_validate(result)