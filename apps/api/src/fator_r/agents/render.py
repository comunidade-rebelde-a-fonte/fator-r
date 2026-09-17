"""Validação do texto do LLM contra a decisão estruturada (T-607, CLAUDE.md §3.12)."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

DISCLAIMER = "Esta plataforma não é a apuração oficial. O PGDAS-D da Receita Federal prevalece."

_RE_DATA = re.compile(r"\b(\d{4})-(\d{2})\b|\b(\d{2})/(\d{4})\b")
# Sinal capturado e sem exigir borda de palavra: "x45000" e "R$-99.000,00" também são checados.
_RE_NUMERO = re.compile(r"-?(?<!\d)\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?(?<!\d)\d+(?:[.,]\d+)?")
# Números por extenso ou multiplicadores burlariam a checagem: texto com eles vai para o template.
_RE_EXTENSO = re.compile(
    r"\b(mil|milh[aã]o|milh[oõ]es|bilh[aã]o|bilh[oõ]es|onze|doze|treze|quatorze|catorze|quinze|"
    r"dezesseis|dezessete|dezoito|dezenove|vinte|trinta|quarenta|cinquenta|sessenta|setenta|"
    r"oitenta|noventa|cem|cento|duzent\w*|trezent\w*|quatrocent\w*|quinhent\w*|seiscent\w*|"
    r"setecent\w*|oitocent\w*|novecent\w*)\b",
    re.IGNORECASE,
)
_RECOMENDA_CORRIGIR = re.compile(
    r"\b(vale|recomend\w*|deve|convém|sugiro)\s+(a\s+)?corrig", re.IGNORECASE
)
_RECOMENDA_NAO_CORRIGIR = re.compile(r"n[aã]o\s+(for[cç]ar|vale|compensa|recomend)", re.IGNORECASE)
_RE_COMPETENCIA = re.compile(r"^\d{4}-\d{2}$")


def com_disclaimer(texto: str) -> str:
    texto = texto.strip()
    return texto if texto.endswith(DISCLAIMER) else f"{texto}\n\n{DISCLAIMER}"


def _decimal(token: str) -> Decimal | None:
    bruto = token.strip()
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", bruto):
        bruto = bruto.replace(".", "")
    try:
        return Decimal(bruto)
    except InvalidOperation:
        return None


def _folhas(valor: Any) -> list[Any]:
    if isinstance(valor, dict):
        return [f for v in valor.values() for f in _folhas(v)]
    if isinstance(valor, list | tuple):
        return [f for v in valor for f in _folhas(v)]
    return [valor]


def valores_permitidos(decisao: dict[str, Any]) -> tuple[set[Decimal], set[str]]:
    """Números aceitos (com as formas de exibição permitidas) e competências (AAAA-MM)."""
    numeros: set[Decimal] = set()
    competencias: set[str] = set()
    for folha in _folhas(decisao):
        if isinstance(folha, bool) or folha is None:
            continue
        if isinstance(folha, str) and _RE_COMPETENCIA.match(folha):
            competencias.add(folha)
            continue
        try:
            valor = Decimal(str(folha))
        except InvalidOperation:
            continue
        for forma in (valor, valor.quantize(Decimal("0.01"))):
            numeros.add(forma.normalize())
        if abs(valor) <= 1:  # frações exibidas como percentual
            percentual = valor * 100
            numeros.update(
                {
                    percentual.quantize(Decimal("0.01")).normalize(),
                    percentual.quantize(Decimal("1")).normalize()
                    if percentual == percentual.quantize(Decimal("1"))
                    else percentual.quantize(Decimal("0.01")).normalize(),
                }
            )
    return numeros, competencias


@dataclass(frozen=True)
class Validacao:
    valido: bool
    orfaos: tuple[str, ...]


def validar_texto(texto: str, decisao: dict[str, Any]) -> Validacao:
    numeros, competencias = valores_permitidos(decisao)
    orfaos: list[str] = []
    sem_disclaimer = texto.replace(DISCLAIMER, "")
    orfaos += [m.group(0) for m in _RE_EXTENSO.finditer(sem_disclaimer)]
    veredito = decisao.get("veredito")
    if veredito in ("nao_forcar", "ja_na_meta") and _RECOMENDA_CORRIGIR.search(sem_disclaimer):
        orfaos.append("veredito_contraditorio")
    if veredito == "corrigir" and _RECOMENDA_NAO_CORRIGIR.search(sem_disclaimer):
        orfaos.append("veredito_contraditorio")
    for match in _RE_DATA.finditer(sem_disclaimer):
        competencia = (
            f"{match.group(1)}-{match.group(2)}"
            if match.group(1)
            else f"{match.group(4)}-{match.group(3)}"
        )
        if competencia not in competencias:
            orfaos.append(match.group(0))
    restante = _RE_DATA.sub(" ", sem_disclaimer)
    for token in _RE_NUMERO.findall(restante):
        valor = _decimal(token)
        if valor is None or valor.normalize() not in numeros:
            orfaos.append(token)
    return Validacao(valido=not orfaos, orfaos=tuple(orfaos))
