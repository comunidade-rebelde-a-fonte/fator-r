"""Caso de uso: carregar dados do escritório e chamar o motor (sem conta fora de domain/)."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.domain.fator_r import MovimentoMes, ResultadoFatorR, calcular
from fator_r.domain.janela import janela
from fator_r.repositories import firms, movements, simples_tables
from fator_r.repositories.orm import Company, MonthlyMovement


def movimento_mes(m: MonthlyMovement) -> MovimentoMes:
    return MovimentoMes(
        competencia=m.competencia,
        receita_bruta=m.receita_bruta,
        pro_labore=m.pro_labore,
        salarios=m.salarios,
        cpp=m.cpp,
        fgts=m.fgts,
        origem=m.origem,
    )


async def resultado_empresa(
    session: AsyncSession, firm_id: uuid.UUID, company: Company, pa: date
) -> ResultadoFatorR:
    j = janela(pa)
    firm = await firms.obter(session, firm_id)
    lancados = await movements.listar(session, firm_id, company.id, j.inicio, j.fim)
    tabelas = await simples_tables.tabelas_vigentes(session, j.pa)
    return calcular(
        pa=j.pa,
        inicio_atividade=company.inicio_atividade,
        movimentos=[movimento_mes(m) for m in lancados],
        tabelas=tabelas,
        politica=firms.politica_de(firm),
    )
