from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from fator_r.agents import echo
from fator_r.api.deps import CurrentUser, FirmSession

router = APIRouter(prefix="/agents/echo", tags=["agentes (dev)"])


class EchoIn(BaseModel):
    mensagem: str = Field(min_length=1, max_length=500)


class AgentOut(BaseModel):
    texto: str
    decisao: dict[str, Any]
    trace_id: str


@router.post("/run", response_model=AgentOut)
async def rodar_echo(payload: EchoIn, user: CurrentUser, session: FirmSession) -> AgentOut:
    return AgentOut(**await echo.executar(session, user, payload.mensagem))
