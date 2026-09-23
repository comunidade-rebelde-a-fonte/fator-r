from decimal import Decimal

import pytest

from fator_r.parsing.pgdas import numero_br, parse
from fator_r.parsing.texto import extrair_texto


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("1.234,56", "1234.56"),
        ("600.000,00", "600000.00"),
        ("0,30", "0.30"),
        ("1234.56", "1234.56"),
    ],
)
def test_numero_br(entrada: str, esperado: str) -> None:
    assert numero_br(entrada) == Decimal(esperado)


def test_mes_invalido_no_pa_nao_e_aceito() -> None:
    assert parse("Período de Apuração (PA): 13/2026").campos["pa"] is None


def test_anexo_vi_nao_vira_anexo_v() -> None:
    assert parse("Atividade do Anexo VI").campos["anexo"] is None


def test_fator_inconsistente_reduz_confianca_e_registra_motivo() -> None:
    texto = "PA: 09/2026\nCNPJ: 11222333000181\nRBT12: 600.000,00\nFS12: 180.000,00\nFator r: 0,10"
    resultado = parse(texto)
    assert "fator_r_inconsistente_com_fs12_rbt12" in resultado.motivos


def test_pdf_corrompido() -> None:
    resultado = extrair_texto(b"%PDF-1.4 lixo sem estrutura", "application/pdf")
    assert resultado.motivo in ("pdf_ilegivel", "sem_camada_texto")


# --- M8 (T-801): PA em intervalo, anexo estruturado e identificação para cadastro ---


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [
        ("Periodo de Apuracao: 01/08/2026 a 31/08/2026", "2026-08"),
        ("Período de Apuração (PA): 01/12/2025 a 31/12/2025", "2025-12"),
        ("Periodo de Apuracao: 01/08/2026 a 30/09/2026", None),
        ("Periodo de Apuracao: 01/12/2025 a 31/12/2026", None),
        ("Periodo de Apuracao: 01/13/2026 a 31/13/2026", None),
    ],
)
def test_pa_em_intervalo_so_dentro_do_mesmo_mes(linha: str, esperado: str | None) -> None:
    assert parse(linha).campos["pa"] == esperado


def test_pa_no_formato_mes_ano_tem_precedencia_sobre_intervalo() -> None:
    texto = "PA: 09/2026\nPeriodo de Apuracao: 01/08/2026 a 31/08/2026"
    assert parse(texto).campos["pa"] == "2026-09"


def test_anexo_de_linha_estruturada_ignora_paragrafo_explicativo() -> None:
    texto = (
        "Fator r = Nao se aplica - Anexo I\n"
        "Criterio: atividades sujeitas ao fator r vao para o Anexo III."
    )
    assert parse(texto).campos["anexo"] is None


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Fator r = 0,20 - Anexo V", "V"),
        ("Enquadramento Anexo III", "III"),
        ("Atividade: Prestação de serviços - Anexo III", "III"),
        ("Enquadramento: Anexo II", None),
        ("Texto livre citando o Anexo V", "V"),
    ],
)
def test_anexo(texto: str, esperado: str | None) -> None:
    assert parse(texto).campos["anexo"] == esperado


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [
        ("Nome empresarial: CLINICA EXEMPLO LTDA", "CLINICA EXEMPLO LTDA"),
        ("NOME EMPRESARIAL CLINICA EXEMPLO LTDA", "CLINICA EXEMPLO LTDA"),
        ("Nome empresarial:", None),
        ("Razão social: CLINICA EXEMPLO LTDA", None),
    ],
)
def test_nome_empresarial(linha: str, esperado: str | None) -> None:
    assert parse(linha).identificacao.nome_empresarial == esperado


def test_nome_empresarial_longo_e_cortado_em_200_caracteres() -> None:
    nome = parse("Nome empresarial: " + "A" * 300).identificacao.nome_empresarial
    assert nome == "A" * 200


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Fator r = 0,20 - Anexo V", True),
        ("Fator r: 30,00%", True),
        ("Fator r = Nao se aplica - Anexo I", False),
        ("Fator r = Não se aplica - Anexo III", False),
        ("Folha para fator r Nao se aplica a esta atividade", False),
        ("Sem nenhuma menção", None),
    ],
)
def test_sugestao_sujeita_fator_r(texto: str, esperado: bool | None) -> None:
    assert parse(texto).identificacao.sujeita_fator_r is esperado


