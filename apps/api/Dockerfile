FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY fixtures/simples_tables_2018.csv ./fixtures/simples_tables_2018.csv
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 app && mkdir -p /data/uploads && chown -R app /data/uploads
USER app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
ENV FORWARDED_ALLOW_IPS=127.0.0.1
# IP real do cliente só quando vier de proxy confiável (FORWARDED_ALLOW_IPS).
CMD ["uvicorn", "fator_r.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
