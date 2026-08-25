# AI Sales Dashboard

A supplier-scoped business intelligence dashboard with a conversational AI
assistant. Users can explore sales through the standard dashboard or ask
questions in English and Swedish and receive grounded answers with metric
cards, bar charts, line charts, or tables.

## How it works

```text
React frontend
      |
      v
FastAPI backend -----> Dashboard services ----------------> PostgreSQL
      |
      v
Google ADK LlmAgent <----> LLM
      |
      v
MCP analytics server -------------------------------------> PostgreSQL
```

The chat uses one Google ADK `LlmAgent` with native MCP tool calling. The model
chooses between four typed analytics tools (`sales_summary`, `sales_rank`,
`sales_trend`, and `product_overview`) plus the supporting `resolve_product`
tool. MCP returns semantic `DataView` objects, and React renders them according
to their shape.

The backend authenticates every request and creates a short-lived internal MCP
token containing the verified supplier context. `supplier_id` is never a
model-visible tool argument, and every analytics query is supplier-filtered.

## Project structure

```text
frontend/     React, TypeScript, Recharts, and export functionality
backend/      FastAPI API, authentication, dashboard services, and ADK agent
mcp_server/   Typed MCP analytics tools and supplier-scoped data access
database/     Alembic migrations and demo-data scripts
data/         Generated demo CSV and Excel data
```

## Prerequisites

- Docker Desktop with Docker Compose
- [uv](https://docs.astral.sh/uv/) for database setup
- An OpenAI API key

Python 3.12 is used by all Python projects. Node.js is not required when the
frontend is run through Docker.

## First-time setup

Run these commands from the repository root in PowerShell.

### 1. Configure the backend

```powershell
Copy-Item backend/.env.example backend/.env
```

Open `backend/.env` and replace the placeholder API key:

```dotenv
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini
```

The included JWT secrets and database credentials are development placeholders
and must not be used in production.

### 2. Start PostgreSQL

```powershell
docker compose up -d postgres
```

PostgreSQL is exposed to the host on port `5433`.

### 3. Create and seed the database

```powershell
cd database
uv sync --frozen
uv run alembic upgrade head
uv run python -m scripts.generate_demo_data
uv run python -m scripts.import_demo_data
uv run python -m scripts.seed_dev_auth
cd ..
```

The final command prints all generated demo accounts. Their default password is
`DemoPassword123!`. For example, the included NORDVALE account is:

```text
supplier4@example.com / DemoPassword123!
```

### 4. Build and start the application

```powershell
docker compose up --build
```

Open <http://localhost:5173> and log in with one of the printed supplier
accounts.

## Normal local use

After the first-time setup, start the complete stack with:

```powershell
docker compose up
```

The local services are available at:

| Service | URL |
|---|---|
| Frontend | <http://localhost:5173> |
| Backend API and OpenAPI | <http://localhost:8000/docs> |
| MCP endpoint | <http://localhost:8001/mcp> |
| PostgreSQL | `localhost:5433` |

Stop the stack with `Ctrl+C`, or run it in the background with
`docker compose up -d`. To stop background services:

```powershell
docker compose down
```

The PostgreSQL data remains in the `postgres_data` Docker volume. Running
`docker compose down -v` also deletes that local database and requires the
migration/import steps to be run again.

## Verification

```powershell
cd backend
uv run --frozen pytest -q

cd ../mcp_server
uv run --frozen pytest -q

cd ../frontend
npm ci
npm test
npm run build
```

## Notes

- Conversation state is stored in memory and is reset when the backend restarts.
- The containers mount the source directories during local development, so most
  backend and frontend edits reload automatically. The MCP container must be
  restarted after MCP tool or contract changes.
- The application and bundled credentials are configured for local development,
  not production deployment.
