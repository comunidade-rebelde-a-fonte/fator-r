"""Contrato do tracing (Plano §7.2).

    async with tracer.run(session, agente=..., gatilho=..., firm_id=..., ...) as run:
        with run.span("plan"): ...
        with run.span("tool", input=...) as span: span.update(output=...)
        await record_decision(run, tipo="...", dados={...})
        await run.finish(decisao=..., texto=..., confianca=..., status="ok")

- O trace local (agent_traces) nasce na mesma transação das decisões: sem trace, nada grava.
- Exceção dentro do run: rollback das decisões e trace local preservado com status "error".
- O Langfuse recebe o mesmo trace_id (spans plan|parse|tool|decide|render).
"""

import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from langfuse import propagate_attributes
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import AgentDecision, AgentTrace
from fator_r.tracing.client import get_langfuse, novo_trace_id

SPANS_PERMITIDOS = ("plan", "parse", "tool", "decide", "render")
StatusTrace = Literal["ok", "error", "needs_review"]


class RunEncerrado(RuntimeError):
    pass


class DecisaoSemTrace(RuntimeError):
    pass


def _json(valor: Any) -> Any:
    """Decimal/UUID/date viram string para JSONB e Langfuse."""
    if isinstance(valor, dict):
        return {str(k): _json(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple | set):
        return [_json(v) for v in valor]
    if isinstance(valor, Decimal | uuid.UUID):
        return str(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor


def json_safe(valor: Any) -> Any:
    """Versão pública da conversão para JSON (Decimal, UUID e datas viram string)."""
    return _json(valor)


class SpanHandle:
    def __init__(self, observacao: Any) -> None:
        self._observacao = observacao

    def update(self, **kwargs: Any) -> None:
        self._observacao.update(**{k: _json(v) for k, v in kwargs.items()})


@dataclass
class AgentRun:
    session: AsyncSession
    trace: AgentTrace
    inicio: float
    root: Any
    finalizado: bool = False
    ativo: bool = True
    _decisoes: list[AgentDecision] = field(default_factory=list)

    @property
    def trace_id(self) -> str:
        return self.trace.id

    @property
    def firm_id(self) -> uuid.UUID:
        return self.trace.firm_id

    @contextmanager
    def span(
        self, nome: str, *, input: Any = None, metadata: dict[str, Any] | None = None
    ) -> Iterator["SpanHandle"]:
        if nome not in SPANS_PERMITIDOS:
            raise ValueError(f"Span '{nome}' não permitido; use {SPANS_PERMITIDOS}")
        if not self.ativo:
            raise RunEncerrado("Run já encerrado")
        langfuse = get_langfuse()
        payload = {"name": nome, "input": _json(input), "metadata": _json(metadata)}
        if nome in ("parse", "tool"):
            with langfuse.start_as_current_observation(as_type="tool", **payload) as observacao:
                yield SpanHandle(observacao)
        else:
            with langfuse.start_as_current_observation(as_type="chain", **payload) as observacao:
                yield SpanHandle(observacao)

    async def finish(
        self,
        *,
        decisao: dict[str, Any],
        texto: str,
        status: StatusTrace,
        confianca: Decimal | None = None,
        saida: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.ativo:
            raise RunEncerrado("Run já encerrado")
        self.trace.decisao_json = _json(decisao)
        self.trace.saida_json = _json({"texto": texto, **(saida or {})})
        self.trace.status = status
        self.trace.confianca = confianca
        self.trace.latencia_ms = int((time.perf_counter() - self.inicio) * 1000)
        self.root.update(
            output=_json({"texto": texto, "decisao": decisao}),
            level="WARNING" if status == "needs_review" else "DEFAULT",
            metadata={"status": status, "confianca": _json(confianca)},
        )
        await self.session.commit()
        self.finalizado = True
        self.ativo = False
        return {"texto": texto, "decisao": _json(decisao), "trace_id": self.trace_id}


async def record_decision(
    run: AgentRun | None, *, tipo: str, dados: dict[str, Any]
) -> AgentDecision:
    """Único caminho de escrita de decisão de agente (CLAUDE.md §3.10)."""
    if run is None or not run.ativo:
        raise DecisaoSemTrace("Decisão de agente só pode ser gravada dentro de tracer.run()")
    decisao = AgentDecision(
        firm_id=run.firm_id,
        trace_id=run.trace_id,
        agente=run.trace.agente,
        tipo=tipo,
        dados_json=_json(dados),
    )
    run.session.add(decisao)
    await run.session.flush()
    run._decisoes.append(decisao)
    return decisao


def anexar_ao_run(run: AgentRun, objeto: Any) -> None:
    """Grava uma linha de tabela de decisão (ex.: simulations) amarrada ao trace do run."""
    if not run.ativo:
        raise DecisaoSemTrace("Run já encerrado")
    objeto.trace_id = run.trace_id
    run.session.add(objeto)


@asynccontextmanager
async def run(
    session: AsyncSession,
    *,
    agente: str,
    gatilho: str,
    firm_id: uuid.UUID,
    user_id: uuid.UUID | None,
    company_id: uuid.UUID | None = None,
    entrada: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AsyncIterator[AgentRun]:
    trace_id = novo_trace_id()
    trace = AgentTrace(
        id=trace_id,
        firm_id=firm_id,
        agente=agente,
        gatilho=gatilho,
        user_id=user_id,
        company_id=company_id,
        entrada_json=_json(entrada or {}),
        saida_json={},
        decisao_json={},
        status="error",  # provisório: só é commitado com o status real em finish()
    )
    session.add(trace)
    await session.flush()

    langfuse = get_langfuse()
    meta = {"firm_id": str(firm_id), "company_id": str(company_id or ""), **(metadata or {})}
    with (
        langfuse.start_as_current_observation(
            name=agente,
            as_type="agent",
            trace_context={"trace_id": trace_id},
            input=_json(entrada or {}),
        ) as root,
        propagate_attributes(
            user_id=str(user_id) if user_id else None,
            session_id=str(company_id) if company_id else None,
            tags=[agente, gatilho, f"firm:{firm_id}"],
            metadata={k: str(_json(v)) for k, v in meta.items()},
            trace_name=agente,
        ),
    ):
        agent_run = AgentRun(session=session, trace=trace, inicio=time.perf_counter(), root=root)
        try:
            yield agent_run
            if not agent_run.finalizado:
                raise RunEncerrado("tracer.run terminou sem finish()")
        except BaseException as exc:
            agent_run.ativo = False
            await session.rollback()
            root.update(level="ERROR", status_message=type(exc).__name__)
            await _gravar_trace_de_erro(session, trace, exc, agent_run.inicio)
            raise


async def _gravar_trace_de_erro(
    session: AsyncSession, trace: AgentTrace, exc: BaseException, inicio: float
) -> None:
    erro = AgentTrace(
        id=trace.id,
        firm_id=trace.firm_id,
        agente=trace.agente,
        gatilho=trace.gatilho,
        user_id=trace.user_id,
        company_id=trace.company_id,
        entrada_json=trace.entrada_json,
        saida_json={"erro": type(exc).__name__},
        decisao_json={},
        status="error",
        latencia_ms=int((time.perf_counter() - inicio) * 1000),
    )
    session.expunge_all()
    session.add(erro)
    await session.commit()
