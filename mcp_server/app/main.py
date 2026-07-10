from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.db.engine import get_engine
from app.repositories.sales_query_repository import SalesQueryRepository
from app.tools.sales_query_tools import register_sales_query_tools

# Keep this only if you added the Windows asyncio helper.
# It is harmless on Linux if the helper checks sys.platform == "win32".
try:
    from app.db.windows_asyncio import configure_windows_event_loop

    configure_windows_event_loop()
except ImportError:
    pass


mcp = FastMCP(
    "supplier-sales-mcp",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    port=8000,
)

sales_query_repository = SalesQueryRepository(get_engine())
register_sales_query_tools(mcp, sales_query_repository)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )