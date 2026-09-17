"""Competência (mês de referência) como date no dia 1; na API, string YYYY-MM."""

import re
from datetime import date

_FORMATO = re.compile(r"^(\d{4})-(\d{2})$")


class CompetenciaInvalida(ValueError):
    pass


def parse_competencia(valor: str) -> date:
    match = _FORMATO.match(valor)
    if not match:
        raise CompetenciaInvalida("Competência deve estar no formato YYYY-MM")
    ano, mes = int(match.group(1)), int(match.group(2))
    if not 1 <= mes <= 12 or ano < 1900:
        raise CompetenciaInvalida("Competência inválida")
    return date(ano, mes, 1)


def format_competencia(valor: date) -> str:
    return f"{valor.year:04d}-{valor.month:02d}"


def somar_meses(valor: date, meses: int) -> date:
    indice = valor.year * 12 + (valor.month - 1) + meses
    return date(indice // 12, indice % 12 + 1, 1)


def primeiro_dia(valor: date) -> date:
    return date(valor.year, valor.month, 1)


def competencia_corrente() -> date:
    hoje = date.today()  # noqa: DTZ011 - competência é o mês civil local do escritório
    return date(hoje.year, hoje.month, 1)
