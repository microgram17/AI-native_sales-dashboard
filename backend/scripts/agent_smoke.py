"""Manual multi-turn smoke test against the REAL MCP server + OpenAI.

Prerequisites:
- docker compose up (postgres + mcp_server) with matching MCP_JWT_* config
- backend/.env has a valid OPENAI_API_KEY

Run from backend/:
    uv run python scripts/agent_smoke.py

Verifies: turn 1 & 2 use MCP with trusted supplier context, turn 3 uses no MCP,
and supplier_id never appears in a tool argument.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.agents.agents.analytics import build_analytics_agent
from app.agents.agents.conversation import build_conversation_agent
from app.agents.agents.planner import build_planner_agent
from app.agents.agents.router import build_router_agent
from app.agents.agents.visualization import build_visualization_agent
from app.agents.graph import build_workflow
from app.agents.models import build_model
from app.config import get_settings
from app.integrations.mcp.client import McpClient, McpToolResult
from app.schemas.agent import AgentQueryRequest
from app.schemas.request_context import RequestContext
from app.services.agent_service import AgentService


class CountingMcpClient(McpClient):
    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.call_count = 0
        self.tool_arg_keys: set[str] = set()

    async def call_tool(self, name, arguments, token=None) -> McpToolResult:
        self.call_count += 1
        self.tool_arg_keys.update(arguments.keys())
        return await super().call_tool(name, arguments, token=token)


async def main() -> None:
    settings = get_settings()
    model = build_model(settings)
    mcp = CountingMcpClient(settings.mcp_server_url)
    workflow = build_workflow(
        mcp=mcp,
        router=build_router_agent(model),
        planner=build_planner_agent(model),
        visualization=build_visualization_agent(model),
        analytics=build_analytics_agent(model),
        conversation=build_conversation_agent(model),
    )
    session_service = InMemorySessionService()
    runner = Runner(app_name="sales-agent", agent=workflow, session_service=session_service)
    service = AgentService(
        runner=runner, session_service=session_service, app_name="sales-agent",
        mcp=mcp, settings=settings,
    )

    context = RequestContext(user_id="DEV-USER-001", supplier_id="NORDVALE", roles=["admin"])
    conversation_id = uuid.uuid4().hex

    turns = [
        "What is our best-selling product online this year?",
        "Show its monthly sales.",
        "Show that as a bar chart.",
    ]
    for i, message in enumerate(turns, start=1):
        before = mcp.call_count
        response = await service.handle_query(
            AgentQueryRequest(message=message, conversation_id=conversation_id), context
        )
        used = mcp.call_count - before
        print(f"\n=== TURN {i}: {message}")
        print(f"MCP calls this turn: {used}")
        print("MESSAGE:", response.message[:200])
        print("TOOL CALLS:", [(c.tool_name, c.arguments) for c in response.tool_calls])
        print("VISUALIZATIONS:", [(v.type, v.dataset) for v in response.visualizations])

    print("\nsupplier_id ever in a tool argument:", "supplier_id" in mcp.tool_arg_keys)


if __name__ == "__main__":
    asyncio.run(main())
