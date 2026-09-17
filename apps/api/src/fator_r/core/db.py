import uuid
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, SessionTransaction
from sqlalchemy.pool import NullPool

from fator_r.core.settings import get_settings

FIRM_INFO_KEY = "firm_id"


def _create_engine(url: str) -> AsyncEngine:
    if get_settings().env == "test":
        # Sem pool nos testes: cada teste roda no seu event loop.
        return create_async_engine(url, poolclass=NullPool)
    return create_async_engine(url, pool_pre_ping=True)


@lru_cache
def get_engine() -> AsyncEngine:
    """Engine da role da aplicação (sujeita a RLS)."""
    return _create_engine(get_settings().database_url)


@lru_cache
def get_owner_engine() -> AsyncEngine:
    """Engine da role dona. Só para migrações, seed e infraestrutura de testes."""
    return _create_engine(get_settings().owner_database_url)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


@lru_cache
def get_owner_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_owner_engine(), expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _definir_escritorio_na_transacao(
    session: Session, transaction: SessionTransaction, connection: Connection, *_: Any
) -> None:
    """Toda transação de uma sessão com escritório começa com app.firm_id (RLS)."""
    firm_id = session.info.get(FIRM_INFO_KEY)
    if firm_id is not None:
        connection.execute(
            text("SELECT set_config('app.firm_id', :firm_id, true)"), {"firm_id": str(firm_id)}
        )


def firm_session(firm_id: uuid.UUID) -> AsyncSession:
    session = get_sessionmaker()()
    session.info[FIRM_INFO_KEY] = firm_id
    return session


async def get_session() -> AsyncIterator[AsyncSession]:
    """Sessão sem escritório: só enxerga o que as funções de autenticação expõem."""
    async with get_sessionmaker()() as session:
        yield session
