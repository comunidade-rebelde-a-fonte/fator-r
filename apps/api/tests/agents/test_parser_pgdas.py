"""Agente parser_pgdas (T-509..T-512): vínculo, escrita de receita, ouro e ações manuais."""

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import select, update

from fator_r.core.competencia import somar_meses
from fator_r.core.db import get_owner_sessionmaker
from fator_r.repositories.orm import (
    AgentDecision,
    AgentTrace,
    Company,
    EvalGold,
    Firm,
    MonthlyMovement,
    PgdasDocument,
)
from tests.factories import UsuarioCriado, criar_escritorio_com_usuario, login

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "pgdas"
EXTRATO = (
    FIXTURES / "txt_padrao" / "documento.txt"
).read_bytes()  # CNPJ 11222333000181, PA 09/2026
CNPJ = "11222333000181"


async def _empresa(u: UsuarioCriado, cnpj: str = CNPJ) -> uuid.UUID:
    async with get_owner_sessionmaker()() as session:
        company = Company(
            firm_id=u.firm_id, nome="Clínica Exemplo", cnpj=cnpj, sujeita_fator_r=True
        )
        session.add(company)
        await session.commit()
        return company.id


async def _serie_manual(u: UsuarioCriado, company_id: uuid.UUID, pro_labore: str = "15000") -> None:
    async with get_owner_sessionmaker()() as session:
        for i in range(12):
            session.add(
                MonthlyMovement(
                    firm_id=u.firm_id,
                    company_id=company_id,
                    competencia=somar_meses(date(2025, 9, 1), i),
                    receita_bruta=Decimal("50000"),
                    pro_labore=Decimal(pro_labore),
                    origem="manual",
                )
            )
        await session.commit()


async def _enviar(client: httpx.AsyncClient, conteudo: bytes = EXTRATO) -> dict[str, object]:
    response = await client.post(
        "/inbox/pgdas", files={"arquivo": ("extrato.txt", conteudo, "text/plain")}
    )
    assert response.status_code in (200, 201), response.text
    return dict(response.json())


async def _movimento(company_id: uuid.UUID, competencia: date) -> MonthlyMovement | None:
    async with get_owner_sessionmaker()() as session:
        return (
            await session.execute(
                select(MonthlyMovement).where(
                    MonthlyMovement.company_id == company_id,
                    MonthlyMovement.competencia == competencia,
                )
            )
        ).scalar_one_or_none()


async def _evals(trace_id: str) -> dict[str, EvalGold]:
    async with get_owner_sessionmaker()() as session:
        rows = (
            await session.execute(select(EvalGold).where(EvalGold.trace_id == trace_id))
        ).scalars()
        return {e.campo: e for e in rows}


async def test_cnpj_conhecido_vincula_e_cria_receita_na_competencia_do_pa(
    client: httpx.AsyncClient,
) -> None:
    u = await criar_escritorio_com_usuario()
    company_id = await _empresa(u)
    await login(client, u)
    doc = await _enviar(client)
    assert doc["status"] == "linked"
    assert doc["company_id"] == str(company_id)
    assert "competência 2026-09" in str(doc["texto_agente"])
    movimento = await _movimento(company_id, date(2026, 9, 1))  # PA 09/2026 -> 2026-09
    assert movimento is not None
    assert movimento.origem == "pgdas"
    assert movimento.receita_bruta == Decimal("50000.00")
    assert (movimento.pro_labore, movimento.salarios, movimento.cpp, movimento.fgts) == (0, 0, 0, 0)
    assert movimento.pgdas_document_id == uuid.UUID(str(doc["id"]))
    assert await _movimento(company_id, date(2026, 8, 1)) is None  # nunca no mês anterior
    async with get_owner_sessionmaker()() as session:
        trace = (
            await session.execute(select(AgentTrace).where(AgentTrace.id == doc["trace_id"]))
        ).scalar_one()
        decisao = (
            await session.execute(
                select(AgentDecision).where(AgentDecision.trace_id == doc["trace_id"])
            )
        ).scalar_one()
    assert trace.status == "ok"
    assert decisao.dados_json["movimento"] == "criado"


async def test_competencia_existente_nao_e_alterada_e_folha_fica_intacta(
    client: httpx.AsyncClient,
) -> None:
    u = await criar_escritorio_com_usuario()
    company_id = await _empresa(u)
    async with get_owner_sessionmaker()() as session:
        session.add(
            MonthlyMovement(
                firm_id=u.firm_id,
                company_id=company_id,
                competencia=date(2026, 9, 1),
                receita_bruta=Decimal("48000.00"),
                pro_labore=Decimal("7000.00"),
                salarios=Decimal("9000.00"),
                cpp=Decimal("3200.00"),
                fgts=Decimal("720.00"),
                origem="manual",
                observacao="lançado pelo analista",
            )
        )
        await session.commit()
    antes = await _movimento(company_id, date(2026, 9, 1))
    await login(client, u)
    doc = await _enviar(client)
    assert doc["status"] == "linked"
    assert "já tinha lançamento" in str(doc["texto_agente"])
    depois = await _movimento(company_id, date(2026, 9, 1))
    assert antes is not None
    assert depois is not None
    for campo in ("receita_bruta", "pro_labore", "salarios", "cpp", "fgts", "origem", "observacao"):
        assert getattr(depois, campo) == getattr(antes, campo), campo


