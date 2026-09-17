"""Classificação de intenção por palavras-chave (fallback do span plan, sem LLM)."""

import re
import unicodedata
from decimal import Decimal

from fator_r.agents.llm import Intencao, TipoIntencao


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


PALAVRAS: list[tuple[TipoIntencao, tuple[str, ...]]] = [
    ("priorizar", ("prioriz", "carteira", "fila", "atacar primeiro", "quais empresas")),
    ("simular", ("simul", "pro-labore", "pro labore", "corrigir", "correcao", "reforco")),
    ("explicar", ("explic", "o que e", "o que significa", "por que", "porque", "como funciona")),
    ("status_empresa", ("como esta", "situacao", "status", "fator r", "anexo")),
]


def empresa_citada(mensagem: str, empresas: list[str]) -> str | None:
    alvo = _normalizar(mensagem)
    candidatos = [e for e in empresas if _normalizar(e) and _normalizar(e) in alvo]
    return max(candidatos, key=len) if candidatos else None


def classificar_por_palavras(mensagem: str, empresas: list[str]) -> Intencao:
    alvo = _normalizar(mensagem)
    intencao: TipoIntencao = "status_empresa"
    for tipo, palavras in PALAVRAS:
        if any(p in alvo for p in palavras):
            intencao = tipo
            break
    pa = None
    if match := re.search(r"\b(0[1-9]|1[0-2])/(\d{4})\b", mensagem):
        pa = f"{match.group(2)}-{match.group(1)}"
    elif match := re.search(r"\b(\d{4})-(0[1-9]|1[0-2])\b", mensagem):
        pa = f"{match.group(1)}-{match.group(2)}"
    meta = None
    if match := re.search(r"meta\D{0,10}(\d{2})(?:[.,](\d{1,2}))?\s*%", alvo):
        valor = Decimal(f"{match.group(1)}.{match.group(2) or 0}") / 100
        meta = valor if Decimal("0.28") <= valor < 1 else None
    return Intencao(
        intencao=intencao, company_ref=empresa_citada(mensagem, empresas), pa=pa, meta=meta
    )
