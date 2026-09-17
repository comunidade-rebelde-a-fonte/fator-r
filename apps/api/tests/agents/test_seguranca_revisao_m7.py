"""Regressões da revisão de segurança final (M2, M3, B1, B7)."""

import json
from typing import Any

import httpx2
import pytest

from fator_r.agents.llm import AnthropicLLM, Intencao
from fator_r.agents.render import validar_texto
from fator_r.tracing.client import mascarar_cnpj

DECISAO = {
    "economia_12m": "43740.00",
    "horizonte_meses": 12,
    "veredito": "nao_forcar",
    "custo": "0.00",
}


@pytest.mark.parametrize(
    "texto",
    [
        "A economia é de trinta mil reais.",
        "Economia de R$ 12 mil no ano.",
        "Código x45000 aplicado.",
        "Perda de R$-99.000,00.",
        "Vale corrigir a folha agora.",
    ],
)
def test_m2_validador_fecha_brechas(texto: str) -> None:
    assert not validar_texto(texto, DECISAO).valido


def test_m2_texto_coerente_com_veredito_passa() -> None:
    assert validar_texto("Não forçar: economia de R$ 43.740,00 em 12 meses.", DECISAO).valido


async def test_m3_plan_nao_envia_lista_de_empresas() -> None:
    capturas: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        capturas.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "id": "m",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-5",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t",
                        "name": "classificar_intencao",
                        "input": {
                            "intencao": "priorizar",
                            "company_ref": None,
                            "pa": None,
                            "meta": None,
                        },
                    }
                ],
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    llm = AnthropicLLM(
        "sk-ant-teste", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    )
    await llm.classificar("o que priorizar?", ["Empresa Sigilosa Um", "João da Silva ME"])
    bruto = json.dumps(capturas[0], ensure_ascii=False)
    assert "Empresa Sigilosa" not in bruto
    assert "João da Silva" not in bruto


def test_b1_pa_fora_da_faixa_e_descartado() -> None:
    assert Intencao(intencao="simular", pa="0001-01").pa is None
    assert Intencao(intencao="simular", pa="2026-09").pa == "2026-09"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("CPF 123.456.789-09", "CPF ***8909"), ("CNPJ 11 222 333 0001 81", "CNPJ ***0181")],
)
def test_b7_mascara_cpf_e_cnpj_com_espacos(entrada: str, esperado: str) -> None:
    assert mascarar_cnpj(entrada) == esperado
