import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.api.schemas import CnpjIn, CompetenciaIn, CompetenciaOut, Dinheiro
from fator_r.core.cnpj import formatar_cnpj
from fator_r.core.competencia import parse_competencia
from fator_r.repositories import companies as repo
from fator_r.repositories.orm import Company

router = APIRouter(prefix="/companies", tags=["empresas"])

Pacote = Literal["monitoramento", "correcao", "retainer"]
NAO_ENCONTRADA = "Empresa não encontrada"


class CompanyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=200)
    cnpj: CnpjIn
    cnae: str | None = Field(default=None, max_length=20)
    atividade: str | None = Field(default=None, max_length=500)
    sujeita_fator_r: bool
    qtd_socios: int = Field(default=1, ge=0, le=1000)
    contato: str | None = Field(default=None, max_length=500)
    pacote: Pacote | None = None
    honorario_mensal: Dinheiro = Decimal("0")
    ativo: bool = True
    notas: str | None = Field(default=None, max_length=5000)
    inicio_atividade: CompetenciaIn | None = None


class CompanyPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    cnpj: CnpjIn | None = None
    cnae: str | None = Field(default=None, max_length=20)
    atividade: str | None = Field(default=None, max_length=500)
    sujeita_fator_r: bool | None = None
    qtd_socios: int | None = Field(default=None, ge=0, le=1000)
    contato: str | None = Field(default=None, max_length=500)
    pacote: Pacote | None = None
    honorario_mensal: Dinheiro | None = None
    ativo: bool | None = None
    notas: str | None = Field(default=None, max_length=5000)
    inicio_atividade: CompetenciaIn | None = None


class CompanyOut(BaseModel):
    id: uuid.UUID
    nome: str
    cnpj: str
    cnpj_formatado: str
    cnae: str | None
    atividade: str | None
    sujeita_fator_r: bool
    qtd_socios: int
    contato: str | None
    pacote: Pacote | None
    honorario_mensal: Decimal
    ativo: bool
    notas: str | None
    inicio_atividade: CompetenciaOut | None

    @classmethod
    def de(cls, c: Company) -> "CompanyOut":
        return cls(
            id=c.id,
            nome=c.nome,
            cnpj=c.cnpj,
            cnpj_formatado=formatar_cnpj(c.cnpj),
            cnae=c.cnae,
            atividade=c.atividade,
            sujeita_fator_r=c.sujeita_fator_r,
            qtd_socios=c.qtd_socios,
            contato=c.contato,
            pacote=c.pacote,
            honorario_mensal=c.honorario_mensal,
            ativo=c.ativo,
            notas=c.notas,
            inicio_atividade=c.inicio_atividade,
        )


class CompanyList(BaseModel):
    items: list[CompanyOut]
    total: int


def _dados(payload: BaseModel, exclude_unset: bool) -> dict[str, object]:
    dados = payload.model_dump(exclude_unset=exclude_unset)
    inicio = dados.get("inicio_atividade")
    if isinstance(inicio, str):
        dados["inicio_atividade"] = parse_competencia(inicio)
    return dados


@router.get("", response_model=CompanyList)
async def listar_empresas(
    user: CurrentUser,
    session: FirmSession,
    ativo: bool | None = None,
    sujeita_fator_r: bool | None = None,
    busca: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CompanyList:
    filtro = repo.FiltroEmpresas(
        ativo=ativo, sujeita_fator_r=sujeita_fator_r, busca=busca, limit=limit, offset=offset
    )
    items, total = await repo.listar(session, user.firm_id, filtro)
    return CompanyList(items=[CompanyOut.de(c) for c in items], total=total)


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def criar_empresa(payload: CompanyIn, user: CurrentUser, session: FirmSession) -> CompanyOut:
    try:
        company = await repo.criar(session, user.firm_id, _dados(payload, exclude_unset=False))
    except repo.CnpjDuplicado as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "CNPJ já cadastrado neste escritório"
        ) from exc
    return CompanyOut.de(company)


@router.get("/{company_id}", response_model=CompanyOut)
async def obter_empresa(
    company_id: uuid.UUID, user: CurrentUser, session: FirmSession
) -> CompanyOut:
    company = await repo.obter(session, user.firm_id, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NAO_ENCONTRADA)
    return CompanyOut.de(company)


@router.patch("/{company_id}", response_model=CompanyOut)
async def atualizar_empresa(
    company_id: uuid.UUID, payload: CompanyPatch, user: CurrentUser, session: FirmSession
) -> CompanyOut:
    dados = _dados(payload, exclude_unset=True)
    for campo in ("nome", "cnpj", "sujeita_fator_r", "qtd_socios", "honorario_mensal", "ativo"):
        if campo in dados and dados[campo] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{campo} não pode ser nulo")
    try:
        company = await repo.atualizar(session, user.firm_id, company_id, dados)
    except repo.CnpjDuplicado as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "CNPJ já cadastrado neste escritório"
        ) from exc
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NAO_ENCONTRADA)
    return CompanyOut.de(company)


async def empresa_do_escritorio(
    session: FirmSession, firm_id: uuid.UUID, company_id: uuid.UUID
) -> Company:
    company = await repo.obter(session, firm_id, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NAO_ENCONTRADA)
    return company
