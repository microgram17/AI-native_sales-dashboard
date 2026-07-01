from pathlib import Path

from app.adapters.mcp_sales_client import McpSalesClient
from app.services.agent_service import AgentService

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    sales_analytics = McpSalesClient()
    service = AgentService(sales_analytics=sales_analytics)

    compiled_graph = service._build_graph()

    output_path = Path("agent_graph.png")
    output_path.write_bytes(compiled_graph.get_graph().draw_mermaid_png())

    print(f"Saved graph PNG to: {output_path.resolve()}")


if __name__ == "__main__":
    main()