async def test_cnpj_desconhecido_fica_needs_review_sem_escrita(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    company_id = await _empresa(u, cnpj="45723174000110")  # outra empresa do escritório
    await login(client, u)
    doc = await _enviar(client)
    assert doc["status"] == "needs_review"
    assert doc["motivo"] == "cnpj_nao_encontrado"
    assert doc["company_id"] is None
    assert await _movimento(company_id, date(2026, 9, 1)) is None


async def test_confianca_abaixo_do_limiar_fica_needs_review(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    company_id = await _empresa(u)
    async with get_owner_sessionmaker()() as session:
        await session.execute(
            update(Firm).where(Firm.id == u.firm_id).values(limiar_confianca_parser=Decimal("0.99"))
        )
        await session.commit()
    parcial = (FIXTURES / "txt_parcial_sem_folha_e_fator" / "documento.txt").read_bytes()  # 0,80
    await login(client, u)
    doc = await _enviar(client, parcial)
    assert doc["status"] == "needs_review"
    assert str(doc["motivo"]).startswith("confianca_baixa")
    assert await _movimento(company_id, date(2026, 9, 1)) is None


async def test_cnpj_de_empresa_de_outro_escritorio_fica_needs_review(
    client: httpx.AsyncClient,
) -> None:
    dono = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    await _empresa(dono)  # a empresa com esse CNPJ é do escritório B
    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    await login(client, a)
    doc = await _enviar(client)
    assert doc["status"] == "needs_review"
    assert doc["motivo"] == "cnpj_nao_encontrado"


async def test_pdf_sem_camada_de_texto(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    pdf = (FIXTURES / "pdf_sem_camada_texto" / "documento.pdf").read_bytes()
    response = await client.post(
        "/inbox/pgdas", files={"arquivo": ("x.pdf", pdf, "application/pdf")}
    )
    doc = response.json()
    assert doc["status"] == "needs_review"
    assert doc["motivo"] == "sem_camada_texto"


async def test_ouro_com_serie_manual_completa(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()  # factory: CPP não integra FS12, tolerância 1%
    company_id = await _empresa(u)
    await _serie_manual(u, company_id)  # RBT12 600k, FS12 180k, fator 30%: igual ao extrato
    await login(client, u)
    doc = await _enviar(client)
    evals = await _evals(str(doc["trace_id"]))
    assert evals["cnpj"].status == "ok"
    assert evals["pa"].status == "ouro_indisponivel"
    assert (evals["rbt12"].status, evals["fs12"].status, evals["fator_r"].status) == (
        "ok",
        "ok",
        "ok",
    )
    assert evals["anexo"].status == "ok"


async def test_ouro_detecta_erro_de_extracao(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    company_id = await _empresa(u)
    await _serie_manual(u, company_id, pro_labore="10000")  # FS12 real 120k, extrato diz 180k
    await login(client, u)
    doc = await _enviar(client)
    evals = await _evals(str(doc["trace_id"]))
    assert evals["fs12"].status == "erro"
    assert evals["fator_r"].status == "erro"
    assert evals["anexo"].status == "erro"  # série: 20% -> Anexo V; extrato: III
    assert evals["rbt12"].status == "ok"


async def test_ouro_indisponivel_com_movimento_pgdas_na_janela(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    company_id = await _empresa(u)
    await _serie_manual(u, company_id)
    async with get_owner_sessionmaker()() as session:
        await session.execute(
            update(MonthlyMovement)
            .where(MonthlyMovement.competencia == date(2026, 3, 1))
            .values(origem="pgdas")
        )
        await session.commit()
    await login(client, u)
    doc = await _enviar(client)
    evals = await _evals(str(doc["trace_id"]))
    assert all(
        evals[c].status == "ouro_indisponivel" for c in ("rbt12", "fs12", "fator_r", "anexo")
    )
    assert evals["cnpj"].status == "ok"


async def test_vinculo_manual_e_rejeicao_geram_traces_novos(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    doc = await _enviar(client)  # sem empresa cadastrada: needs_review
    assert doc["status"] == "needs_review"
    company_id = await _empresa(u)

    vinculado = (
        await client.post(f"/inbox/{doc['id']}/link", json={"company_id": str(company_id)})
    ).json()
    assert vinculado["status"] == "linked"
    assert vinculado["trace_id"] != doc["trace_id"]
    assert await _movimento(company_id, date(2026, 9, 1)) is not None
    de_novo = await client.post(f"/inbox/{doc['id']}/link", json={"company_id": str(company_id)})
    assert de_novo.status_code == 409

    outro = await _enviar(client, (FIXTURES / "txt_sem_relacao" / "documento.txt").read_bytes())
    rejeitado = (
        await client.post(f"/inbox/{outro['id']}/reject", json={"motivo": "não é extrato"})
    ).json()
    assert rejeitado["status"] == "rejected"
    assert rejeitado["trace_id"] != outro["trace_id"]
    async with get_owner_sessionmaker()() as session:
        doc_db = (
            await session.execute(
                select(PgdasDocument).where(PgdasDocument.id == uuid.UUID(str(outro["id"])))
            )
        ).scalar_one()
        gatilhos = set((await session.execute(select(AgentTrace.gatilho))).scalars())
    assert doc_db.motivo == "não é extrato"
    assert {"upload", "vinculo_manual", "rejeicao"} <= gatilhos


async def test_vinculo_manual_com_empresa_de_outro_escritorio_da_404(
    client: httpx.AsyncClient,
) -> None:
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    empresa_b = await _empresa(b)
    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    await login(client, a)
    doc = await _enviar(client)
    response = await client.post(f"/inbox/{doc['id']}/link", json={"company_id": str(empresa_b)})
    assert response.status_code == 404
