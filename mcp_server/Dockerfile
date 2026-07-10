FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

CMD ["python", "-m", "app.main"]