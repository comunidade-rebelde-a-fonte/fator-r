"""Cadastro de empresa pelo extrato (M8, T-803/T-804): AT-001 a AT-008, AT-011 e AT-014."""

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select

from fator_r.core.db import get_owner_sessionmaker
from fator_r.parsing.pgdas import CAMPOS
from fator_r.repositories import companies as repo_companies
from fator_r.repositories.orm import (
    AgentDecision,
    AgentTrace,
    Company,
    EvalGold,
    MonthlyMovement,
    PgdasDocument,
)
from tests.factories import criar_escritorio_com_usuario, empresa_payload, login

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "pgdas"
EXTRATO = (FIXTURES / "txt_padrao" / "documento.txt").read_bytes()  # PA 09/2026, RPA 50.000,00
CNPJ = "11222333000181"
CNPJ_FORMATADO = "11.222.333/0001-81"
DISCLAIMER = "O PGDAS-D da Receita Federal prevalece."


async def _enviar(
    client: httpx.AsyncClient, conteudo: bytes = EXTRATO, nome: str = "extrato.txt"
) -> dict[str, Any]:
    mime = "application/pdf" if nome.endswith(".pdf") else "text/plain"
    response = await client.post("/inbox/pgdas", files={"arquivo": (nome, conteudo, mime)})
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


def _corpo(cnpj: str = CNPJ_FORMATADO, **extra: object) -> dict[str, object]:
    return {"nome": "CLINICA EXEMPLO LTDA", "cnpj": cnpj, "sujeita_fator_r": True, **extra}


async def _cadastrar(
    client: httpx.AsyncClient, document_id: object, corpo: dict[str, object] | None = None
) -> httpx.Response:
    return await client.post(f"/inbox/{document_id}/cadastrar-empresa", json=corpo or _corpo())


async def _contar(modelo: Any, *condicoes: Any) -> int:
    async with get_owner_sessionmaker()() as session:
        return int(
            (
                await session.execute(select(func.count()).select_from(modelo).where(*condicoes))
            ).scalar_one()
        )


async def _documento(document_id: object) -> PgdasDocument:
    async with get_owner_sessionmaker()() as session:
        return (
            await session.execute(
                select(PgdasDocument).where(PgdasDocument.id == uuid.UUID(str(document_id)))
            )
        ).scalar_one()


async def _movimentos(company_id: object) -> list[MonthlyMovement]:
    async with get_owner_sessionmaker()() as session:
        return list(
            (
                await session.execute(
                    select(MonthlyMovement).where(
                        MonthlyMovement.company_id == uuid.UUID(str(company_id))
                    )
                )
            ).scalars()
        )


async def test_sugestao_so_para_cnpj_valido_fora_da_carteira(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client)
    assert doc["status"] == "needs_review"
    assert doc["motivo"] == "cnpj_nao_encontrado"
    assert doc["sugestao_cadastro"] == {
        "cnpj": CNPJ,
        "cnpj_formatado": CNPJ_FORMATADO,
        "nome_empresarial": "CLINICA EXEMPLO LTDA",
        "sujeita_fator_r": True,
        "inicio_atividade": "2019-03",
    }
    listagem = (await client.get("/inbox")).json()["items"]
    assert listagem[0]["sugestao_cadastro"]["cnpj"] == CNPJ
    assert (await client.get(f"/inbox/{doc['id']}")).json()["sugestao_cadastro"] is not None


@pytest.mark.parametrize("fixture", ["txt_sem_cnpj", "txt_cnpj_dv_invalido"])
async def test_sem_cnpj_valido_nao_ha_sugestao_e_cadastro_e_recusado(
    client: httpx.AsyncClient, fixture: str
) -> None:
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client, (FIXTURES / fixture / "documento.txt").read_bytes())
    assert doc["status"] == "needs_review"
    assert doc["sugestao_cadastro"] is None
    response = await _cadastrar(client, doc["id"])
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "extrato_sem_cnpj_valido"
    assert await _contar(Company) == 0


