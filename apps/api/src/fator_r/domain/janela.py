"""Janela móvel do Fator R: os 12 meses anteriores ao período de apuração (PA)."""

from dataclasses import dataclass
from datetime import date

from fator_r.core.competencia import primeiro_dia, somar_meses

MESES_JANELA = 12


@dataclass(frozen=True)
class Janela:
    pa: date
    inicio: date
    fim: date

    @property
    def meses(self) -> tuple[date, ...]:
        return tuple(somar_meses(self.inicio, i) for i in range(MESES_JANELA))


def janela(pa: date) -> Janela:
    """PA-12 a PA-1. Ex.: PA 09/2026 → 2025-09 a 2026-08."""
    pa = primeiro_dia(pa)
    return Janela(pa=pa, inicio=somar_meses(pa, -MESES_JANELA), fim=somar_meses(pa, -1))


def meses_validos(j: Janela, inicio_atividade: date | None) -> tuple[date, ...]:
    """Meses da janela em que a empresa já existia. Sem início informado: todos."""
    if inicio_atividade is None:
        return j.meses
    inicio = primeiro_dia(inicio_atividade)
    return tuple(m for m in j.meses if m >= inicio)


def classificar(
    validos: tuple[date, ...], competencias_lancadas: set[date]
) -> tuple[tuple[date, ...], tuple[date, ...]]:
    """(preenchidos, faltantes). Mês antes do início de atividade não é faltante."""
    preenchidos = tuple(m for m in validos if m in competencias_lancadas)
    faltantes = tuple(m for m in validos if m not in competencias_lancadas)
    return preenchidos, faltantes


def empresa_nova_na_janela(j: Janela, inicio_atividade: date | None) -> bool:
    """Começou a atividade depois do início da janela: tem menos de 12 meses no período."""
    return inicio_atividade is not None and primeiro_dia(inicio_atividade) > j.inicio
