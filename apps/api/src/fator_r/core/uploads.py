"""Armazenamento de uploads fora da web root (PRD §8, CLAUDE.md §5.3).

- Tipo validado pelo conteúdo (magic bytes / texto), nunca pela extensão.
- Tamanho limitado durante a leitura em streaming.
- Caminho derivado só de firm_id e sha256 (sem nome enviado pelo usuário).
"""

import hashlib
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

Mime = Literal["application/pdf", "text/plain"]
CHUNK = 64 * 1024


class ArquivoInvalido(ValueError):
    pass


class ArquivoGrandeDemais(ValueError):
    pass


class LeitorAssincrono(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True)
class ArquivoRecebido:
    caminho: Path
    sha256: str
    mime: Mime
    tamanho_bytes: int
    conteudo: bytes


def detectar_mime(conteudo: bytes) -> Mime:
    if conteudo.startswith(b"%PDF-"):
        return "application/pdf"
    if not conteudo or b"\x00" in conteudo:
        raise ArquivoInvalido("Envie um PDF ou TXT do extrato do PGDAS-D")
    try:
        conteudo.decode("utf-8")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")
        imprimiveis = sum(ch.isprintable() or ch in "\r\n\t" for ch in texto)
        if imprimiveis / len(texto) < 0.95:
            raise ArquivoInvalido("Envie um PDF ou TXT do extrato do PGDAS-D") from None
    return "text/plain"


def decodificar_texto(conteudo: bytes) -> str:
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("latin-1")


def caminho_seguro(base: Path, firm_id: uuid.UUID, sha256: str) -> Path:
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise ArquivoInvalido("hash inválido")
    destino = (base / str(firm_id) / sha256).resolve()
    if not destino.is_relative_to(base.resolve()):
        raise ArquivoInvalido("caminho fora do diretório de uploads")
    return destino


async def receber(
    leitor: LeitorAssincrono, base: Path, firm_id: uuid.UUID, max_bytes: int
) -> ArquivoRecebido:
    partes: list[bytes] = []
    total = 0
    hasher = hashlib.sha256()
    while True:
        bloco = await leitor.read(CHUNK)
        if not bloco:
            break
        total += len(bloco)
        if total > max_bytes:
            raise ArquivoGrandeDemais(f"Arquivo acima de {max_bytes // (1024 * 1024)} MB")
        hasher.update(bloco)
        partes.append(bloco)
    conteudo = b"".join(partes)
    mime = detectar_mime(conteudo)
    sha256 = hasher.hexdigest()
    destino = caminho_seguro(base, firm_id, sha256)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(base, 0o700)  # revisão B7: a pasta base também fica restrita ao dono
    destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not destino.exists():
        fd, temporario = tempfile.mkstemp(dir=destino.parent)
        try:
            with os.fdopen(fd, "wb") as arquivo:
                arquivo.write(conteudo)
            os.chmod(temporario, 0o600)
            os.replace(temporario, destino)
        except BaseException:
            Path(temporario).unlink(missing_ok=True)
            raise
    return ArquivoRecebido(destino, sha256, mime, total, conteudo)
