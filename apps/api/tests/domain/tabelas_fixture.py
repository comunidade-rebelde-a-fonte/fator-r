"""Tabelas do CSV de fixtures para testes de domínio (sem banco)."""

from datetime import date
from decimal import Decimal

from fator_r.domain.tabelas import Faixa, TabelaAnexo, TabelasVigentes
from fator_r.repositories.simples_tables import CSV_PADRAO, _ler_csv


def tabelas_2018() -> TabelasVigentes:
    linhas = _ler_csv(CSV_PADRAO)

    def anexo(nome: str) -> TabelaAnexo:
        faixas = tuple(
            Faixa(
                int(str(linha["faixa"])),
                Decimal(str(linha["rbt12_ate"])),
                Decimal(str(linha["aliquota_nominal"])),
                Decimal(str(linha["parcela_deduzir"])),
            )
            for linha in linhas
            if linha["anexo"] == nome
        )
        return TabelaAnexo(anexo=nome, vigencia_inicio=date(2018, 1, 1), faixas=faixas)  # type: ignore[arg-type]

    return TabelasVigentes(anexo_iii=anexo("III"), anexo_v=anexo("V"))
