"""Nota ouro do parser (T-511): extrato vs. motor sobre a série lançada (Plano §7.4).

A série de referência exclui movimentos origem=pgdas (Plano §2.2-2): o parser nunca é
avaliado contra dados que ele mesmo criou.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Final, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.core.competencia import parse_competencia
from fator_r.domain.fator_r import ResultadoFatorR, calcular
from fator_r.domain.janela import janela
from fator_r.domain.tabelas import TabelaNaoVigente
from fator_r.repositories import firms, movements, simples_tables
from fator_r.repositories.orm import Company, PgdasDocument
from fator_r.services.fator_r import movimento_mes
from fator_r.tracing.scores import ResultadoCampoOuro, gold

INDISPONIVEL: Final[Literal["ouro_indisponivel"]] = "ouro_indisponivel"


def _dentro(obtido: Decimal, esperado: Decimal, tolerancia: Decimal) -> bool:
    if esperado == 0:
        return obtido == 0
    return abs(obtido - esperado) <= tolerancia * abs(esperado)


def _comparar_numero(
    campo: str, obtido: str | None, esperado: Decimal | None, tolerancia: Decimal
) -> ResultadoCampoOuro:
    if obtido is None or esperado is None:
        return ResultadoCampoOuro(
            campo, str(esperado) if esperado is not None else None, obtido, None, INDISPONIVEL
        )
    ok = _dentro(Decimal(obtido), esperado, tolerancia)
    return ResultadoCampoOuro(campo, str(esperado), obtido, ok, "ok" if ok else "erro")


async def _referencia(
    session: AsyncSession, firm_id: uuid.UUID, company: Company, pa: date
) -> ResultadoFatorR | None:
    """Motor sobre a série sem origem=pgdas; None se a série não serve de referência."""
    j = janela(pa)
    lancados = await movements.listar(session, firm_id, company.id, j.inicio, j.fim)
    if any(m.origem == "pgdas" for m in lancados):
        return None
    try:
        tabelas = await simples_tables.tabelas_vigentes(session, j.pa)
    except TabelaNaoVigente:
        return None
    firm = await firms.obter(session, firm_id)
    resultado = calcular(
        pa=j.pa,
        inicio_atividade=company.inicio_atividade,
        movimentos=[movimento_mes(m) for m in lancados],
        tabelas=tabelas,
        politica=firms.politica_de(firm),
    )
    if resultado.status != "ok" or resultado.meses_faltantes:
        return None
    return resultado


async def avaliar(
    session: AsyncSession, firm_id: uuid.UUID, documento: PgdasDocument, company: Company
) -> Decimal | None:
    campos = documento.campos_json
    firm = await firms.obter(session, firm_id)
    tolerancia = firm.tolerancia_ouro_pct

    cnpj = campos.get("cnpj")
    resultados = [
        ResultadoCampoOuro(
            "cnpj",
            company.cnpj,
            cnpj,
            cnpj == company.cnpj,
            "ok" if cnpj == company.cnpj else "erro",
        ),
        # A série mensal não informa o PA: não há referência independente para ele.
        ResultadoCampoOuro("pa", None, campos.get("pa"), None, INDISPONIVEL),
    ]
    referencia = None
    if campos.get("pa"):
        referencia = await _referencia(session, firm_id, company, parse_competencia(campos["pa"]))
    if referencia is None:
        resultados += [
            ResultadoCampoOuro(c, None, campos.get(c), None, INDISPONIVEL)
            for c in ("rbt12", "fs12", "fator_r", "anexo")
        ]
    else:
        resultados += [
            _comparar_numero("rbt12", campos.get("rbt12"), referencia.rbt12, tolerancia),
            _comparar_numero("fs12", campos.get("fs12"), referencia.fs12, tolerancia),
            _comparar_numero("fator_r", campos.get("fator_r"), referencia.fator_r, tolerancia),
        ]
        anexo = campos.get("anexo")
        resultados.append(
            ResultadoCampoOuro(
                "anexo",
                referencia.anexo,
                anexo,
                None if anexo is None else anexo == referencia.anexo,
                INDISPONIVEL if anexo is None else ("ok" if anexo == referencia.anexo else "erro"),
            )
        )
    return await gold(session, firm_id, documento.trace_id, resultados)
