"""Movimentos mensais. Toda função exige firm_id (e o RLS confere de novo)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import Company, MonthlyMovement

CAMPOS_VALOR = ("receita_bruta", "pro_labore", "salarios", "cpp", "fgts")


async def listar(
    session: AsyncSession,
    firm_id: uuid.UUID,
    company_id: uuid.UUID,
    de: date | None = None,
    ate: date | None = None,
) -> list[MonthlyMovement]:
    query = select(MonthlyMovement).where(
        MonthlyMovement.firm_id == firm_id, MonthlyMovement.company_id == company_id
    )
    if de is not None:
        query = query.where(MonthlyMovement.competencia >= de)
    if ate is not None:
        query = query.where(MonthlyMovement.competencia <= ate)
    rows = await session.execute(query.order_by(MonthlyMovement.competencia))
    return list(rows.scalars())


async def listar_para_empresas(
    session: AsyncSession, firm_id: uuid.UUID, company_ids: list[uuid.UUID], de: date, ate: date
) -> list[MonthlyMovement]:
    """Uma consulta para os movimentos de várias empresas numa janela (carteira)."""
    if not company_ids:
        return []
    rows = await session.execute(
        select(MonthlyMovement).where(
            MonthlyMovement.firm_id == firm_id,
            MonthlyMovement.company_id.in_(company_ids),
            MonthlyMovement.competencia >= de,
            MonthlyMovement.competencia <= ate,
        )
    )
    return list(rows.scalars())


async def obter(
    session: AsyncSession, firm_id: uuid.UUID, company_id: uuid.UUID, competencia: date
) -> MonthlyMovement | None:
    result = await session.execute(
        select(MonthlyMovement).where(
            MonthlyMovement.firm_id == firm_id,
            MonthlyMovement.company_id == company_id,
            MonthlyMovement.competencia == competencia,
        )
    )
    return result.scalar_one_or_none()


async def upsert_manual(
    session: AsyncSession,
    firm_id: uuid.UUID,
    company: Company,
    competencia: date,
    valores: dict[str, Decimal],
    observacao: str | None,
) -> MonthlyMovement:
    """Lançamento manual: cria ou substitui a competência inteira (origem=manual)."""
    dados = {campo: valores.get(campo, Decimal("0")) for campo in CAMPOS_VALOR}
    statement = insert(MonthlyMovement).values(
        firm_id=firm_id,
        company_id=company.id,
        competencia=competencia,
        origem="manual",
        observacao=observacao,
        **dados,
    )
    statement = statement.on_conflict_do_update(
        constraint="uq_movements_company_competencia",
        set_={**dados, "origem": "manual", "observacao": observacao, "atualizado_em": func.now()},
    )
    await session.execute(statement)
    await session.commit()
    movimento = await obter(session, firm_id, company.id, competencia)
    assert movimento is not None  # noqa: S101 - acabou de ser gravado na mesma sessão
    return movimento


async def criar_se_ausente(session: AsyncSession, movimento: MonthlyMovement) -> bool:
    """Insere só se a competência não existir. Nunca sobrescreve (usado pelo PGDAS)."""
    statement = (
        insert(MonthlyMovement)
        .values(
            firm_id=movimento.firm_id,
            company_id=movimento.company_id,
            competencia=movimento.competencia,
            origem=movimento.origem,
            observacao=movimento.observacao,
            pgdas_document_id=movimento.pgdas_document_id,
            **{campo: getattr(movimento, campo) or Decimal("0") for campo in CAMPOS_VALOR},
        )
        .on_conflict_do_nothing(constraint="uq_movements_company_competencia")
        .returning(MonthlyMovement.id)
    )
    inserido = (await session.execute(statement)).scalar_one_or_none()
    return inserido is not None
