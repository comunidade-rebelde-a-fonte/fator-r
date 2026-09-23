"""Isolamento entre escritórios em TODAS as rotas (T-110).

As rotas vêm do schema OpenAPI. Rota nova sem cenário registrado aqui faz o teste
`test_isolation_toda_rota_tem_cenario` falhar, obrigando a cobrir o isolamento.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import pytest

from fator_r.main import PUBLIC_PATHS, create_app
from tests.factories import criar_escritorio_com_usuario, empresa_payload, login

ROTAS = sorted(
    (method.upper(), path)
    for path, operations in create_app().openapi()["paths"].items()
    for method in operations
    if path not in PUBLIC_PATHS
)

# Rotas que só dizem respeito ao próprio usuário (sem recurso de outro escritório).
ROTAS_DO_PROPRIO_USUARIO = {("GET", "/auth/me"), ("POST", "/auth/logout")}

# Corpo válido por rota com body, para o 404 não ser mascarado por 422.
CORPOS: dict[tuple[str, str], dict[str, object]] = {
    ("PATCH", "/companies/{company_id}"): {"notas": "tentativa"},
    ("PUT", "/companies/{company_id}/movements/{competencia}"): {"receita_bruta": "1.00"},
    ("POST", "/traces/{trace_id}/human-eval"): {"nota": "acerto"},
    ("POST", "/companies/{company_id}/simulations"): {"pa": "2026-09"},
    # Agentes: company_id no corpo é validado em test_consultor_empresa_de_outro_escritorio_404.
    ("POST", "/agents/consultor/chat"): {"mensagem": "situação"},
    ("POST", "/agents/priorizador/chat"): {"mensagem": "o que priorizar?"},
    ("POST", "/inbox/{document_id}/link"): {"company_id": "00000000-0000-0000-0000-000000000000"},
    ("POST", "/inbox/{document_id}/reject"): {"motivo": "tentativa de A"},
    ("POST", "/inbox/{document_id}/cadastrar-empresa"): empresa_payload(cnpj="04.252.011/0001-10"),
    # Upload: multipart; testado em test_isolation_upload_fica_no_proprio_escritorio.
    ("POST", "/inbox/pgdas"): {},
    ("POST", "/companies"): empresa_payload(cnpj="04.252.011/0001-10"),
    # Agente de dev: só usa dados do próprio escritório (trace nasce com o firm_id do usuário).
    ("POST", "/agents/echo/run"): {"mensagem": "isolamento"},
}

# Rotas de listagem: o teste confere que nada do escritório B aparece.
LISTAGENS = {
    ("GET", "/inbox"),
    ("GET", "/companies"),
    ("GET", "/portfolio"),
    ("GET", "/observability/summary"),
    ("GET", "/traces"),
}


@dataclass
class Cenario:
    client_a: httpx.AsyncClient
    params_b: dict[str, str]
    marcadores_b: list[str]


@pytest.fixture
async def cenario() -> AsyncIterator[Cenario]:
    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    app = create_app()
    async with (
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://a") as ca,
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://b") as cb,
    ):
        await login(ca, a)
        await login(cb, b)
        empresa_b = (
            await cb.post("/companies", json=empresa_payload(nome="Segredo do B Ltda"))
        ).json()
        await cb.put(f"/companies/{empresa_b['id']}/movements/2026-08", json={"receita_bruta": "9"})
        trace_b = (await cb.post("/agents/echo/run", json={"mensagem": "segredo-b"})).json()
        doc_b = (
            await cb.post(
                "/inbox/pgdas",
                files={"arquivo": ("b.txt", b"Extrato segredo do B\n", "text/plain")},
            )
        ).json()
        yield Cenario(
            client_a=ca,
            params_b={
                "company_id": empresa_b["id"],
                "competencia": "2026-08",
                "trace_id": trace_b["trace_id"],
                "document_id": doc_b["id"],
            },
            marcadores_b=[
                empresa_b["id"],
                "Segredo do B Ltda",
                "11222333000181",
                trace_b["trace_id"],
                doc_b["id"],
            ],
        )


def test_isolation_toda_rota_tem_cenario() -> None:
    for method, path in ROTAS:
        if (method, path) in ROTAS_DO_PROPRIO_USUARIO or (method, path) in LISTAGENS:
            continue
        if "{" not in path:
            assert (method, path) in CORPOS, f"Registrar cenário de isolamento para {method} {path}"


@pytest.mark.parametrize(
    ("method", "path"),
    [r for r in ROTAS if "{" in r[1]],
)
async def test_isolation_recurso_de_outro_escritorio_da_404(
    cenario: Cenario, method: str, path: str
) -> None:
    url = path
    for nome in [p.strip("{}") for p in path.split("/") if p.startswith("{")]:
        assert nome in cenario.params_b, f"Registrar parâmetro {nome} no cenário de isolamento"
        url = url.replace("{" + nome + "}", cenario.params_b[nome])
    response = await cenario.client_a.request(method, url, json=CORPOS.get((method, path)))
    assert response.status_code == 404, f"{method} {url}: {response.status_code} {response.text}"


@pytest.mark.parametrize(("method", "path"), sorted(LISTAGENS))
async def test_isolation_listagem_nao_mostra_outro_escritorio(
    cenario: Cenario, method: str, path: str
) -> None:
    url = f"{path}?pa=2026-09" if path == "/portfolio" else path
    response = await cenario.client_a.request(method, url)
    assert response.status_code == 200
    for marcador in cenario.marcadores_b:
        assert marcador not in response.text


async def test_isolation_criar_no_proprio_escritorio_nao_ve_dados_de_b(cenario: Cenario) -> None:
    criada = await cenario.client_a.post("/companies", json=CORPOS[("POST", "/companies")])
    assert criada.status_code == 201
    lista = (await cenario.client_a.get("/companies")).json()
    assert [c["nome"] for c in lista["items"]] == ["Clínica Exemplo Ltda"]


async def test_isolation_upload_fica_no_proprio_escritorio(cenario: Cenario) -> None:
    # Mesmo conteúdo enviado por B: para A é um documento novo, nunca o de B.
    resposta = await cenario.client_a.post(
        "/inbox/pgdas", files={"arquivo": ("a.txt", b"Extrato segredo do B\n", "text/plain")}
    )
    assert resposta.status_code == 201
    assert resposta.json()["id"] != cenario.params_b["document_id"]
