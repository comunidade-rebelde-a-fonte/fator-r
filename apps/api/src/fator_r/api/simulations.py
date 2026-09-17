import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from fator_r.api.companies import empresa_do_escritorio
from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.api.schemas import CompetenciaIn, CompetenciaOut
from fator_r.core.competencia import parse_competencia
from fator_r.core.money import quantizar_dinheiro, quantizar_percentual
from fator_r.domain.tabelas import TabelaNaoVigente
from fator_r.repositories import simulations as repo
from fator_r.repositories.orm import Simulation
from fator_r.services.simulacao import (
    HORIZONTE_PADRAO,
    INSS_PADRAO,
    IRRF_PADRAO,
    EntradaSimulacao,
    simular_e_registrar,
    texto_simulacao,
)
from fator_r.tracing import tracer

router = APIRouter(prefix="/companies/{company_id}/simulations", tags=["simulador"])

Taxa = Annotated[Decimal, Field(ge=0, le=1, max_digits=7, decimal_places=6)]
Veredito = Literal["ja_na_meta", "corrigir", "nao_forcar"]


CAMPOS_DINHEIRO = (
    "reforco_12m",
    "reforco_mensal",
    "pro_labore_extra_mensal",
    "pro_labore_extra_horizonte",
    "custo_inss",
    "custo_irrf",
    "custo_total",
    "economia_12m",
    "economia_horizonte",
    "liquido",
)


def para_exibicao(resultado: dict[str, Any]) -> dict[str, Any]:
    """Quantiza só na saída (CLAUDE.md §10.1); o banco guarda o valor completo."""
    saida = dict(resultado)
    for campo in CAMPOS_DINHEIRO:
        if saida.get(campo) is not None:
            saida[campo] = str(quantizar_dinheiro(Decimal(str(saida[campo]))))
    if saida.get("fator_atual") is not None:
        saida["fator_atual"] = str(quantizar_percentual(Decimal(str(saida["fator_atual"]))))
    return saida


class SimulacaoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pa: CompetenciaIn
    meta: (
        Annotated[Decimal, Field(ge=Decimal("0.28"), lt=1, max_digits=7, decimal_places=6)] | None
    ) = None
    fracao_pro_labore: Taxa = Decimal("1")
    inss: Taxa = INSS_PADRAO
    irrf: Taxa = IRRF_PADRAO
    horizonte_meses: int = Field(default=HORIZONTE_PADRAO, ge=1, le=60)


class SimulacaoOut(BaseModel):
    simulation_id: uuid.UUID
    trace_id: str
    pa: CompetenciaOut
    veredito: Veredito | None
    texto: str
    parametros: dict[str, Any]
    resultado: dict[str, Any]
    criado_em: datetime | None = None

    @classmethod
    def de(cls, s: Simulation, texto: str) -> "SimulacaoOut":
        return cls(
            simulation_id=s.id,
            trace_id=s.trace_id,
            pa=s.pa,
            veredito=s.veredito,
            texto=texto,
            parametros=s.parametros_json,
            resultado=para_exibicao(s.resultado_json),
            criado_em=s.criado_em,
        )


@router.post("", response_model=SimulacaoOut, status_code=status.HTTP_201_CREATED)
async def simular_empresa(
    company_id: uuid.UUID, payload: SimulacaoIn, user: CurrentUser, session: FirmSession
) -> SimulacaoOut:
    company = await empresa_do_escritorio(session, user.firm_id, company_id)
    entrada = EntradaSimulacao(
        pa=parse_competencia(payload.pa),
        meta=payload.meta,
        fracao_pro_labore=payload.fracao_pro_labore,
        inss=payload.inss,
        irrf=payload.irrf,
        horizonte_meses=payload.horizonte_meses,
    )
    try:
        async with tracer.run(
            session,
            agente="consultor",
            gatilho="ficha",
            firm_id=user.firm_id,
            user_id=user.id,
            company_id=company.id,
            entrada={"intencao": "simular", **payload.model_dump()},
            metadata={"pa": payload.pa},
        ) as run:
            simulacao, resultado = await simular_e_registrar(
                run, session, user.firm_id, company, entrada
            )
            with run.span("render") as span:
                texto = texto_simulacao(company, entrada.pa, resultado)
                span.update(output={"texto": texto})
            await run.finish(
                decisao={"veredito": resultado.veredito, "simulation_id": simulacao.id},
                texto=texto,
                status="ok",
            )
    except TabelaNaoVigente as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return SimulacaoOut(
        simulation_id=simulacao.id,
        trace_id=run.trace_id,
        pa=entrada.pa,
        veredito=resultado.veredito,
        texto=texto,
        parametros=simulacao.parametros_json,
        resultado=para_exibicao(simulacao.resultado_json),
    )


@router.get("", response_model=list[SimulacaoOut])
async def historico_simulacoes(
    company_id: uuid.UUID,
    user: CurrentUser,
    session: FirmSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[SimulacaoOut]:
    company = await empresa_do_escritorio(session, user.firm_id, company_id)
    return [
        SimulacaoOut.de(s, texto="")
        for s in await repo.listar(session, user.firm_id, company.id, limit)
    ]
