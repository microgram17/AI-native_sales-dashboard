"""The agent workflow as an ADK graph (google.adk.workflow).

New-data path:

    planner
      -> apply_context
      -> finalize_retrieval_plan
      -> execute
      -> validate

The planner decides which prior-context dimensions should be inherited.
apply_context performs those merges deterministically. finalize_retrieval_plan
then enforces narrow retrieval invariants before MCP execution.
"""

from __future__ import annotations

from google.adk.workflow import START, BaseNode, Edge, Workflow, node

from app.agents.nodes.apply_context import build_apply_context_node
from app.agents.nodes.compose_response import build_compose_response_node
from app.agents.nodes.dispatch import build_dispatch_node
from app.agents.nodes.execute_tools import build_execute_tools_node
from app.agents.nodes.finalize_retrieval_plan import (
    build_finalize_retrieval_plan_node,
)
from app.agents.nodes.gates import (
    build_analytics_gate_node,
    build_visualization_gate_node,
)
from app.agents.nodes.load_results import build_load_results_node
from app.agents.nodes.normalize_visualizations import (
    build_normalize_visualizations_node,
)
from app.agents.nodes.persist_context import build_persist_context_node
from app.agents.nodes.validate_results import build_validate_results_node
from app.agents.nodes.validate_visualizations import (
    build_validate_visualizations_node,
)
from app.agents.state import (
    ROUTE_ANALYSIS_ONLY,
    ROUTE_CONVERSATION,
    ROUTE_DO_ANALYTICS,
    ROUTE_DO_VIZ,
    ROUTE_NEW_DATA,
    ROUTE_PROCEED,
    ROUTE_RETRY,
    ROUTE_REUSE_DATA,
    ROUTE_SKIP_ANALYTICS,
    ROUTE_SKIP_VIZ,
    ROUTE_VISUALIZATION_ONLY,
)
from app.integrations.mcp.client import McpClient


def build_workflow(
    *,
    mcp: McpClient,
    router: BaseNode,
    planner: BaseNode,
    visualization: BaseNode,
    analytics: BaseNode,
    conversation: BaseNode,
) -> Workflow:
    router_node = node(router, name="router")
    dispatch_node = build_dispatch_node()

    planner_node = node(planner, name="planner")
    context_node = build_apply_context_node()
    retrieval_node = build_finalize_retrieval_plan_node()
    executor_node = build_execute_tools_node(mcp)
    validator_node = build_validate_results_node()
    persist_node = build_persist_context_node()

    load_node = build_load_results_node()
    normalize_node = build_normalize_visualizations_node()
    viz_gate_node = build_visualization_gate_node()
    visualization_node = node(
        visualization,
        name="visualization",
    )
    viz_validator_node = build_validate_visualizations_node()

    analytics_gate_node = build_analytics_gate_node()
    analytics_node = node(analytics, name="analytics")
    conversation_node = node(
        conversation,
        name="conversation",
    )
    composer_node = build_compose_response_node()

    edges = [
        Edge(from_node=START, to_node=router_node),
        Edge(from_node=router_node, to_node=dispatch_node),

        # Dispatch branches.
        Edge(
            from_node=dispatch_node,
            to_node=planner_node,
            route=ROUTE_NEW_DATA,
        ),
        Edge(
            from_node=dispatch_node,
            to_node=load_node,
            route=[
                ROUTE_REUSE_DATA,
                ROUTE_VISUALIZATION_ONLY,
                ROUTE_ANALYSIS_ONLY,
            ],
        ),
        Edge(
            from_node=dispatch_node,
            to_node=conversation_node,
            route=ROUTE_CONVERSATION,
        ),

        # New-data path. Every fresh planner output is context-resolved and then
        # retrieval-finalized before execution, including planner retries.
        Edge(from_node=planner_node, to_node=context_node),
        Edge(from_node=context_node, to_node=retrieval_node),
        Edge(from_node=retrieval_node, to_node=executor_node),
        Edge(from_node=executor_node, to_node=validator_node),
        Edge(
            from_node=validator_node,
            to_node=planner_node,
            route=ROUTE_RETRY,
        ),
        Edge(
            from_node=validator_node,
            to_node=persist_node,
            route=ROUTE_PROCEED,
        ),
        Edge(from_node=persist_node, to_node=normalize_node),

        # Reuse path joins at normalization.
        Edge(from_node=load_node, to_node=normalize_node),
        Edge(from_node=normalize_node, to_node=viz_gate_node),

        # Visualization gate.
        Edge(
            from_node=viz_gate_node,
            to_node=visualization_node,
            route=ROUTE_DO_VIZ,
        ),
        Edge(
            from_node=viz_gate_node,
            to_node=analytics_gate_node,
            route=ROUTE_SKIP_VIZ,
        ),
        Edge(
            from_node=visualization_node,
            to_node=viz_validator_node,
        ),
        Edge(
            from_node=viz_validator_node,
            to_node=analytics_gate_node,
        ),

        # Analytics gate.
        Edge(
            from_node=analytics_gate_node,
            to_node=analytics_node,
            route=ROUTE_DO_ANALYTICS,
        ),
        Edge(
            from_node=analytics_gate_node,
            to_node=composer_node,
            route=ROUTE_SKIP_ANALYTICS,
        ),
        Edge(from_node=analytics_node, to_node=composer_node),

        # Conversation path.
        Edge(from_node=conversation_node, to_node=composer_node),
    ]

    return Workflow(
        name="sales_agent",
        edges=edges,
    )
