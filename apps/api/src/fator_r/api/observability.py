import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.repositories import traces as repo
from fator_r.repositories.orm import AgentTrace
from fator_r.tracing import scores
from fator_r.tracing.client import url_do_trace
from fator_r.tracing.consulta import LangfuseConsulta, LangfuseIndisponivel

router = APIRouter(tags=["observabilidade"])

TraceId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
StatusTrace = Literal["ok", "error", "needs_review"]
_CACHE_CUSTO: dict[uuid.UUID, tuple[float, dict[str, Any]]] = {}
CACHE_CUSTO_S = 300


class ResumoAgenteOut(BaseModel):
    agente: str
    volume: int
    latencia_media_ms: Decimal | None
    confianca_media: Decimal | None
    erros: int
    reviews: int


class ResumoOut(BaseModel):
    corridas_24h: int
    corridas_total: int
    pendencias_sem_nota: int
    acerto_ouro: Decimal | None
    acerto_humano: Decimal | None
    por_agente: list[ResumoAgenteOut]
    custo_llm_30d: Decimal | None
    tokens_llm_30d: int | None


class TraceResumoOut(BaseModel):
    id: str
    agente: str
    gatilho: str
    status: StatusTrace
    confianca: Decimal | None
    latencia_ms: int | None
    langfuse_sync: Literal["pending", "ok", "failed"]
    company_id: uuid.UUID | None
    criado_em: datetime
    tem_nota_humana: bool

    @classmethod
    def de(cls, t: AgentTrace, tem_nota: bool) -> "TraceResumoOut":
        return cls(
            id=t.id,
            agente=t.agente,
            gatilho=t.gatilho,
            status=t.status,
            confianca=t.confianca,
            latencia_ms=t.latencia_ms,
            langfuse_sync=t.langfuse_sync,
            company_id=t.company_id,
            criado_em=t.criado_em,
            tem_nota_humana=tem_nota,
        )


class TraceList(BaseModel):
    items: list[TraceResumoOut]
    total: int


class SpanOut(BaseModel):
    id: str
    nome: str
    tipo: str
    inicio: str | None
    fim: str | None
    latencia_ms: float | None
    nivel: str | None
    parent_id: str | None
    modelo: str | None
    custo: float | None


class EvalOuroOut(BaseModel):
    campo: str
    esperado: str | None
    obtido: str | None
    dentro_tolerancia: bool | None
    status: Literal["ok", "erro", "ouro_indisponivel"]


class EvalHumanaOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    nota: Literal["acerto", "parcial", "erro"]
    comentario: str | None
    criado_em: datetime


class TraceDetalheOut(BaseModel):
    trace: TraceResumoOut
    entrada: dict[str, Any]
    saida: dict[str, Any]
    decisao: dict[str, Any]
    spans: list[SpanOut]
    spans_indisponiveis: bool
    evals_ouro: list[EvalOuroOut]
    evals_humanas: list[EvalHumanaOut]
    langfuse_url: str


class NotaHumanaIn(BaseModel):
    nota: Literal["acerto", "parcial", "erro"]
    comentario: str | None = Field(default=None, max_length=2000)


async def _custo_llm(firm_id: uuid.UUID) -> dict[str, Any]:
    agora = time.monotonic()
    em_cache = _CACHE_CUSTO.get(firm_id)
    if em_cache and agora - em_cache[0] < CACHE_CUSTO_S:
        return em_cache[1]
    fim = datetime.now(UTC)
    try:
        valor = await LangfuseConsulta().custo_e_tokens(
            fim - timedelta(days=30), fim, f"firm:{firm_id}"
        )
    except LangfuseIndisponivel:
        return {"custo_total": None, "tokens_total": None}
    _CACHE_CUSTO[firm_id] = (agora, valor)
    return valor


