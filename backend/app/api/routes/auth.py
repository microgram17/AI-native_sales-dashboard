from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import RequestContextDep
from app.schemas.auth import AuthMeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=AuthMeResponse)
def read_me(context: RequestContextDep) -> AuthMeResponse:
    return AuthMeResponse(
        user_id=context.user_id,
        supplier_id=context.supplier_id,
        roles=context.roles,
    )
