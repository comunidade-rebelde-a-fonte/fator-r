"""Extração + parse num processo separado, com timeout e limite de memória.

Protege a api de PDFs maliciosos e de entradas patológicas: o loop de eventos nunca executa
o parse, e um processo preso é encerrado.
"""

import asyncio
import multiprocessing
import threading
from dataclasses import dataclass
from multiprocessing.connection import Connection

from fator_r.core.uploads import Mime
from fator_r.parsing.pgdas import ResultadoParse, parse, resultado_vazio
from fator_r.parsing.texto import extrair_texto

TIMEOUT_S = 30.0
MAX_EXTRACOES_SIMULTANEAS = 2
_semaforo = threading.BoundedSemaphore(MAX_EXTRACOES_SIMULTANEAS)
LIMITE_MEMORIA_BYTES = 1024 * 1024 * 1024


@dataclass(frozen=True)
class Extracao:
    texto: str
    resultado: ResultadoParse
    motivo: str | None


def _limitar_memoria() -> None:
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (LIMITE_MEMORIA_BYTES, LIMITE_MEMORIA_BYTES))
    except (
        ImportError,
        ValueError,
        OSError,
    ):  # pragma: no cover - ex.: macOS não suporta RLIMIT_AS
        pass


def extrair_e_parsear(conteudo: bytes, mime: Mime) -> Extracao:
    texto = extrair_texto(conteudo, mime)
    if texto.motivo:
        return Extracao("", resultado_vazio(texto.motivo), texto.motivo)
    return Extracao(texto.texto, parse(texto.texto), None)


def _trabalhador(conexao: Connection, conteudo: bytes, mime: Mime) -> None:
    _limitar_memoria()
    try:
        conexao.send(extrair_e_parsear(conteudo, mime))
    except MemoryError:
        conexao.send(None)
    finally:
        conexao.close()


def _executar(conteudo: bytes, mime: Mime, timeout_s: float) -> Extracao:
    with _semaforo:
        return _executar_processo(conteudo, mime, timeout_s)


def _executar_processo(conteudo: bytes, mime: Mime, timeout_s: float) -> Extracao:
    contexto = multiprocessing.get_context("spawn")
    receptor, emissor = contexto.Pipe(duplex=False)
    processo = contexto.Process(target=_trabalhador, args=(emissor, conteudo, mime), daemon=True)
    processo.start()
    emissor.close()
    try:
        if receptor.poll(timeout_s):
            extracao = receptor.recv()
            if isinstance(extracao, Extracao):
                return extracao
        return Extracao("", resultado_vazio("extracao_excedeu_limites"), "extracao_excedeu_limites")
    except EOFError:
        return Extracao("", resultado_vazio("extracao_excedeu_limites"), "extracao_excedeu_limites")
    finally:
        receptor.close()
        if processo.is_alive():
            processo.kill()
        processo.join(timeout=5)


async def extrair_e_parsear_isolado(
    conteudo: bytes, mime: Mime, timeout_s: float = TIMEOUT_S
) -> Extracao:
    return await asyncio.to_thread(_executar, conteudo, mime, timeout_s)
