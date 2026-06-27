FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen || uv sync

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "app.server"]