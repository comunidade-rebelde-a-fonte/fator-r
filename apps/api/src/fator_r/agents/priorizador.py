"""Agente priorizador (T-610/T-611): fila da semana (Anexo V e 28-30%) por economia de DAS."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.agents.etapas import decidir, planejar, renderizar
from fator_r.agents.llm import ClienteLLM
from fator_r.core.competencia import competencia_corrente, format_competencia, parse_competencia
from fator_r.core.db import firm_session, get_sessionmaker
from fator_r.core.money import formatar_brl, quantizar_dinheiro, quantizar_percentual
from fator_r.repositories.auth import AuthenticatedUser
from fator_r.repositories.orm import AgentTrace
from fator_r.services.carteira import carteira_do_escritorio
from fator_r.tracing import tracer
from fator_r.tracing.tracer import AgentRun

AGENTE = "priorizador"
LIMITE_TEXTO = 5


async def fila_no_run(
    run: AgentRun, session: AsyncSession, firm_id: uuid.UUID, pa_texto: str | None
) -> tuple[dict[str, Any], str]:
    pa = parse_competencia(pa_texto) if pa_texto else competencia_corrente()
    with run.span("tool", input={"pa": pa}) as span:
        carteira = await carteira_do_escritorio(session, firm_id, pa)
        fila = sorted(
            (
                linha
                for linha in carteira.linhas
                if linha.resultado.semaforo in ("vermelho", "amarelo")
            ),
            key=lambda linha: -(linha.resultado.economia_12m or Decimal(0)),
        )
        itens = [
            {
                "posicao": i,
                "company_id": str(linha.empresa.id),
                "empresa": linha.empresa.nome,
                "semaforo": linha.resultado.semaforo,
                "fator_r": str(quantizar_percentual(linha.resultado.fator_r))
                if linha.resultado.fator_r is not None
                else None,
                "economia_12m": str(quantizar_dinheiro(linha.resultado.economia_12m))
                if linha.resultado.economia_12m is not None
                else None,
                "acao": linha.acao_texto,
            }
            for i, linha in enumerate(fila, start=1)
        ]
        span.update(output={"total_fila": len(itens)})
    decisao = {"intencao": "priorizar", "pa": format_competencia(pa), "fila": itens}
    if not itens:
        template = f"PA {decisao['pa']}: nenhuma empresa no Anexo V ou no limite. Carteira segura."
    else:
        linhas = "; ".join(
            f"{it['posicao']}. {it['empresa']} ({it['semaforo']}, "
            f"economia R$ {formatar_brl(it['economia_12m'])})"
            for it in itens[:LIMITE_TEXTO]
        )
        template = f"PA {decisao['pa']}: {len(itens)} empresa(s) na fila. Priorize: {linhas}."
    return decisao, template


async def responder(
    session: AsyncSession,
    user: AuthenticatedUser,
    llm: ClienteLLM,
    mensagem: str,
    pa: str | None,
) -> dict[str, Any]:
    async with tracer.run(
        session,
        agente=AGENTE,
        gatilho="chat",
        firm_id=user.firm_id,
        user_id=user.id,
        entrada={"mensagem": mensagem, "pa": pa},
    ) as run:
        intencao = await planejar(run, llm, mensagem, [])
        decisao, template = await fila_no_run(run, session, user.firm_id, pa or intencao.pa)
        await decidir(run, session, user.firm_id, decisao)
        await tracer.record_decision(run, tipo="fila_priorizacao", dados=decisao)
        texto = await renderizar(run, llm, decisao, template)
        return await run.finish(decisao=decisao, texto=texto, status="ok")


def inicio_da_semana(agora: datetime) -> datetime:
    return (agora - timedelta(days=agora.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


async def rotina_semanal(agora: datetime | None = None) -> int:
    """Roda o priorizador para cada escritório (gatilho=rotina, sem LLM). Idempotente na semana."""
    agora = agora or datetime.now(UTC)
    async with get_sessionmaker()() as sistema:
        firm_ids = list(
            (await sistema.execute(text("SELECT * FROM rotina_escritorios()"))).scalars()
        )
    executadas = 0
    for firm_id in firm_ids:
        async with firm_session(firm_id) as session:
            ja_rodou = (
                await session.execute(
                    select(func.count())
                    .select_from(AgentTrace)
                    .where(
                        AgentTrace.firm_id == firm_id,
                        AgentTrace.agente == AGENTE,
                        AgentTrace.gatilho == "rotina",
                        AgentTrace.criado_em >= inicio_da_semana(agora),
                    )
                )
            ).scalar_one()
            if ja_rodou:
                continue
            async with tracer.run(
                session, agente=AGENTE, gatilho="rotina", firm_id=firm_id, user_id=None
            ) as run:
                with run.span("plan", input={"gatilho": "rotina"}) as span:
                    span.update(output={"intencao": "priorizar", "llm": False})
                decisao, template = await fila_no_run(run, session, firm_id, None)
                await decidir(run, session, firm_id, decisao)
                await tracer.record_decision(run, tipo="fila_priorizacao", dados=decisao)
                texto = await renderizar(run, None, decisao, template, usar_llm=False)
                await run.finish(decisao=decisao, texto=texto, status="ok")
            executadas += 1
    return executadas
