from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.dashboard import DashboardArtifact


# ChatArtifact is the same shape as DashboardArtifact — reuse directly.
ChatArtifact = DashboardArtifact


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    assistant_message: str
    artifacts: list[DashboardArtifact] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    # Backend-only: actual tool arguments used this turn. Excluded from API JSON.
    used_filters: dict[str, Any] = Field(default_factory=dict, exclude=True)
