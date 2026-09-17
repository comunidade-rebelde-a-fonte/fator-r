"""Agente parser_pgdas: recebe o extrato, extrai, vincula por CNPJ e decide (Plano §6, §7.3).

Regras invioláveis (CLAUDE.md §3.8, §3.9):
- confiança abaixo do limiar do escritório ou CNPJ não encontrado -> needs_review, sem escrita;
- vinculado com RPA: cria só a RECEITA na competência do PA, só se a competência não existir;
- nunca escreve pró-labore, salários, CPP ou FGTS.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.agents.render import com_disclaimer
from fator_r.core.cnpj import cnpj_valido
from fator_r.core.competencia import parse_competencia
from fator_r.core.uploads import ArquivoRecebido
from fator_r.parsing.isolado import extrair_e_parsear_isolado
from fator_r.parsing.pgdas import ResultadoParse
from fator_r.repositories import companies, firms, movements
from fator_r.repositories import pgdas as repo
from fator_r.repositories.auth import AuthenticatedUser
from fator_r.repositories.orm import Company, MonthlyMovement, PgdasDocument
from fator_r.services import ouro_pgdas
from fator_r.tracing import tracer

AGENTE = "parser_pgdas"
Movimento = Literal["criado", "existente", "sem_rpa", "nao_aplicavel"]


class DocumentoEmEstadoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class ResultadoAgente:
    documento: PgdasDocument
    novo: bool
    trace_id: str
    texto: str
    acerto_ouro: Decimal | None = None


def _texto(documento: PgdasDocument, movimento: Movimento, company: Company | None) -> str:
    return com_disclaimer(_texto_base(documento, movimento, company))


def _texto_base(documento: PgdasDocument, movimento: Movimento, company: Company | None) -> str:
    campos = documento.campos_json
    pa = campos.get("pa") or "não identificado"
    if documento.status == "linked" and company is not None:
        frases = {
            "criado": f"Receita do PA {pa} lançada na competência {pa} (origem pgdas).",
            "existente": f"A competência {pa} já tinha lançamento; nada foi alterado.",
            "sem_rpa": "O extrato não trouxe a receita do PA; nenhum movimento foi criado.",
            "nao_aplicavel": "Nenhum movimento foi criado.",
        }
        return f"Extrato vinculado a {company.nome}. {frases[movimento]} A folha não é alterada."
    if documento.status == "rejected":
        return "Extrato rejeitado pelo analista."
    return f"Extrato do PA {pa} precisa de revisão: {documento.motivo}."


async def _aplicar_vinculo(
    session: AsyncSession, documento: PgdasDocument, company: Company
) -> Movimento:
    """Vincula e cria só a receita da competência do PA, se ainda não existir."""
    documento.company_id = company.id
    documento.status = "linked"
    documento.motivo = None
    campos = documento.campos_json
    if not campos.get("pa") or not campos.get("rpa"):
        return "sem_rpa"
    criado = await movements.criar_se_ausente(
        session,
        MonthlyMovement(
            firm_id=documento.firm_id,
            company_id=company.id,
            competencia=parse_competencia(campos["pa"]),
            receita_bruta=Decimal(campos["rpa"]),
            pro_labore=Decimal(0),
            salarios=Decimal(0),
            cpp=Decimal(0),
            fgts=Decimal(0),
            origem="pgdas",
            observacao="Receita do PA lida do extrato PGDAS-D",
            pgdas_document_id=documento.id,
        ),
    )
    return "criado" if criado else "existente"


def _campos_json(resultado: ResultadoParse) -> dict[str, Any]:
    campos: dict[str, Any] = {str(c): v for c, v in resultado.campos.items()}
    return {
        **campos,
        "_confianca_campos": {c: str(v) for c, v in resultado.confianca_campos.items()},
        "_motivos": list(resultado.motivos),
    }


async def _avaliar_ouro(
    session: AsyncSession, user: AuthenticatedUser, documento: PgdasDocument
) -> Decimal | None:
    if documento.status != "linked" or documento.company_id is None:
        return None
    company = await companies.obter(session, user.firm_id, documento.company_id)
    if company is None:
        return None
    return await ouro_pgdas.avaliar(session, user.firm_id, documento, company)


async def receber_documento(
    session: AsyncSession,
    user: AuthenticatedUser,
    arquivo: ArquivoRecebido,
    nome_original: str | None,
) -> ResultadoAgente:
    existente = await repo.obter_por_sha(session, user.firm_id, arquivo.sha256)
    if existente is not None:
        return ResultadoAgente(existente, False, existente.trace_id, "Extrato já recebido.")

    firm = await firms.obter(session, user.firm_id)
    async with tracer.run(
        session,
        agente=AGENTE,
        gatilho="upload",
        firm_id=user.firm_id,
        user_id=user.id,
        entrada={"mime": arquivo.mime, "tamanho_bytes": arquivo.tamanho_bytes},
        metadata={"limiar": firm.limiar_confianca_parser},
    ) as run:
        documento = PgdasDocument(
            firm_id=user.firm_id,
            arquivo_path=str(arquivo.caminho),
            sha256=arquivo.sha256,
            mime=arquivo.mime,
            tamanho_bytes=arquivo.tamanho_bytes,
            nome_original=Path(nome_original).name[:255] if nome_original else None,
            campos_json={},
            status="received",
        )
        tracer.anexar_ao_run(run, documento)
        await session.flush()

        with run.span(
            "parse", input={"mime": arquivo.mime, "tamanho": arquivo.tamanho_bytes}
        ) as span:
            texto = await extrair_e_parsear_isolado(arquivo.conteudo, arquivo.mime)
            resultado = texto.resultado
            documento.texto_extraido = texto.texto or None
            documento.campos_json = _campos_json(resultado)
            documento.confianca = resultado.confianca
            documento.parser_version = resultado.parser_version
            documento.status = "parsed"
            span.update(
                output={
                    "campos": resultado.campos,
                    "confianca": resultado.confianca,
                    "motivos": list(resultado.motivos),
                    "parser_version": resultado.parser_version,
                }
            )

        with run.span("tool", input={"cnpj": resultado.campos["cnpj"]}) as span:
            cnpj = resultado.campos["cnpj"]
            company = (
                await companies.obter_por_cnpj(session, user.firm_id, cnpj)
                if cnpj and cnpj_valido(cnpj)
                else None
            )
            span.update(output={"company_id": company.id if company else None})

        with run.span("decide") as span:
            limiar = firm.limiar_confianca_parser
            movimento: Movimento = "nao_aplicavel"
            if texto.motivo:
                documento.status, documento.motivo = "needs_review", texto.motivo
            elif company is None:
                documento.status, documento.motivo = "needs_review", "cnpj_nao_encontrado"
            elif resultado.confianca < limiar:
                documento.status = "needs_review"
                documento.motivo = f"confianca_baixa ({resultado.confianca} < {limiar})"
            else:
                movimento = await _aplicar_vinculo(session, documento, company)
            decisao = {
                "document_id": documento.id,
                "status": documento.status,
                "motivo": documento.motivo,
                "company_id": documento.company_id,
                "confianca": resultado.confianca,
                "limiar": limiar,
                "movimento": movimento,
                "competencia": resultado.campos["pa"],
            }
            await tracer.record_decision(run, tipo="pgdas_documento", dados=decisao)
            span.update(output=decisao)

        with run.span("render") as span:
            texto_final = _texto(documento, movimento, company)
            span.update(output={"texto": texto_final})

        await run.finish(
            decisao=decisao,
            texto=texto_final,
            status="ok" if documento.status == "linked" else "needs_review",
            confianca=resultado.confianca,
        )
    acerto = await _avaliar_ouro(session, user, documento)
    return ResultadoAgente(documento, True, run.trace_id, texto_final, acerto)


async def vincular_manual(
    session: AsyncSession, user: AuthenticatedUser, documento: PgdasDocument, company: Company
) -> ResultadoAgente:
    if documento.status not in ("needs_review", "parsed"):
        raise DocumentoEmEstadoInvalido(f"Documento em '{documento.status}' não pode ser vinculado")
    async with tracer.run(
        session,
        agente=AGENTE,
        gatilho="vinculo_manual",
        firm_id=user.firm_id,
        user_id=user.id,
        company_id=company.id,
        entrada={"document_id": documento.id, "company_id": company.id},
    ) as run:
        with run.span("tool", input={"company_id": company.id}) as span:
            span.update(output={"empresa": company.nome})
        with run.span("decide") as span:
            movimento = await _aplicar_vinculo(session, documento, company)
            documento.trace_id = run.trace_id
            decisao = {
                "document_id": documento.id,
                "status": documento.status,
                "company_id": company.id,
                "movimento": movimento,
                "competencia": documento.campos_json.get("pa"),
                "origem_decisao": "analista",
            }
            await tracer.record_decision(run, tipo="pgdas_vinculo_manual", dados=decisao)
            span.update(output=decisao)
        with run.span("render") as span:
            texto_final = _texto(documento, movimento, company)
            span.update(output={"texto": texto_final})
        await run.finish(decisao=decisao, texto=texto_final, status="ok")
    acerto = await _avaliar_ouro(session, user, documento)
    return ResultadoAgente(documento, False, run.trace_id, texto_final, acerto)


async def rejeitar(
    session: AsyncSession, user: AuthenticatedUser, documento: PgdasDocument, motivo: str
) -> ResultadoAgente:
    if documento.status in ("rejected", "linked"):
        raise DocumentoEmEstadoInvalido(f"Documento em '{documento.status}' não pode ser rejeitado")
    async with tracer.run(
        session,
        agente=AGENTE,
        gatilho="rejeicao",
        firm_id=user.firm_id,
        user_id=user.id,
        entrada={"document_id": documento.id, "motivo": motivo},
    ) as run:
        with run.span("decide") as span:
            documento.status = "rejected"
            documento.motivo = motivo
            documento.trace_id = run.trace_id
            decisao = {"document_id": documento.id, "status": "rejected", "motivo": motivo}
            await tracer.record_decision(run, tipo="pgdas_rejeicao", dados=decisao)
            span.update(output=decisao)
        texto_final = _texto(documento, "nao_aplicavel", None)
        await run.finish(decisao=decisao, texto=texto_final, status="ok")
    return ResultadoAgente(documento, False, run.trace_id, texto_final)
