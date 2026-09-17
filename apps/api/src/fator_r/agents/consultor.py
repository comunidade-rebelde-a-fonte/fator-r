"""Agente consultor (T-609): situação, simulação e explicação para uma empresa.

plan (LLM ou palavras-chave) -> tool (motor/simulador) -> decide (guarda do corrigir)
-> render (LLM validado ou template). Cálculo só em domain/.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.agents import priorizador
from fator_r.agents.etapas import decidir, planejar, renderizar
from fator_r.agents.guardas import garantir_simulacao_para_corrigir
from fator_r.agents.llm import ClienteLLM, Intencao
from fator_r.core.competencia import competencia_corrente, format_competencia, parse_competencia
from fator_r.core.money import (
    formatar_brl,
    formatar_percentual_br,
    quantizar_dinheiro,
    quantizar_percentual,
)
from fator_r.domain.fator_r import ResultadoFatorR
from fator_r.repositories import companies
from fator_r.repositories.auth import AuthenticatedUser
from fator_r.repositories.orm import Company
from fator_r.services.fator_r import resultado_empresa
from fator_r.services.simulacao import VEREDITOS_TEXTO, EntradaSimulacao, simular_e_registrar
from fator_r.tracing import tracer

AGENTE = "consultor"


def resumo_motor(company: Company, r: ResultadoFatorR) -> dict[str, Any]:
    def din(v: Any) -> str | None:
        return str(quantizar_dinheiro(v)) if v is not None else None

    def pct(v: Any) -> str | None:
        return str(quantizar_percentual(v)) if v is not None else None

    return {
        "empresa": company.nome,
        "pa": format_competencia(r.pa),
        "status": r.status,
        "motivo": r.motivo,
        "fator_r": pct(r.fator_r),
        "anexo": r.anexo,
        "semaforo": r.semaforo,
        "rbt12": din(r.rbt12),
        "fs12": din(r.fs12),
        "gap_12m_28": din(r.gap_12m_28),
        "reforco_mensal_28": din(r.reforco_mensal_28),
        "gap_12m_meta": din(r.gap_12m_meta),
        "reforco_mensal_meta": din(r.reforco_mensal_meta),
        "meta_operacional": pct(r.meta_operacional),
        "economia_12m": din(r.economia_12m),
        "meses_faltantes": [format_competencia(m) for m in r.meses_faltantes],
    }


def template_status(d: dict[str, Any]) -> str:
    if d["status"] != "ok":
        return f"{d['empresa']}, PA {d['pa']}: dados insuficientes para calcular ({d['motivo']})."
    return (
        f"{d['empresa']}, PA {d['pa']}: Fator R {formatar_percentual_br(d['fator_r'])} "
        f"(Anexo {d['anexo']}, semáforo {d['semaforo']}). Reforço mensal até a meta: "
        f"R$ {formatar_brl(d['reforco_mensal_meta'])}. Economia estimada de DAS em 12 meses: "
        f"R$ {formatar_brl(d['economia_12m'])}."
    )


async def _empresa(
    session: AsyncSession, user: AuthenticatedUser, company_id: uuid.UUID | None, intencao: Intencao
) -> Company | None:
    if company_id is not None:
        return await companies.obter(session, user.firm_id, company_id)
    if intencao.company_ref:
        filtro = companies.FiltroEmpresas(ativo=True, busca=intencao.company_ref, limit=5)
        encontradas, _ = await companies.listar(session, user.firm_id, filtro)
        exatas = [c for c in encontradas if c.nome.lower() == intencao.company_ref.lower()]
        candidatas = exatas or encontradas
        return candidatas[0] if candidatas else None
    return None


async def responder(
    session: AsyncSession,
    user: AuthenticatedUser,
    llm: ClienteLLM,
    mensagem: str,
    company_id: uuid.UUID | None,
) -> dict[str, Any]:
    ativas, _ = await companies.listar(
        session, user.firm_id, companies.FiltroEmpresas(ativo=True, limit=500)
    )
    async with tracer.run(
        session,
        agente=AGENTE,
        gatilho="chat",
        firm_id=user.firm_id,
        user_id=user.id,
        company_id=company_id,
        entrada={"mensagem": mensagem, "company_id": company_id},
    ) as run:
        intencao = await planejar(run, llm, mensagem, [c.nome for c in ativas])
        if intencao.intencao == "priorizar":
            decisao, template = await priorizador.fila_no_run(
                run, session, user.firm_id, intencao.pa
            )
            await decidir(run, session, user.firm_id, decisao)
        else:
            company = await _empresa(session, user, company_id, intencao)
            pa = parse_competencia(intencao.pa) if intencao.pa else competencia_corrente()
            if company is None:
                decisao = {"intencao": intencao.intencao, "erro": "empresa_nao_identificada"}
                template = "Não identifiquei a empresa. Abra a ficha da empresa ou cite o nome."
                await decidir(run, session, user.firm_id, decisao)
            elif intencao.intencao == "simular":
                simulacao, resultado = await simular_e_registrar(
                    run, session, user.firm_id, company, EntradaSimulacao(pa=pa, meta=intencao.meta)
                )
                decisao = {
                    "intencao": "simular",
                    "empresa": company.nome,
                    "pa": format_competencia(pa),
                    "veredito": resultado.veredito,
                    "simulation_id": str(simulacao.id),
                    "reforco_mensal": str(quantizar_dinheiro(resultado.reforco_mensal)),
                    "custo_total": str(quantizar_dinheiro(resultado.custo_total)),
                    "liquido": str(quantizar_dinheiro(resultado.liquido))
                    if resultado.liquido is not None
                    else None,
                    "horizonte_meses": resultado.parametros.horizonte_meses,
                }
                await garantir_simulacao_para_corrigir(session, user.firm_id, decisao)
                template = (
                    f"{company.nome}, PA {decisao['pa']}: "
                    + (
                        VEREDITOS_TEXTO[resultado.veredito]
                        if resultado.veredito
                        else "dados insuficientes para simular."
                    )
                    + f" Líquido estimado: R$ {formatar_brl(decisao['liquido'])}."
                )
            else:
                with run.span("tool", input={"company_id": company.id, "pa": pa}) as span:
                    resultado_motor = await resultado_empresa(session, user.firm_id, company, pa)
                    decisao = {
                        "intencao": intencao.intencao,
                        **resumo_motor(company, resultado_motor),
                    }
                    span.update(output=decisao)
                template = template_status(decisao)
                await decidir(run, session, user.firm_id, decisao)
        await tracer.record_decision(run, tipo="consultor_resposta", dados=decisao)
        texto = await renderizar(run, llm, decisao, template)
        return await run.finish(
            decisao=decisao, texto=texto, status="needs_review" if decisao.get("erro") else "ok"
        )
