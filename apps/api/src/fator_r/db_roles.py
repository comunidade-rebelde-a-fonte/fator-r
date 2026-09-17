"""Habilita LOGIN e define a senha da role da aplicação (rodar após as migrações).

Uso: python -m fator_r.db_roles  (APP_DB_PASSWORD e DATABASE_OWNER_URL no ambiente)
"""

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from fator_r.core.rls_sql import APP_ROLE
from fator_r.core.settings import get_settings


async def configurar_role_app(owner_url: str, senha: str) -> None:
    engine = create_async_engine(owner_url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            comando = (
                await conn.execute(
                    text(
                        f"SELECT format('ALTER ROLE {APP_ROLE} WITH LOGIN PASSWORD %L', "
                        "CAST(:senha AS text))"
                    ),
                    {"senha": senha},
                )
            ).scalar_one()
            await conn.execute(text(comando))
    finally:
        await engine.dispose()


def main() -> None:
    senha = os.environ.get("APP_DB_PASSWORD")
    if not senha:
        raise SystemExit("APP_DB_PASSWORD ausente")
    asyncio.run(configurar_role_app(get_settings().owner_database_url, senha))


if __name__ == "__main__":
    main()
