"""Tabelas do Simples por vigência (referência legal, sem firm_id)."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.domain.tabelas import Anexo, Faixa, TabelaAnexo, TabelaNaoVigente, TabelasVigentes
from fator_r.repositories.orm import SimplesTable

CSV_PADRAO = Path(__file__).resolve().parents[3] / "fixtures" / "simples_tables_2018.csv"


async def tabela_vigente(session: AsyncSession, anexo: Anexo, data: date) -> TabelaAnexo:
    rows = (
        await session.execute(
            select(SimplesTable)
            .where(
                SimplesTable.anexo == anexo,
                SimplesTable.vigencia_inicio <= data,
                or_(SimplesTable.vigencia_fim.is_(None), SimplesTable.vigencia_fim > data),
            )
            .order_by(SimplesTable.vigencia_inicio.desc(), SimplesTable.faixa)
        )
    ).scalars()
    linhas = list(rows)
    if not linhas:
        raise TabelaNaoVigente(f"Sem tabela do Anexo {anexo} vigente em {data.isoformat()}")
    vigencia = linhas[0].vigencia_inicio
    faixas = tuple(
        Faixa(r.faixa, r.rbt12_ate, r.aliquota_nominal, r.parcela_deduzir)
        for r in linhas
        if r.vigencia_inicio == vigencia
    )
    return TabelaAnexo(anexo=anexo, vigencia_inicio=vigencia, faixas=faixas)


async def tabelas_vigentes(session: AsyncSession, data: date) -> TabelasVigentes:
    """Anexos III e V vigentes numa data, com uma consulta só."""
    rows = (
        await session.execute(
            select(SimplesTable)
            .where(
                SimplesTable.vigencia_inicio <= data,
                or_(SimplesTable.vigencia_fim.is_(None), SimplesTable.vigencia_fim > data),
            )
            .order_by(SimplesTable.vigencia_inicio.desc(), SimplesTable.faixa)
        )
    ).scalars()
    por_anexo: dict[str, list[SimplesTable]] = {"III": [], "V": []}
    for linha in rows:
        por_anexo[linha.anexo].append(linha)

    def montar(anexo: Anexo) -> TabelaAnexo:
        linhas = por_anexo[anexo]
        if not linhas:
            raise TabelaNaoVigente(f"Sem tabela do Anexo {anexo} vigente em {data.isoformat()}")
        vigencia = linhas[0].vigencia_inicio
        faixas = tuple(
            Faixa(r.faixa, r.rbt12_ate, r.aliquota_nominal, r.parcela_deduzir)
            for r in linhas
            if r.vigencia_inicio == vigencia
        )
        return TabelaAnexo(anexo=anexo, vigencia_inicio=vigencia, faixas=faixas)

    return TabelasVigentes(anexo_iii=montar("III"), anexo_v=montar("V"))


def _ler_csv(caminho: Path) -> list[dict[str, object]]:
    with caminho.open(newline="", encoding="utf-8") as arquivo:
        return [
            {
                "anexo": linha["anexo"],
                "faixa": int(linha["faixa"]),
                "rbt12_ate": Decimal(linha["rbt12_ate"]),
                "aliquota_nominal": Decimal(linha["aliquota_nominal"]),
                "parcela_deduzir": Decimal(linha["parcela_deduzir"]),
                "vigencia_inicio": date.fromisoformat(linha["vigencia_inicio"]),
                "vigencia_fim": date.fromisoformat(linha["vigencia_fim"])
                if linha["vigencia_fim"]
                else None,
            }
            for linha in csv.DictReader(arquivo)
        ]


async def carregar_csv(session: AsyncSession, caminho: Path = CSV_PADRAO) -> int:
    """Seed idempotente (role dona): insere linhas novas e não altera vigências existentes."""
    linhas = _ler_csv(caminho)
    statement = (
        insert(SimplesTable)
        .values(linhas)
        .on_conflict_do_nothing(constraint="uq_simples_faixa_vigencia")
        .returning(SimplesTable.id)
    )
    inseridas = len((await session.execute(statement)).all())
    await session.commit()
    return inseridas
