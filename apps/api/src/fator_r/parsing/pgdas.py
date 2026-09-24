"""Parser do extrato PGDAS-D: regras e regex, sem LLM (CLAUDE.md §3.2).

Função pura sobre o texto: não decide vínculo nem grava nada.
"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Literal

from fator_r.core.cnpj import cnpj_valido
from fator_r.core.competencia import format_competencia, parse_competencia, somar_meses

PARSER_VERSION = "2026.09.3"

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
# Layout declaratório: "Periodo de Apuracao: 01/08/2026 a 31/08/2026" (só vale dentro do mesmo mês).
_RE_PA_INTERVALO = re.compile(
    r"Per[ií]odo\s+de\s+Apura[cç][aã]o(?:\s*\(PA\))?\s*[:\-]?\s*"
    r"\d{2}/(\d{2})/(\d{4})\s+a\s+\d{2}/(\d{2})/(\d{4})",
    re.IGNORECASE,
)
_ROTULOS: dict[str, list[re.Pattern[str]]] = {
    "rpa": [
        re.compile(r"Receita\s+Bruta\s+do\s+PA\s*\(RPA\)", re.IGNORECASE),
        re.compile(r"\bRPA\b\s*[:\-]"),
    ],
    "rbt12": [
        re.compile(r"doze\s+meses\s+anteriores\s+ao\s+PA\s*\(RBT12\)", re.IGNORECASE),
        re.compile(r"12\s+meses\s+anteriores(?:\s+ao\s+PA)?\s*\(RBT12\)", re.IGNORECASE),
        re.compile(r"\bRBT12\b\s*[:\-]"),
    ],
    "fs12": [
        re.compile(r"Total\s+de\s+Folhas?\s+de\s+Sal[aá]rios\s+Anteriores", re.IGNORECASE),
        re.compile(r"Folha\s+de\s+sal[aá]rios\s*\(FS12\)", re.IGNORECASE),
        re.compile(r"^Total\s+FS12\b", re.IGNORECASE),
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
_RE_QUALQUER_ANEXO = re.compile(r"\bAnexo\s+(I{1,3}|IV|V)(?![IVX])", re.IGNORECASE)
# Linhas que declaram o enquadramento; parágrafos explicativos do extrato não contam.
_RE_LINHA_ESTRUTURADA = re.compile(r"^(?:Fator\s*r|Enquadramento|Atividade)\b", re.IGNORECASE)
_RE_NOME = re.compile(r"^Nome\s+empresarial\b\s*:?\s*(.*)$", re.IGNORECASE)
MAX_CHARS_NOME = 200  # limite de CompanyIn.nome
_RE_FATOR_NAO_SE_APLICA = re.compile(r"Fator\s*r\s*[:=]?\s*N[aã]o\s+se\s+aplica", re.IGNORECASE)
_RE_DATA_ABERTURA = re.compile(
    r"Data\s+de\s+abertura(?:\s+no\s+CNPJ)?\s*:?\s*\d{2}/(\d{2})/(\d{4})", re.IGNORECASE
)
# Tabelas mensais do layout declaratório (2.2 receitas e 2.3 folha dos 12 meses anteriores ao PA).
_RE_SECAO = re.compile(r"^\d+(?:\.\d+)*\s+\S")
_RE_SECAO_RECEITAS = re.compile(r"^\d+(?:\.\d+)*\s+Receitas\s+Brutas\s+Anteriores", re.IGNORECASE)
_RE_SECAO_FOLHAS = re.compile(
    r"^\d+(?:\.\d+)*\s+Folhas?\s+de\s+Sal[aá]rios\s+Anteriores", re.IGNORECASE
)
_RE_MES_VALOR = re.compile(r"\b(\d{2})/(\d{4})\s+" + _NUMERO)
TOLERANCIA_SERIE = Decimal("0.01")  # centavos: a soma dos meses tem de bater com o total declarado


@dataclass(frozen=True)
class Identificacao:
    """Dados de cadastro lidos do extrato: fora da confiança e da nota ouro (M8, DEFINE D-02)."""

    nome_empresarial: str | None = None
    sujeita_fator_r: bool | None = None
    inicio_atividade: str | None = None  # "YYYY-MM" da data de abertura no CNPJ


@dataclass(frozen=True)
class SeriesAnteriores:
    """Receita e folha mês a mês dos 12 meses anteriores ao PA, como declaradas no extrato.

    `*_conferem` só é True quando os meses são exatamente a janela do PA (PA-12 a PA-1) e a soma
    bate com o total declarado (RBT12 / FS12). Série que não confere nunca é gravada.
    """

    receitas: dict[str, str] = field(default_factory=dict)
    folhas: dict[str, str] = field(default_factory=dict)
    receitas_conferem: bool = False
    folhas_conferem: bool = False


@dataclass(frozen=True)
class ResultadoParse:
    campos: dict[Campo, str | None]
    confianca_campos: dict[Campo, Decimal]
    confianca: Decimal
    motivos: tuple[str, ...] = field(default_factory=tuple)
    parser_version: str = PARSER_VERSION
    identificacao: Identificacao = field(default_factory=Identificacao)
    series: SeriesAnteriores = field(default_factory=SeriesAnteriores)


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
    for linha in linhas:
        if match := _RE_PA_INTERVALO.search(linha):
            mes_inicio, ano_inicio, mes_fim, ano_fim = match.groups()
            if (mes_inicio, ano_inicio) == (mes_fim, ano_fim) and 1 <= int(mes_inicio) <= 12:
                return f"{ano_inicio}-{mes_inicio}"
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
    """Anexo III ou V. Linha estruturada manda; o texto livre só vale se não houver nenhuma."""
    for linha in linhas:
        if _RE_LINHA_ESTRUTURADA.match(linha) and (match := _RE_QUALQUER_ANEXO.search(linha)):
            anexo = match.group(1).upper()
            return anexo if anexo in ("III", "V") else None
    for linha in linhas:
        if match := _RE_ANEXO.search(linha):
            return match.group(1).upper()
    return None


def _nome_empresarial(linhas: list[str]) -> str | None:
    for linha in linhas:
        if (match := _RE_NOME.match(linha)) and (nome := match.group(1).strip()[:MAX_CHARS_NOME]):
            return nome.strip()
    return None


def _inicio_atividade(linhas: list[str]) -> str | None:
    for linha in linhas:
        if (match := _RE_DATA_ABERTURA.search(linha)) and 1 <= int(match.group(1)) <= 12:
            return f"{match.group(2)}-{match.group(1)}"
    return None


def _serie(linhas: list[str], secao: re.Pattern[str]) -> dict[str, Decimal]:
    """Soma por mês os pares "MM/AAAA valor" das seções com o cabeçalho (ex.: interno e externo)."""
    valores: dict[str, Decimal] = {}
    dentro = False
    for linha in linhas:
        if secao.match(linha):
            dentro = True
            continue
        if dentro and _RE_SECAO.match(linha):
            dentro = False
        if not dentro:
            continue
        for mes, ano, numero in _RE_MES_VALOR.findall(linha):
            valor = numero_br(numero)
            if valor is not None and 1 <= int(mes) <= 12:
                chave = f"{ano}-{mes}"
                valores[chave] = valores.get(chave, Decimal(0)) + valor
    return valores


def _confere(serie: dict[str, Decimal], pa: str | None, total: str | None) -> bool:
    if not serie or pa is None or total is None:
        return False
    inicio = parse_competencia(pa)
    janela = {format_competencia(somar_meses(inicio, -i)) for i in range(1, 13)}
    soma = sum(serie.values(), Decimal(0))
    return set(serie) == janela and abs(soma - Decimal(total)) <= TOLERANCIA_SERIE


def _series_anteriores(linhas: list[str], campos: dict[Campo, str | None]) -> SeriesAnteriores:
    receitas = _serie(linhas, _RE_SECAO_RECEITAS)
    folhas = _serie(linhas, _RE_SECAO_FOLHAS)
    centavos = Decimal("0.01")
    return SeriesAnteriores(
        receitas={m: str(v.quantize(centavos)) for m, v in sorted(receitas.items())},
        folhas={m: str(v.quantize(centavos)) for m, v in sorted(folhas.items())},
        receitas_conferem=_confere(receitas, campos["pa"], campos["rbt12"]),
        folhas_conferem=_confere(folhas, campos["pa"], campos["fs12"]),
    )


def _sugestao_sujeita_fator_r(linhas: list[str], fator_r: str | None) -> bool | None:
    """Fator r numérico → sujeita; "não se aplica" → não sujeita; sem indício → sem sugestão."""
    if fator_r is not None:
        return True
    if any(_RE_FATOR_NAO_SE_APLICA.search(linha) for linha in linhas):
        return False
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
    identificacao = Identificacao(
        nome_empresarial=_nome_empresarial(linhas),
        sujeita_fator_r=_sugestao_sujeita_fator_r(linhas, campos["fator_r"]),
        inicio_atividade=_inicio_atividade(linhas),
    )
    return ResultadoParse(
        campos,
        confianca_campos,
        confianca,
        tuple(motivos),
        identificacao=identificacao,
        series=_series_anteriores(linhas, campos),
    )


def resultado_vazio(motivo: str) -> ResultadoParse:
    return ResultadoParse(
        campos=dict.fromkeys(CAMPOS),
        confianca_campos=dict.fromkeys(CAMPOS, Decimal(0)),
        confianca=Decimal("0.0000"),
        motivos=(motivo,),
    )
