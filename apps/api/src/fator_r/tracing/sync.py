"""Sincroniza agent_traces.langfuse_sync com o resultado real da exportação (T-407)."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.tracing.client import ExportStatus, export_status, get_langfuse

logger = logging.getLogger(__name__)


async def aplicar_status(session: AsyncSession, status: ExportStatus = export_status) -> int:
    resultados = status.drenar()
    ok = [trace_id for trace_id, sucesso in resultados.items() if sucesso]
    falhas = [trace_id for trace_id, sucesso in resultados.items() if not sucesso]
    alterados = 0
    for ids, valor in ((ok, "ok"), (falhas, "failed")):
        if ids:
            alterados += (
                await session.execute(
                    text(
                        "SELECT tracing_marcar_sync("
                        "CAST(:ids AS text[]), CAST(:v AS langfuse_sync))"
                    ),
                    {"ids": ids, "v": valor},
                )
            ).scalar_one()
    await session.commit()
    if falhas:
        # Sem dado de cliente no log: só a contagem.
        logger.warning("Langfuse: %d trace(s) com falha de exportação", len(falhas))
    return alterados


async def reenviar_falhas(session: AsyncSession, limite: int = 50) -> int:
    """Reemite no Langfuse o resumo local dos traces com falha (mesmo trace_id)."""
    rows = (
        await session.execute(
            text("SELECT * FROM tracing_traces_com_falha(:limite)"), {"limite": limite}
        )
    ).mappings()
    langfuse = get_langfuse()
    reenviados = 0
    for row in rows:
        # Só metadados técnicos: o conteúdo completo continua no Postgres (revisão B1).
        with langfuse.start_as_current_observation(
            name=row["agente"],
            as_type="agent",
            trace_context={"trace_id": row["id"]},
            metadata={
                "reenvio": "true",
                "status": row["status"],
                "gatilho": row["gatilho"],
                "criado_em": row["criado_em"].isoformat(),
            },
        ):
            reenviados += 1
    langfuse.flush()
    return reenviados
