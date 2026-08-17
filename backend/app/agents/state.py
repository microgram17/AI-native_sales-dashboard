"""Typed helpers for the ADK workflow session state."""

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

    ROUTE_DECISION = "route_decision"
    EFFECTIVE_ROUTE = "effective_route"
    HAS_PRIOR_RESULTS = "has_prior_results"
    PRIOR_CONTEXT_SUMMARY = "prior_context_summary"

    TOOL_CATALOG_JSON = "tool_catalog_json"
    AVAILABLE_TOOL_NAMES = "available_tool_names"
    VALIDATION_ERRORS_TEXT = "validation_errors_text"
    RETRY_COUNT = "retry_count"
    TOOL_PLAN = "tool_plan"

    TOOL_RESULTS = "tool_results"
    SUCCESSFUL_RESULTS_JSON = "successful_results_json"
    LAST_VALIDATION_FAILED = "last_validation_failed"

    VISUALIZATION_DATASETS_JSON = "visualization_datasets_json"
    VISUALIZATION_PLAN = "visualization_plan"
    ANALYSIS = "analysis"
    RESPONSE = "response"

    CTX_HAS_RESULTS = "ctx_has_results"
    CTX_RESULTS_JSON = "ctx_results_json"
    CTX_TOOL_CALLS_JSON = "ctx_tool_calls_json"
    CTX_ENTITIES_JSON = "ctx_entities_json"
    CTX_PERIOD_JSON = "ctx_period_json"
    CTX_SCOPE_JSON = "ctx_scope_json"
    CTX_LAST_REQUEST_JSON = "ctx_last_request_json"


ROUTE_NEW_DATA = "new_data"
ROUTE_REUSE_DATA = "reuse_data"
ROUTE_VISUALIZATION_ONLY = "visualization_only"
ROUTE_ANALYSIS_ONLY = "analysis_only"
ROUTE_CONVERSATION = "conversation"

ROUTE_RETRY = "retry"
ROUTE_PROCEED = "proceed"
ROUTE_DO_VIZ = "do_viz"
ROUTE_SKIP_VIZ = "skip_viz"
ROUTE_DO_ANALYTICS = "do_analytics"
ROUTE_SKIP_ANALYTICS = "skip_analytics"


TRANSIENT_STATE_RESET = {
    StateKeys.TOOL_PLAN: None,
    StateKeys.TOOL_RESULTS: [],
    StateKeys.SUCCESSFUL_RESULTS_JSON: "[]",
    StateKeys.VALIDATION_ERRORS_TEXT: "",
    StateKeys.RETRY_COUNT: 0,
    StateKeys.LAST_VALIDATION_FAILED: False,
    StateKeys.VISUALIZATION_DATASETS_JSON: "[]",
    StateKeys.VISUALIZATION_PLAN: None,
    StateKeys.ANALYSIS: None,
    StateKeys.RESPONSE: None,
    StateKeys.ROUTE_DECISION: None,
    StateKeys.EFFECTIVE_ROUTE: None,
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
        return self.error is None and self.status == "success" and self.result is not None
