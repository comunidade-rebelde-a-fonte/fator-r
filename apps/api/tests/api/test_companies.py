import httpx

from tests.factories import criar_escritorio_com_usuario, empresa_payload, login


async def test_cria_e_obtem_empresa_com_cnpj_normalizado(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    response = await client.post(
        "/companies", json=empresa_payload(inicio_atividade="2020-03", qtd_socios=2)
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["cnpj"] == "11222333000181"
    assert body["cnpj_formatado"] == "11.222.333/0001-81"
    assert body["honorario_mensal"] == "450.00"
    assert body["inicio_atividade"] == "2020-03"
    obtida = await client.get(f"/companies/{body['id']}")
    assert obtida.json() == body


async def test_cnpj_invalido_e_recusado(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    response = await client.post("/companies", json=empresa_payload(cnpj="11.222.333/0001-82"))
    assert response.status_code == 422


async def test_cnpj_duplicado_no_mesmo_escritorio_e_recusado(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    assert (await client.post("/companies", json=empresa_payload())).status_code == 201
    duplicada = await client.post("/companies", json=empresa_payload(cnpj="11222333000181"))
    assert duplicada.status_code == 409


async def test_mesmo_cnpj_em_outro_escritorio_e_aceito() -> None:
    from fator_r.main import create_app

    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    for usuario in (a, b):
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            await login(c, usuario)
            assert (await c.post("/companies", json=empresa_payload())).status_code == 201


async def test_filtros_busca_e_desativacao(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    a = (await client.post("/companies", json=empresa_payload(nome="Alfa Serviços"))).json()
    await client.post(
        "/companies",
        json=empresa_payload(
            cnpj="45.723.174/0001-10", nome="Beta Comércio", sujeita_fator_r=False
        ),
    )
    assert (await client.get("/companies?sujeita_fator_r=true")).json()["total"] == 1
    assert (await client.get("/companies?busca=beta")).json()["items"][0]["nome"] == "Beta Comércio"
    assert (await client.get("/companies?busca=45723")).json()["total"] == 1

    desativada = await client.patch(f"/companies/{a['id']}", json={"ativo": False})
    assert desativada.json()["ativo"] is False
    assert (await client.get("/companies?ativo=true")).json()["total"] == 1
    assert (await client.get("/companies")).json()["total"] == 2  # desativar não apaga


async def test_nao_existe_delete_de_empresa(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    empresa = (await client.post("/companies", json=empresa_payload())).json()
    assert (await client.delete(f"/companies/{empresa['id']}")).status_code == 405


async def test_patch_nao_aceita_nulo_em_campo_obrigatorio(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    empresa = (await client.post("/companies", json=empresa_payload())).json()
    response = await client.patch(f"/companies/{empresa['id']}", json={"nome": None})
    assert response.status_code == 422
