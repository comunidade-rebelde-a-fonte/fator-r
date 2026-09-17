import httpx

from tests.factories import criar_escritorio_com_usuario, empresa_payload, login

MESES = [f"2025-{m:02d}" for m in range(9, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]


async def _empresa_com_serie(client: httpx.AsyncClient, pro_labore: str = "15000") -> str:
    await login(client, await criar_escritorio_com_usuario())
    empresa = (await client.post("/companies", json=empresa_payload())).json()
    for mes in MESES:
        await client.put(
            f"/companies/{empresa['id']}/movements/{mes}",
            json={"receita_bruta": "50000.00", "pro_labore": pro_labore},
        )
    return str(empresa["id"])


async def test_fator_r_do_pa_com_janela_e_tabela(client: httpx.AsyncClient) -> None:
    company_id = await _empresa_com_serie(client)
    body = (await client.get(f"/companies/{company_id}/fator-r?pa=2026-09")).json()
    assert body["status"] == "ok"
    assert (body["janela_inicio"], body["janela_fim"]) == ("2025-09", "2026-08")
    assert body["rbt12"] == "600000.00"
    assert body["fs12"] == "180000.00"
    assert body["anexo"] == "III"
    assert body["semaforo"] == "verde"
    assert body["meses_faltantes"] == []
    assert body["tabela_vigencia_inicio"] == "2018-01-01"
    assert body["cpp_integra_fs12"] is False  # factory usa política sem CPP


async def test_trocar_pa_move_a_janela(client: httpx.AsyncClient) -> None:
    company_id = await _empresa_com_serie(client)
    seguinte = (await client.get(f"/companies/{company_id}/fator-r?pa=2026-10")).json()
    assert (seguinte["janela_inicio"], seguinte["janela_fim"]) == ("2025-10", "2026-09")
    assert seguinte["meses_faltantes"] == ["2026-09"]
    assert seguinte["rbt12"] == "550000.00"


async def test_rbt12_zero_sem_anexo(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    empresa = (await client.post("/companies", json=empresa_payload())).json()
    body = (await client.get(f"/companies/{empresa['id']}/fator-r?pa=2026-09")).json()
    assert body["status"] == "dados_insuficientes"
    assert body["motivo"] == "rbt12_zero"
    assert body["anexo"] is None
    assert body["aliquota_efetiva_iii"] is None


async def test_pa_invalido_e_sem_tabela(client: httpx.AsyncClient) -> None:
    company_id = await _empresa_com_serie(client)
    assert (await client.get(f"/companies/{company_id}/fator-r?pa=2026-13")).status_code == 422
    antes_2018 = await client.get(f"/companies/{company_id}/fator-r?pa=2017-06")
    assert antes_2018.status_code == 422
