from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.visualization import VisualizationSpec


RequestRoute = Literal[
    "new_data",
    "reuse_data",
    "visualization_only",
    "analysis_only",
    "conversation",
]


class RouteDecision(BaseModel):
    """Structured router output (closed schema for OpenAI strict mode)."""

    route: RequestRoute
    reason: str


class AgentQueryRequest(BaseModel):
    """Request body for POST /agent/query. Intentionally has no supplier_id:
    supplier context comes only from the authenticated RequestContext."""

    message: str
    conversation_id: str | None = None


class PlannedToolCall(BaseModel):
    """A tool invocation proposed by the planner (internal, dict arguments)."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    purpose: str | None = None


class PlannedToolCallDraft(BaseModel):
    """Planner LLM output for one call.

    Arguments are carried as a JSON-encoded string so the structured-output
    schema stays closed (OpenAI strict mode forbids open-ended objects).
    """

    call_id: str
    tool_name: str
    arguments_json: str = "{}"
    purpose: str | None = None

    def to_call(self) -> PlannedToolCall:
        try:
            arguments = json.loads(self.arguments_json) if self.arguments_json else {}
        except (json.JSONDecodeError, TypeError):
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        return PlannedToolCall(
            call_id=self.call_id,
            tool_name=self.tool_name,
            arguments=arguments,
            purpose=self.purpose,
        )


class ToolPlan(BaseModel):
    """Structured planner output (ADK LlmAgent output_schema)."""

    tool_calls: list[PlannedToolCallDraft] = Field(default_factory=list)


class ToolCallInfo(BaseModel):
    """Executed tool-call metadata returned to the client."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    purpose: str | None = None
    status: str | None = None
    error: str | None = None


class Dataset(BaseModel):
    """A successful tool result exposed to the client."""

    call_id: str
    tool_name: str
    status: str
    result: dict[str, Any]


class AgentQueryResponse(BaseModel):
    conversation_id: str
    message: str
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    visualizations: list[VisualizationSpec] = Field(default_factory=list)
