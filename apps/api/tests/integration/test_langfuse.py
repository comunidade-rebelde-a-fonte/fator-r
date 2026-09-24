"""Integração com o Langfuse local de pé (pytest -m langfuse). T-403..T-408."""

import asyncio
import json
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from fator_r.core.db import firm_session, get_owner_sessionmaker, get_sessionmaker
from fator_r.core.settings import Settings
from fator_r.repositories.orm import AgentTrace
from fator_r.tracing import client as tracing_client
from fator_r.tracing import scores, tracer
from fator_r.tracing.client import ExportStatus, criar_cliente, usar_cliente
from fator_r.tracing.consulta import LangfuseConsulta
from fator_r.tracing.scores import ResultadoCampoOuro
from fator_r.tracing.sync import aplicar_status
from tests.factories import criar_escritorio_com_usuario, login

pytestmark = pytest.mark.langfuse
ROOT = Path(__file__).resolve().parents[4]


def _settings(**extra: Any) -> Settings:
    env: dict[str, str] = {}
    for linha in (ROOT / "infra/langfuse/.env").read_text().splitlines():
        if "=" in linha and not linha.startswith("#"):
            chave, _, valor = linha.partition("=")
            env[chave] = valor
    base: dict[str, Any] = {
        "env": "test",
        "langfuse_tracing_enabled": True,
        "langfuse_public_key": env["LANGFUSE_PUBLIC_KEY"],
        "langfuse_secret_key": env["LANGFUSE_SECRET_KEY"],
        "langfuse_host": f"http://localhost:{env.get('LANGFUSE_WEB_PORT', '3100')}",
    }
    return Settings(**{**base, **extra})


async def esperar[T](
    fn: Callable[[], Awaitable[T]], ok: Callable[[T], bool], segundos: int = 90
) -> T:
    for _ in range(segundos):
        valor = await fn()
        if ok(valor):
            return valor
        await asyncio.sleep(1)
    return valor


def _criar_cliente_ligado(settings: Settings, status: ExportStatus) -> Any:
    """O SDK também lê LANGFUSE_TRACING_ENABLED do ambiente (desligado na suíte unitária)."""
    anterior = os.environ.get("LANGFUSE_TRACING_ENABLED")
    os.environ["LANGFUSE_TRACING_ENABLED"] = "true"
    try:
        return criar_cliente(settings, status)
    finally:
        if anterior is None:
            os.environ.pop("LANGFUSE_TRACING_ENABLED", None)
        else:
            os.environ["LANGFUSE_TRACING_ENABLED"] = anterior


@pytest.fixture
async def langfuse_real() -> AsyncIterator[ExportStatus]:
    status = ExportStatus()
    cliente = _criar_cliente_ligado(_settings(), status)
    usar_cliente(cliente)
    try:
        yield status
    finally:
        cliente.flush()
        usar_cliente(None)


async def _sync(status: ExportStatus) -> None:
    tracing_client.get_langfuse().flush()
    async with get_sessionmaker()() as session:
        await aplicar_status(session, status)


async def _trace_local(trace_id: str) -> AgentTrace:
    async with get_owner_sessionmaker()() as session:
        from sqlalchemy import select

        return (
            await session.execute(select(AgentTrace).where(AgentTrace.id == trace_id))
        ).scalar_one()


async def test_echo_aparece_no_langfuse_com_mesmo_trace_id_e_spans(
    client: httpx.AsyncClient, langfuse_real: ExportStatus
) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    body = (await client.post("/agents/echo/run", json={"mensagem": "integração"})).json()
    trace_id = body["trace_id"]
    await _sync(langfuse_real)
    assert (await _trace_local(trace_id)).langfuse_sync == "ok"

    consulta = LangfuseConsulta(_settings())
    observacoes = await esperar(lambda: consulta.observacoes(trace_id), lambda obs: len(obs) >= 5)
    nomes = {o["name"] for o in observacoes}
    assert {"echo", "plan", "tool", "decide", "render"} <= nomes
    assert all(o["traceId"] == trace_id for o in observacoes)
    raiz = next(o for o in observacoes if o["name"] == "echo")
    assert {"echo", "dev", f"firm:{u.firm_id}"} <= set(raiz.get("tags") or [])
    assert raiz.get("userId") == str(u.user_id)


async def test_scores_ouro_e_humano_espelhados(langfuse_real: ExportStatus) -> None:
    u = await criar_escritorio_com_usuario()
    async with (
        firm_session(u.firm_id) as session,
        tracer.run(
            session, agente="teste", gatilho="integ", firm_id=u.firm_id, user_id=u.user_id
        ) as run,
    ):
        with run.span("parse"):
            pass
        trace_id = (await run.finish(decisao={}, texto="ok", status="ok"))["trace_id"]
    async with firm_session(u.firm_id) as session:
        acerto = await scores.gold(
            session,
            u.firm_id,
            trace_id,
            [
                ResultadoCampoOuro("cnpj", "1", "1", True, "ok"),
                ResultadoCampoOuro("rbt12", "10", "11", False, "erro"),
                ResultadoCampoOuro("fs12", None, None, None, "ouro_indisponivel"),
            ],
        )
        await scores.human(session, u.firm_id, trace_id, u.user_id, "erro", "RBT12 errado")
    assert acerto is not None
    assert float(acerto) == 0.5
    await _sync(langfuse_real)
    consulta = LangfuseConsulta(_settings())
    encontrados = await esperar(lambda: consulta.scores(trace_id), lambda s: len(s) >= 4)
    por_nome = {s["name"]: s for s in encontrados}
    assert por_nome["gold_cnpj"]["value"] == 1
    assert por_nome["gold_rbt12"]["value"] == 0
    assert por_nome["gold_acerto"]["value"] == 0.5
    assert por_nome["human_eval"]["value"] == "erro"
    assert por_nome["human_eval"]["comment"] == "RBT12 errado"
    assert "gold_fs12" not in por_nome


