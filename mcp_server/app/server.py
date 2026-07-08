from mcp.server.fastmcp import FastMCP

from app.db.connection import create_pool
from app.repositories.sales_repository import SalesRepository
from app.tools.sales_tools import register_sales_tools


mcp = FastMCP(
    name="Supplier BI MCP Server",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
)


@mcp.tool()
def health_check() -> dict:
    """Check whether the MCP server is alive."""
    return {"status": "ok", "service": "supplier_bi_mcp_server"}


pool = create_pool()
sales_repository = SalesRepository(pool)

register_sales_tools(mcp, sales_repository)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")