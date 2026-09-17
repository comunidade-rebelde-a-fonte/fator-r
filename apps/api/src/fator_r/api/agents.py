import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from fator_r.agents import consultor, priorizador
from fator_r.agents.guardas import RecomendacaoSemSimulacao
from fator_r.agents.llm import get_llm
from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.api.schemas import CompetenciaIn
from fator_r.domain.tabelas import TabelaNaoVigente
from fator_r.repositories import companies

router = APIRouter(prefix="/agents", tags=["agentes"])


class ConsultorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mensagem: str = Field(min_length=1, max_length=1000)
    company_id: uuid.UUID | None = None


class PriorizadorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mensagem: str = Field(min_length=1, max_length=1000)
    pa: CompetenciaIn | None = None


class RespostaAgente(BaseModel):
    texto: str
    decisao: dict[str, Any]
    trace_id: str


@router.post("/consultor/chat", response_model=RespostaAgente)
async def conversar_consultor(
    payload: ConsultorIn, user: CurrentUser, session: FirmSession
) -> RespostaAgente:
    if payload.company_id is not None and (
        await companies.obter(session, user.firm_id, payload.company_id) is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")
    try:
        resposta = await consultor.responder(
            session, user, get_llm(), payload.mensagem, payload.company_id
        )
    except TabelaNaoVigente as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except RecomendacaoSemSimulacao as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return RespostaAgente(**resposta)


@router.post("/priorizador/chat", response_model=RespostaAgente)
async def conversar_priorizador(
    payload: PriorizadorIn, user: CurrentUser, session: FirmSession
) -> RespostaAgente:
    try:
        resposta = await priorizador.responder(
            session, user, get_llm(), payload.mensagem, payload.pa
        )
    except TabelaNaoVigente as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return RespostaAgente(**resposta)
