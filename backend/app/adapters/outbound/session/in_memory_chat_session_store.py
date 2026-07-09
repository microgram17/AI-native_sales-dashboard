from __future__ import annotations

import uuid

from app.domain.chat_session import ChatSessionState
from app.domain.user_context import UserContext


class InMemoryChatSessionStore:
    """Process-local in-memory chat session store.

    Stores sessions in a plain dict keyed by session_id.
    Use a shared singleton instance (see dependencies.py) — never create per-request.

    Thread/concurrency note: safe for single-worker async uvicorn.
    Add asyncio.Lock if moving to multi-worker or replacing with a shared store.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSessionState] = {}

    async def get_or_create(
        self,
        *,
        session_id: str | None,
        user: UserContext,
    ) -> ChatSessionState:
        if session_id is not None and session_id in self._sessions:
            return self._sessions[session_id]

        new_id = str(uuid.uuid4())
        state = ChatSessionState(
            session_id=new_id,
            user_id=user.user_id,
            supplier_id=user.supplier_id,
        )
        self._sessions[new_id] = state
        return state

    async def save(self, state: ChatSessionState) -> None:
        self._sessions[state.session_id] = state
