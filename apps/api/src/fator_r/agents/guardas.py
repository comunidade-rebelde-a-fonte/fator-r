"""Guarda do span decide (T-608): 'corrigir' só com simulação persistida (PRD §7.9)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories import simulations


class RecomendacaoSemSimulacao(ValueError):
    pass


def _recomenda_corrigir(decisao: dict[str, Any]) -> bool:
    return any(decisao.get(campo) == "corrigir" for campo in ("veredito", "recomendacao", "acao"))


async def garantir_simulacao_para_corrigir(
    session: AsyncSession, firm_id: uuid.UUID, decisao: dict[str, Any]
) -> None:
    if not _recomenda_corrigir(decisao):
        return
    bruto = decisao.get("simulation_id")
    try:
        simulation_id = uuid.UUID(str(bruto))
    except (TypeError, ValueError) as exc:
        raise RecomendacaoSemSimulacao("Recomendação 'corrigir' sem simulation_id") from exc
    simulacao = await simulations.obter(session, firm_id, simulation_id)
    if simulacao is None or simulacao.veredito != "corrigir":
        raise RecomendacaoSemSimulacao("Recomendação 'corrigir' sem simulação correspondente")
