import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from fator_r.agents import parser_pgdas
from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.core.settings import get_settings
from fator_r.core.uploads import ArquivoGrandeDemais, ArquivoInvalido, receber
from fator_r.repositories import companies
from fator_r.repositories import pgdas as repo
from fator_r.repositories.orm import PgdasDocument

router = APIRouter(prefix="/inbox", tags=["inbox PGDAS-D"])

StatusDocumento = Literal["received", "parsed", "needs_review", "linked", "rejected"]
NAO_ENCONTRADO = "Documento não encontrado"


class DocumentoOut(BaseModel):
    id: uuid.UUID
    texto_agente: str | None = None
    status: StatusDocumento
    motivo: str | None
    company_id: uuid.UUID | None
    nome_original: str | None
    mime: Literal["application/pdf", "text/plain"]
    tamanho_bytes: int
    campos: dict[str, Any]
    confianca: Decimal | None
    parser_version: str | None
    trace_id: str
    criado_em: datetime

    @classmethod
    def de(cls, d: PgdasDocument, texto_agente: str | None = None) -> "DocumentoOut":
        return cls(
            id=d.id,
            texto_agente=texto_agente,
            status=d.status,
            motivo=d.motivo,
            company_id=d.company_id,
            nome_original=d.nome_original,
            mime=d.mime,
            tamanho_bytes=d.tamanho_bytes,
            campos=d.campos_json,
            confianca=d.confianca,
            parser_version=d.parser_version,
            trace_id=d.trace_id,
            criado_em=d.criado_em,
        )


class DocumentoList(BaseModel):
    items: list[DocumentoOut]
    total: int
    contagem_por_status: dict[str, int]


@router.post("/pgdas", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def enviar_extrato(
    arquivo: Annotated[UploadFile, File()],
    response: Response,
    user: CurrentUser,
    session: FirmSession,
) -> DocumentoOut:
    settings = get_settings()
    try:
        recebido = await receber(
            arquivo, Path(settings.upload_dir), user.firm_id, settings.upload_max_mb * 1024 * 1024
        )
    except ArquivoGrandeDemais as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except ArquivoInvalido as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    try:
        resultado = await parser_pgdas.receber_documento(session, user, recebido, arquivo.filename)
    except Exception:
        # Revisão B6: sem registro no banco, o arquivo não pode ficar órfão no disco.
        await session.rollback()
        if await repo.obter_por_sha(session, user.firm_id, recebido.sha256) is None:
            recebido.caminho.unlink(missing_ok=True)
        raise
    if not resultado.novo:
        response.status_code = status.HTTP_200_OK
    return DocumentoOut.de(resultado.documento, resultado.texto)


@router.get("", response_model=DocumentoList)
async def listar_documentos(
    user: CurrentUser,
    session: FirmSession,
    status_: Annotated[StatusDocumento | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentoList:
    items, total, contagem = await repo.listar(session, user.firm_id, status_, limit, offset)
    return DocumentoList(
        items=[DocumentoOut.de(d) for d in items], total=total, contagem_por_status=contagem
    )


async def documento_do_escritorio(
    session: FirmSession, firm_id: uuid.UUID, document_id: uuid.UUID
) -> PgdasDocument:
    documento = await repo.obter(session, firm_id, document_id)
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NAO_ENCONTRADO)
    return documento


@router.get("/{document_id}", response_model=DocumentoOut)
async def obter_documento(
    document_id: uuid.UUID, user: CurrentUser, session: FirmSession
) -> DocumentoOut:
    return DocumentoOut.de(await documento_do_escritorio(session, user.firm_id, document_id))


@router.get("/{document_id}/arquivo", response_class=FileResponse)
async def baixar_original(
    document_id: uuid.UUID, user: CurrentUser, session: FirmSession
) -> FileResponse:
    documento = await documento_do_escritorio(session, user.firm_id, document_id)
    base = Path(get_settings().upload_dir).resolve()
    caminho = Path(documento.arquivo_path).resolve()
    if not caminho.is_relative_to(base) or not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo original indisponível")
    extensao = "pdf" if documento.mime == "application/pdf" else "txt"
    return FileResponse(
        caminho,
        media_type=documento.mime,
        filename=f"extrato-pgdas-{documento.id}.{extensao}",
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
    )


class VinculoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: uuid.UUID


class RejeicaoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=3, max_length=500)


@router.post("/{document_id}/link", response_model=DocumentoOut)
async def vincular_documento(
    document_id: uuid.UUID, payload: VinculoIn, user: CurrentUser, session: FirmSession
) -> DocumentoOut:
    documento = await documento_do_escritorio(session, user.firm_id, document_id)
    company = await companies.obter(session, user.firm_id, payload.company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")
    try:
        resultado = await parser_pgdas.vincular_manual(session, user, documento, company)
    except parser_pgdas.DocumentoEmEstadoInvalido as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return DocumentoOut.de(resultado.documento, resultado.texto)


@router.post("/{document_id}/reject", response_model=DocumentoOut)
async def rejeitar_documento(
    document_id: uuid.UUID, payload: RejeicaoIn, user: CurrentUser, session: FirmSession
) -> DocumentoOut:
    documento = await documento_do_escritorio(session, user.firm_id, document_id)
    try:
        resultado = await parser_pgdas.rejeitar(session, user, documento, payload.motivo)
    except parser_pgdas.DocumentoEmEstadoInvalido as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return DocumentoOut.de(resultado.documento, resultado.texto)
