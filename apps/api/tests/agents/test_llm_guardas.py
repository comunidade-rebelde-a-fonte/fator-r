"""Cliente Claude, plan, validador de render e guarda do corrigir (T-605..T-608).

A API da Anthropic é sempre simulada no nível HTTP (CLAUDE.md §4.4).
"""

import json
from decimal import Decimal
from typing import Any

import httpx2
import pytest

from fator_r.agents.etapas import decidir, planejar, renderizar
from fator_r.agents.guardas import RecomendacaoSemSimulacao, garantir_simulacao_para_corrigir
from fator_r.agents.intencao import classificar_por_palavras
from fator_r.agents.llm import AnthropicLLM, LLMIndisponivel
from fator_r.agents.render import DISCLAIMER, com_disclaimer, validar_texto
from fator_r.core.db import firm_session, get_owner_sessionmaker
from fator_r.repositories.orm import Company, Simulation
from fator_r.tracing import tracer
from tests.factories import criar_escritorio_com_usuario

EMPRESAS = ["Clínica Alfa Ltda", "Beta Engenharia"]


def _resposta(conteudo: list[dict[str, Any]], stop: str = "end_turn") -> dict[str, Any]:
    return {
        "id": "msg_teste",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5",
        "content": conteudo,
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def _llm(respostas: list[httpx2.Response], capturas: list[dict[str, Any]]) -> AnthropicLLM:
    fila = list(respostas)

    def handler(request: httpx2.Request) -> httpx2.Response:
        capturas.append(json.loads(request.content))
        return fila.pop(0)

    return AnthropicLLM(
        "sk-ant-teste", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    )


def _tool_use(entrada: dict[str, Any]) -> httpx2.Response:
    return httpx2.Response(
        200,
        json=_resposta(
            [
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "classificar_intencao",
                    "input": entrada,
                }
            ],
            stop="tool_use",
        ),
    )


@pytest.mark.parametrize("intencao", ["status_empresa", "simular", "explicar", "priorizar"])
async def test_plan_classifica_as_quatro_intencoes(intencao: str) -> None:
    capturas: list[dict[str, Any]] = []
    llm = _llm(
        [
            _tool_use(
                {
                    "intencao": intencao,
                    "company_ref": "Beta Engenharia",
                    "pa": "2026-09",
                    "meta": None,
                }
            )
        ],
        capturas,
    )
    resultado = await llm.classificar("pedido qualquer", EMPRESAS)
    assert resultado.intencao == intencao
    assert resultado.company_ref == "Beta Engenharia"
    enviado = capturas[0]
    assert enviado["model"] == "claude-sonnet-5"
    assert enviado["tool_choice"] == {"type": "tool", "name": "classificar_intencao"}
    assert "temperature" not in enviado


async def test_payload_do_plan_nao_leva_valores_financeiros() -> None:
    capturas: list[dict[str, Any]] = []
    llm = _llm(
        [_tool_use({"intencao": "status_empresa", "company_ref": None, "pa": None, "meta": None})],
        capturas,
    )
    await llm.classificar("como está a Beta Engenharia?", EMPRESAS)
    bruto = json.dumps(capturas[0], ensure_ascii=False)
    for proibido in ("rbt12", "fs12", "600000", "R$", "economia", "cnpj"):
        assert proibido not in bruto.lower()
    assert "Beta Engenharia" in bruto


async def test_plan_cai_no_fallback_por_erro_http_e_json_invalido() -> None:
    u = await criar_escritorio_com_usuario()
    for resposta in (
        httpx2.Response(
            500, json={"type": "error", "error": {"type": "api_error", "message": "x"}}
        ),
        _tool_use({"intencao": "inventada", "company_ref": None, "pa": None, "meta": None}),
    ):
        llm = _llm([resposta] * 3, [])
        async with (
            firm_session(u.firm_id) as session,
            tracer.run(
                session, agente="consultor", gatilho="chat", firm_id=u.firm_id, user_id=u.user_id
            ) as run,
        ):
            intencao = await planejar(run, llm, "o que priorizar esta semana?", EMPRESAS)
            await run.finish(decisao={}, texto="", status="ok")
        assert intencao.intencao == "priorizar"  # veio do classificador por palavras


def test_classificador_por_palavras_extrai_empresa_pa_e_meta() -> None:
    i = classificar_por_palavras(
        "simule a clinica alfa ltda para 09/2026 com meta de 32%", EMPRESAS
    )
    assert (i.intencao, i.company_ref, i.pa, i.meta) == (
        "simular",
        "Clínica Alfa Ltda",
        "2026-09",
        Decimal("0.32"),
    )


DECISAO = {
    "empresa": "Beta Engenharia",
    "pa": "2026-09",
    "fator_r": "0.240000",
    "rbt12": "600000.00",
    "reforco_mensal_meta": "3000.00",
    "horizonte_meses": 12,
    "veredito": "corrigir",
}


