"""Caso de uso da carteira: 4 consultas fixas (escritório, empresas, movimentos, tabelas)."""

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.domain.carteira import Carteira, EmpresaCarteira, montar_carteira
from fator_r.domain.fator_r import MovimentoMes
from fator_r.domain.janela import janela
from fator_r.repositories import companies, firms, movements, simples_tables
from fator_r.services.fator_r import movimento_mes


async def carteira_do_escritorio(session: AsyncSession, firm_id: uuid.UUID, pa: date) -> Carteira:
    j = janela(pa)
    firm = await firms.obter(session, firm_id)
    empresas = await companies.listar_carteira(session, firm_id)
    lancados = await movements.listar_para_empresas(
        session, firm_id, [e.id for e in empresas], j.inicio, j.fim
    )
    tabelas = await simples_tables.tabelas_vigentes(session, j.pa)

    por_empresa: dict[uuid.UUID, list[MovimentoMes]] = defaultdict(list)
    for m in lancados:
        por_empresa[m.company_id].append(movimento_mes(m))
    return montar_carteira(
        pa=j.pa,
        empresas=[
            EmpresaCarteira(
                id=e.id,
                nome=e.nome,
                cnpj=e.cnpj,
                pacote=e.pacote,
                honorario_mensal=e.honorario_mensal,
                inicio_atividade=e.inicio_atividade,
            )
            for e in empresas
        ],
        movimentos=por_empresa,
        tabelas=tabelas,
        politica=firms.politica_de(firm),
    )
