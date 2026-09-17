from datetime import date

import pytest

from fator_r.core.competencia import (
    CompetenciaInvalida,
    format_competencia,
    parse_competencia,
    somar_meses,
)


def test_parse_e_format() -> None:
    assert parse_competencia("2026-09") == date(2026, 9, 1)
    assert format_competencia(date(2026, 9, 1)) == "2026-09"


@pytest.mark.parametrize("valor", ["2026-13", "2026-00", "2026-9", "09/2026", "2026-09-01", ""])
def test_competencia_invalida(valor: str) -> None:
    with pytest.raises(CompetenciaInvalida):
        parse_competencia(valor)


@pytest.mark.parametrize(
    ("inicio", "meses", "esperado"),
    [
        (date(2026, 9, 1), -12, date(2025, 9, 1)),
        (date(2026, 1, 1), -1, date(2025, 12, 1)),
        (date(2025, 12, 1), 1, date(2026, 1, 1)),
    ],
)
def test_somar_meses(inicio: date, meses: int, esperado: date) -> None:
    assert somar_meses(inicio, meses) == esperado


def test_formatacao_br_dos_templates() -> None:
    from decimal import Decimal

    from fator_r.agents.render import validar_texto
    from fator_r.core.money import formatar_brl, formatar_percentual_br

    assert formatar_brl(Decimal("600000")) == "600.000,00"
    assert formatar_brl("-12000.5") == "-12.000,50"
    assert formatar_percentual_br("0.240000") == "24,00%"
    decisao = {"rbt12": "600000.00", "fator_r": "0.240000"}
    assert validar_texto(
        f"R$ {formatar_brl('600000.00')} e {formatar_percentual_br('0.24')}", decisao
    ).valido
