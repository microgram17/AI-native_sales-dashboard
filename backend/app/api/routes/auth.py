from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import (
    AuthenticationServiceDep,
    RequestContextDep,
)
from app.schemas.auth import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
)
from app.services.authentication_service import (
    InvalidCredentialsError,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=AuthLoginResponse,
)
def login(
    request: AuthLoginRequest,
    service: AuthenticationServiceDep,
) -> AuthLoginResponse:
    try:
        return service.login(
            email=request.email,
            password=request.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get(
    "/me",
    response_model=AuthMeResponse,
)
def read_me(
    context: RequestContextDep,
) -> AuthMeResponse:
    return AuthMeResponse(
        user_id=context.user_id,
        email=context.email,
        display_name=context.display_name,
        account_type=context.account_type,
        supplier_id=context.supplier_id,
        roles=context.roles,
    )
