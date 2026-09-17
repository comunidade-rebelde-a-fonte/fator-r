"""Consultor, priorizador e rotina semanal (T-609..T-613), com LLM controlado nos testes."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select

from fator_r.agents.llm import Intencao, LLMIndisponivel, usar_llm
from fator_r.agents.priorizador import rotina_semanal
from fator_r.agents.render import DISCLAIMER
from fator_r.core.db import get_owner_sessionmaker
from fator_r.repositories.orm import AgentDecision, AgentTrace, Simulation
from tests.factories import criar_escritorio_com_usuario, empresa_payload, login

MESES = [f"2025-{m:02d}" for m in range(9, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]


class LLMControlado:
    def __init__(self, intencao: Intencao | None, texto: str | None) -> None:
        self.intencao = intencao
        self.texto = texto
        self.decisoes: list[dict[str, Any]] = []

    async def classificar(self, mensagem: str, empresas: list[str]) -> Intencao:
        if self.intencao is None:
            raise LLMIndisponivel("simulado")
        return self.intencao

    async def redigir(self, decisao: dict[str, Any]) -> str:
        self.decisoes.append(decisao)
        if self.texto is None:
            raise LLMIndisponivel("simulado")
        return self.texto


@pytest.fixture(autouse=True)
def _sem_llm_global() -> AsyncIterator[None]:
    yield
    usar_llm(None)


async def _empresa(client: httpx.AsyncClient, nome: str, cnpj: str, pro_labore: str) -> str:
    empresa = (await client.post("/companies", json=empresa_payload(nome=nome, cnpj=cnpj))).json()
    for mes in MESES:
        await client.put(
            f"/companies/{empresa['id']}/movements/{mes}",
            json={"receita_bruta": "50000.00", "pro_labore": pro_labore},
        )
    return str(empresa["id"])


async def test_consultor_status_com_texto_do_llm_validado(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    company_id = await _empresa(client, "Beta Engenharia", "11.222.333/0001-81", "12000.00")
    usar_llm(
        LLMControlado(
            Intencao(intencao="status_empresa", company_ref="Beta Engenharia", pa="2026-09"),
            "A Beta Engenharia está com Fator R de 24,00% e está no Anexo V.",
        )
    )
    body = (
        await client.post(
            "/agents/consultor/chat", json={"mensagem": "como está a Beta Engenharia?"}
        )
    ).json()
    assert body["decisao"]["anexo"] == "V"
    assert body["decisao"]["empresa"] == "Beta Engenharia"
    assert body["texto"].startswith("A Beta Engenharia está com Fator R de 24,00%")
    assert body["texto"].endswith(DISCLAIMER)
    async with get_owner_sessionmaker()() as session:
        trace = (
            await session.execute(select(AgentTrace).where(AgentTrace.id == body["trace_id"]))
        ).scalar_one()
    assert (trace.agente, trace.status, str(trace.company_id or "")) in (
        ("consultor", "ok", ""),
        ("consultor", "ok", company_id),
    )


async def test_consultor_numero_inventado_cai_no_template(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    company_id = await _empresa(client, "Beta Engenharia", "11.222.333/0001-81", "12000.00")
    usar_llm(
        LLMControlado(
            Intencao(intencao="status_empresa", pa="2026-09"), "Economia de R$ 1.234.567,00!"
        )
    )
    body = (
        await client.post(
            "/agents/consultor/chat", json={"mensagem": "situação", "company_id": company_id}
        )
    ).json()
    assert "1.234.567" not in body["texto"]
    assert body["texto"].startswith("Beta Engenharia, PA 2026-09: Fator R")


async def test_consultor_simular_persiste_simulacao_e_passa_na_guarda(
    client: httpx.AsyncClient,
) -> None:
    await login(client, await criar_escritorio_com_usuario())
    company_id = await _empresa(client, "Beta Engenharia", "11.222.333/0001-81", "10000.00")
    usar_llm(LLMControlado(Intencao(intencao="simular", pa="2026-09"), None))
    body = (
        await client.post(
            "/agents/consultor/chat",
            json={"mensagem": "simule a correção", "company_id": company_id},
        )
    ).json()
    assert body["decisao"]["veredito"] == "corrigir"
    async with get_owner_sessionmaker()() as session:
        sim = (
            await session.execute(select(Simulation).where(Simulation.trace_id == body["trace_id"]))
        ).scalar_one()
    assert str(sim.id) == body["decisao"]["simulation_id"]


async def test_consultor_fallback_de_intencao_sem_llm(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    await _empresa(client, "Beta Engenharia", "11.222.333/0001-81", "12000.00")
    usar_llm(LLMControlado(None, None))
    body = (
        await client.post(
            "/agents/consultor/chat",
            json={"mensagem": "qual a situação da Beta Engenharia em 09/2026?"},
        )
    ).json()
    assert body["decisao"]["intencao"] == "status_empresa"
    assert body["decisao"]["pa"] == "2026-09"


async def test_consultor_empresa_de_outro_escritorio_404(client: httpx.AsyncClient) -> None:
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    await login(client, b)
    empresa_b = await _empresa(client, "Segredo B", "11.222.333/0001-81", "1.00")
    client.cookies.clear()
    await login(client, await criar_escritorio_com_usuario("a@escritorio-a.com.br"))
    resposta = await client.post(
        "/agents/consultor/chat", json={"mensagem": "situação", "company_id": empresa_b}
    )
    assert resposta.status_code == 404


async def test_priorizador_fila_por_economia_com_trace(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    await _empresa(client, "Verde", "11.222.333/0001-81", "15000.00")
    await _empresa(client, "Amarela", "45.723.174/0001-10", "14500.00")
    await _empresa(client, "Vermelha", "04.252.011/0001-10", "5000.00")
    usar_llm(LLMControlado(Intencao(intencao="priorizar"), None))
    body = (
        await client.post(
            "/agents/priorizador/chat", json={"mensagem": "o que priorizar?", "pa": "2026-09"}
        )
    ).json()
    fila = body["decisao"]["fila"]
    assert [item["empresa"] for item in fila] == ["Vermelha", "Amarela"] or [
        item["empresa"] for item in fila
    ] == ["Amarela", "Vermelha"]
    economias = [float(item["economia_12m"]) for item in fila]
    assert economias == sorted(economias, reverse=True)
    assert "Verde" not in {item["empresa"] for item in fila}
    assert len(body["trace_id"]) == 32
    assert body["texto"].endswith(DISCLAIMER)


async def test_rotina_semanal_nao_duplica_na_mesma_semana(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    await _empresa(client, "Vermelha", "04.252.011/0001-10", "5000.00")
    domingo = datetime(2026, 9, 20, 10, tzinfo=UTC)
    assert await rotina_semanal(domingo) >= 1
    assert await rotina_semanal(domingo) == 0
    async with get_owner_sessionmaker()() as session:
        total = (
            await session.execute(
                select(func.count())
                .select_from(AgentTrace)
                .where(AgentTrace.firm_id == u.firm_id, AgentTrace.gatilho == "rotina")
            )
        ).scalar_one()
        decisoes = (
            await session.execute(
                select(func.count())
                .select_from(AgentDecision)
                .where(AgentDecision.tipo == "fila_priorizacao")
            )
        ).scalar_one()
    assert total == 1
    assert decisoes >= 1
