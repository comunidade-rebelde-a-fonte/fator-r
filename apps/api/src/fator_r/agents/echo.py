"""Agente fictício 'echo' (T-411): exercita tracer, spans, decisão e scores sem LLM.

Registrado só em ENV dev/test.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.agents.render import com_disclaimer
from fator_r.repositories.auth import AuthenticatedUser
from fator_r.tracing import tracer


async def executar(session: AsyncSession, user: AuthenticatedUser, mensagem: str) -> dict[str, Any]:
    async with tracer.run(
        session,
        agente="echo",
        gatilho="dev",
        firm_id=user.firm_id,
        user_id=user.id,
        entrada={"mensagem": mensagem},
    ) as run:
        with run.span("plan", input={"mensagem": mensagem}) as span:
            intencao = "eco"
            span.update(output={"intencao": intencao})
        with run.span("tool", input={"mensagem": mensagem}) as span:
            resultado = {"tamanho": len(mensagem)}
            span.update(output=resultado)
        with run.span("decide") as span:
            decisao = {"intencao": intencao, **resultado}
            await tracer.record_decision(run, tipo="eco", dados=decisao)
            span.update(output=decisao)
        with run.span("render") as span:
            texto = com_disclaimer(f"Eco: {mensagem}")
            span.update(output={"texto": texto})
        return await run.finish(decisao=decisao, texto=texto, status="ok")
