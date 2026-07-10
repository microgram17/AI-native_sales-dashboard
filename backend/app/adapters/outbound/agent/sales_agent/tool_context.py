from __future__ import annotations

from dataclasses import dataclass, field

from app.application.ports.supplier_analytics_port import SupplierAnalyticsPort
from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.tool_result import ToolResultPayload
from app.domain.user_context import UserContext


@dataclass
class SalesToolContext:
    """Per-request mutable state container shared by all tool closures in a single run.

    Immutable fields (user, runtime_context, analytics_port) are injected at construction.
    Mutable fields (collected, tools_used) are appended by each tool as it executes,
    then read by the adapter to build the ChatResponse. Cross-turn follow-up filter
    state is written directly to ADK session.state via tool_context.state, not here.

    Each request creates a fresh SalesToolContext — no cross-request state leakage.
    """

    user: UserContext
    runtime_context: AgentRuntimeContext
    analytics_port: SupplierAnalyticsPort
    collected: list[tuple[str, ToolResultPayload]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
