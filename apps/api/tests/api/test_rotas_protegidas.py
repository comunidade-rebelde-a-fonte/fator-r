"""Garante que toda rota nova nasce protegida (CLAUDE.md §5.3).

As rotas são listadas pelo schema OpenAPI; rota com include_in_schema=False
não é permitida neste projeto justamente para não escapar deste teste.
"""

import httpx
import pytest

from fator_r.main import PUBLIC_PATHS, create_app

ROTAS = sorted(
    (method.upper(), path)
    for path, operations in create_app().openapi()["paths"].items()
    for method in operations
)


def test_rotas_publicas_existem_e_sao_so_as_permitidas() -> None:
    assert {path for _, path in ROTAS} >= PUBLIC_PATHS


@pytest.mark.parametrize(("method", "path"), [r for r in ROTAS if r[1] not in PUBLIC_PATHS])
async def test_rota_nao_publica_exige_sessao(
    client: httpx.AsyncClient, method: str, path: str
) -> None:
    url = path.replace("{", "").replace("}", "")
    response = await client.request(method, url)
    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_documentacao_interativa_nao_e_publica(client: httpx.AsyncClient, path: str) -> None:
    assert (await client.get(path)).status_code == 404
