"""Motor Fator R (Plano §5.1). Python puro, só Decimal, sem I/O e sem arredondamento interno."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from fator_r.domain.janela import classificar, empresa_nova_na_janela, janela, meses_validos
from fator_r.domain.tabelas import Anexo, TabelaAnexo, TabelasVigentes

# Corte legal (LC 123/2006, art. 18 §§ 5º-J e 5º-M). A meta operacional nunca muda o anexo.
CORTE_LEGAL = Decimal("0.28")
ZERO = Decimal("0")
DOZE = Decimal("12")

Status = Literal["ok", "dados_insuficientes"]
Semaforo = Literal["vermelho", "amarelo", "verde"]
Motivo = Literal["rbt12_zero", "empresa_nova_regra_pendente", "rbt12_acima_do_limite_do_simples"]


@dataclass(frozen=True)
class MovimentoMes:
    competencia: date
    receita_bruta: Decimal
    pro_labore: Decimal
    salarios: Decimal
    cpp: Decimal
    fgts: Decimal
    origem: str = "manual"


@dataclass(frozen=True)
class Politica:
    cpp_das_integra_fs12: bool
    meta_operacional: Decimal


@dataclass(frozen=True)
class ResultadoFatorR:
    pa: date
    janela_inicio: date
    janela_fim: date
    meses_preenchidos: tuple[date, ...]
    meses_faltantes: tuple[date, ...]
    status: Status
    motivo: Motivo | None
    rbt12: Decimal
    fs12: Decimal
    fator_r: Decimal | None
    anexo: Anexo | None
    semaforo: Semaforo | None
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


def folha_para_fs12(m: MovimentoMes, politica: Politica) -> Decimal:
    """Remunerações com INSS + FGTS + CPP (se a política do escritório mandar)."""
    folha = m.pro_labore + m.salarios + m.fgts
    return folha + m.cpp if politica.cpp_das_integra_fs12 else folha


def aliquota_efetiva(tabela: TabelaAnexo, rbt12: Decimal) -> Decimal | None:
    faixa = tabela.faixa_para(rbt12)
    if faixa is None or rbt12 <= ZERO:
        return None
    return (rbt12 * faixa.aliquota_nominal - faixa.parcela_deduzir) / rbt12


def semaforo_para(fator: Decimal, meta: Decimal) -> Semaforo:
    if fator < CORTE_LEGAL:
        return "vermelho"
    if fator < meta:
        return "amarelo"
    return "verde"


def calcular(
    pa: date,
    inicio_atividade: date | None,
    movimentos: list[MovimentoMes],
    tabelas: TabelasVigentes,
    politica: Politica,
) -> ResultadoFatorR:
    j = janela(pa)
    validos = meses_validos(j, inicio_atividade)
    por_mes = {m.competencia: m for m in movimentos if m.competencia in validos}
    preenchidos, faltantes = classificar(validos, set(por_mes))

    rbt12 = sum((m.receita_bruta for m in por_mes.values()), ZERO)
    fs12 = sum((folha_para_fs12(m, politica) for m in por_mes.values()), ZERO)

    base = {
        "pa": j.pa,
        "janela_inicio": j.inicio,
        "janela_fim": j.fim,
        "meses_preenchidos": preenchidos,
        "meses_faltantes": faltantes,
        "rbt12": rbt12,
        "fs12": fs12,
        "meta_operacional": politica.meta_operacional,
        "cpp_integra_fs12": politica.cpp_das_integra_fs12,
        "tabela_vigencia_inicio": tabelas.anexo_iii.vigencia_inicio,
    }

    motivo: Motivo | None = None
    if empresa_nova_na_janela(j, inicio_atividade):
        # P-05: proporcionalização (Res. CGSN 140/2018, arts. 22 e 26) pendente de conferência.
        motivo = "empresa_nova_regra_pendente"
    elif rbt12 <= ZERO:
        motivo = "rbt12_zero"
    else:
        efetiva_iii = aliquota_efetiva(tabelas.anexo_iii, rbt12)
        efetiva_v = aliquota_efetiva(tabelas.anexo_v, rbt12)
        if efetiva_iii is None or efetiva_v is None:
            motivo = "rbt12_acima_do_limite_do_simples"

    if motivo is not None:
        return ResultadoFatorR(
            **base,  # type: ignore[arg-type]
            status="dados_insuficientes",
            motivo=motivo,
            fator_r=None,
            anexo=None,
            semaforo=None,
            folha_minima_28=None,
            folha_minima_meta=None,
            gap_12m_28=None,
            reforco_mensal_28=None,
            gap_12m_meta=None,
            reforco_mensal_meta=None,
            aliquota_efetiva_iii=None,
            aliquota_efetiva_v=None,
            economia_12m=None,
        )

    assert efetiva_iii is not None  # noqa: S101 - garantido pelo bloco acima
    assert efetiva_v is not None  # noqa: S101 - garantido pelo bloco acima
    fator = fs12 / rbt12
    folha_min_28 = CORTE_LEGAL * rbt12
    folha_min_meta = politica.meta_operacional * rbt12
    gap_28 = max(ZERO, folha_min_28 - fs12)
    gap_meta = max(ZERO, folha_min_meta - fs12)
    return ResultadoFatorR(
        **base,  # type: ignore[arg-type]
        status="ok",
        motivo=None,
        fator_r=fator,
        anexo="III" if fator >= CORTE_LEGAL else "V",
        semaforo=semaforo_para(fator, politica.meta_operacional),
        folha_minima_28=folha_min_28,
        folha_minima_meta=folha_min_meta,
        gap_12m_28=gap_28,
        reforco_mensal_28=gap_28 / DOZE,
        gap_12m_meta=gap_meta,
        reforco_mensal_meta=gap_meta / DOZE,
        aliquota_efetiva_iii=efetiva_iii,
        aliquota_efetiva_v=efetiva_v,
        economia_12m=(efetiva_v - efetiva_iii) * rbt12,
    )
