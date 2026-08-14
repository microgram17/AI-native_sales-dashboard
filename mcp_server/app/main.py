from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.context.supplier_context import build_supplier_context_resolver
from app.db.engine import get_engine
from app.repositories.sales_analytics_repository import SalesAnalyticsRepository
from app.services.sales_analytics_service import SalesAnalyticsService
from app.tools.sales_tools import register_sales_tools

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

_repository = SalesAnalyticsRepository(get_engine())
_service = SalesAnalyticsService(_repository)
_supplier_resolver = build_supplier_context_resolver()

register_sales_tools(mcp, _service, _supplier_resolver)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )