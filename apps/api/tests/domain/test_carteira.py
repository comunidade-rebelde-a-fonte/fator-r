import uuid
from datetime import date
from decimal import Decimal

from fator_r.core.competencia import somar_meses
from fator_r.domain.carteira import ACOES, EmpresaCarteira, montar_carteira
from fator_r.domain.fator_r import MovimentoMes, Politica
from tests.domain.tabelas_fixture import tabelas_2018

PA = date(2026, 9, 1)
JANELA = [somar_meses(date(2025, 9, 1), i) for i in range(12)]
POLITICA = Politica(cpp_das_integra_fs12=False, meta_operacional=Decimal("0.30"))


def empresa(nome: str, honorario: str = "0") -> EmpresaCarteira:
    return EmpresaCarteira(uuid.uuid4(), nome, "11222333000181", None, Decimal(honorario), None)


def serie(receita: str, pro_labore: str) -> list[MovimentoMes]:
    return [
        MovimentoMes(m, Decimal(receita), Decimal(pro_labore), Decimal(0), Decimal(0), Decimal(0))
        for m in JANELA
    ]


def test_ordenacao_semaforo_e_economia_e_kpis() -> None:
    verde = empresa("Verde", "300")
    amarelo = empresa("Amarelo", "200")
    vermelho_pequeno = empresa("Vermelho pequeno", "100")
    vermelho_grande = empresa("Vermelho grande", "150")
    sem_dados = empresa("Sem dados")
    movimentos = {
        verde.id: serie("50000", "15000"),  # 30%
        amarelo.id: serie("50000", "14500"),  # 29%
        vermelho_pequeno.id: serie("15000", "1000"),  # RBT12 180k: economia menor
        vermelho_grande.id: serie("50000", "1000"),  # RBT12 600k: economia maior
    }
    carteira = montar_carteira(
        PA,
        [verde, sem_dados, vermelho_pequeno, amarelo, vermelho_grande],
        movimentos,
        tabelas_2018(),
        POLITICA,
    )
    nomes = [linha.empresa.nome for linha in carteira.linhas]
    assert nomes == ["Vermelho grande", "Vermelho pequeno", "Amarelo", "Verde", "Sem dados"]
    assert [linha.acao_texto for linha in carteira.linhas] == [
        "reunião de correção",
        "reunião de correção",
        "vigiar / simular",
        "manter",
        "completar lançamentos",
    ]
    k = carteira.kpis
    assert (k.monitoradas, k.no_v, k.no_limite, k.seguras, k.dados_insuficientes) == (5, 2, 1, 1, 1)
    assert k.honorarios_pacotes == Decimal("750")
    esperado = sum(
        (
            linha.resultado.economia_12m
            for linha in carteira.linhas
            if linha.resultado.semaforo in ("vermelho", "amarelo")
            and linha.resultado.economia_12m is not None
        ),
        Decimal(0),
    )
    assert k.economia_em_jogo == esperado
    assert k.economia_em_jogo > 0


def test_empate_de_economia_desempata_por_nome() -> None:
    b, a = empresa("Beta"), empresa("Alfa")
    movimentos = {b.id: serie("50000", "1000"), a.id: serie("50000", "1000")}
    carteira = montar_carteira(PA, [b, a], movimentos, tabelas_2018(), POLITICA)
    assert [linha.empresa.nome for linha in carteira.linhas] == ["Alfa", "Beta"]


def test_carteira_vazia() -> None:
    carteira = montar_carteira(PA, [], {}, tabelas_2018(), POLITICA)
    assert carteira.linhas == ()
    assert carteira.kpis.monitoradas == 0
    assert carteira.kpis.economia_em_jogo == 0


def test_textos_de_acao_sao_fonte_unica() -> None:
    assert set(ACOES.values()) == {
        "reunião de correção",
        "vigiar / simular",
        "manter",
        "completar lançamentos",
    }
