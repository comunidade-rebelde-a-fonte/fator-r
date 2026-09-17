"""Regressões dos achados da revisão de segurança do M5 (A1, A2, M1, M2, M3, B4)."""

import time

import httpx
import pytest

from fator_r.core.rate_limit import LoginRateLimiter
from fator_r.core.settings import Settings
from fator_r.parsing.isolado import extrair_e_parsear_isolado
from fator_r.parsing.pgdas import parse
from fator_r.tracing.client import mascarar_atributo, mascarar_cnpj


async def test_a1_corpo_gigante_recusado_antes_da_autenticacao(client: httpx.AsyncClient) -> None:
    grande = b"x" * (11 * 1024 * 1024)
    response = await client.post(
        "/companies", content=grande, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413  # não 401: nem chega na autenticação


async def test_a1_corpo_sem_content_length_tambem_e_limitado(client: httpx.AsyncClient) -> None:
    async def corpo() -> object:
        for _ in range(12):
            yield b"x" * (1024 * 1024)

    response = await client.post("/auth/login", content=corpo())
    assert response.status_code == 413


def test_a2_regex_linear_em_sequencia_longa_de_digitos() -> None:
    inicio = time.perf_counter()
    parse("RPA: " + "1" * 200_000 + "\nRBT12: " + "9" * 200_000)
    assert time.perf_counter() - inicio < 1.0


async def test_m1_extracao_isolada_respeita_timeout() -> None:
    extracao = await extrair_e_parsear_isolado(b"PA: 09/2026\n", "text/plain", timeout_s=0.0001)
    assert extracao.motivo == "extracao_excedeu_limites"


async def test_m1_extracao_isolada_funciona() -> None:
    extracao = await extrair_e_parsear_isolado(
        "Período de Apuração (PA): 09/2026\nCNPJ Matriz: 11.222.333/0001-81\n".encode(),
        "text/plain",
    )
    assert extracao.motivo is None
    assert extracao.resultado.campos["cnpj"] == "11222333000181"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("11.222.333/0001-81", "***0181"),
        ("CNPJ 11222333000181 vinculado", "CNPJ ***0181 vinculado"),
    ],
)
def test_m2_cnpj_mascarado(entrada: str, esperado: str) -> None:
    assert mascarar_cnpj(entrada) == esperado


def test_m2_cnpj_mascarado_dentro_de_payload_json() -> None:
    saida = mascarar_atributo('{"campos": {"cnpj": "11222333000181", "rbt12": "600000.00"}}', 4096)
    assert "11222333000181" not in saida
    assert "***0181" in saida
    assert "600000.00" in saida


def test_m3_bloqueio_por_par_nao_tranca_a_conta_para_outro_ip() -> None:
    limiter = LoginRateLimiter(attempts=3, window_seconds=900)
    for _ in range(3):
        limiter.register_failure("1.1.1.1", "vitima@escritorio.com.br")
    assert limiter.is_blocked("1.1.1.1", "vitima@escritorio.com.br")
    assert not limiter.is_blocked("2.2.2.2", "vitima@escritorio.com.br")


def test_m3_consulta_nao_cria_chaves() -> None:
    limiter = LoginRateLimiter(attempts=3, window_seconds=900)
    for i in range(1000):
        limiter.is_blocked("1.1.1.1", f"aleatorio{i}@x.com")
    assert limiter._failures == {}


def test_m3_varredura_por_ip_e_freada() -> None:
    limiter = LoginRateLimiter(attempts=5, window_seconds=900, attempts_por_ip=10)
    for i in range(10):
        limiter.register_failure("3.3.3.3", f"email{i}@x.com")
    assert limiter.is_blocked("3.3.3.3", "novo@x.com")


def test_b4_env_padrao_e_producao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    assert Settings(_env_file=None).env == "prod"  # type: ignore[call-arg]
