"""Acesso a usuários e sessões.

Exceção documentada à regra "firm_id obrigatório": o login acontece antes de o
escritório ser conhecido. A leitura de usuários passa pelas funções SECURITY DEFINER
auth_find_user / auth_session_user (migração 0004), que devolvem só o mínimo.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import UserSession


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID
    firm_id: uuid.UUID
    email: str
    nome: str


@dataclass(frozen=True)
class UserCredentials:
    id: uuid.UUID
    firm_id: uuid.UUID
    email: str
    nome: str
    senha_hash: str
    ativo: bool


async def get_user_by_email(session: AsyncSession, email: str) -> UserCredentials | None:
    row = (
        await session.execute(text("SELECT * FROM auth_find_user(:email)"), {"email": email})
    ).one_or_none()
    return UserCredentials(*row) if row else None


async def create_session(
    session: AsyncSession, user_id: uuid.UUID, token_hash: str, ttl: timedelta
) -> None:
    session.add(
        UserSession(user_id=user_id, token_hash=token_hash, expira_em=datetime.now(UTC) + ttl)
    )
    await session.commit()


async def get_user_by_session_token(
    session: AsyncSession, token_hash: str
) -> AuthenticatedUser | None:
    row = (
        await session.execute(
            text("SELECT * FROM auth_session_user(:token_hash)"), {"token_hash": token_hash}
        )
    ).one_or_none()
    return AuthenticatedUser(*row) if row else None


async def delete_session(session: AsyncSession, token_hash: str) -> None:
    await session.execute(delete(UserSession).where(UserSession.token_hash == token_hash))
    await session.commit()
