FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY server/pyproject.toml ./
COPY server/src/ src/
COPY server/alembic.ini ./
COPY server/alembic/ alembic/

RUN uv sync --no-dev

ENV PORT=8000

CMD uv run uvicorn madaminu.main:app --host 0.0.0.0 --port $PORT