@router.get("/observability/summary", response_model=ResumoOut)
async def resumo_observabilidade(user: CurrentUser, session: FirmSession) -> ResumoOut:
    r = await repo.resumo(session, user.firm_id)
    custo = await _custo_llm(user.firm_id)
    return ResumoOut(
        corridas_24h=r.corridas_24h,
        corridas_total=r.corridas_total,
        pendencias_sem_nota=r.pendencias_sem_nota,
        acerto_ouro=r.acerto_ouro,
        acerto_humano=r.acerto_humano,
        por_agente=[ResumoAgenteOut(**vars(a)) for a in r.por_agente],
        custo_llm_30d=Decimal(str(custo["custo_total"]))
        if custo["custo_total"] is not None
        else None,
        tokens_llm_30d=int(custo["tokens_total"]) if custo["tokens_total"] is not None else None,
    )


@router.get("/traces", response_model=TraceList)
async def listar_traces(
    user: CurrentUser,
    session: FirmSession,
    agente: Annotated[str | None, Query(max_length=50)] = None,
    status_: Annotated[StatusTrace | None, Query(alias="status")] = None,
    sem_nota: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TraceList:
    filtro = repo.FiltroTraces(
        agente=agente, status=status_, sem_nota=sem_nota, limit=limit, offset=offset
    )
    items, total = await repo.listar(session, user.firm_id, filtro)
    return TraceList(items=[TraceResumoOut.de(t, n) for t, n in items], total=total)


def _span(o: dict[str, Any]) -> SpanOut:
    return SpanOut(
        id=o["id"],
        nome=o.get("name") or "",
        tipo=o.get("type") or "",
        inicio=o.get("startTime"),
        fim=o.get("endTime"),
        latencia_ms=(o["latency"] * 1000) if isinstance(o.get("latency"), int | float) else None,
        nivel=o.get("level"),
        parent_id=o.get("parentObservationId"),
        modelo=o.get("model"),
        custo=o.get("totalCost"),
    )


@router.get("/traces/{trace_id}", response_model=TraceDetalheOut)
async def detalhe_trace(
    trace_id: TraceId, user: CurrentUser, session: FirmSession
) -> TraceDetalheOut:
    trace = await repo.obter(session, user.firm_id, trace_id)
    if trace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trace não encontrado")
    ouro, humanas = await repo.evals(session, user.firm_id, trace_id)
    try:
        observacoes = await LangfuseConsulta().observacoes(trace_id)
        spans = sorted((_span(o) for o in observacoes), key=lambda s: s.inicio or "")
        indisponiveis = False
    except LangfuseIndisponivel:
        spans, indisponiveis = [], True
    return TraceDetalheOut(
        trace=TraceResumoOut.de(trace, bool(humanas)),
        entrada=trace.entrada_json,
        saida=trace.saida_json,
        decisao=trace.decisao_json,
        spans=spans,
        spans_indisponiveis=indisponiveis,
        evals_ouro=[
            EvalOuroOut(
                campo=e.campo,
                esperado=e.esperado,
                obtido=e.obtido,
                dentro_tolerancia=e.dentro_tolerancia,
                status=e.status,
            )
            for e in ouro
        ],
        evals_humanas=[
            EvalHumanaOut(
                id=h.id,
                user_id=h.user_id,
                nota=h.nota,
                comentario=h.comentario,
                criado_em=h.criado_em,
            )
            for h in humanas
        ],
        langfuse_url=url_do_trace(trace_id),
    )


@router.post(
    "/traces/{trace_id}/human-eval",
    response_model=EvalHumanaOut,
    status_code=status.HTTP_201_CREATED,
)
async def avaliar_trace(
    trace_id: TraceId, payload: NotaHumanaIn, user: CurrentUser, session: FirmSession
) -> EvalHumanaOut:
    try:
        avaliacao = await scores.human(
            session, user.firm_id, trace_id, user.id, payload.nota, payload.comentario
        )
    except scores.TraceNaoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trace não encontrado") from exc
    except scores.NotaSemComentario as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return EvalHumanaOut(
        id=avaliacao.id,
        user_id=avaliacao.user_id,
        nota=payload.nota,
        comentario=avaliacao.comentario,
        criado_em=avaliacao.criado_em,
    )