def test_identificacao_nao_altera_confianca() -> None:
    base = "PA: 09/2026\nCNPJ: 11222333000181\nRPA: 50.000,00"
    com_nome = base + "\nNome empresarial: CLINICA EXEMPLO LTDA\nFator r = Nao se aplica"
    assert parse(base).confianca == parse(com_nome).confianca


# --- M8 (T-808): tabelas dos 12 meses anteriores e data de abertura ---


def _declaratorio(receitas: list[str], folhas: list[str] | None, rbt12: str, fs12: str) -> str:
    meses = [
        "08/2025", "09/2025", "10/2025", "11/2025", "12/2025", "01/2026",
        "02/2026", "03/2026", "04/2026", "05/2026", "06/2026", "07/2026",
    ]  # fmt: skip
    linhas = [
        "Periodo de Apuracao: 01/08/2026 a 31/08/2026",
        "Data de abertura no CNPJ: 12/03/2019",
        f"Receita bruta acumulada nos 12 meses anteriores (RBT12) {rbt12} 0,00 {rbt12}",
        "2.2 Receitas Brutas Anteriores (R$) - Mercado Interno",
        "Mes Valor Mes Valor Mes Valor",
    ]
    for i in range(0, 12, 3):
        linhas.append(" ".join(f"{meses[j]} {receitas[j]}" for j in range(i, i + 3)))
    linhas.append("2.3 Folha de Salarios Anteriores (R$)")
    if folhas is not None:
        for i in range(0, 12, 3):
            linhas.append(" ".join(f"{meses[j]} {folhas[j]}" for j in range(i, i + 3)))
        linhas.append(f"Total FS12 {fs12}")
    linhas += ["2.4 Fator r", "Fator r = 0,20 - Anexo V"]
    return "\n".join(linhas)


def test_series_anteriores_conferem_com_rbt12_e_fs12() -> None:
    r = parse(_declaratorio(["10.000,00"] * 12, ["2.000,00"] * 12, "120.000,00", "24.000,00"))
    assert r.campos["rbt12"] == "120000.00"
    assert r.campos["fs12"] == "24000.00"
    assert r.series.receitas["2025-08"] == "10000.00"
    assert r.series.folhas["2026-07"] == "2000.00"
    assert len(r.series.receitas) == len(r.series.folhas) == 12
    assert r.series.receitas_conferem
    assert r.series.folhas_conferem
    assert r.identificacao.inicio_atividade == "2019-03"


def test_serie_que_nao_soma_o_total_declarado_nao_confere() -> None:
    receitas = ["10.000,00"] * 11 + ["11.000,00"]
    r = parse(_declaratorio(receitas, ["2.000,00"] * 12, "120.000,00", "24.000,00"))
    assert not r.series.receitas_conferem
    assert r.series.folhas_conferem


def test_serie_fora_da_janela_do_pa_nao_confere() -> None:
    texto = _declaratorio(["10.000,00"] * 12, ["2.000,00"] * 12, "120.000,00", "24.000,00")
    texto = texto.replace("01/08/2026 a 31/08/2026", "01/09/2026 a 30/09/2026")
    r = parse(texto)
    assert r.campos["pa"] == "2026-09"
    assert not r.series.receitas_conferem
    assert not r.series.folhas_conferem


def test_sem_tabela_de_folha_ou_sem_total_nao_confere() -> None:
    r = parse(_declaratorio(["10.000,00"] * 12, None, "120.000,00", "0,00"))
    assert r.series.receitas_conferem
    assert r.series.folhas == {}
    assert not r.series.folhas_conferem


def test_layout_sem_tabelas_nao_tem_series() -> None:
    r = parse("PA: 09/2026\nCNPJ: 11222333000181\nRBT12: 600.000,00")
    assert r.series.receitas == {}
    assert r.series.folhas == {}
    assert not r.series.receitas_conferem


@pytest.mark.parametrize(
    ("linha", "esperado"),
    [
        ("Data de abertura no CNPJ: 12/03/2019", "2019-03"),
        ("Data de abertura: 01/12/2020", "2020-12"),
        ("Data de abertura no CNPJ: XX/XX/XXXX", None),
        ("Data de abertura no CNPJ: 01/13/2020", None),
    ],
)
def test_data_de_abertura_vira_inicio_de_atividade(linha: str, esperado: str | None) -> None:
    assert parse(linha).identificacao.inicio_atividade == esperado
