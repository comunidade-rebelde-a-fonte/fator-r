"""Parser do extrato PGDAS-D: regras e regex, sem LLM (CLAUDE.md §3.2).

Função pura sobre o texto: não decide vínculo nem grava nada.
"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Literal

from fator_r.core.cnpj import cnpj_valido

PARSER_VERSION = "2026.09.1"

Campo = Literal["cnpj", "pa", "rbt12", "rpa", "fs12", "fator_r", "das", "anexo"]
CAMPOS: tuple[Campo, ...] = ("cnpj", "pa", "rbt12", "rpa", "fs12", "fator_r", "das", "anexo")

# Peso de cada campo na confiança do documento (anexo é informativo, peso 0).
PESOS: dict[Campo, Decimal] = {
    "cnpj": Decimal("0.25"),
    "pa": Decimal("0.25"),
    "rbt12": Decimal("0.15"),
    "rpa": Decimal("0.10"),
    "fs12": Decimal("0.10"),
    "fator_r": Decimal("0.10"),
    "das": Decimal("0.05"),
    "anexo": Decimal("0"),
}
BONUS_CONSISTENCIA = Decimal("0.10")
TOLERANCIA_CONSISTENCIA = Decimal("0.005")
LIMITE_INCONSISTENCIA = Decimal("0.02")
CONFIANCA_CNPJ_DV_INVALIDO = Decimal("0.3")
NBSP = chr(0xA0)

# Quantificadores limitados: sem backtracking quadrático em sequências longas de dígitos.
_NUMERO = r"(\d{1,3}(?:\.\d{3}){1,6},\d{2}|\d{1,15},\d{2}|\d{1,15}\.\d{2}(?!\d))"
MAX_CHARS_LINHA = 2000
_RE_NUMERO = re.compile(_NUMERO)
_RE_CNPJ = re.compile(
    r"\bCNPJ(?:\s+Matriz)?\s*[:\-]?\s*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b", re.IGNORECASE
)
_RE_PA = [
    re.compile(
        r"Per[ií]odo\s+de\s+Apura[cç][aã]o(?:\s*\(PA\))?\s*[:\-]?\s*(\d{2})/(\d{4})", re.IGNORECASE
    ),
    re.compile(r"\bPA\s*[:\-]\s*(\d{2})/(\d{4})\b"),
]
_ROTULOS: dict[str, list[re.Pattern[str]]] = {
    "rpa": [
        re.compile(r"Receita\s+Bruta\s+do\s+PA\s*\(RPA\)", re.IGNORECASE),
        re.compile(r"\bRPA\b\s*[:\-]"),
    ],
    "rbt12": [
        re.compile(r"doze\s+meses\s+anteriores\s+ao\s+PA\s*\(RBT12\)", re.IGNORECASE),
        re.compile(r"\bRBT12\b\s*[:\-]"),
    ],
    "fs12": [
        re.compile(r"Total\s+de\s+Folhas?\s+de\s+Sal[aá]rios\s+Anteriores", re.IGNORECASE),
        re.compile(r"Folha\s+de\s+sal[aá]rios\s*\(FS12\)", re.IGNORECASE),
        re.compile(r"\bFS12\b\s*[:\-]"),
    ],
    "das": [
        re.compile(r"Valor\s+Total\s+do\s+D[eé]bito\s+Declarado", re.IGNORECASE),
        re.compile(r"Total\s+do\s+DAS", re.IGNORECASE),
        re.compile(r"Valor\s+do\s+DAS", re.IGNORECASE),
    ],
}
_RE_FATOR = re.compile(r"Fator\s*r\s*[:=]?\s*(\d{1,6}(?:[.,]\d{1,6})?)\s*(%)?", re.IGNORECASE)
_RE_ANEXO = re.compile(r"\bAnexo\s+(III|V)(?![IVX])", re.IGNORECASE)


@dataclass(frozen=True)
class ResultadoParse:
    campos: dict[Campo, str | None]
    confianca_campos: dict[Campo, Decimal]
    confianca: Decimal
    motivos: tuple[str, ...] = field(default_factory=tuple)
    parser_version: str = PARSER_VERSION


def normalizar(texto: str) -> list[str]:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace(NBSP, " ")
    return [re.sub(r"[ \t]+", " ", linha[:MAX_CHARS_LINHA]).strip() for linha in texto.split("\n")]


def numero_br(valor: str) -> Decimal | None:
    bruto = valor.strip()
    normalizado = bruto.replace(".", "").replace(",", ".") if "," in bruto else bruto
    try:
        return Decimal(normalizado)
    except InvalidOperation:
        return None


def _decimal_ou_none(valor: str | None) -> Decimal | None:
    return numero_br(valor) if valor is not None else None


def _cnpj(linhas: list[str]) -> str | None:
    for linha in linhas:
        if match := _RE_CNPJ.search(linha):
            return re.sub(r"\D", "", match.group(1))
    return None


def _pa(linhas: list[str]) -> str | None:
    for regex in _RE_PA:
        for linha in linhas:
            if (match := regex.search(linha)) and 1 <= int(match.group(1)) <= 12:
                return f"{match.group(2)}-{match.group(1)}"
    return None


def _valor_rotulado(linhas: list[str], campo: str) -> str | None:
    """Última quantia da linha do rótulo (nas tabelas do extrato, a coluna Total)."""
    for regex in _ROTULOS[campo]:
        for linha in linhas:
            if match := regex.search(linha):
                numeros = _RE_NUMERO.findall(linha[match.end() :])
                if numeros and (valor := numero_br(numeros[-1])) is not None:
                    return str(valor.quantize(Decimal("0.01")))
    return None


def _fator(linhas: list[str]) -> str | None:
    for linha in linhas:
        if match := _RE_FATOR.search(linha):
            valor = numero_br(match.group(1))
            if valor is None:
                continue
            if match.group(2) or valor > 1:
                valor = (valor / Decimal(100)).quantize(Decimal("0.0001"))
            return str(valor)
    return None


def _anexo(linhas: list[str]) -> str | None:
    for linha in linhas:
        if match := _RE_ANEXO.search(linha):
            return match.group(1).upper()
    return None


def parse(texto: str) -> ResultadoParse:
    linhas = normalizar(texto)
    campos: dict[Campo, str | None] = {
        "cnpj": _cnpj(linhas),
        "pa": _pa(linhas),
        "rbt12": _valor_rotulado(linhas, "rbt12"),
        "rpa": _valor_rotulado(linhas, "rpa"),
        "fs12": _valor_rotulado(linhas, "fs12"),
        "fator_r": _fator(linhas),
        "das": _valor_rotulado(linhas, "das"),
        "anexo": _anexo(linhas),
    }
    motivos: list[str] = []
    confianca_campos: dict[Campo, Decimal] = {
        campo: Decimal(1) if valor is not None else Decimal(0) for campo, valor in campos.items()
    }
    if campos["cnpj"] is not None and not cnpj_valido(campos["cnpj"]):
        confianca_campos["cnpj"] = CONFIANCA_CNPJ_DV_INVALIDO
        motivos.append("cnpj_digito_verificador_invalido")
    for campo in ("cnpj", "pa"):
        if campos[campo] is None:
            motivos.append(f"{campo}_nao_encontrado")

    total = sum((PESOS[c] * confianca_campos[c] for c in CAMPOS), Decimal(0))
    rbt12, fs12, fator = (_decimal_ou_none(campos[c]) for c in ("rbt12", "fs12", "fator_r"))
    if rbt12 and fs12 is not None and fator is not None:
        diferenca = abs(fator - fs12 / rbt12)
        if diferenca <= TOLERANCIA_CONSISTENCIA:
            total += BONUS_CONSISTENCIA
        elif diferenca > LIMITE_INCONSISTENCIA:
            total -= BONUS_CONSISTENCIA
            motivos.append("fator_r_inconsistente_com_fs12_rbt12")
    confianca = min(Decimal(1), max(Decimal(0), total)).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_EVEN
    )
    return ResultadoParse(campos, confianca_campos, confianca, tuple(motivos))


def resultado_vazio(motivo: str) -> ResultadoParse:
    return ResultadoParse(
        campos=dict.fromkeys(CAMPOS),
        confianca_campos=dict.fromkeys(CAMPOS, Decimal(0)),
        confianca=Decimal("0.0000"),
        motivos=(motivo,),
    )
