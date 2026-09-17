"""Tabelas dos Anexos III e V (dados vêm do banco; nenhum valor fixo aqui)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

Anexo = Literal["III", "V"]


@dataclass(frozen=True)
class Faixa:
    faixa: int
    rbt12_ate: Decimal
    aliquota_nominal: Decimal
    parcela_deduzir: Decimal


@dataclass(frozen=True)
class TabelaAnexo:
    anexo: Anexo
    vigencia_inicio: date
    faixas: tuple[Faixa, ...]

    def faixa_para(self, rbt12: Decimal) -> Faixa | None:
        """Primeira faixa cujo limite comporta o RBT12; None acima do limite do Simples."""
        for faixa in sorted(self.faixas, key=lambda f: f.rbt12_ate):
            if rbt12 <= faixa.rbt12_ate:
                return faixa
        return None


@dataclass(frozen=True)
class TabelasVigentes:
    anexo_iii: TabelaAnexo
    anexo_v: TabelaAnexo


class TabelaNaoVigente(LookupError):
    """Não há tabela do Simples vigente para a data pedida."""
