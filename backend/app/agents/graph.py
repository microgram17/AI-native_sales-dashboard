
"""Simplified semantic sales-agent workflow.

Normal analytical turn:

    interpreter (LLM)
      -> resolve_turn (merge semantic state)
      -> resolve_entities (canonical product identity)
      -> execute_request (deterministic MCP compilation + execution)
      -> normalize_visualizations
      -> build_visualizations (deterministic)
      -> response_policy
      -> optional analytics LLM
      -> compose

Presentation/analysis follow-ups reuse the existing analytical result without a
new MCP call. Conversation branches directly to the conversational LLM.
"""

from __future__ import annotations

from google.adk.workflow import (
    START,
    BaseNode,
    Edge,
    Workflow,
    node,
)

from app.agents.nodes.build_visualizations import (
    build_build_visualizations_node,
)
from app.agents.nodes.compose_response import (
    build_compose_response_node,
)
from app.agents.nodes.execute_request import (
    build_execute_request_node,
)
from app.agents.nodes.load_results import (
    build_load_results_node,
)
from app.agents.nodes.normalize_visualizations import (
    build_normalize_visualizations_node,
)
from app.agents.nodes.resolve_entities import (
    build_resolve_entities_node,
)
from app.agents.nodes.resolve_turn import (
    build_resolve_turn_node,
)
from app.agents.nodes.response_policy import (
    build_response_policy_node,
)
from app.agents.state import (
    ROUTE_CONVERSATION,
    ROUTE_DIRECT,
    ROUTE_DO_ANALYTICS,
    ROUTE_EXECUTE,
    ROUTE_RESOLUTION_PROCEED,
    ROUTE_RESOLUTION_STOP,
    ROUTE_REUSE,
    ROUTE_SKIP_ANALYTICS,
)
from app.integrations.mcp.client import McpClient


def build_workflow(
    *,
    mcp: McpClient,
    interpreter: BaseNode,
    analytics: BaseNode,
    conversation: BaseNode,
) -> Workflow:
    interpreter_node = node(
        interpreter,
        name="interpreter",
    )
    resolve_turn_node = (
        build_resolve_turn_node()
    )

    entity_node = build_resolve_entities_node(
        mcp
    )
    execute_node = build_execute_request_node(
        mcp
    )
    load_node = build_load_results_node()

    normalize_node = (
        build_normalize_visualizations_node()
    )
    visualization_node = (
        build_build_visualizations_node()
    )
    response_policy_node = (
        build_response_policy_node()
    )

    analytics_node = node(
        analytics,
        name="analytics",
    )
    conversation_node = node(
        conversation,
        name="conversation",
    )
    composer_node = (
        build_compose_response_node()
    )

    edges = [
        Edge(
            from_node=START,
            to_node=interpreter_node,
        ),
        Edge(
            from_node=interpreter_node,
            to_node=resolve_turn_node,
        ),

        Edge(
            from_node=resolve_turn_node,
            to_node=entity_node,
            route=ROUTE_EXECUTE,
        ),
        Edge(
            from_node=resolve_turn_node,
            to_node=load_node,
            route=ROUTE_REUSE,
        ),
        Edge(
            from_node=resolve_turn_node,
            to_node=conversation_node,
            route=ROUTE_CONVERSATION,
        ),
        Edge(
            from_node=resolve_turn_node,
            to_node=composer_node,
            route=ROUTE_DIRECT,
        ),

        Edge(
            from_node=entity_node,
            to_node=execute_node,
            route=ROUTE_RESOLUTION_PROCEED,
        ),
        Edge(
            from_node=entity_node,
            to_node=normalize_node,
            route=ROUTE_RESOLUTION_STOP,
        ),

        Edge(
            from_node=execute_node,
            to_node=normalize_node,
        ),
        Edge(
            from_node=load_node,
            to_node=normalize_node,
        ),

        Edge(
            from_node=normalize_node,
            to_node=visualization_node,
        ),
        Edge(
            from_node=visualization_node,
            to_node=response_policy_node,
        ),

        Edge(
            from_node=response_policy_node,
            to_node=analytics_node,
            route=ROUTE_DO_ANALYTICS,
        ),
        Edge(
            from_node=response_policy_node,
            to_node=composer_node,
            route=ROUTE_SKIP_ANALYTICS,
        ),

        Edge(
            from_node=analytics_node,
            to_node=composer_node,
        ),
        Edge(
            from_node=conversation_node,
            to_node=composer_node,
        ),
    ]

    return Workflow(
        name="sales_agent",
        edges=edges,
    )
