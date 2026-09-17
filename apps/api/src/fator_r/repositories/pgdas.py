"""Documentos PGDAS-D do escritório. firm_id obrigatório (e RLS)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import PgdasDocument


async def obter(
    session: AsyncSession, firm_id: uuid.UUID, document_id: uuid.UUID
) -> PgdasDocument | None:
    return (
        await session.execute(
            select(PgdasDocument).where(
                PgdasDocument.firm_id == firm_id, PgdasDocument.id == document_id
            )
        )
    ).scalar_one_or_none()


async def obter_por_sha(
    session: AsyncSession, firm_id: uuid.UUID, sha256: str
) -> PgdasDocument | None:
    return (
        await session.execute(
            select(PgdasDocument).where(
                PgdasDocument.firm_id == firm_id, PgdasDocument.sha256 == sha256
            )
        )
    ).scalar_one_or_none()


async def listar(
    session: AsyncSession, firm_id: uuid.UUID, status: str | None, limit: int, offset: int
) -> tuple[list[PgdasDocument], int, dict[str, int]]:
    base = select(PgdasDocument).where(PgdasDocument.firm_id == firm_id)
    filtrada = base.where(PgdasDocument.status == status) if status else base
    total = (
        await session.execute(select(func.count()).select_from(filtrada.subquery()))
    ).scalar_one()
    rows = await session.execute(
        filtrada.order_by(PgdasDocument.criado_em.desc()).limit(limit).offset(offset)
    )
    contagem = await session.execute(
        select(PgdasDocument.status, func.count())
        .where(PgdasDocument.firm_id == firm_id)
        .group_by(PgdasDocument.status)
    )
    return list(rows.scalars()), total, {s: n for s, n in contagem.all()}
