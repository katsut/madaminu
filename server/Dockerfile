FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY src/ src/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "madaminu.main:app", "--host", "0.0.0.0", "--port", "8000"]
