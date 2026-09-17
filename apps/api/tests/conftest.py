"""Infra de testes: banco `*_test` isolado, migrado com Alembic e limpo a cada teste.

- A api roda com a role da aplicação (DATABASE_URL, sujeita a RLS).
- Preparação, limpeza e factories usam a role dona (DATABASE_OWNER_URL).
Em CI essas variáveis já vêm do workflow. Localmente, são montadas a partir do .env da raiz.
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _env_da_raiz() -> dict[str, str]:
    values: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip("'\"")
    return values


if os.environ.get("ENV") != "test":
    _env = _env_da_raiz()
    _port = _env.get("DB_PORT", "5432")
    _owner = f"{_env.get('POSTGRES_USER', 'fator_r_owner')}:{_env.get('POSTGRES_PASSWORD', '')}"
    _app = f"{_env.get('APP_DB_USER', 'fator_r_app')}:{_env.get('APP_DB_PASSWORD', '')}"
    os.environ["ENV"] = "test"
    os.environ["DATABASE_URL"] = f"postgresql+asyncpg://{_app}@localhost:{_port}/fator_r_test"
    os.environ["DATABASE_OWNER_URL"] = (
        f"postgresql+asyncpg://{_owner}@localhost:{_port}/fator_r_test"
    )
    os.environ["APP_DB_PASSWORD"] = _env.get("APP_DB_PASSWORD", "")
os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "false")
import tempfile as _tempfile  # noqa: E402

# Uploads dos testes sempre num diretório temporário novo (nunca /data/uploads).
os.environ["UPLOAD_DIR"] = _tempfile.mkdtemp(prefix="fator-r-uploads-")

import asyncio  # noqa: E402  (as variáveis de ambiente precisam vir antes dos imports do app)

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from fator_r.core import db  # noqa: E402
from fator_r.core.settings import get_settings  # noqa: E402
from fator_r.db_roles import configurar_role_app  # noqa: E402
from fator_r.main import create_app  # noqa: E402
from fator_r.repositories.simples_tables import carregar_csv  # noqa: E402


async def _ensure_database(url: str) -> None:
    parsed = make_url(url)
    conn = await asyncpg.connect(
        user=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", parsed.database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{parsed.database}"')
    finally:
        await conn.close()


def _limpar_caches() -> None:
    for fn in (
        get_settings,
        db.get_engine,
        db.get_owner_engine,
        db.get_sessionmaker,
        db.get_owner_sessionmaker,
    ):
        fn.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    _limpar_caches()
    settings = get_settings()
    assert make_url(settings.database_url).database.endswith("_test")
    assert make_url(settings.owner_database_url).database.endswith("_test")
    asyncio.run(_ensure_database(settings.owner_database_url))
    config = Config(str(ROOT / "apps/api/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "apps/api/alembic"))
    command.upgrade(config, "head")
    asyncio.run(configurar_role_app(settings.owner_database_url, os.environ["APP_DB_PASSWORD"]))
    asyncio.run(_carregar_tabelas())


async def _carregar_tabelas() -> None:
    async with db.get_owner_sessionmaker()() as session:
        await carregar_csv(session)
    await db.get_owner_engine().dispose()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    _limpar_caches()
    from fator_r.api.auth import login_rate_limiter

    login_rate_limiter.clear()
    yield
    async with db.get_owner_engine().begin() as conn:
        tables = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename NOT IN ('alembic_version', 'simples_tables')"
            )
        )
        names = ", ".join(f'"{row[0]}"' for row in tables)
        if names:
            await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    await db.get_owner_engine().dispose()
    await db.get_engine().dispose()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
