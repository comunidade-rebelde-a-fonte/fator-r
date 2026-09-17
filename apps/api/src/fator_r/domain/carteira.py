"""Carteira do escritório (T-301/T-302). Reusa o motor por empresa; sem I/O."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from fator_r.domain.fator_r import MovimentoMes, Politica, ResultadoFatorR, calcular
from fator_r.domain.tabelas import TabelasVigentes

ZERO = Decimal("0")

Acao = Literal["reuniao_correcao", "vigiar_simular", "manter", "completar_lancamentos"]

# Textos da ação sugerida (fonte única).
ACOES: dict[Acao, str] = {
    "reuniao_correcao": "reunião de correção",
    "vigiar_simular": "vigiar / simular",
    "manter": "manter",
    "completar_lancamentos": "completar lançamentos",
}

_ORDEM_SEMAFORO = {"vermelho": 0, "amarelo": 1, "verde": 2, None: 3}


@dataclass(frozen=True)
class EmpresaCarteira:
    id: uuid.UUID
    nome: str
    cnpj: str
    pacote: str | None
    honorario_mensal: Decimal
    inicio_atividade: date | None


@dataclass(frozen=True)
class LinhaCarteira:
    empresa: EmpresaCarteira
    resultado: ResultadoFatorR
    acao: Acao

    @property
    def acao_texto(self) -> str:
        return ACOES[self.acao]


@dataclass(frozen=True)
class KpisCarteira:
    monitoradas: int
    no_v: int
    no_limite: int
    seguras: int
    dados_insuficientes: int
    economia_em_jogo: Decimal
    honorarios_pacotes: Decimal


@dataclass(frozen=True)
class Carteira:
    pa: date
    linhas: tuple[LinhaCarteira, ...]
    kpis: KpisCarteira


def acao_sugerida(resultado: ResultadoFatorR) -> Acao:
    match resultado.semaforo:
        case "vermelho":
            return "reuniao_correcao"
        case "amarelo":
            return "vigiar_simular"
        case "verde":
            return "manter"
        case _:
            return "completar_lancamentos"


def _chave_ordem(linha: LinhaCarteira) -> tuple[int, Decimal, str]:
    economia = linha.resultado.economia_12m
    # Maior economia primeiro; sem economia (dados insuficientes) por último no grupo.
    return (
        _ORDEM_SEMAFORO[linha.resultado.semaforo],
        -economia if economia is not None else Decimal("Infinity"),
        linha.empresa.nome,
    )


def montar_carteira(
    pa: date,
    empresas: list[EmpresaCarteira],
    movimentos: dict[uuid.UUID, list[MovimentoMes]],
    tabelas: TabelasVigentes,
    politica: Politica,
) -> Carteira:
    linhas = []
    for empresa in empresas:
        resultado = calcular(
            pa=pa,
            inicio_atividade=empresa.inicio_atividade,
            movimentos=movimentos.get(empresa.id, []),
            tabelas=tabelas,
            politica=politica,
        )
        linhas.append(LinhaCarteira(empresa, resultado, acao_sugerida(resultado)))
    ordenadas = tuple(sorted(linhas, key=_chave_ordem))

    def conta(semaforo: str | None) -> int:
        return sum(1 for linha in ordenadas if linha.resultado.semaforo == semaforo)

    # "Economia em jogo": economia positiva de quem está no V ou no limite (vermelho e amarelo).
    em_jogo = sum(
        (
            linha.resultado.economia_12m
            for linha in ordenadas
            if linha.resultado.semaforo in ("vermelho", "amarelo")
            and linha.resultado.economia_12m is not None
            and linha.resultado.economia_12m > ZERO
        ),
        ZERO,
    )
    kpis = KpisCarteira(
        monitoradas=len(ordenadas),
        no_v=sum(1 for linha in ordenadas if linha.resultado.anexo == "V"),
        no_limite=conta("amarelo"),
        seguras=conta("verde"),
        dados_insuficientes=conta(None),
        economia_em_jogo=em_jogo,
        honorarios_pacotes=sum((e.honorario_mensal for e in empresas), ZERO),
    )
    return Carteira(pa=pa, linhas=ordenadas, kpis=kpis)
