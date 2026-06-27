from mcp.server.fastmcp import FastMCP

from app.repositories.sales_repository import (
    get_supplier_revenue_trend as fetch_supplier_revenue_trend,
)
from app.repositories.sales_repository import get_supplier_summary as fetch_supplier_summary
from app.repositories.sales_repository import get_top_products as fetch_top_products
from app.repositories.sales_repository import list_suppliers as fetch_suppliers

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


@mcp.tool()
def get_supplier_summary(supplier_code: str) -> dict:
    """Get a sales summary for one supplier."""
    return fetch_supplier_summary(supplier_code)


@mcp.tool()
def get_supplier_revenue_trend(
    supplier_code: str,
    period_type: str = "month",
) -> dict:
    """Get supplier revenue trend and market benchmark for week/month periods."""
    return fetch_supplier_revenue_trend(
        supplier_code=supplier_code,
        period_type=period_type,
    )


@mcp.tool()
def get_top_products(
    supplier_code: str,
    limit: int = 5,
    sort_by: str = "revenue",
) -> dict:
    """Get top supplier products by revenue, units, or orders."""
    return fetch_top_products(
        supplier_code=supplier_code,
        limit=limit,
        sort_by=sort_by,
    )


@mcp.tool()
def list_suppliers() -> dict:
    """List available suppliers for dashboard filtering."""
    return fetch_suppliers()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")