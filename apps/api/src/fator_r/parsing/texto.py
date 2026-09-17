"""Extração de texto de PDF/TXT (determinística, sem OCR na v1)."""

import io
import logging
from dataclasses import dataclass
from typing import Literal

import pdfplumber
from pypdf import PdfReader

from fator_r.core.uploads import Mime, decodificar_texto

MotivoTexto = Literal["sem_camada_texto", "pdf_ilegivel", "extracao_excedeu_limites"]

# Limites contra PDFs maliciosos (bomba de descompressão, páginas demais).
MAX_PAGINAS = 20
MAX_CHARS_TEXTO = 2_000_000

logging.getLogger("pdfminer").setLevel(logging.ERROR)


@dataclass(frozen=True)
class TextoExtraido:
    texto: str
    motivo: MotivoTexto | None = None


def _pdfplumber(conteudo: bytes) -> str:
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)


def _pypdf(conteudo: bytes) -> str:
    return "\n".join(
        pagina.extract_text() or "" for pagina in PdfReader(io.BytesIO(conteudo)).pages
    )


def extrair_texto(conteudo: bytes, mime: Mime) -> TextoExtraido:
    if mime == "text/plain":
        return TextoExtraido(decodificar_texto(conteudo)[:MAX_CHARS_TEXTO])
    texto = ""
    falhas = 0
    for extrator in (_pdfplumber, _pypdf):
        try:
            texto = extrator(conteudo)
        except Exception:
            falhas += 1
            continue
        if texto.strip():
            return TextoExtraido(texto[:MAX_CHARS_TEXTO])
    if falhas == 2:
        return TextoExtraido("", motivo="pdf_ilegivel")
    return TextoExtraido("", motivo="sem_camada_texto")
