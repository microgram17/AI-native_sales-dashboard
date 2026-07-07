FROM python:3.13-slim-bookworm

WORKDIR /app

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies first (better layer caching)
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen || uv sync

# Copy application source
COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "app.server"]
