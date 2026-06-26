from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Supplier BI MCP Server",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def health_check() -> dict:
    """Check whether the MCP server is alive."""
    return {"status": "ok", "service": "mcp_server"}


@mcp.tool()
def get_sales_summary(supplier_code: str) -> dict:
    """
    Return a placeholder sales summary for a supplier.

    This will later query the database.
    """
    return {
        "supplier_code": supplier_code,
        "total_revenue": 0,
        "total_orders": 0,
        "average_order_value": 0,
        "note": "Placeholder MCP result",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")