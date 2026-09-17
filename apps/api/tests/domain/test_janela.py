from datetime import date

import pytest

from fator_r.domain.janela import classificar, empresa_nova_na_janela, janela, meses_validos


def test_exemplo_do_prd_pa_setembro_2026() -> None:
    j = janela(date(2026, 9, 1))
    assert (j.inicio, j.fim) == (date(2025, 9, 1), date(2026, 8, 1))
    assert len(j.meses) == 12
    assert j.meses[0] == date(2025, 9, 1)
    assert j.meses[-1] == date(2026, 8, 1)


def test_pa_de_janeiro_vira_o_ano() -> None:
    j = janela(date(2026, 1, 1))
    assert (j.inicio, j.fim) == (date(2025, 1, 1), date(2025, 12, 1))


def test_trocar_pa_move_um_mes_entra_e_um_sai() -> None:
    antes, depois = janela(date(2026, 9, 1)), janela(date(2026, 10, 1))
    assert set(depois.meses) - set(antes.meses) == {date(2026, 9, 1)}
    assert set(antes.meses) - set(depois.meses) == {date(2025, 9, 1)}


@pytest.mark.parametrize(
    ("inicio_atividade", "esperado", "nova"),
    [
        (None, 12, False),
        (date(2020, 1, 1), 12, False),  # antes da janela
        (date(2025, 9, 1), 12, False),  # exatamente no início da janela
        (date(2026, 3, 1), 6, True),  # dentro da janela
        (date(2026, 9, 1), 0, True),  # igual ao PA
    ],
)
def test_meses_validos_por_inicio_de_atividade(
    inicio_atividade: date | None, esperado: int, nova: bool
) -> None:
    j = janela(date(2026, 9, 1))
    assert len(meses_validos(j, inicio_atividade)) == esperado
    assert empresa_nova_na_janela(j, inicio_atividade) is nova


def test_faltante_so_conta_meses_validos() -> None:
    j = janela(date(2026, 9, 1))
    validos = meses_validos(j, date(2026, 3, 1))
    preenchidos, faltantes = classificar(validos, {date(2026, 3, 1), date(2026, 5, 1)})
    assert preenchidos == (date(2026, 3, 1), date(2026, 5, 1))
    assert faltantes == (date(2026, 4, 1), date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 1))
    assert date(2025, 12, 1) not in faltantes  # antes do início de atividade
