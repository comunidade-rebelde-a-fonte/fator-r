import statistics
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
from sqlalchemy import event

from fator_r.core import db
from fator_r.core.security import hash_password
from fator_r.repositories.orm import User
from fator_r.seed_carga import gerar_carga
from tests.factories import (
    SENHA_PADRAO,
    UsuarioCriado,
    criar_escritorio_com_usuario,
    empresa_payload,
    login,
)

MESES = [f"2025-{m:02d}" for m in range(9, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]


async def _lancar_serie(
    client: httpx.AsyncClient, company_id: str, receita: str, pro_labore: str
) -> None:
    for mes in MESES:
        await client.put(
            f"/companies/{company_id}/movements/{mes}",
            json={"receita_bruta": receita, "pro_labore": pro_labore},
        )


@contextmanager
def contar_queries() -> Iterator[list[str]]:
    statements: list[str] = []

    def before(conn: Any, cursor: Any, statement: str, *args: Any) -> None:
        if "set_config" not in statement:
            statements.append(statement)

    engine = db.get_engine().sync_engine
    event.listen(engine, "before_cursor_execute", before)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before)


async def test_carteira_filtra_ordena_e_soma(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    criar = lambda **kw: client.post("/companies", json=empresa_payload(**kw))  # noqa: E731
    vermelha = (await criar(nome="Vermelha", honorario_mensal="100.00")).json()
    verde = (await criar(nome="Verde", cnpj="45.723.174/0001-10", honorario_mensal="200.00")).json()
    inativa = (await criar(nome="Inativa", cnpj="04.252.011/0001-10", ativo=False)).json()
    comercio = (
        await criar(nome="Comércio", cnpj="33.000.167/0001-01", sujeita_fator_r=False)
    ).json()
    await _lancar_serie(client, vermelha["id"], "50000.00", "5000.00")
    await _lancar_serie(client, verde["id"], "50000.00", "15000.00")
    await _lancar_serie(client, inativa["id"], "50000.00", "1000.00")

    body = (await client.get("/portfolio?pa=2026-09")).json()
    nomes = [linha["nome"] for linha in body["linhas"]]
    assert nomes == ["Vermelha", "Verde"]
    assert comercio["nome"] not in nomes
    assert body["linhas"][0]["semaforo"] == "vermelho"
    assert body["linhas"][0]["acao_texto"] == "reunião de correção"
    assert body["kpis"]["monitoradas"] == 2
    assert body["kpis"]["no_v"] == 1
    assert body["kpis"]["seguras"] == 1
    assert body["kpis"]["honorarios_pacotes"] == "300.00"
    assert body["kpis"]["economia_em_jogo"] == body["linhas"][0]["economia_12m"]


async def test_carteira_sem_n_mais_1(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    cnpjs = ["11.222.333/0001-81", "45.723.174/0001-10", "04.252.011/0001-10", "33.000.167/0001-01"]
    ids = [
        (await client.post("/companies", json=empresa_payload(cnpj=c, nome=c))).json()["id"]
        for c in cnpjs
    ]
    await _lancar_serie(client, ids[0], "1000.00", "100.00")
    with contar_queries() as com_uma:
        await client.get("/portfolio?pa=2026-09")
    for company_id in ids[1:]:
        await _lancar_serie(client, company_id, "1000.00", "100.00")
    with contar_queries() as com_quatro:
        await client.get("/portfolio?pa=2026-09")
    consultas = [s for s in com_quatro if s.lstrip().upper().startswith("SELECT")]
    assert len(com_uma) == len(com_quatro)
    assert len(consultas) <= 5  # sessão + escritório + empresas + movimentos + tabelas


async def _usuario_do_escritorio_de_carga() -> UsuarioCriado:
    async with db.get_owner_sessionmaker()() as session:
        from datetime import date

        firm_id = await gerar_carga(session, ultimo_mes=date(2026, 8, 1))
        session.add(
            User(
                firm_id=firm_id,
                email="carga@carga.com.br",
                senha_hash=hash_password(SENHA_PADRAO),
                nome="Carga",
            )
        )
        await session.commit()
    return UsuarioCriado(firm_id, firm_id, "carga@carga.com.br", SENHA_PADRAO)


@pytest.mark.perf
async def test_carteira_200_empresas_em_menos_de_1s(client: httpx.AsyncClient) -> None:
    usuario = await _usuario_do_escritorio_de_carga()
    await login(client, usuario)
    await client.get("/portfolio?pa=2026-09")  # aquece
    tempos = []
    for _ in range(5):
        inicio = time.perf_counter()
        response = await client.get("/portfolio?pa=2026-09")
        tempos.append(time.perf_counter() - inicio)
        assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["monitoradas"] == 200
    assert {linha["semaforo"] for linha in body["linhas"]} == {"vermelho", "amarelo", "verde"}
    mediana = statistics.median(tempos)
    print(
        f"\nCarteira 200 empresas: mediana {mediana * 1000:.0f} ms "
        f"(tempos: {[round(t * 1000) for t in tempos]})"
    )
    assert mediana < 1.0
