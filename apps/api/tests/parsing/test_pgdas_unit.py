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
