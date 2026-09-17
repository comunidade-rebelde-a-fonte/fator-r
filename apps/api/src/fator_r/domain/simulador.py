"""Simulador de correção (Plano §5.2, PRD §7.7). Python puro, só Decimal.

Hipóteses da v1 (CLAUDE.md §2):
- o reforço de folha vem de pró-labore (fração) e o custo considerado é INSS do sócio + IRRF;
- a CPP não entra no custo porque, nos Anexos III e V, já está dentro do DAS;
- INSS sem teto e sem múltiplos sócios (Fase 2).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from fator_r.domain.fator_r import ResultadoFatorR

ZERO = Decimal("0")
DOZE = Decimal("12")

Veredito = Literal["ja_na_meta", "corrigir", "nao_forcar"]


@dataclass(frozen=True)
class ParametrosSimulacao:
    meta: Decimal
    fracao_pro_labore: Decimal
    inss: Decimal
    irrf: Decimal
    horizonte_meses: int
    piso_economia_anual: Decimal


@dataclass(frozen=True)
class ResultadoSimulacao:
    status: Literal["ok", "dados_insuficientes"]
    motivo: str | None
    veredito: Veredito | None
    parametros: ParametrosSimulacao
    fator_atual: Decimal | None
    reforco_12m: Decimal
    reforco_mensal: Decimal
    pro_labore_extra_mensal: Decimal
    pro_labore_extra_horizonte: Decimal
    custo_inss: Decimal
    custo_irrf: Decimal
    custo_total: Decimal
    economia_12m: Decimal | None
    economia_horizonte: Decimal | None
    liquido: Decimal | None


def simular(resultado: ResultadoFatorR, p: ParametrosSimulacao) -> ResultadoSimulacao:
    if resultado.status != "ok" or resultado.fator_r is None or resultado.economia_12m is None:
        return ResultadoSimulacao(
            status="dados_insuficientes",
            motivo=resultado.motivo,
            veredito=None,
            parametros=p,
            fator_atual=resultado.fator_r,
            reforco_12m=ZERO,
            reforco_mensal=ZERO,
            pro_labore_extra_mensal=ZERO,
            pro_labore_extra_horizonte=ZERO,
            custo_inss=ZERO,
            custo_irrf=ZERO,
            custo_total=ZERO,
            economia_12m=None,
            economia_horizonte=None,
            liquido=None,
        )

    horizonte = Decimal(p.horizonte_meses)
    reforco_12m = max(ZERO, p.meta * resultado.rbt12 - resultado.fs12)
    reforco_mensal = reforco_12m / DOZE
    pl_mensal = reforco_mensal * p.fracao_pro_labore
    pl_horizonte = pl_mensal * horizonte
    custo_inss = pl_horizonte * p.inss
    custo_irrf = pl_horizonte * p.irrf
    custo_total = custo_inss + custo_irrf
    economia_horizonte = resultado.economia_12m * horizonte / DOZE
    liquido = economia_horizonte - custo_total

    veredito: Veredito
    if resultado.fator_r >= p.meta:
        veredito = "ja_na_meta"
    elif resultado.economia_12m < p.piso_economia_anual or liquido <= ZERO:
        veredito = "nao_forcar"
    else:
        veredito = "corrigir"

    return ResultadoSimulacao(
        status="ok",
        motivo=None,
        veredito=veredito,
        parametros=p,
        fator_atual=resultado.fator_r,
        reforco_12m=reforco_12m,
        reforco_mensal=reforco_mensal,
        pro_labore_extra_mensal=pl_mensal,
        pro_labore_extra_horizonte=pl_horizonte,
        custo_inss=custo_inss,
        custo_irrf=custo_irrf,
        custo_total=custo_total,
        economia_12m=resultado.economia_12m,
        economia_horizonte=economia_horizonte,
        liquido=liquido,
    )
