from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.dashboard import DashboardArtifact


# ChatArtifact is the same shape as DashboardArtifact — reuse directly.
ChatArtifact = DashboardArtifact


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    assistant_message: str
    artifacts: list[DashboardArtifact] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
