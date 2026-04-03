FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY server/pyproject.toml ./
COPY server/src/ src/
COPY server/alembic.ini ./
COPY server/alembic/ alembic/

RUN uv sync --no-dev

ENV PORT=8000

COPY server/scripts/ scripts/

COPY server/scripts/start.sh ./
CMD ["sh", "start.sh"]