async def test_cadastro_cria_empresa_vincula_e_cria_receita_do_pa(
    client: httpx.AsyncClient,
) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    doc = await _enviar(client)

    response = await _cadastrar(client, doc["id"], _corpo(pacote="monitoramento"))
    assert response.status_code == 201, response.text
    corpo = response.json()
    empresa, documento = corpo["empresa"], corpo["documento"]
    assert empresa["cnpj"] == CNPJ
    assert empresa["nome"] == "CLINICA EXEMPLO LTDA"
    assert empresa["pacote"] == "monitoramento"
    assert documento["status"] == "linked"
    assert documento["company_id"] == empresa["id"]
    assert documento["sugestao_cadastro"] is None
    assert documento["trace_id"] != doc["trace_id"]
    assert "cadastrada a partir do extrato" in documento["texto_agente"]
    assert DISCLAIMER in documento["texto_agente"]

    movimentos = await _movimentos(empresa["id"])
    assert len(movimentos) == 1
    movimento = movimentos[0]
    assert movimento.competencia == date(2026, 9, 1)
    assert movimento.receita_bruta == Decimal("50000.00")
    assert movimento.origem == "pgdas"
    assert movimento.pro_labore == movimento.salarios == movimento.cpp == movimento.fgts == 0

    ids = [e["id"] for e in (await client.get("/companies")).json()["items"]]
    assert ids == [empresa["id"]]


async def test_trace_e_decisao_do_cadastro(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    doc = await _enviar(client)
    corpo = (await _cadastrar(client, doc["id"])).json()
    trace_id = corpo["documento"]["trace_id"]

    async with get_owner_sessionmaker()() as session:
        trace = (
            await session.execute(select(AgentTrace).where(AgentTrace.id == trace_id))
        ).scalar_one()
        decisao = (
            await session.execute(select(AgentDecision).where(AgentDecision.trace_id == trace_id))
        ).scalar_one()
        campos_ouro = set(
            (
                await session.execute(select(EvalGold.campo).where(EvalGold.trace_id == trace_id))
            ).scalars()
        )
    assert trace.gatilho == "cadastro_pelo_extrato"
    assert trace.agente == "parser_pgdas"
    assert trace.status == "ok"
    assert str(trace.company_id) == corpo["empresa"]["id"]
    assert trace.firm_id == u.firm_id
    assert decisao.tipo == "pgdas_cadastro_pelo_extrato"
    dados = decisao.dados_json
    assert dados["company_id"] == corpo["empresa"]["id"]
    assert dados["movimento"] == "criado"
    assert dados["competencia"] == "2026-09"
    assert dados["empresa_criada"] is True
    assert dados["nome_igual_extrato"] is True
    assert dados["sujeita_igual_sugestao"] is True
    assert "nome" not in dados  # só booleanos sobre o nome entram na decisão
    # AT-014: identificação não entra na nota ouro.
    assert campos_ouro <= set(CAMPOS) | {"acerto"}


async def test_nome_e_enquadramento_editados_ficam_registrados(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client)
    corpo = (
        await _cadastrar(
            client, doc["id"], _corpo(nome="Clínica Exemplo (nome fantasia)", sujeita_fator_r=False)
        )
    ).json()
    async with get_owner_sessionmaker()() as session:
        dados = (
            await session.execute(
                select(AgentDecision.dados_json).where(
                    AgentDecision.trace_id == corpo["documento"]["trace_id"]
                )
            )
        ).scalar_one()
    assert corpo["empresa"]["nome"] == "Clínica Exemplo (nome fantasia)"
    assert dados["nome_igual_extrato"] is False
    assert dados["sujeita_igual_sugestao"] is False


async def test_cnpj_divergente_e_recusado_sem_escrita(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client)
    response = await _cadastrar(client, doc["id"], _corpo(cnpj="04.252.011/0001-10"))
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "cnpj_divergente"
    assert await _contar(Company) == 0
    assert (await _documento(doc["id"])).status == "needs_review"
    assert await _contar(AgentTrace, AgentTrace.gatilho == "cadastro_pelo_extrato") == 0


async def test_cnpj_invalido_no_corpo_e_422_de_validacao(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client)
    response = await _cadastrar(client, doc["id"], _corpo(cnpj="11.222.333/0001-82"))
    assert response.status_code == 422
    assert await _contar(Company) == 0


async def test_documento_em_estado_final_e_recusado(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client)
    assert (await _cadastrar(client, doc["id"])).status_code == 201
    de_novo = await _cadastrar(client, doc["id"])
    assert de_novo.status_code == 409
    assert de_novo.json()["detail"]["codigo"] == "documento_em_estado_invalido"

    outro = await _enviar(
        client, EXTRATO.replace(CNPJ_FORMATADO.encode(), b"04.252.011/0001-10"), "outro.txt"
    )
    await client.post(f"/inbox/{outro['id']}/reject", json={"motivo": "extrato duplicado"})
    rejeitado = await _cadastrar(client, outro["id"], _corpo(cnpj="04.252.011/0001-10"))
    assert rejeitado.status_code == 409
    assert await _contar(Company) == 1


async def test_cnpj_ja_cadastrado_devolve_company_id_e_permite_vincular(
    client: httpx.AsyncClient,
) -> None:
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client)
    existente = (await client.post("/companies", json=empresa_payload(cnpj=CNPJ_FORMATADO))).json()

    response = await _cadastrar(client, doc["id"])
    assert response.status_code == 409
    detalhe = response.json()["detail"]
    assert detalhe["codigo"] == "cnpj_ja_cadastrado"
    assert detalhe["company_id"] == existente["id"]
    assert await _contar(Company) == 1
    assert (await _documento(doc["id"])).status == "needs_review"
    assert await _contar(AgentTrace, AgentTrace.gatilho == "cadastro_pelo_extrato") == 0

    vinculado = await client.post(f"/inbox/{doc['id']}/link", json={"company_id": existente["id"]})
    assert vinculado.json()["status"] == "linked"


