"""Endurecimento do M7 (T-703): Origin, headers, arquivo órfão e FKs compostas."""

from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from fator_r.agents import parser_pgdas
from fator_r.core.db import firm_session, get_owner_sessionmaker
from fator_r.core.settings import get_settings
from tests.factories import criar_escritorio_com_usuario, login


async def test_origin_de_outro_site_e_recusado_em_metodo_inseguro(
    client: httpx.AsyncClient,
) -> None:
    u = await criar_escritorio_com_usuario()
    resposta = await client.post(
        "/auth/login",
        json={"email": u.email, "senha": u.senha},
        headers={"origin": "https://atacante.example"},
    )
    assert resposta.status_code == 403
    ok = await client.post(
        "/auth/login",
        json={"email": u.email, "senha": u.senha},
        headers={"origin": get_settings().cors_origins[0]},
    )
    assert ok.status_code == 200


async def test_cross_site_sem_origin_valida_e_recusado(client: httpx.AsyncClient) -> None:
    resposta = await client.post("/companies", json={}, headers={"sec-fetch-site": "cross-site"})
    assert resposta.status_code == 403


async def test_headers_de_seguranca(client: httpx.AsyncClient) -> None:
    resposta = await client.get("/health")
    for header, valor in (
        ("x-content-type-options", "nosniff"),
        ("x-frame-options", "DENY"),
        ("referrer-policy", "no-referrer"),
    ):
        assert resposta.headers[header] == valor
    assert "default-src 'none'" in resposta.headers["content-security-policy"]


async def test_falha_no_agente_nao_deixa_arquivo_orfao(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)

    async def quebra(*_: object, **__: object) -> None:
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(parser_pgdas, "receber_documento", quebra)
    with pytest.raises(RuntimeError):
        await client.post(
            "/inbox/pgdas", files={"arquivo": ("x.txt", b"PA: 09/2026\n", "text/plain")}
        )
    pasta = Path(get_settings().upload_dir) / str(u.firm_id)
    assert not pasta.exists() or list(pasta.iterdir()) == []


async def test_fk_composta_impede_decisao_ligada_a_trace_de_outro_escritorio() -> None:
    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    async with get_owner_sessionmaker()() as session:
        await session.execute(
            text(
                "INSERT INTO agent_traces (id, firm_id, agente, gatilho, status) "
                "VALUES (:id, :f, 'x', 'y', 'ok')"
            ),
            {"id": "b" * 32, "f": b.firm_id},
        )
        await session.commit()
    async with firm_session(a.firm_id) as session:
        with pytest.raises(IntegrityError, match="fk_agent_decisions_trace_firm"):
            await session.execute(
                text(
                    "INSERT INTO agent_decisions (firm_id, trace_id, agente, tipo, dados_json) "
                    "VALUES (:f, :t, 'x', 'y', '{}')"
                ),
                {"f": a.firm_id, "t": "b" * 32},
            )


async def test_funcao_de_falhas_nao_expoe_conteudo() -> None:
    async with get_owner_sessionmaker()() as session:
        colunas = (
            await session.execute(
                text(
                    "SELECT pg_get_function_result("
                    "'tracing_traces_com_falha(integer)'::regprocedure)"
                )
            )
        ).scalar_one()
    assert "entrada_json" not in colunas
    assert "decisao_json" not in colunas
