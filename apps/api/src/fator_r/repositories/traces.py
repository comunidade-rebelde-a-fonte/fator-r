"""Leitura de traces e notas do escritório (painel de observabilidade). firm_id obrigatório."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import ColumnElement, Integer, case, cast, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import AgentTrace, EvalGold, EvalHuman


@dataclass(frozen=True)
class ResumoAgente:
    agente: str
    volume: int
    latencia_media_ms: Decimal | None
    confianca_media: Decimal | None
    erros: int
    reviews: int


@dataclass(frozen=True)
class Resumo:
    corridas_24h: int
    corridas_total: int
    pendencias_sem_nota: int
    acerto_ouro: Decimal | None
    acerto_humano: Decimal | None
    por_agente: list[ResumoAgente]


def _sem_nota() -> ColumnElement[bool]:
    return ~exists().where(EvalHuman.trace_id == AgentTrace.id)


async def resumo(session: AsyncSession, firm_id: uuid.UUID) -> Resumo:
    agora = datetime.now(UTC)
    totais = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(AgentTrace.criado_em >= agora - timedelta(hours=24)),
                func.count().filter(_sem_nota()),
            ).where(AgentTrace.firm_id == firm_id)
        )
    ).one()
    ouro = (
        await session.execute(
            select(
                func.count().filter(EvalGold.status == "ok"),
                func.count().filter(EvalGold.status == "erro"),
            ).where(EvalGold.firm_id == firm_id)
        )
    ).one()
    humano = (
        await session.execute(
            select(func.count().filter(EvalHuman.nota == "acerto"), func.count()).where(
                EvalHuman.firm_id == firm_id
            )
        )
    ).one()
    agentes = (
        await session.execute(
            select(
                AgentTrace.agente,
                func.count(),
                func.avg(AgentTrace.latencia_ms),
                func.avg(AgentTrace.confianca),
                func.sum(cast(case((AgentTrace.status == "error", 1), else_=0), Integer)),
                func.sum(cast(case((AgentTrace.status == "needs_review", 1), else_=0), Integer)),
            )
            .where(AgentTrace.firm_id == firm_id)
            .group_by(AgentTrace.agente)
            .order_by(AgentTrace.agente)
        )
    ).all()
    comparaveis = ouro[0] + ouro[1]
    return Resumo(
        corridas_24h=totais[1],
        corridas_total=totais[0],
        pendencias_sem_nota=totais[2],
        acerto_ouro=Decimal(ouro[0]) / Decimal(comparaveis) if comparaveis else None,
        acerto_humano=Decimal(humano[0]) / Decimal(humano[1]) if humano[1] else None,
        por_agente=[
            ResumoAgente(
                agente=a,
                volume=v,
                latencia_media_ms=Decimal(lat) if lat is not None else None,
                confianca_media=Decimal(conf) if conf is not None else None,
                erros=e or 0,
                reviews=r or 0,
            )
            for a, v, lat, conf, e, r in agentes
        ],
    )


@dataclass(frozen=True)
class FiltroTraces:
    agente: str | None = None
    status: str | None = None
    sem_nota: bool | None = None
    limit: int = 50
    offset: int = 0


async def listar(
    session: AsyncSession, firm_id: uuid.UUID, filtro: FiltroTraces
) -> tuple[list[tuple[AgentTrace, bool]], int]:
    tem_nota = exists().where(EvalHuman.trace_id == AgentTrace.id).label("tem_nota")
    query = select(AgentTrace, tem_nota).where(AgentTrace.firm_id == firm_id)
    if filtro.agente:
        query = query.where(AgentTrace.agente == filtro.agente)
    if filtro.status:
        query = query.where(AgentTrace.status == filtro.status)
    if filtro.sem_nota is True:
        query = query.where(_sem_nota())
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await session.execute(
        query.order_by(AgentTrace.criado_em.desc()).limit(filtro.limit).offset(filtro.offset)
    )
    return [(row[0], bool(row[1])) for row in rows.all()], total


async def obter(session: AsyncSession, firm_id: uuid.UUID, trace_id: str) -> AgentTrace | None:
    return (
        await session.execute(
            select(AgentTrace).where(AgentTrace.firm_id == firm_id, AgentTrace.id == trace_id)
        )
    ).scalar_one_or_none()


async def evals(
    session: AsyncSession, firm_id: uuid.UUID, trace_id: str
) -> tuple[list[EvalGold], list[EvalHuman]]:
    ouro = await session.execute(
        select(EvalGold)
        .where(EvalGold.firm_id == firm_id, EvalGold.trace_id == trace_id)
        .order_by(EvalGold.campo)
    )
    humano = await session.execute(
        select(EvalHuman)
        .where(EvalHuman.firm_id == firm_id, EvalHuman.trace_id == trace_id)
        .order_by(EvalHuman.criado_em.desc())
    )
    return list(ouro.scalars()), list(humano.scalars())
