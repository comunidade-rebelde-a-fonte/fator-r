import httpx

from fator_r.core.db import firm_session
from fator_r.tracing import scores
from fator_r.tracing.scores import ResultadoCampoOuro
from tests.factories import criar_escritorio_com_usuario, login


async def _echo(client: httpx.AsyncClient, mensagem: str = "oi") -> str:
    return str(
        (await client.post("/agents/echo/run", json={"mensagem": mensagem})).json()["trace_id"]
    )


async def test_resumo_lista_e_detalhe(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    t1 = await _echo(client)
    t2 = await _echo(client, "segunda")
    async with firm_session(u.firm_id) as session:
        await scores.gold(
            session,
            u.firm_id,
            t1,
            [
                ResultadoCampoOuro("cnpj", "1", "1", True, "ok"),
                ResultadoCampoOuro("rbt12", "1", "2", False, "erro"),
                ResultadoCampoOuro("fs12", None, None, None, "ouro_indisponivel"),
            ],
        )
    nota = await client.post(f"/traces/{t1}/human-eval", json={"nota": "acerto"})
    assert nota.status_code == 201

    resumo = (await client.get("/observability/summary")).json()
    assert resumo["corridas_total"] == 2
    assert resumo["corridas_24h"] == 2
    assert resumo["pendencias_sem_nota"] == 1
    assert resumo["acerto_ouro"] == "0.5"
    assert resumo["acerto_humano"] == "1"
    assert resumo["por_agente"][0]["agente"] == "echo"
    assert resumo["por_agente"][0]["volume"] == 2
    assert resumo["custo_llm_30d"] is None  # Langfuse indisponível nos testes unitários

    lista = (await client.get("/traces?agente=echo")).json()
    assert lista["total"] == 2
    sem_nota = (await client.get("/traces?sem_nota=true")).json()
    assert [t["id"] for t in sem_nota["items"]] == [t2]

    detalhe = (await client.get(f"/traces/{t1}")).json()
    assert detalhe["trace"]["tem_nota_humana"] is True
    assert detalhe["decisao"] == {"intencao": "eco", "tamanho": 2}
    assert detalhe["spans_indisponiveis"] is True
    assert {e["campo"] for e in detalhe["evals_ouro"]} == {"cnpj", "rbt12", "fs12"}
    assert detalhe["evals_humanas"][0]["nota"] == "acerto"
    assert detalhe["langfuse_url"].endswith(f"/traces/{t1}")


async def test_nota_erro_sem_comentario_e_recusada(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    trace_id = await _echo(client)
    sem = await client.post(f"/traces/{trace_id}/human-eval", json={"nota": "erro"})
    assert sem.status_code == 422
    vazio = await client.post(
        f"/traces/{trace_id}/human-eval", json={"nota": "erro", "comentario": "  "}
    )
    assert vazio.status_code == 422
    com = await client.post(
        f"/traces/{trace_id}/human-eval", json={"nota": "erro", "comentario": "CNPJ errado"}
    )
    assert com.status_code == 201


async def test_trace_inexistente_e_id_invalido(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    assert (await client.get(f"/traces/{'a' * 32}")).status_code == 404
    assert (await client.get("/traces/nao-e-hex")).status_code == 422
