"""Empresas do escritório. Toda função exige firm_id (e o RLS confere de novo)."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import Company


class CnpjDuplicado(Exception):
    pass


@dataclass(frozen=True)
class FiltroEmpresas:
    ativo: bool | None = None
    sujeita_fator_r: bool | None = None
    busca: str | None = None
    limit: int = 50
    offset: int = 0


async def listar(
    session: AsyncSession, firm_id: uuid.UUID, filtro: FiltroEmpresas
) -> tuple[list[Company], int]:
    query = select(Company).where(Company.firm_id == firm_id)
    if filtro.ativo is not None:
        query = query.where(Company.ativo.is_(filtro.ativo))
    if filtro.sujeita_fator_r is not None:
        query = query.where(Company.sujeita_fator_r.is_(filtro.sujeita_fator_r))
    if filtro.busca:
        termo = f"%{filtro.busca.strip()}%"
        digitos = "".join(ch for ch in filtro.busca if ch.isdigit())
        condicoes = [Company.nome.ilike(termo)]
        if digitos:
            condicoes.append(Company.cnpj.like(f"%{digitos}%"))
        query = query.where(or_(*condicoes))
    total = len((await session.execute(query.with_only_columns(Company.id))).all())
    rows = await session.execute(
        query.order_by(Company.nome).limit(filtro.limit).offset(filtro.offset)
    )
    return list(rows.scalars()), total


async def obter(session: AsyncSession, firm_id: uuid.UUID, company_id: uuid.UUID) -> Company | None:
    result = await session.execute(
        select(Company).where(Company.firm_id == firm_id, Company.id == company_id)
    )
    return result.scalar_one_or_none()


async def criar(session: AsyncSession, firm_id: uuid.UUID, dados: dict[str, Any]) -> Company:
    company = Company(firm_id=firm_id, **dados)
    session.add(company)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "uq_companies_firm_cnpj" in str(exc.orig):
            raise CnpjDuplicado from exc
        raise
    await session.refresh(company)
    return company


async def atualizar(
    session: AsyncSession, firm_id: uuid.UUID, company_id: uuid.UUID, dados: dict[str, Any]
) -> Company | None:
    company = await obter(session, firm_id, company_id)
    if company is None:
        return None
    for campo, valor in dados.items():
        setattr(company, campo, valor)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "uq_companies_firm_cnpj" in str(exc.orig):
            raise CnpjDuplicado from exc
        raise
    await session.refresh(company)
    return company


async def listar_carteira(session: AsyncSession, firm_id: uuid.UUID) -> list[Company]:
    """Empresas ativas e sujeitas ao Fator R (as únicas que entram na carteira)."""
    rows = await session.execute(
        select(Company)
        .where(
            Company.firm_id == firm_id,
            Company.ativo.is_(True),
            Company.sujeita_fator_r.is_(True),
        )
        .order_by(Company.nome)
    )
    return list(rows.scalars())


async def obter_por_cnpj(session: AsyncSession, firm_id: uuid.UUID, cnpj: str) -> Company | None:
    """Empresa do escritório com o CNPJ (só dígitos). Empresa de outro escritório nunca volta."""
    return (
        await session.execute(
            select(Company).where(Company.firm_id == firm_id, Company.cnpj == cnpj)
        )
    ).scalar_one_or_none()
