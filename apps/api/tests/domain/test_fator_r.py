"""Motor Fator R (T-204): casos tabelados da Plano §5.1."""

from datetime import date
from decimal import Decimal

import pytest

from fator_r.core.competencia import somar_meses
from fator_r.domain.fator_r import MovimentoMes, Politica, ResultadoFatorR, calcular
from fator_r.domain.tabelas import Faixa, TabelaAnexo, TabelasVigentes
from tests.domain.tabelas_fixture import tabelas_2018

PA = date(2026, 9, 1)
JANELA = [somar_meses(date(2025, 9, 1), i) for i in range(12)]
POLITICA_COM_CPP = Politica(cpp_das_integra_fs12=True, meta_operacional=Decimal("0.30"))
POLITICA_SEM_CPP = Politica(cpp_das_integra_fs12=False, meta_operacional=Decimal("0.30"))
D = Decimal


def mov(
    competencia: date,
    receita: str = "50000",
    pro_labore: str = "0",
    salarios: str = "0",
    cpp: str = "0",
    fgts: str = "0",
    origem: str = "manual",
) -> MovimentoMes:
    return MovimentoMes(
        competencia, D(receita), D(pro_labore), D(salarios), D(cpp), D(fgts), origem
    )


def serie(**kwargs: str) -> list[MovimentoMes]:
    return [mov(m, **kwargs) for m in JANELA]


def calc(movimentos: list[MovimentoMes], **kwargs: object) -> ResultadoFatorR:
    params: dict[str, object] = {
        "pa": PA,
        "inicio_atividade": None,
        "movimentos": movimentos,
        "tabelas": tabelas_2018(),
        "politica": POLITICA_COM_CPP,
    }
    params.update(kwargs)
    return calcular(**params)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("pro_labore_mensal", "fator", "anexo", "semaforo"),
    [
        ("13995", "0.279900", "V", "vermelho"),
        ("14000", "0.280000", "III", "amarelo"),
        ("14995", "0.299900", "III", "amarelo"),
        ("15000", "0.300000", "III", "verde"),
    ],
)
def test_fronteiras_do_corte_legal_e_da_meta(
    pro_labore_mensal: str, fator: str, anexo: str, semaforo: str
) -> None:
    r = calc(serie(pro_labore=pro_labore_mensal))
    assert r.status == "ok"
    assert r.rbt12 == D("600000")
    assert r.fator_r is not None
    assert r.fator_r.quantize(D("0.000001")) == D(fator)
    assert r.anexo == anexo
    assert r.semaforo == semaforo


def test_valores_completos_faixa_3() -> None:
    r = calc(serie(pro_labore="10000"))  # FS12 = 120.000; RBT12 = 600.000; fator 20%
    assert r.fs12 == D("120000")
    assert r.folha_minima_28 == D("168000.00")
    assert r.folha_minima_meta == D("180000.00")
    assert r.gap_12m_28 == D("48000.00")
    assert r.reforco_mensal_28 == D("4000")
    assert r.gap_12m_meta == D("60000.00")
    assert r.reforco_mensal_meta == D("5000")
    # III: (600000·13,5% - 17.640)/600000 = 10,56%; V: (600000·19,5% - 9.900)/600000 = 17,85%
    assert r.aliquota_efetiva_iii == D("0.1056")
    assert r.aliquota_efetiva_v == D("0.1785")
    assert r.economia_12m == D("43740.00")
    assert r.tabela_vigencia_inicio == date(2018, 1, 1)
    assert r.cpp_integra_fs12 is True


def test_gap_zero_quando_folha_ja_supera_minimo() -> None:
    r = calc(serie(pro_labore="20000"))
    assert r.gap_12m_28 == 0
    assert r.reforco_mensal_28 == 0
    assert r.gap_12m_meta == 0


def test_rbt12_zero_nao_inventa_anexo_nem_aliquota() -> None:
    r = calc(serie(receita="0", pro_labore="5000"))
    assert r.status == "dados_insuficientes"
    assert r.motivo == "rbt12_zero"
    for campo in ("fator_r", "anexo", "semaforo", "aliquota_efetiva_iii", "aliquota_efetiva_v"):
        assert getattr(r, campo) is None, campo
    assert r.economia_12m is None


def test_sem_movimentos() -> None:
    r = calc([])
    assert r.status == "dados_insuficientes"
    assert len(r.meses_faltantes) == 12


