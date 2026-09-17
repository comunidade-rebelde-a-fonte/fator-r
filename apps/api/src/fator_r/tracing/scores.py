"""Notas dos traces: gravadas no Postgres (fonte da verdade) e espelhadas no Langfuse (T-408)."""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import AgentTrace, EvalGold, EvalHuman
from fator_r.tracing.client import get_langfuse

Nota = Literal["acerto", "parcial", "erro"]
StatusOuro = Literal["ok", "erro", "ouro_indisponivel"]


class NotaSemComentario(ValueError):
    """Nota 'erro' exige comentário (PRD §7.9)."""


class TraceNaoEncontrado(LookupError):
    pass


@dataclass(frozen=True)
class ResultadoCampoOuro:
    campo: str
    esperado: str | None
    obtido: str | None
    dentro_tolerancia: bool | None
    status: StatusOuro


async def _trace_do_escritorio(
    session: AsyncSession, firm_id: uuid.UUID, trace_id: str
) -> AgentTrace:
    trace = (
        await session.execute(
            select(AgentTrace).where(AgentTrace.firm_id == firm_id, AgentTrace.id == trace_id)
        )
    ).scalar_one_or_none()
    if trace is None:
        raise TraceNaoEncontrado(trace_id)
    return trace


async def gold(
    session: AsyncSession,
    firm_id: uuid.UUID,
    trace_id: str,
    resultados: list[ResultadoCampoOuro],
) -> Decimal | None:
    """Grava a nota ouro por campo e devolve o acerto (0 a 1) entre campos comparáveis."""
    await _trace_do_escritorio(session, firm_id, trace_id)
    for r in resultados:
        session.add(
            EvalGold(
                firm_id=firm_id,
                trace_id=trace_id,
                campo=r.campo,
                esperado=r.esperado,
                obtido=r.obtido,
                dentro_tolerancia=r.dentro_tolerancia,
                status=r.status,
            )
        )
    await session.commit()

    comparaveis = [r for r in resultados if r.status != "ouro_indisponivel"]
    langfuse = get_langfuse()
    for r in comparaveis:
        langfuse.create_score(
            name=f"gold_{r.campo}",
            value=1.0 if r.status == "ok" else 0.0,
            data_type="BOOLEAN",
            trace_id=trace_id,
        )
    if not comparaveis:
        return None
    acerto = Decimal(sum(1 for r in comparaveis if r.status == "ok")) / Decimal(len(comparaveis))
    langfuse.create_score(
        name="gold_acerto", value=float(acerto), data_type="NUMERIC", trace_id=trace_id
    )
    return acerto


async def human(
    session: AsyncSession,
    firm_id: uuid.UUID,
    trace_id: str,
    user_id: uuid.UUID,
    nota: Nota,
    comentario: str | None,
) -> EvalHuman:
    comentario = (comentario or "").strip() or None
    if nota == "erro" and comentario is None:
        raise NotaSemComentario("Comentário é obrigatório quando a nota é 'erro'")
    await _trace_do_escritorio(session, firm_id, trace_id)
    avaliacao = EvalHuman(
        firm_id=firm_id, trace_id=trace_id, user_id=user_id, nota=nota, comentario=comentario
    )
    session.add(avaliacao)
    await session.commit()
    get_langfuse().create_score(
        name="human_eval",
        value=nota,
        data_type="CATEGORICAL",
        trace_id=trace_id,
        comment=comentario,
    )
    return avaliacao
