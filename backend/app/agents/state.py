
"""State contract for the simplified semantic agent workflow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StateKeys:
    USER_ID = "user_id"
    SUPPLIER_ID = "supplier_id"
    ROLES = "roles"
    USER_MESSAGE = "user_message"
    UI_LANGUAGE = "ui_language"
    CURRENT_DATE = "current_date"
    CONVERSATION_ID = "conversation_id"
    MCP_TOKEN = "mcp_token"

    MCP_CAPABILITIES_JSON = "mcp_capabilities_json"

    CANONICAL_REQUEST_JSON = "canonical_request_json"
    LAST_HAS_RESULTS = "last_has_results"
    LAST_TOOL_RESULTS = "last_tool_results"
    LAST_BUSINESS_RESULTS_JSON = "last_business_results_json"

    TURN_INTERPRETATION = "turn_interpretation"
    EFFECTIVE_MODE = "effective_mode"
    TOOL_RESULTS = "tool_results"
    BUSINESS_RESULTS_JSON = "business_results_json"
    VISUALIZATION_DATASETS_JSON = "visualization_datasets_json"
    VISUALIZATION_PLAN = "visualization_plan"
    ANALYSIS = "analysis"
    DIRECT_MESSAGE = "direct_message"
    RESPONSE = "response"


ROUTE_EXECUTE = "execute"
ROUTE_REUSE = "reuse"
ROUTE_CONVERSATION = "conversation"
ROUTE_DIRECT = "direct"

ROUTE_RESOLUTION_PROCEED = "resolution_proceed"
ROUTE_RESOLUTION_STOP = "resolution_stop"

ROUTE_DO_ANALYTICS = "do_analytics"
ROUTE_SKIP_ANALYTICS = "skip_analytics"


TRANSIENT_STATE_RESET = {
    StateKeys.TURN_INTERPRETATION: None,
    StateKeys.EFFECTIVE_MODE: None,
    StateKeys.TOOL_RESULTS: [],
    StateKeys.BUSINESS_RESULTS_JSON: "[]",
    StateKeys.VISUALIZATION_DATASETS_JSON: "[]",
    StateKeys.VISUALIZATION_PLAN: None,
    StateKeys.ANALYSIS: None,
    StateKeys.DIRECT_MESSAGE: None,
    StateKeys.RESPONSE: None,
}


class ExecutedToolCall(BaseModel):
    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    purpose: str | None = None
    status: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None

    @property
    def is_success(self) -> bool:
        return (
            self.error is None
            and self.status == "success"
            and self.result is not None
        )

    @property
    def is_business_result(self) -> bool:
        return (
            self.error is None
            and self.status in {
                "success",
                "no_data",
                "not_found",
                "ambiguous",
            }
            and self.result is not None
        )
