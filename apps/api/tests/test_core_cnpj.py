import pytest

from fator_r.core.cnpj import CnpjInvalido, cnpj_valido, formatar_cnpj, normalizar_cnpj

VALIDOS = ["11.222.333/0001-81", "11222333000181", "45.723.174/0001-10", "04.252.011/0001-10"]


@pytest.mark.parametrize("valor", VALIDOS)
def test_cnpj_valido_com_e_sem_mascara(valor: str) -> None:
    assert cnpj_valido(valor)
    assert len(normalizar_cnpj(valor)) == 14


@pytest.mark.parametrize(
    "valor",
    [
        "11.222.333/0001-82",  # DV errado
        "11222333000180",
        "00000000000000",  # todos iguais
        "11111111111111",
        "1122233300018",  # 13 dígitos
        "",
        "abc",
    ],
)
def test_cnpj_invalido(valor: str) -> None:
    assert not cnpj_valido(valor)
    with pytest.raises(CnpjInvalido):
        normalizar_cnpj(valor)


def test_formatar_cnpj() -> None:
    assert formatar_cnpj("11222333000181") == "11.222.333/0001-81"
