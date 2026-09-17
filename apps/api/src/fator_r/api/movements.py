import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field

from fator_r.api.companies import empresa_do_escritorio
from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.api.schemas import CompetenciaIn, CompetenciaOut, Dinheiro
from fator_r.core.competencia import CompetenciaInvalida, parse_competencia
from fator_r.repositories import movements as repo
from fator_r.repositories.orm import MonthlyMovement

router = APIRouter(prefix="/companies/{company_id}/movements", tags=["movimentos"])

Origem = Literal["manual", "pgdas", "folha", "agente"]


class MovementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receita_bruta: Dinheiro = Decimal("0")
    pro_labore: Dinheiro = Decimal("0")
    salarios: Dinheiro = Decimal("0")
    cpp: Dinheiro = Decimal("0")
    fgts: Dinheiro = Decimal("0")
    observacao: str | None = Field(default=None, max_length=1000)


class MovementOut(BaseModel):
    competencia: CompetenciaOut
    receita_bruta: Decimal
    pro_labore: Decimal
    salarios: Decimal
    cpp: Decimal
    fgts: Decimal
    folha_mes: Decimal
    origem: Origem
    observacao: str | None
    pgdas_document_id: uuid.UUID | None

    @classmethod
    def de(cls, m: MonthlyMovement) -> "MovementOut":
        return cls(
            competencia=m.competencia,
            receita_bruta=m.receita_bruta,
            pro_labore=m.pro_labore,
            salarios=m.salarios,
            cpp=m.cpp,
            fgts=m.fgts,
            folha_mes=m.folha_mes,
            origem=m.origem,
            observacao=m.observacao,
            pgdas_document_id=m.pgdas_document_id,
        )


def _competencia(valor: str) -> date:
    try:
        return parse_competencia(valor)
    except CompetenciaInvalida as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.get("", response_model=list[MovementOut])
async def listar_movimentos(
    company_id: uuid.UUID,
    user: CurrentUser,
    session: FirmSession,
    de: CompetenciaIn | None = None,
    ate: CompetenciaIn | None = None,
) -> list[MovementOut]:
    company = await empresa_do_escritorio(session, user.firm_id, company_id)
    movimentos = await repo.listar(
        session,
        user.firm_id,
        company.id,
        parse_competencia(de) if de else None,
        parse_competencia(ate) if ate else None,
    )
    return [MovementOut.de(m) for m in movimentos]


@router.put("/{competencia}", response_model=MovementOut)
async def lancar_movimento(
    company_id: uuid.UUID,
    payload: MovementIn,
    user: CurrentUser,
    session: FirmSession,
    competencia: Annotated[str, Path(pattern=r"^\d{4}-\d{2}$")],
) -> MovementOut:
    data = _competencia(competencia)
    company = await empresa_do_escritorio(session, user.firm_id, company_id)
    valores = payload.model_dump(exclude={"observacao"})
    movimento = await repo.upsert_manual(
        session,
        user.firm_id,
        company,
        data,
        valores,
        payload.observacao,
    )
    return MovementOut.de(movimento)
