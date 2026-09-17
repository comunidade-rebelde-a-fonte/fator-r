import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from fator_r.api.deps import CurrentUser, FirmSession
from fator_r.api.schemas import CompetenciaIn, CompetenciaOut
from fator_r.core.cnpj import formatar_cnpj
from fator_r.core.competencia import competencia_corrente, parse_competencia
from fator_r.domain.carteira import Acao, LinhaCarteira
from fator_r.domain.tabelas import TabelaNaoVigente
from fator_r.services.carteira import carteira_do_escritorio

router = APIRouter(prefix="/portfolio", tags=["carteira"])


class LinhaCarteiraOut(BaseModel):
    company_id: uuid.UUID
    nome: str
    cnpj_formatado: str
    pacote: Literal["monitoramento", "correcao", "retainer"] | None
    honorario_mensal: Decimal
    acao: Acao
    acao_texto: str
    status: Literal["ok", "dados_insuficientes"]
    motivo: str | None
    semaforo: Literal["vermelho", "amarelo", "verde"] | None
    fator_r: Decimal | None
    anexo: Literal["III", "V"] | None
    rbt12: Decimal
    fs12: Decimal
    reforco_mensal_28: Decimal | None
    reforco_mensal_meta: Decimal | None
    economia_12m: Decimal | None
    meses_faltantes: list[CompetenciaOut]

    @classmethod
    def de(cls, linha: LinhaCarteira) -> "LinhaCarteiraOut":
        e, r = linha.empresa, linha.resultado
        return cls(
            company_id=e.id,
            nome=e.nome,
            cnpj_formatado=formatar_cnpj(e.cnpj),
            pacote=e.pacote,
            honorario_mensal=e.honorario_mensal,
            acao=linha.acao,
            acao_texto=linha.acao_texto,
            status=r.status,
            motivo=r.motivo,
            semaforo=r.semaforo,
            fator_r=r.fator_r,
            anexo=r.anexo,
            rbt12=r.rbt12,
            fs12=r.fs12,
            reforco_mensal_28=r.reforco_mensal_28,
            reforco_mensal_meta=r.reforco_mensal_meta,
            economia_12m=r.economia_12m,
            meses_faltantes=list(r.meses_faltantes),
        )


class KpisOut(BaseModel):
    monitoradas: int
    no_v: int
    no_limite: int
    seguras: int
    dados_insuficientes: int
    economia_em_jogo: Decimal
    honorarios_pacotes: Decimal


class CarteiraOut(BaseModel):
    pa: CompetenciaOut
    kpis: KpisOut
    linhas: list[LinhaCarteiraOut]


@router.get("", response_model=CarteiraOut)
async def carteira(
    user: CurrentUser, session: FirmSession, pa: CompetenciaIn | None = None
) -> CarteiraOut:
    periodo: date = parse_competencia(pa) if pa else competencia_corrente()
    try:
        resultado = await carteira_do_escritorio(session, user.firm_id, periodo)
    except TabelaNaoVigente as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return CarteiraOut(
        pa=resultado.pa,
        kpis=KpisOut(**vars(resultado.kpis)),
        linhas=[LinhaCarteiraOut.de(linha) for linha in resultado.linhas],
    )
