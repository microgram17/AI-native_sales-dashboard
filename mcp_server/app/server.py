from mcp.server.fastmcp import FastMCP

from app.db.connection import LazyAsyncConnectionPool, get_database_url
from app.repositories.supplier_analytics_repository import SupplierAnalyticsRepository
from app.tools import register_sales_tools

mcp = FastMCP(
    name="Supplier BI MCP Server",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
)


@mcp.tool()
def health_check() -> dict:
    """Check whether the MCP server is alive."""
    return {"status": "ok", "service": "mcp_server"}


pool = LazyAsyncConnectionPool(get_database_url())
repo = SupplierAnalyticsRepository(pool)
register_sales_tools(mcp, repo)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")