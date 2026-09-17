import httpx
from sqlalchemy import func, select

from fator_r.core.db import get_owner_sessionmaker
from fator_r.repositories.orm import MonthlyMovement
from tests.factories import criar_escritorio_com_usuario, empresa_payload, login


async def _empresa(client: httpx.AsyncClient) -> str:
    await login(client, await criar_escritorio_com_usuario())
    return str((await client.post("/companies", json=empresa_payload())).json()["id"])


async def test_lanca_movimento_e_calcula_folha(client: httpx.AsyncClient) -> None:
    company_id = await _empresa(client)
    response = await client.put(
        f"/companies/{company_id}/movements/2026-08",
        json={
            "receita_bruta": "50000.00",
            "pro_labore": "5000.00",
            "salarios": "7000.00",
            "cpp": "2400.00",
            "fgts": "560.00",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["competencia"] == "2026-08"
    assert body["folha_mes"] == "14960.00"
    assert body["origem"] == "manual"


async def test_upsert_nao_duplica_linha(client: httpx.AsyncClient) -> None:
    company_id = await _empresa(client)
    url = f"/companies/{company_id}/movements/2026-08"
    await client.put(url, json={"receita_bruta": "1000.00"})
    segundo = await client.put(url, json={"receita_bruta": "2000.00", "observacao": "corrigido"})
    assert segundo.json()["receita_bruta"] == "2000.00"
    async with get_owner_sessionmaker()() as session:
        total = (
            await session.execute(select(func.count()).select_from(MonthlyMovement))
        ).scalar_one()
    assert total == 1


async def test_valores_negativos_e_competencia_invalida(client: httpx.AsyncClient) -> None:
    company_id = await _empresa(client)
    negativo = await client.put(
        f"/companies/{company_id}/movements/2026-08", json={"receita_bruta": "-1.00"}
    )
    assert negativo.status_code == 422
    mes_invalido = await client.put(f"/companies/{company_id}/movements/2026-13", json={})
    assert mes_invalido.status_code == 422


async def test_lista_por_intervalo(client: httpx.AsyncClient) -> None:
    company_id = await _empresa(client)
    for mes in ("2026-01", "2026-02", "2026-03", "2026-04"):
        await client.put(f"/companies/{company_id}/movements/{mes}", json={"receita_bruta": "1.00"})
    response = await client.get(f"/companies/{company_id}/movements?de=2026-02&ate=2026-03")
    assert [m["competencia"] for m in response.json()] == ["2026-02", "2026-03"]
