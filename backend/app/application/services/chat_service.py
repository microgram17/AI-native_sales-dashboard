from __future__ import annotations

from app.application.ports.agent_port import AgentPort
from app.application.ports.chat_session_store_port import ChatSessionStorePort
from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.chat import ChatMessage, ChatResponse
from app.domain.user_context import UserContext

MAX_RECENT_MESSAGES = 10


class ChatService:
    def __init__(self, agent: AgentPort, session_store: ChatSessionStorePort) -> None:
        self._agent = agent
        self._session_store = session_store

    async def chat(
        self,
        user: UserContext,
        message: str,
        runtime_context: AgentRuntimeContext,
        session_id: str | None = None,
    ) -> ChatResponse:
        state = await self._session_store.get_or_create(session_id=session_id, user=user)

        response = await self._agent.run(
            user=user,
            message=message,
            runtime_context=runtime_context,
            session_state=state,
        )

        if response.tools_used and not response.artifacts:
            raise RuntimeError(
                "Agent invoked data tools but returned no artifacts — contract violation"
            )

        # ChatService owns all session state mutations.
        state.last_user_message = message
        state.last_assistant_message = response.assistant_message
        if response.tools_used:
            state.last_tool_used = response.tools_used[-1]
        if response.artifacts:
            state.last_artifact = response.artifacts[-1]
        state.last_filters = response.used_filters

        state.recent_messages.append(ChatMessage(role="user", content=message))
        state.recent_messages.append(
            ChatMessage(role="assistant", content=response.assistant_message)
        )
        state.recent_messages = state.recent_messages[-MAX_RECENT_MESSAGES:]

        await self._session_store.save(state)

        return response
