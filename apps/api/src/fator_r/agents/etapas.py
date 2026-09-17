"""Spans plan e render compartilhados pelos agentes consultor e priorizador."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.agents.guardas import garantir_simulacao_para_corrigir
from fator_r.agents.intencao import classificar_por_palavras, empresa_citada
from fator_r.agents.llm import PROMPT_VERSION, ClienteLLM, Intencao, LLMIndisponivel
from fator_r.agents.render import com_disclaimer, validar_texto
from fator_r.tracing.tracer import AgentRun


async def planejar(run: AgentRun, llm: ClienteLLM, mensagem: str, empresas: list[str]) -> Intencao:
    with run.span(
        "plan",
        input={"mensagem": mensagem, "total_empresas": len(empresas)},
        metadata={"prompt_version": PROMPT_VERSION},
    ) as span:
        try:
            intencao = await llm.classificar(mensagem, [])
            # Empresa resolvida localmente contra a carteira do escritório (nunca pelo LLM).
            local = empresa_citada(mensagem, empresas)
            intencao = intencao.model_copy(update={"company_ref": local or intencao.company_ref})
            fallback, motivo = False, None
        except LLMIndisponivel as exc:
            intencao = classificar_por_palavras(mensagem, empresas)
            fallback, motivo = True, str(exc)
        span.update(
            output={**intencao.model_dump(), "fallback": fallback, "motivo_fallback": motivo}
        )
    return intencao


async def decidir(
    run: AgentRun, session: AsyncSession, firm_id: uuid.UUID, decisao: dict[str, Any]
) -> None:
    """Guarda do decide: levanta RecomendacaoSemSimulacao e o run termina em erro."""
    with run.span("decide", input=decisao) as span:
        await garantir_simulacao_para_corrigir(session, firm_id, decisao)
        span.update(output=decisao)


async def renderizar(
    run: AgentRun,
    llm: ClienteLLM | None,
    decisao: dict[str, Any],
    template: str,
    usar_llm: bool = True,
) -> str:
    with run.span("render", metadata={"prompt_version": PROMPT_VERSION}) as span:
        texto = template
        rejeitado = False
        orfaos: tuple[str, ...] = ()
        motivo = None
        if usar_llm and llm is not None:
            try:
                candidato = await llm.redigir(decisao)
                validacao = validar_texto(candidato, decisao)
                if validacao.valido:
                    texto = candidato
                else:
                    rejeitado, orfaos = True, validacao.orfaos
            except LLMIndisponivel as exc:
                motivo = str(exc)
        final = com_disclaimer(texto)
        span.update(
            output={"texto": final},
            metadata={
                "render_rejeitado": rejeitado,
                "numeros_orfaos": list(orfaos),
                "llm_indisponivel": motivo,
                "usou_template": texto is template,
            },
        )
    return final
