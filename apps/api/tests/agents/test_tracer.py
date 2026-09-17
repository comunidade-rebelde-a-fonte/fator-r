"""Tracer e guarda "sem trace não grava" (T-403/T-404), com LANGFUSE_TRACING_ENABLED=false."""

import json
from collections.abc import Sequence

import httpx
import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import SpanContext
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from fator_r.core.db import firm_session, get_owner_sessionmaker
from fator_r.repositories.orm import AgentDecision, AgentTrace, EvalHuman
from fator_r.tracing import scores, tracer
from fator_r.tracing.client import ExportStatus, MonitoredSpanExporter, mascarar_atributo
from fator_r.tracing.sync import aplicar_status
from tests.factories import criar_escritorio_com_usuario, login


async def _contar(model: type) -> int:
    async with get_owner_sessionmaker()() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def _trace(trace_id: str) -> AgentTrace:
    async with get_owner_sessionmaker()() as session:
        return (
            await session.execute(select(AgentTrace).where(AgentTrace.id == trace_id))
        ).scalar_one()


async def test_run_grava_trace_e_decisao_na_mesma_transacao() -> None:
    u = await criar_escritorio_com_usuario()
    async with (
        firm_session(u.firm_id) as session,
        tracer.run(
            session,
            agente="teste",
            gatilho="unit",
            firm_id=u.firm_id,
            user_id=u.user_id,
            entrada={"x": 1},
        ) as run,
    ):
        with run.span("plan"), run.span("tool"):
            pass
        await tracer.record_decision(run, tipo="t", dados={"valor": "1.50"})
        saida = await run.finish(decisao={"ok": True}, texto="feito", status="ok")
    assert len(saida["trace_id"]) == 32
    trace = await _trace(saida["trace_id"])
    assert trace.status == "ok"
    assert trace.saida_json["texto"] == "feito"
    assert trace.latencia_ms is not None
    assert trace.langfuse_sync == "pending"
    assert await _contar(AgentDecision) == 1


async def test_excecao_desfaz_decisoes_e_preserva_trace_de_erro() -> None:
    u = await criar_escritorio_com_usuario()
    ids: list[str] = []

    async def corrida_com_erro() -> None:
        async with (
            firm_session(u.firm_id) as session,
            tracer.run(
                session, agente="teste", gatilho="unit", firm_id=u.firm_id, user_id=u.user_id
            ) as run,
        ):
            ids.append(run.trace_id)
            await tracer.record_decision(run, tipo="t", dados={})
            raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        await corrida_com_erro()
    trace = await _trace(ids[0])
    assert trace.status == "error"
    assert trace.saida_json == {"erro": "ZeroDivisionError"}
    assert await _contar(AgentDecision) == 0


async def test_run_sem_finish_vira_erro() -> None:
    u = await criar_escritorio_com_usuario()
    with pytest.raises(tracer.RunEncerrado):
        async with (
            firm_session(u.firm_id) as session,
            tracer.run(
                session, agente="teste", gatilho="unit", firm_id=u.firm_id, user_id=u.user_id
            ),
        ):
            pass
    assert await _contar(AgentTrace) == 1


async def test_span_so_aceita_nomes_do_contrato() -> None:
    u = await criar_escritorio_com_usuario()

    async def corrida_com_span_invalido() -> None:
        async with (
            firm_session(u.firm_id) as session,
            tracer.run(
                session, agente="teste", gatilho="unit", firm_id=u.firm_id, user_id=u.user_id
            ) as run,
        ):
            with run.span("qualquer"):
                pass

    with pytest.raises(ValueError, match="não permitido"):
        await corrida_com_span_invalido()


async def test_decisao_sem_run_falha_pela_api_python() -> None:
    with pytest.raises(tracer.DecisaoSemTrace):
        await tracer.record_decision(None, tipo="t", dados={})


async def test_decisao_sem_trace_falha_no_banco() -> None:
    u = await criar_escritorio_com_usuario()
    async with firm_session(u.firm_id) as session:
        with pytest.raises((IntegrityError, DBAPIError)):
            await session.execute(
                text(
                    "INSERT INTO agent_decisions (firm_id, trace_id, agente, tipo, dados_json) "
                    "VALUES (:f, NULL, 'x', 'y', '{}')"
                ),
                {"f": u.firm_id},
            )
    async with firm_session(u.firm_id) as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                text(
                    "INSERT INTO agent_decisions (firm_id, trace_id, agente, tipo, dados_json) "
                    "VALUES (:f, :t, 'x', 'y', '{}')"
                ),
                {"f": u.firm_id, "t": "0" * 32},
            )


async def test_echo_pela_api(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    body = (await client.post("/agents/echo/run", json={"mensagem": "olá"})).json()
    assert body["texto"].startswith("Eco: olá")
    assert body["decisao"] == {"intencao": "eco", "tamanho": 3}
    trace = await _trace(body["trace_id"])
    assert (trace.agente, trace.status, trace.firm_id) == ("echo", "ok", u.firm_id)


async def test_nota_humana_erro_exige_comentario_na_api_python_e_no_banco() -> None:
    u = await criar_escritorio_com_usuario()
    async with (
        firm_session(u.firm_id) as session,
        tracer.run(
            session, agente="teste", gatilho="unit", firm_id=u.firm_id, user_id=u.user_id
        ) as run,
    ):
        trace_id = (await run.finish(decisao={}, texto="", status="ok"))["trace_id"]
    async with firm_session(u.firm_id) as session:
        with pytest.raises(scores.NotaSemComentario):
            await scores.human(session, u.firm_id, trace_id, u.user_id, "erro", "   ")
        await scores.human(session, u.firm_id, trace_id, u.user_id, "parcial", None)
    async with firm_session(u.firm_id) as session:
        session.add(EvalHuman(firm_id=u.firm_id, trace_id=trace_id, user_id=u.user_id, nota="erro"))
        with pytest.raises(IntegrityError, match="ck_evals_human_comentario_em_erro"):
            await session.commit()


def test_mascara_remove_texto_do_pdf_e_trunca() -> None:
    payload = json.dumps({"cnpj": "11222333000181", "texto_extraido": "conteúdo do pdf" * 10})
    mascarado = json.loads(mascarar_atributo(payload, 1024))
    assert mascarado["texto_extraido"] == "[removido]"
    assert mascarado["cnpj"] == "***0181"  # CNPJ também é mascarado (revisão de segurança M2)
    grande = mascarar_atributo("x" * 5000, 1024)
    assert len(grande) < 1100
    assert grande.endswith("…[truncado]")


class _ExporterFalho(SpanExporter):
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return SpanExportResult.FAILURE


async def test_falha_de_exportacao_marca_trace_como_failed() -> None:
    u = await criar_escritorio_com_usuario()
    async with (
        firm_session(u.firm_id) as session,
        tracer.run(
            session, agente="teste", gatilho="unit", firm_id=u.firm_id, user_id=u.user_id
        ) as run,
    ):
        trace_id = (await run.finish(decisao={}, texto="", status="ok"))["trace_id"]
    status = ExportStatus()
    span = ReadableSpan(
        name="x", context=SpanContext(trace_id=int(trace_id, 16), span_id=1, is_remote=False)
    )
    MonitoredSpanExporter(_ExporterFalho(), status).export([span])
    from fator_r.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:  # rotina de sistema, sem escritório
        assert await aplicar_status(session, status) == 1
    assert (await _trace(trace_id)).langfuse_sync == "failed"