def test_politica_de_cpp_muda_fs12() -> None:
    movimentos = serie(pro_labore="12000", cpp="2000")
    com = calc(movimentos, politica=POLITICA_COM_CPP)
    sem = calc(movimentos, politica=POLITICA_SEM_CPP)
    assert com.fs12 == D("168000")
    assert com.anexo == "III"
    assert sem.fs12 == D("144000")
    assert sem.anexo == "V"
    assert sem.cpp_integra_fs12 is False


def test_fs12_soma_pro_labore_salarios_fgts() -> None:
    r = calc(serie(pro_labore="1000", salarios="2000", fgts="160", cpp="0"))
    assert r.fs12 == D("37920")


def test_mes_faltante_conta_e_soma_zero() -> None:
    movimentos = serie(pro_labore="14000")[1:]  # falta o primeiro mês da janela
    r = calc(movimentos)
    assert r.status == "ok"
    assert r.meses_faltantes == (date(2025, 9, 1),)
    assert len(r.meses_preenchidos) == 11
    assert r.rbt12 == D("550000")


def test_movimentos_fora_da_janela_sao_ignorados() -> None:
    movimentos = [*serie(pro_labore="15000"), mov(PA, receita="999999"), mov(date(2025, 8, 1))]
    r = calc(movimentos)
    assert r.rbt12 == D("600000")


@pytest.mark.parametrize(
    ("meses", "status"), [(1, "dados_insuficientes"), (5, "dados_insuficientes"), (12, "ok")]
)
def test_empresa_com_1_5_e_12_meses(meses: int, status: str) -> None:
    inicio = somar_meses(PA, -meses)
    movimentos = [mov(m, pro_labore="15000") for m in JANELA if m >= inicio]
    r = calc(movimentos, inicio_atividade=inicio)
    assert r.status == status
    assert r.meses_faltantes == ()
    assert len(r.meses_preenchidos) == meses
    if status != "ok":
        assert r.motivo == "empresa_nova_regra_pendente"
        assert r.fator_r is None
        assert r.anexo is None


def test_mudanca_de_faixa_do_rbt12() -> None:
    faixa1 = calc(serie(receita="15000", pro_labore="5000"))  # RBT12 = 180.000,00
    faixa2 = calc(
        [
            mov(m, receita="15000.01" if i == 0 else "15000", pro_labore="5000")
            for i, m in enumerate(JANELA)
        ]
    )
    assert faixa1.aliquota_efetiva_iii == D("0.06")
    assert faixa1.aliquota_efetiva_v == D("0.155")
    assert faixa1.aliquota_efetiva_iii is not None
    assert faixa2.aliquota_efetiva_iii is not None
    assert faixa2.aliquota_efetiva_iii > faixa1.aliquota_efetiva_iii


def test_economia_pode_ser_negativa_na_faixa_6() -> None:
    # RBT12 = 4,8 mi: III efetiva 19,50% > V efetiva 19,25% (tabela legal)
    r = calc(serie(receita="400000", pro_labore="150000"))
    assert r.aliquota_efetiva_iii == D("0.195")
    assert r.aliquota_efetiva_v == D("0.1925")
    assert r.economia_12m == D("-12000.0000")


def test_rbt12_acima_do_limite_do_simples() -> None:
    r = calc(serie(receita="400001", pro_labore="150000"))
    assert r.status == "dados_insuficientes"
    assert r.motivo == "rbt12_acima_do_limite_do_simples"
    assert r.anexo is None


def test_troca_de_vigencia_usa_a_tabela_recebida() -> None:
    nova = TabelasVigentes(
        anexo_iii=TabelaAnexo(
            "III", date(2027, 1, 1), (Faixa(1, D("4800000"), D("0.10"), D("0")),)
        ),
        anexo_v=TabelaAnexo("V", date(2027, 1, 1), (Faixa(1, D("4800000"), D("0.20"), D("0")),)),
    )
    antiga = calc(serie(pro_labore="15000"))
    atual = calc(serie(pro_labore="15000"), tabelas=nova)
    assert antiga.tabela_vigencia_inicio == date(2018, 1, 1)
    assert atual.tabela_vigencia_inicio == date(2027, 1, 1)
    assert atual.aliquota_efetiva_iii == D("0.10")
    assert atual.economia_12m == D("60000.00")


def test_meta_diferente_so_muda_semaforo_e_folha_meta_nunca_o_anexo() -> None:
    politica = Politica(cpp_das_integra_fs12=True, meta_operacional=D("0.32"))
    r = calc(serie(pro_labore="15000"), politica=politica)
    assert r.anexo == "III"
    assert r.semaforo == "amarelo"
    assert r.folha_minima_meta == D("192000.00")
