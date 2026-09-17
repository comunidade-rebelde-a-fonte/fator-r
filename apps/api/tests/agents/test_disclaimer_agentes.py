"""Disclaimer do PGDAS-D em 100% das respostas de agente pela API (T-704)."""

import httpx

from fator_r.agents.render import DISCLAIMER
from tests.factories import criar_escritorio_com_usuario, empresa_payload, login

MESES = [f"2025-{m:02d}" for m in range(9, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]


async def test_todas_as_respostas_de_agente_trazem_o_disclaimer(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    empresa = (await client.post("/companies", json=empresa_payload())).json()
    for mes in MESES:
        await client.put(
            f"/companies/{empresa['id']}/movements/{mes}",
            json={"receita_bruta": "50000.00", "pro_labore": "10000.00"},
        )
    textos = [
        (await client.post("/agents/echo/run", json={"mensagem": "oi"})).json()["texto"],
        (
            await client.post(
                "/agents/consultor/chat",
                json={"mensagem": "situação em 09/2026", "company_id": empresa["id"]},
            )
        ).json()["texto"],
        (
            await client.post(
                "/agents/consultor/chat",
                json={"mensagem": "simule a correção em 09/2026", "company_id": empresa["id"]},
            )
        ).json()["texto"],
        (await client.post("/agents/consultor/chat", json={"mensagem": "o que é fator r?"})).json()[
            "texto"
        ],
        (
            await client.post(
                "/agents/priorizador/chat", json={"mensagem": "priorizar", "pa": "2026-09"}
            )
        ).json()["texto"],
        (
            await client.post(f"/companies/{empresa['id']}/simulations", json={"pa": "2026-09"})
        ).json()["texto"],
    ]
    upload = (
        await client.post(
            "/inbox/pgdas", files={"arquivo": ("x.txt", b"PA: 09/2026\n", "text/plain")}
        )
    ).json()
    textos.append(upload["texto_agente"])
    rejeitado = (
        await client.post(f"/inbox/{upload['id']}/reject", json={"motivo": "teste de disclaimer"})
    ).json()
    textos.append(rejeitado["texto_agente"])
    assert len(textos) == 8
    for texto in textos:
        assert texto.rstrip().endswith(DISCLAIMER), texto
