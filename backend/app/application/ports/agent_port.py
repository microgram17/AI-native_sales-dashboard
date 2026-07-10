from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.chat import ChatResponse
from app.domain.user_context import UserContext


class AgentPort(ABC):
    @abstractmethod
    async def run(
        self,
        *,
        user: UserContext,
        message: str,
        runtime_context: AgentRuntimeContext,
        session_id: str | None,
    ) -> ChatResponse: ...
