from __future__ import annotations

from app.application.ports.agent_port import AgentPort
from app.domain.chat import ChatResponse
from app.domain.user_context import UserContext


class ChatService:
    def __init__(self, agent: AgentPort) -> None:
        self._agent = agent

    async def chat(self, user: UserContext, message: str) -> ChatResponse:
        response = await self._agent.run(user=user, message=message)
        if response.tools_used and not response.artifacts:
            raise RuntimeError(
                "Agent invoked data tools but returned no artifacts — contract violation"
            )
        return response
