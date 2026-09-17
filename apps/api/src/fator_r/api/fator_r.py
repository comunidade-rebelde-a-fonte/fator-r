import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from fator_r.api.companies import empresa_do_escritorio
from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.api.schemas import CompetenciaIn, CompetenciaOut
from fator_r.core.competencia import competencia_corrente, parse_competencia
from fator_r.domain.fator_r import ResultadoFatorR
from fator_r.domain.tabelas import TabelaNaoVigente
from fator_r.services.fator_r import resultado_empresa

router = APIRouter(prefix="/companies/{company_id}/fator-r", tags=["fator-r"])


class FatorROut(BaseModel):
    pa: CompetenciaOut
    janela_inicio: CompetenciaOut
    janela_fim: CompetenciaOut
    meses_preenchidos: list[CompetenciaOut]
    meses_faltantes: list[CompetenciaOut]
    status: Literal["ok", "dados_insuficientes"]
    motivo: (
        Literal["rbt12_zero", "empresa_nova_regra_pendente", "rbt12_acima_do_limite_do_simples"]
        | None
    )
    rbt12: Decimal
    fs12: Decimal
    fator_r: Decimal | None
    anexo: Literal["III", "V"] | None
    semaforo: Literal["vermelho", "amarelo", "verde"] | None
    folha_minima_28: Decimal | None
    folha_minima_meta: Decimal | None
    gap_12m_28: Decimal | None
    reforco_mensal_28: Decimal | None
    gap_12m_meta: Decimal | None
    reforco_mensal_meta: Decimal | None
    aliquota_efetiva_iii: Decimal | None
    aliquota_efetiva_v: Decimal | None
    economia_12m: Decimal | None
    meta_operacional: Decimal
    cpp_integra_fs12: bool
    tabela_vigencia_inicio: date

    @classmethod
    def de(cls, r: ResultadoFatorR) -> "FatorROut":
        return cls(**{campo: getattr(r, campo) for campo in cls.model_fields})


@router.get("", response_model=FatorROut)
async def fator_r_da_empresa(
    company_id: uuid.UUID,
    user: CurrentUser,
    session: FirmSession,
    pa: CompetenciaIn | None = None,
) -> FatorROut:
    company = await empresa_do_escritorio(session, user.firm_id, company_id)
    periodo = parse_competencia(pa) if pa else competencia_corrente()
    try:
        resultado = await resultado_empresa(session, user.firm_id, company, periodo)
    except TabelaNaoVigente as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return FatorROut.de(resultado)
