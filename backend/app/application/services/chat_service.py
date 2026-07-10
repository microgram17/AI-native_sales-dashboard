from __future__ import annotations

from app.application.ports.agent_port import AgentPort
from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.chat import ChatResponse
from app.domain.user_context import UserContext


class ChatService:
    def __init__(self, agent: AgentPort) -> None:
        self._agent = agent

    async def chat(
        self,
        user: UserContext,
        message: str,
        runtime_context: AgentRuntimeContext,
        session_id: str | None = None,
    ) -> ChatResponse:
        response = await self._agent.run(
            user=user,
            message=message,
            runtime_context=runtime_context,
            session_id=session_id,
        )

        if response.tools_used and not response.artifacts:
            raise RuntimeError(
                "Agent invoked data tools but returned no artifacts — contract violation"
            )

        return response
