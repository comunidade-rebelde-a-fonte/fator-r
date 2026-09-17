from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import update

from fator_r.core.db import get_owner_sessionmaker
from fator_r.core.settings import get_settings
from fator_r.repositories.orm import UserSession
from tests.factories import criar_escritorio_com_usuario

COOKIE = get_settings().session_cookie_name


async def _login(client: httpx.AsyncClient, email: str, senha: str) -> httpx.Response:
    return await client.post("/auth/login", json={"email": email, "senha": senha})


async def test_login_valido_define_cookie_httponly_e_me_responde(
    client: httpx.AsyncClient,
) -> None:
    u = await criar_escritorio_com_usuario()
    response = await _login(client, u.email, u.senha)
    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["firm_id"] == str(u.firm_id)


async def test_login_email_case_insensitive(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    response = await _login(client, u.email.upper(), u.senha)
    assert response.status_code == 200


async def test_senha_errada_e_email_inexistente_tem_mesma_resposta(
    client: httpx.AsyncClient,
) -> None:
    u = await criar_escritorio_com_usuario()
    errada = await _login(client, u.email, "senha-errada")
    inexistente = await _login(client, "ninguem@escritorio-a.com.br", "senha-errada")
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json()
    assert COOKIE not in client.cookies


async def test_usuario_inativo_nao_entra(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario(ativo=False)
    response = await _login(client, u.email, u.senha)
    assert response.status_code == 401


async def test_sessao_expirada_devolve_401(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await _login(client, u.email, u.senha)
    async with get_owner_sessionmaker()() as session:
        await session.execute(
            update(UserSession).values(expira_em=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    assert (await client.get("/auth/me")).status_code == 401


async def test_logout_invalida_o_token(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await _login(client, u.email, u.senha)
    token = client.cookies[COOKIE]
    assert (await client.post("/auth/logout")).status_code == 204
    # Reusar o token antigo não funciona mais.
    client.cookies.set(COOKIE, token)
    assert (await client.get("/auth/me")).status_code == 401


async def test_rota_protegida_sem_cookie_devolve_401(client: httpx.AsyncClient) -> None:
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.post("/auth/logout")).status_code == 401


async def test_cookie_forjado_devolve_401(client: httpx.AsyncClient) -> None:
    client.cookies.set(COOKIE, "token-inventado")
    assert (await client.get("/auth/me")).status_code == 401


async def test_rate_limit_bloqueia_apos_tentativas(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    limite = get_settings().login_rate_limit_attempts
    for _ in range(limite):
        assert (await _login(client, u.email, "errada")).status_code == 401
    bloqueado = await _login(client, u.email, u.senha)
    assert bloqueado.status_code == 429
