"""Tipos compartilhados dos schemas da API."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field, PlainSerializer

from fator_r.core.cnpj import normalizar_cnpj
from fator_r.core.competencia import format_competencia, parse_competencia

Dinheiro = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
CompetenciaStr = Annotated[str, Field(pattern=r"^\d{4}-\d{2}$", examples=["2026-09"])]


def _validar_competencia(valor: str) -> str:
    parse_competencia(valor)
    return valor


CompetenciaIn = Annotated[CompetenciaStr, AfterValidator(_validar_competencia)]
CnpjIn = Annotated[str, AfterValidator(normalizar_cnpj)]
CompetenciaOut = Annotated[date, PlainSerializer(format_competencia, return_type=str)]
