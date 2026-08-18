from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.visualization import VisualizationDataset, VisualizationSpec


UiLanguage = Literal["en", "sv"]
RequestedGrain = Literal["day", "week", "month", "quarter"]


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
    """Request body for POST /agent/query.

    Supplier identity intentionally does not appear here. It comes from trusted
    authenticated RequestContext on the server.
    """

    message: str
    conversation_id: str | None = None
    language: UiLanguage = "sv"


class PlannedToolCall(BaseModel):
    """A resolved tool invocation (internal, dict arguments)."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    purpose: str | None = None


class PlannedToolCallDraft(BaseModel):
    """Planner LLM output for one call.

    arguments_json is used instead of an open-ended dict so the structured
    output schema remains compatible with strict model output.
    """

    call_id: str
    tool_name: str
    arguments_json: str = "{}"
    purpose: str | None = None

    def to_call(self) -> PlannedToolCall:
        try:
            arguments = (
                json.loads(self.arguments_json)
                if self.arguments_json
                else {}
            )
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
    """Structured planner output.

    product_query is semantic entity intent, not a database identifier. When it
    is set, a deterministic workflow node resolves it to a canonical product ID
    before any analytical tool is allowed to run.

    requested_grain declares that the requested output is a time series at that
    grain. A deterministic retrieval finalizer uses it (plus high-confidence
    wording in the user message) to prevent summary tools from satisfying a
    trend request.

    The four inheritance flags express which prior-context dimensions the
    planner believes should continue into the current turn.
    """

    tool_calls: list[PlannedToolCallDraft] = Field(default_factory=list)

    product_query: str | None = None
    requested_grain: RequestedGrain | None = None

    inherit_period: bool
    inherit_scope: bool
    inherit_entity: bool
    inherit_operation: bool


class ToolCallInfo(BaseModel):
    """Executed tool-call metadata returned to the client."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    purpose: str | None = None
    status: str | None = None
    error: str | None = None


class Dataset(BaseModel):
    """A successful raw MCP tool result exposed to the client."""

    call_id: str
    tool_name: str
    status: str
    result: dict[str, Any]


class AgentQueryResponse(BaseModel):
    conversation_id: str
    message: str
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    visualization_datasets: list[VisualizationDataset] = Field(default_factory=list)
    visualizations: list[VisualizationSpec] = Field(default_factory=list)
