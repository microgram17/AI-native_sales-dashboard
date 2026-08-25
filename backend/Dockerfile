FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
