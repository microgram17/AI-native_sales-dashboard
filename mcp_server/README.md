# Supplier BI — MCP Server

FastMCP server exposing sales analytics tools for the Supplier BI platform.
Uses streamable-http transport so the backend agent can call it over the network.

## Architecture

```
app/
├── server.py               # FastMCP entry-point with lifespan management
├── db/
│   ├── connection.py       # Async pool (server) + sync connection (scripts)
│   └── schema.sql          # PostgreSQL schema + views
├── repositories/
│   └── sales_repository.py # All SQL queries
├── schemas/
│   ├── common.py           # Shared Pydantic models and type aliases
│   ├── sales.py            # Sales-specific arg schemas with validation
│   ├── tool_result.py      # ToolResult envelope returned by every tool
│   └── visualization.py    # VisualizationSpec for frontend chart hints
└── tools/
    └── sales_tools.py      # @mcp.tool() registrations
scripts/
├── apply_schema.py         # Apply schema.sql to the database
├── generate_mock_excel.py  # Generate synthetic legacy Excel exports
├── import_legacy_excel.py  # Import Excel exports into PostgreSQL
└── test_product_performance_slice.py  # Spot-check a data slice
```

## Running locally (without Docker)

```bash
# Install dependencies
uv sync

# Apply schema (needs PostgreSQL running)
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/retail_bi \
  uv run python -m scripts.apply_schema

# Generate and import mock data
uv run python -m scripts.generate_mock_excel
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/retail_bi \
  uv run python -m scripts.import_legacy_excel

# Start the server
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/retail_bi \
  uv run python -m app.server

# Inspect with MCP Inspector
uv run mcp dev app/server.py
```

## Environment variables

| Variable       | Default                                                   | Description                  |
| -------------- | --------------------------------------------------------- | ---------------------------- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5433/retail_bi` | PostgreSQL connection string |

## Available tools

| Tool                                 | Description                                   |
| ------------------------------------ | --------------------------------------------- |
| `health_check`                       | Liveness check                                |
| `get_product_performance_timeseries` | Revenue / units / margin by product over time |
| `get_supplier_kpi_summary`           | Aggregate KPIs for a date range               |
| `get_top_products`                   | Top-N products ranked by a metric             |
| `get_market_benchmarks`              | Market share and benchmark data by period     |
| `list_supplier_products`             | Product catalog for a supplier                |