@pytest.mark.parametrize(
    "texto",
    [
        "A Beta Engenharia está com Fator R de 24,00% no PA 2026-09, com RBT12 de R$ 600.000,00.",
        "Reforço mensal de R$ 3.000,00 por 12 meses leva à meta.",
        "Fator R em 24% e receita de 600000.00.",
    ],
)
def test_render_com_numeros_da_decisao_passa(texto: str) -> None:
    assert validar_texto(texto, DECISAO).valido


@pytest.mark.parametrize(
    ("texto", "orfao"),
    [
        ("A economia estimada é de R$ 43.740,00.", "43.740,00"),  # número inventado
        ("O Fator R está em 25%.", "25"),  # arredondado diferente
        ("Situação do PA 2026-10.", "2026-10"),  # competência que não está na decisão
    ],
)
def test_render_com_numero_orfao_e_rejeitado(texto: str, orfao: str) -> None:
    validacao = validar_texto(texto, DECISAO)
    assert not validacao.valido
    assert orfao in validacao.orfaos


async def test_render_rejeitado_usa_template_e_sempre_tem_disclaimer() -> None:
    u = await criar_escritorio_com_usuario()
    inventado = httpx2.Response(
        200, json=_resposta([{"type": "text", "text": "Economia de R$ 99.999,00."}])
    )
    aceito = httpx2.Response(
        200, json=_resposta([{"type": "text", "text": "Fator R de 24,00% no PA 2026-09."}])
    )
    async with (
        firm_session(u.firm_id) as session,
        tracer.run(
            session, agente="consultor", gatilho="chat", firm_id=u.firm_id, user_id=u.user_id
        ) as run,
    ):
        rejeitado = await renderizar(run, _llm([inventado], []), DECISAO, "TEMPLATE")
        aprovado = await renderizar(run, _llm([aceito], []), DECISAO, "TEMPLATE")
        indisponivel = await renderizar(
            run, _llm([httpx2.Response(500, json={})] * 3, []), DECISAO, "TEMPLATE"
        )
        await run.finish(decisao={}, texto="", status="ok")
    assert rejeitado == com_disclaimer("TEMPLATE")
    assert aprovado.startswith("Fator R de 24,00%")
    assert indisponivel == com_disclaimer("TEMPLATE")
    for texto in (rejeitado, aprovado, indisponivel):
        assert texto.endswith(DISCLAIMER)


async def test_refusal_vira_indisponivel() -> None:
    llm = _llm([httpx2.Response(200, json=_resposta([], stop="refusal"))], [])
    with pytest.raises(LLMIndisponivel):
        await llm.redigir(DECISAO)


async def _simulacao(firm_id: object, veredito: str) -> str:
    u_firm = firm_id
    async with get_owner_sessionmaker()() as session:
        company = Company(firm_id=u_firm, nome="X", cnpj="11222333000181", sujeita_fator_r=True)
        session.add(company)
        await session.flush()
        from fator_r.repositories.orm import AgentTrace

        session.add(
            AgentTrace(
                id="a" * 32,
                firm_id=u_firm,
                agente="consultor",
                gatilho="ficha",
                status="ok",
                entrada_json={},
                saida_json={},
                decisao_json={},
            )
        )
        await session.flush()
        from datetime import date

        sim = Simulation(
            firm_id=u_firm,
            company_id=company.id,
            pa=date(2026, 9, 1),
            parametros_json={},
            resultado_json={},
            veredito=veredito,
            trace_id="a" * 32,
        )
        session.add(sim)
        await session.commit()
        return str(sim.id)


async def test_guarda_corrigir_sem_simulacao_e_rejeitado_e_run_termina_em_erro() -> None:
    u = await criar_escritorio_com_usuario()
    async with firm_session(u.firm_id) as session:
        with pytest.raises(RecomendacaoSemSimulacao):
            await garantir_simulacao_para_corrigir(session, u.firm_id, {"veredito": "corrigir"})
        await garantir_simulacao_para_corrigir(session, u.firm_id, {"veredito": "nao_forcar"})

    async def corrida() -> None:
        async with (
            firm_session(u.firm_id) as session,
            tracer.run(
                session, agente="consultor", gatilho="chat", firm_id=u.firm_id, user_id=u.user_id
            ) as run,
        ):
            await decidir(run, session, u.firm_id, {"recomendacao": "corrigir"})

    with pytest.raises(RecomendacaoSemSimulacao):
        await corrida()


async def test_guarda_corrigir_com_simulacao_de_outro_escritorio_e_rejeitado() -> None:
    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    sim_b = await _simulacao(b.firm_id, "corrigir")
    async with firm_session(a.firm_id) as session:
        with pytest.raises(RecomendacaoSemSimulacao):
            await garantir_simulacao_para_corrigir(
                session, a.firm_id, {"veredito": "corrigir", "simulation_id": sim_b}
            )
    async with firm_session(b.firm_id) as session:
        await garantir_simulacao_para_corrigir(
            session, b.firm_id, {"veredito": "corrigir", "simulation_id": sim_b}
        )
