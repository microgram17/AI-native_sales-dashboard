from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.chat import ChatMessage
from app.domain.dashboard import DashboardArtifact


class ChatSessionState(BaseModel):
    session_id: str
    user_id: str
    supplier_id: str | None = None
    recent_messages: list[ChatMessage] = Field(default_factory=list)
    last_user_message: str | None = None
    last_assistant_message: str | None = None
    last_tool_used: str | None = None
    last_filters: dict[str, Any] = Field(default_factory=dict)
    last_artifact: DashboardArtifact | None = None
    agent_state: dict[str, Any] = Field(default_factory=dict)
