# AI Sales Dashboard

The chat assistant is a single Google ADK `LlmAgent` with native access to the
sales MCP server. The model selects one of four typed analytics tools; the MCP
result contains flat semantic data views that the React client renders by shape.

## Agent request flow

1. FastAPI authenticates the user and mints a short-lived supplier-scoped MCP
   token.
2. ADK exposes `sales_summary`, `sales_rank`, `sales_trend`,
   `product_overview`, and `resolve_product` through `McpToolset`.
3. The selected MCP tool returns an `AnalyticsResult` containing query context
   and `DataView` rows.
4. The agent returns only a short message and display selections that reference
   those view IDs.
5. The frontend maps `metrics`, `categorical`, and `timeseries` views to cards,
   bars, and lines, with a table override.

Supplier identity is never model-visible or accepted as a tool argument.
Conversation history is managed by ADK; only the latest successful semantic
views are retained for presentation-only follow-ups.

## Local development

```powershell
docker compose up -d postgres

cd database
uv sync --frozen
uv run alembic upgrade head
uv run python -m scripts.generate_demo_data
uv run python -m scripts.import_demo_data
uv run python -m scripts.seed_dev_auth

cd ..
docker compose up --build
```

The frontend runs at `http://localhost:5173`, the API at
`http://localhost:8000`, and the MCP endpoint at
`http://localhost:8001/mcp`.

## Verification

```powershell
cd backend
uv run pytest -q

cd ../mcp_server
uv run pytest -q

cd ../frontend
npm test -- --run
npm run build
```

With the stack running and a valid NORDVALE supplier access token, run the
24-case core and 12-sequence follow-up acceptance corpus with:

```powershell
$env:AGENT_EVAL_TOKEN='<token>'
cd backend
uv run python scripts/evaluate_agent.py
```
