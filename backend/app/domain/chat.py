from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.dashboard import DashboardArtifact


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    assistant_message: str
    artifacts: list[DashboardArtifact] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
