from __future__ import annotations

from typing import Protocol

from app.domain.chat_session import ChatSessionState
from app.domain.user_context import UserContext


class ChatSessionStorePort(Protocol):
    async def get_or_create(
        self,
        *,
        session_id: str | None,
        user: UserContext,
    ) -> ChatSessionState: ...

    async def save(self, state: ChatSessionState) -> None: ...