async def test_corrida_no_cadastro_desfaz_tudo_e_deixa_trace_de_erro(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Outro analista cadastra o CNPJ entre a checagem e o INSERT: o UNIQUE barra e nada fica."""
    await login(client, await criar_escritorio_com_usuario())
    doc = await _enviar(client)
    existente = (await client.post("/companies", json=empresa_payload(cnpj=CNPJ_FORMATADO))).json()

    original = repo_companies.obter_por_cnpj
    chamadas = {"n": 0}

    async def checagem_sem_ver_o_concorrente(*args: Any, **kwargs: Any) -> Company | None:
        chamadas["n"] += 1
        return None if chamadas["n"] == 1 else await original(*args, **kwargs)

    monkeypatch.setattr(repo_companies, "obter_por_cnpj", checagem_sem_ver_o_concorrente)
    response = await _cadastrar(client, doc["id"])

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == {
        "codigo": "cnpj_ja_cadastrado",
        "mensagem": "CNPJ já cadastrado neste escritório",
        "company_id": existente["id"],
    }
    assert await _contar(Company) == 1
    documento = await _documento(doc["id"])
    assert documento.status == "needs_review"
    assert documento.company_id is None
    assert await _movimentos(existente["id"]) == []
    async with get_owner_sessionmaker()() as session:
        traces = list(
            (
                await session.execute(
                    select(AgentTrace).where(AgentTrace.gatilho == "cadastro_pelo_extrato")
                )
            ).scalars()
        )
    assert [(t.status, t.saida_json.get("erro")) for t in traces] == [("error", "CnpjDuplicado")]


async def test_documento_de_outro_escritorio_da_404(client: httpx.AsyncClient) -> None:
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    await login(client, b)
    doc_b = await _enviar(client)
    await client.post("/auth/logout")

    await login(client, await criar_escritorio_com_usuario("a@escritorio-a.com.br"))
    response = await _cadastrar(client, doc_b["id"])
    assert response.status_code == 404
    assert await _contar(Company) == 0
    assert (await _documento(doc_b["id"])).status == "needs_review"


async def test_sem_pa_vincula_sem_criar_receita(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    sem_pa = b"\n".join(x for x in EXTRATO.splitlines() if b"(PA)" not in x.split(b":")[0])
    doc = await _enviar(client, sem_pa, "sem-pa.txt")
    assert doc["campos"]["pa"] is None
    assert doc["sugestao_cadastro"] is not None

    corpo = (await _cadastrar(client, doc["id"])).json()
    assert corpo["documento"]["status"] == "linked"
    assert "nenhum movimento foi criado" in corpo["documento"]["texto_agente"]
    assert await _movimentos(corpo["empresa"]["id"]) == []


def _janela_2026_08() -> list[date]:
    return [date(2025, 8, 1) if m == 0 else date(2025 + (7 + m) // 12, (7 + m) % 12 + 1, 1)
            for m in range(12)]  # fmt: skip


async def _decisao(trace_id: str) -> dict[str, Any]:
    async with get_owner_sessionmaker()() as session:
        return dict(
            (
                await session.execute(
                    select(AgentDecision.dados_json).where(AgentDecision.trace_id == trace_id)
                )
            ).scalar_one()
        )


async def test_pdf_declaratorio_ponta_a_ponta(client: httpx.AsyncClient) -> None:
    """AT-001 com o PDF declaratório: PA 08/2026 + os 12 meses anteriores (receita e folha)."""
    await login(client, await criar_escritorio_com_usuario())
    pdf = (FIXTURES / "pdf_declaratorio_fator_r_abaixo_28" / "documento.pdf").read_bytes()
    doc = await _enviar(client, pdf, "declaracao.pdf")
    assert doc["campos"]["pa"] == "2026-08"
    sugestao = doc["sugestao_cadastro"]
    assert sugestao == {
        "cnpj": "12345678000195",
        "cnpj_formatado": "12.345.678/0001-95",
        "nome_empresarial": "EMPRESA DE SERVICOS A - ANONIMIZADA",
        "sujeita_fator_r": True,
        "inicio_atividade": "2019-03",
    }
    corpo = (
        await _cadastrar(
            client,
            doc["id"],
            {
                "nome": sugestao["nome_empresarial"],
                "cnpj": sugestao["cnpj_formatado"],
                "sujeita_fator_r": True,
                "inicio_atividade": sugestao["inicio_atividade"],
            },
        )
    ).json()
    assert corpo["empresa"]["inicio_atividade"] == "2019-03"
    assert "12 meses anteriores lançados" in corpo["documento"]["texto_agente"]
    assert "Nenhum lançamento existente foi alterado" in corpo["documento"]["texto_agente"]

    movimentos = {m.competencia: m for m in await _movimentos(corpo["empresa"]["id"])}
    assert sorted(movimentos) == [*_janela_2026_08(), date(2026, 8, 1)]
    for competencia in _janela_2026_08():
        m = movimentos[competencia]
        assert (m.receita_bruta, m.salarios) == (Decimal("10000.00"), Decimal("2000.00"))
        assert m.pro_labore == m.cpp == m.fgts == 0
        assert m.origem == "pgdas"
        assert "total declarado no PGDAS-D" in (m.observacao or "")
    pa = movimentos[date(2026, 8, 1)]
    assert (pa.receita_bruta, pa.salarios) == (Decimal("10000.00"), Decimal("0.00"))

    decisao = await _decisao(corpo["documento"]["trace_id"])
    assert decisao["meses_anteriores"] == {
        "criados": 12,
        "existentes": 0,
        "com_folha": True,
        "motivo": None,
    }

    fator = (
        await client.get(f"/companies/{corpo['empresa']['id']}/fator-r", params={"pa": "2026-08"})
    ).json()
    # FS12 = folha declarada (a política de CPP não soma nada: CPP gravada é zero).
    assert (Decimal(fator["rbt12"]), Decimal(fator["fs12"])) == (
        Decimal("120000.00"),
        Decimal("24000.00"),
    )
    assert fator["anexo"] == "V"


async def test_comercio_importa_receitas_com_folha_zero(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    pdf = (FIXTURES / "pdf_declaratorio_comercio_sem_fator_r" / "documento.pdf").read_bytes()
    doc = await _enviar(client, pdf, "declaracao.pdf")
    corpo = (
        await _cadastrar(
            client,
            doc["id"],
            {"nome": "Comércio B", "cnpj": "23.456.789/0001-95", "sujeita_fator_r": False},
        )
    ).json()
    movimentos = await _movimentos(corpo["empresa"]["id"])
    assert len(movimentos) == 13
    assert {m.salarios for m in movimentos} == {Decimal("0.00")}
    assert {m.receita_bruta for m in movimentos} == {Decimal("12000.00")}
    anterior = next(m for m in movimentos if m.competencia == date(2025, 8, 1))
    assert "folha não se aplica" in (anterior.observacao or "")
    decisao = await _decisao(corpo["documento"]["trace_id"])
    assert decisao["meses_anteriores"]["com_folha"] is False
    assert decisao["meses_anteriores"]["criados"] == 12


async def test_pdf_declaratorio_de_empresa_ja_cadastrada_vincula_sozinho(
    client: httpx.AsyncClient,
) -> None:
    """AT-002: CNPJ conhecido vincula sem formulário; competência já lançada não é alterada."""
    await login(client, await criar_escritorio_com_usuario())
    empresa = (
        await client.post("/companies", json=empresa_payload(cnpj="45.678.901/0001-75"))
    ).json()
    manual = await client.put(
        f"/companies/{empresa['id']}/movements/2026-03",
        json={"receita_bruta": "999.00", "pro_labore": "5000.00"},
    )
    assert manual.status_code in (200, 201), manual.text

    pdf = (FIXTURES / "pdf_declaratorio_fator_r_acima_28" / "documento.pdf").read_bytes()
    doc = await _enviar(client, pdf, "declaracao.pdf")
    assert doc["status"] == "linked"
    assert Decimal(doc["confianca"]) == Decimal("1.0000")
    assert doc["sugestao_cadastro"] is None

    movimentos = {m.competencia: m for m in await _movimentos(empresa["id"])}
    assert len(movimentos) == 13
    preservado = movimentos[date(2026, 3, 1)]
    assert (preservado.origem, preservado.receita_bruta, preservado.pro_labore) == (
        "manual",
        Decimal("999.00"),
        Decimal("5000.00"),
    )
    assert movimentos[date(2026, 2, 1)].salarios == Decimal("9200.00")
    decisao = await _decisao(doc["trace_id"])
    assert decisao["meses_anteriores"] == {
        "criados": 11,
        "existentes": 1,
        "com_folha": True,
        "motivo": None,
    }


async def test_tabela_que_nao_soma_o_total_nao_e_gravada(client: httpx.AsyncClient) -> None:
    from fator_r.core.uploads import detectar_mime
    from fator_r.parsing.texto import extrair_texto

    await login(client, await criar_escritorio_com_usuario())
    pdf = (FIXTURES / "pdf_declaratorio_fator_r_abaixo_28" / "documento.pdf").read_bytes()
    texto = extrair_texto(pdf, detectar_mime(pdf)).texto
    adulterado = texto.replace("07/2026 10.000,00", "07/2026 11.000,00", 1)
    assert adulterado != texto
    doc = await _enviar(client, adulterado.encode(), "declaracao.txt")
    corpo = (
        await _cadastrar(
            client,
            doc["id"],
            {"nome": "Serviços A", "cnpj": "12.345.678/0001-95", "sujeita_fator_r": True},
        )
    ).json()
    movimentos = await _movimentos(corpo["empresa"]["id"])
    assert [m.competencia for m in movimentos] == [date(2026, 8, 1)]  # só o PA
    assert "não somam o RBT12 declarado" in corpo["documento"]["texto_agente"]
    decisao = await _decisao(corpo["documento"]["trace_id"])
    assert decisao["meses_anteriores"]["motivo"] == "receitas_anteriores_nao_conferem"
