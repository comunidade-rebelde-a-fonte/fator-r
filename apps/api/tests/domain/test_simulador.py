"""Simulador de correção (T-602): casos tabelados da Plano §5.2."""

from datetime import date
from decimal import Decimal

import pytest

from fator_r.core.competencia import somar_meses
from fator_r.domain.fator_r import MovimentoMes, Politica, ResultadoFatorR, calcular
from fator_r.domain.simulador import ParametrosSimulacao, simular
from tests.domain.tabelas_fixture import tabelas_2018

D = Decimal
PA = date(2026, 9, 1)
POLITICA = Politica(cpp_das_integra_fs12=False, meta_operacional=D("0.30"))


def motor(receita: str, pro_labore: str) -> ResultadoFatorR:
    movimentos = [
        MovimentoMes(somar_meses(date(2025, 9, 1), i), D(receita), D(pro_labore), D(0), D(0), D(0))
        for i in range(12)
    ]
    return calcular(PA, None, movimentos, tabelas_2018(), POLITICA)


def params(**kw: str | int) -> ParametrosSimulacao:
    base: dict[str, object] = {
        "meta": D("0.30"),
        "fracao_pro_labore": D("1"),
        "inss": D("0.11"),
        "irrf": D("0.275"),
        "horizonte_meses": 12,
        "piso_economia_anual": D("6000"),
    }
    base.update({k: D(str(v)) if k != "horizonte_meses" else v for k, v in kw.items()})
    return ParametrosSimulacao(**base)  # type: ignore[arg-type]


def test_ja_na_meta() -> None:
    r = simular(motor("50000", "15000"), params())
    assert r.veredito == "ja_na_meta"
    assert r.reforco_12m == 0
    assert r.custo_total == 0


def test_corrigir_calculo_completo() -> None:
    # RBT12 600k, FS12 120k (20%): reforço até 30% = 60k/12m = 5k/mês.
    r = simular(motor("50000", "10000"), params())
    assert r.status == "ok"
    assert r.reforco_12m == D("60000.00")
    assert r.reforco_mensal == D("5000")
    assert r.pro_labore_extra_mensal == D("5000")
    assert r.pro_labore_extra_horizonte == D("60000")
    assert r.custo_inss == D("6600.00")  # 11%
    assert r.custo_irrf == D("16500.000")  # 27,5%
    assert r.custo_total == D("23100.000")
    assert r.economia_12m == D("43740.00")
    assert r.economia_horizonte == D("43740.00")
    assert r.liquido == D("20640.000")
    assert r.veredito == "corrigir"


def test_nao_forcar_quando_economia_abaixo_do_piso_mesmo_com_liquido_positivo() -> None:
    # RBT12 180k (faixa 1): economia = (15,5% - 6%) x 180k = 17.100; piso 20.000.
    r = simular(motor("15000", "2000"), params(piso_economia_anual="20000", irrf="0"))
    assert r.economia_12m == D("17100.00")
    assert r.liquido > 0
    assert r.veredito == "nao_forcar"


def test_nao_forcar_quando_liquido_nao_positivo() -> None:
    r = simular(motor("50000", "10000"), params(inss="0.30", irrf="0.50"))
    assert r.liquido <= 0
    assert r.veredito == "nao_forcar"


@pytest.mark.parametrize(
    ("fracao", "custo"), [("0", "0"), ("1", "23100.000"), ("0.5", "11550.0000")]
)
def test_fracao_de_pro_labore(fracao: str, custo: str) -> None:
    r = simular(motor("50000", "10000"), params(fracao_pro_labore=fracao))
    assert r.custo_total == D(custo)


@pytest.mark.parametrize(("horizonte", "economia"), [(6, "21870.00"), (12, "43740.00")])
def test_horizonte(horizonte: int, economia: str) -> None:
    r = simular(motor("50000", "10000"), params(horizonte_meses=horizonte))
    assert r.economia_horizonte == D(economia)
    assert r.pro_labore_extra_horizonte == D(5000 * horizonte)


def test_inss_e_irrf_editaveis() -> None:
    a = simular(motor("50000", "10000"), params(inss="0.11", irrf="0"))
    b = simular(motor("50000", "10000"), params(inss="0.20", irrf="0.15"))
    assert a.custo_total == D("6600.00")
    assert b.custo_total == D("21000.00")


def test_meta_do_simulador_pode_diferir_da_politica() -> None:
    r = simular(motor("50000", "15000"), params(meta="0.32"))  # 30% < 32%
    assert r.veredito != "ja_na_meta"
    assert r.reforco_12m == D("12000.00")


def test_dados_insuficientes_nao_inventa_veredito() -> None:
    r = simular(motor("0", "5000"), params())
    assert r.status == "dados_insuficientes"
    assert r.veredito is None
    assert r.motivo == "rbt12_zero"


def test_economia_negativa_na_faixa_6_nao_manda_corrigir() -> None:
    r = simular(motor("400000", "80000"), params(irrf="0", inss="0"))
    assert r.economia_12m is not None
    assert r.economia_12m < 0
    assert r.veredito == "nao_forcar"
