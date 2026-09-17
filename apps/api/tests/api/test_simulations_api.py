import httpx
from sqlalchemy import select

from fator_r.core.db import get_owner_sessionmaker
from fator_r.repositories.orm import AgentDecision, AgentTrace, Simulation
from tests.factories import criar_escritorio_com_usuario, empresa_payload, login

MESES = [f"2025-{m:02d}" for m in range(9, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]


async def _empresa(client: httpx.AsyncClient, pro_labore: str) -> str:
    empresa = (await client.post("/companies", json=empresa_payload())).json()
    for mes in MESES:
        await client.put(
            f"/companies/{empresa['id']}/movements/{mes}",
            json={"receita_bruta": "50000.00", "pro_labore": pro_labore},
        )
    return str(empresa["id"])


async def test_simulacao_persistida_no_trace_com_os_tres_vereditos(
    client: httpx.AsyncClient,
) -> None:
    await login(client, await criar_escritorio_com_usuario())
    company_id = await _empresa(client, "10000.00")
    corrigir = await client.post(f"/companies/{company_id}/simulations", json={"pa": "2026-09"})
    assert corrigir.status_code == 201, corrigir.text
    body = corrigir.json()
    assert body["veredito"] == "corrigir"
    assert body["resultado"]["reforco_12m"] == "60000.00"
    assert "Vale corrigir" in body["texto"]

    nao_forcar = (
        await client.post(
            f"/companies/{company_id}/simulations",
            json={"pa": "2026-09", "inss": "0.30", "irrf": "0.50"},
        )
    ).json()
    assert nao_forcar["veredito"] == "nao_forcar"
    ja = (
        await client.post(
            f"/companies/{company_id}/simulations",
            json={"pa": "2026-09", "meta": "0.28", "fracao_pro_labore": "1"},
        )
    ).json()
    assert ja["veredito"] in ("corrigir", "nao_forcar")  # 20% < 28%

    async with get_owner_sessionmaker()() as session:
        sim = (
            await session.execute(select(Simulation).where(Simulation.id == body["simulation_id"]))
        ).scalar_one()
        trace = (
            await session.execute(select(AgentTrace).where(AgentTrace.id == body["trace_id"]))
        ).scalar_one()
        decisao = (
            await session.execute(
                select(AgentDecision).where(AgentDecision.trace_id == body["trace_id"])
            )
        ).scalar_one()
    assert sim.trace_id == body["trace_id"]
    assert (trace.agente, trace.gatilho, trace.status) == ("consultor", "ficha", "ok")
    assert decisao.dados_json["simulation_id"] == body["simulation_id"]

    historico = (await client.get(f"/companies/{company_id}/simulations")).json()
    assert len(historico) == 3


async def test_ja_na_meta(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    company_id = await _empresa(client, "15000.00")
    body = (
        await client.post(f"/companies/{company_id}/simulations", json={"pa": "2026-09"})
    ).json()
    assert body["veredito"] == "ja_na_meta"


async def test_validacao_de_parametros(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    company_id = await _empresa(client, "10000.00")
    for invalido in (
        {"pa": "2026-09", "meta": "0.20"},
        {"pa": "2026-09", "inss": "1.5"},
        {"pa": "2026-09", "horizonte_meses": 0},
    ):
        assert (
            await client.post(f"/companies/{company_id}/simulations", json=invalido)
        ).status_code == 422
