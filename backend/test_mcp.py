import asyncio
from pprint import pprint

from app.adapters.mcp_sales_client import McpSalesClient

async def main():
    # 127.0.0.1:8001 is where Docker exposes your MCP server to your local machine
    client = McpSalesClient(server_url="http://127.0.0.1:8001/mcp/")

    print("--- Available Tools ---")
    tools = await client.list_tools()
    for t in tools:
        print(f"- {t['name']}")
    
    print("\n--- Testing Sales Breakdown ---")
    custom_query = await client.call_tool("break_down_sales", {
        "supplier_code": "SUP-001",
        "metric": "net_sales",
        "breakdown_by": "region",
    })
    pprint(custom_query)

if __name__ == "__main__":
    asyncio.run(main())