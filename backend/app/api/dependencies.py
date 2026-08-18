from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from sqlalchemy.engine import Connection

from app.config import Settings, get_settings
from app.db.engine import get_connection
from app.integrations.auth.jwt_issuer import JwtIssuer
from app.integrations.auth.jwt_verifier import JwtVerifier
from app.integrations.auth.password_hasher import PasswordHasher
from app.repositories.auth_repository import AuthRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.request_context import RequestContext
from app.services.authentication_service import (
    AccessDeniedError,
    AuthenticationService,
    InvalidTokenError,
    SupplierSelectionRequiredError,
)
from app.services.dashboard_service import DashboardService

from app.agents.agents.analytics import build_analytics_agent
from app.agents.agents.conversation import build_conversation_agent
from app.agents.agents.interpreter import build_interpreter_agent
from app.agents.graph import build_workflow
from app.agents.models import build_model
from app.integrations.mcp.client import McpClient
from app.services.agent_service import AgentService


def get_settings_dependency() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]


def get_connection_dependency() -> Iterator[Connection]:
    with get_connection() as connection:
        yield connection


ConnectionDep = Annotated[Connection, Depends(get_connection_dependency)]


def get_jwt_verifier(settings: SettingsDep) -> JwtVerifier:
    return JwtVerifier(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


JwtVerifierDep = Annotated[JwtVerifier, Depends(get_jwt_verifier)]


def get_auth_repository(connection: ConnectionDep) -> AuthRepository:
    return AuthRepository(connection)


AuthRepositoryDep = Annotated[AuthRepository, Depends(get_auth_repository)]


def get_jwt_issuer(settings: SettingsDep) -> JwtIssuer:
    return JwtIssuer(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        ttl_seconds=settings.jwt_ttl_seconds,
    )


JwtIssuerDep = Annotated[JwtIssuer, Depends(get_jwt_issuer)]


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


PasswordHasherDep = Annotated[
    PasswordHasher,
    Depends(get_password_hasher),
]


def get_authentication_service(
    verifier: JwtVerifierDep,
    repository: AuthRepositoryDep,
    issuer: JwtIssuerDep,
    password_hasher: PasswordHasherDep,
) -> AuthenticationService:
    return AuthenticationService(
        verifier,
        repository,
        issuer,
        password_hasher,
    )


AuthenticationServiceDep = Annotated[
    AuthenticationService,
    Depends(get_authentication_service),
]


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header; expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


def get_request_context(
    service: AuthenticationServiceDep,
    authorization: Annotated[str | None, Header()] = None,
    x_supplier_id: Annotated[str | None, Header()] = None,
) -> RequestContext:
    token = _extract_bearer_token(authorization)
    try:
        return service.authenticate(token, x_supplier_id)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except SupplierSelectionRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]


def get_dashboard_repository(connection: ConnectionDep) -> DashboardRepository:
    return DashboardRepository(connection)


DashboardRepositoryDep = Annotated[
    DashboardRepository, Depends(get_dashboard_repository)
]


def get_dashboard_service(repository: DashboardRepositoryDep) -> DashboardService:
    return DashboardService(repository)


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


_AGENT_APP_NAME = "sales-agent"


@lru_cache
def _build_agent_service() -> AgentService:
    settings = get_settings()
    model = build_model(settings)
    mcp = McpClient(settings.mcp_server_url)
    workflow = build_workflow(
        mcp=mcp,
        interpreter=build_interpreter_agent(model),
        analytics=build_analytics_agent(model),
        conversation=build_conversation_agent(model),
    )
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=_AGENT_APP_NAME, agent=workflow, session_service=session_service
    )
    return AgentService(
        runner=runner,
        session_service=session_service,
        app_name=_AGENT_APP_NAME,
        mcp=mcp,
        settings=settings,
    )


def get_agent_service() -> AgentService:
    return _build_agent_service()


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
