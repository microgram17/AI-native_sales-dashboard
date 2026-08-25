from __future__ import annotations

import pytest
import pytest_asyncio
from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import create_async_engine

# psycopg async on Windows requires the selector event loop policy.
from app.db.windows_asyncio import configure_windows_event_loop

configure_windows_event_loop()

from app.context.supplier_context import SupplierResolver
from app.db.engine import get_settings
from app.repositories.sales_analytics_repository import SalesAnalyticsRepository
from app.services.sales_analytics_service import SalesAnalyticsService
from app.tools.sales_tools import register_sales_tools

SUPPLIER = "NORDVALE"
OTHER_SUPPLIER = "KIDS_CO"

JWT_SECRET = "test-mcp-secret-at-least-32-bytes-long!!"
JWT_ISSUER = "retail-bi-backend"
JWT_AUDIENCE = "retail-bi-mcp"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.fixture
def repository(engine) -> SalesAnalyticsRepository:
    return SalesAnalyticsRepository(engine)


@pytest.fixture
def service(repository) -> SalesAnalyticsService:
    return SalesAnalyticsService(repository)


@pytest.fixture
def resolver() -> SupplierResolver:
    class TestSupplierResolver:
        """Fixed supplier context for direct, in-process tool contract tests."""

        def resolve(self, _ctx) -> str:
            return SUPPLIER

    return TestSupplierResolver()


@pytest.fixture
def mcp_server(service, resolver) -> FastMCP:
    server = FastMCP("test-supplier-sales-mcp")
    register_sales_tools(server, service, resolver)
    return server