async def test_texto_do_pdf_nao_vai_para_o_langfuse(langfuse_real: ExportStatus) -> None:
    u = await criar_escritorio_com_usuario()
    segredo = "CONTEUDO-SIGILOSO-DO-EXTRATO " * 50
    async with (
        firm_session(u.firm_id) as session,
        tracer.run(
            session,
            agente="teste",
            gatilho="integ",
            firm_id=u.firm_id,
            user_id=u.user_id,
            entrada={"arquivo": "x.pdf", "texto_extraido": segredo},
        ) as run,
    ):
        with run.span("parse", input={"texto_extraido": segredo, "tamanho": len(segredo)}):
            pass
        trace_id = (await run.finish(decisao={}, texto="ok", status="ok"))["trace_id"]
    await _sync(langfuse_real)
    consulta = LangfuseConsulta(_settings())
    observacoes = await esperar(lambda: consulta.observacoes(trace_id), lambda o: len(o) >= 2)
    bruto = json.dumps(observacoes)
    assert "CONTEUDO-SIGILOSO" not in bruto
    assert "[removido]" in bruto


async def test_langfuse_fora_do_ar_nao_quebra_o_agente(client: httpx.AsyncClient) -> None:
    status = ExportStatus()
    fora = _criar_cliente_ligado(
        _settings(
            langfuse_public_key="pk-lf-fora-do-ar",
            langfuse_host="http://127.0.0.1:9",
            langfuse_export_timeout_s=1,
        ),
        status,
    )
    usar_cliente(fora)
    try:
        u = await criar_escritorio_com_usuario()
        await login(client, u)
        response = await client.post("/agents/echo/run", json={"mensagem": "sem langfuse"})
        assert response.status_code == 200
        trace_id = response.json()["trace_id"]
        await asyncio.to_thread(fora.flush)
        async with get_sessionmaker()() as session:
            await aplicar_status(session, status)
        local = await _trace_local(trace_id)
        assert (local.status, local.langfuse_sync) == ("ok", "failed")
    finally:
        usar_cliente(None)


def _anthropic_simulado() -> Any:
    """Cliente Anthropic com transporte HTTP falso: nenhuma chamada real (CLAUDE.md §4.4)."""
    import httpx2
    from anthropic import AsyncAnthropic

    def responder(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "id": "msg_teste",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-5",
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 12, "output_tokens": 3},
            },
        )

    return AsyncAnthropic(
        api_key="sk-ant-teste",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(responder)),
    )


async def test_chamada_ao_claude_vira_generation_aninhada(langfuse_real: ExportStatus) -> None:
    from fator_r.tracing.client import instrumentar_anthropic

    instrumentar_anthropic()
    claude = _anthropic_simulado()
    u = await criar_escritorio_com_usuario()
    async with (
        firm_session(u.firm_id) as session,
        tracer.run(
            session, agente="teste", gatilho="integ", firm_id=u.firm_id, user_id=u.user_id
        ) as run,
    ):
        with run.span("plan"):
            await claude.messages.create(
                model="claude-sonnet-5",
                max_tokens=10,
                messages=[{"role": "user", "content": "classifique"}],
            )
        trace_id = (await run.finish(decisao={}, texto="ok", status="ok"))["trace_id"]
    await _sync(langfuse_real)
    consulta = LangfuseConsulta(_settings())
    observacoes = await esperar(
        lambda: consulta.observacoes(trace_id),
        lambda obs: any(o.get("type") == "GENERATION" for o in obs),
        segundos=60,
    )
    plan = next(o for o in observacoes if o["name"] == "plan")
    geracao = next(o for o in observacoes if o.get("type") == "GENERATION")
    assert geracao["parentObservationId"] == plan["id"]
    assert geracao["traceId"] == trace_id


async def test_cadastro_pelo_extrato_no_langfuse(
    client: httpx.AsyncClient, langfuse_real: ExportStatus
) -> None:
    """M8 (AT-011): mesmo trace_id, gatilho próprio, spans tool/decide/render e CNPJ mascarado.

    A prova é a API pública do Langfuse, não a flag langfuse_sync: o SDK v4 guarda um recurso por
    public_key, então só o primeiro cliente do processo recebe o ExportStatus do fixture.
    """
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    extrato = (ROOT / "apps/api/fixtures/pgdas/txt_padrao/documento.txt").read_bytes()
    doc = (
        await client.post("/inbox/pgdas", files={"arquivo": ("extrato.txt", extrato, "text/plain")})
    ).json()
    resposta = await client.post(
        f"/inbox/{doc['id']}/cadastrar-empresa",
        json={
            "nome": "CLINICA EXEMPLO LTDA",
            "cnpj": "11.222.333/0001-81",
            "sujeita_fator_r": True,
        },
    )
    assert resposta.status_code == 201, resposta.text
    trace_id = resposta.json()["documento"]["trace_id"]
    await _sync(langfuse_real)

    consulta = LangfuseConsulta(_settings())
    observacoes = await esperar(lambda: consulta.observacoes(trace_id), lambda obs: len(obs) >= 4)
    assert {"parser_pgdas", "tool", "decide", "render"} <= {o["name"] for o in observacoes}
    assert all(o["traceId"] == trace_id for o in observacoes)
    raiz = next(o for o in observacoes if o["name"] == "parser_pgdas")
    assert {"parser_pgdas", "cadastro_pelo_extrato", f"firm:{u.firm_id}"} <= set(
        raiz.get("tags") or []
    )
    bruto = json.dumps(observacoes)
    assert "11222333000181" not in bruto
    assert "11.222.333/0001-81" not in bruto
