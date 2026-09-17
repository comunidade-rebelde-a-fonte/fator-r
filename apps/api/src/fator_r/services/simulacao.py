"""Simulação persistida no trace (T-603): motor + simulador dentro de um run do consultor."""

import uuid
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.agents.render import com_disclaimer
from fator_r.core.competencia import format_competencia
from fator_r.domain.simulador import ParametrosSimulacao, ResultadoSimulacao, simular
from fator_r.repositories import firms
from fator_r.repositories.orm import Company, Simulation
from fator_r.services.fator_r import resultado_empresa
from fator_r.tracing import tracer
from fator_r.tracing.tracer import AgentRun

INSS_PADRAO = Decimal("0.11")
IRRF_PADRAO = Decimal("0.275")
HORIZONTE_PADRAO = 12

VEREDITOS_TEXTO = {
    "ja_na_meta": "A empresa já está na meta; não é preciso corrigir.",
    "corrigir": (
        "Vale corrigir: a economia de DAS supera o custo de INSS e IRRF do pró-labore extra."
    ),
    "nao_forcar": (
        "Não forçar: a economia não compensa o custo ou fica abaixo do piso do escritório."
    ),
}


@dataclass(frozen=True)
class EntradaSimulacao:
    pa: date
    meta: Decimal | None = None
    fracao_pro_labore: Decimal = Decimal("1")
    inss: Decimal = INSS_PADRAO
    irrf: Decimal = IRRF_PADRAO
    horizonte_meses: int = HORIZONTE_PADRAO


def resultado_json(r: ResultadoSimulacao) -> dict[str, Any]:
    dados = asdict(r)
    dados["parametros"] = asdict(r.parametros)
    return dados


def texto_simulacao(company: Company, pa: date, r: ResultadoSimulacao) -> str:
    return com_disclaimer(_texto_simulacao(company, pa, r))


def _texto_simulacao(company: Company, pa: date, r: ResultadoSimulacao) -> str:
    if r.veredito is None:
        return (
            f"{company.nome}, PA {format_competencia(pa)}: "
            f"dados insuficientes para simular ({r.motivo})."
        )
    return f"{company.nome}, PA {format_competencia(pa)}: {VEREDITOS_TEXTO[r.veredito]}"


async def simular_e_registrar(
    run: AgentRun, session: AsyncSession, firm_id: uuid.UUID, company: Company, e: EntradaSimulacao
) -> tuple[Simulation, ResultadoSimulacao]:
    """Roda motor + simulador nos spans tool/decide do run e grava a simulação no trace."""
    firm = await firms.obter(session, firm_id)
    parametros = ParametrosSimulacao(
        meta=e.meta if e.meta is not None else firm.meta_operacional,
        fracao_pro_labore=e.fracao_pro_labore,
        inss=e.inss,
        irrf=e.irrf,
        horizonte_meses=e.horizonte_meses,
        piso_economia_anual=firm.piso_economia_anual,
    )
    with run.span("tool", input={"pa": e.pa, "parametros": asdict(parametros)}) as span:
        motor = await resultado_empresa(session, firm_id, company, e.pa)
        resultado = simular(motor, parametros)
        span.update(output=resultado_json(resultado))
    with run.span("decide") as span:
        simulacao = Simulation(
            firm_id=firm_id,
            company_id=company.id,
            pa=e.pa,
            parametros_json=tracer.json_safe(asdict(parametros)),
            resultado_json=tracer.json_safe(resultado_json(resultado)),
            veredito=resultado.veredito,
        )
        tracer.anexar_ao_run(run, simulacao)
        await session.flush()
        await tracer.record_decision(
            run,
            tipo="simulacao",
            dados={"simulation_id": simulacao.id, "veredito": resultado.veredito},
        )
        span.update(output={"simulation_id": simulacao.id, "veredito": resultado.veredito})
    return simulacao, resultado
