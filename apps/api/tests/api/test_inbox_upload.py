"""Upload e armazenamento do PGDAS-D (T-501..T-503)."""

from pathlib import Path

import httpx
import pytest

from fator_r.core.settings import get_settings
from tests.factories import criar_escritorio_com_usuario, login

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
TXT = b"Extrato do Simples Nacional\nCNPJ Matriz: 11.222.333/0001-81\n"


async def _enviar(
    client: httpx.AsyncClient, conteudo: bytes, nome: str, tipo: str = "application/octet-stream"
) -> httpx.Response:
    return await client.post("/inbox/pgdas", files={"arquivo": (nome, conteudo, tipo)})


async def test_upload_txt_e_pdf_ficam_fora_da_web_root_com_permissao_restrita(
    client: httpx.AsyncClient,
) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    txt = await _enviar(client, TXT, "extrato.txt")
    pdf = await _enviar(client, PDF_MINIMO, "extrato.pdf")
    assert (txt.status_code, pdf.status_code) == (201, 201)
    assert txt.json()["mime"] == "text/plain"
    assert pdf.json()["mime"] == "application/pdf"
    assert txt.json()["status"] == "needs_review"  # parse + decisão rodam no upload (T-509)
    assert len(txt.json()["trace_id"]) == 32
    arquivos = list((Path(get_settings().upload_dir) / str(u.firm_id)).iterdir())
    assert len(arquivos) == 2
    for arquivo in arquivos:
        assert len(arquivo.name) == 64  # só o sha256, sem nome do usuário
        assert oct(arquivo.stat().st_mode & 0o777) == "0o600"


@pytest.mark.parametrize(
    ("conteudo", "nome"),
    [
        (b"MZ\x90\x00\x03\x00\x00\x00executavel", "extrato.pdf"),  # executável renomeado
        (b"\x89PNG\r\n\x1a\n\x00\x00imagem", "extrato.txt"),  # imagem renomeada
        (b"", "vazio.txt"),
    ],
)
async def test_tipo_validado_pelo_conteudo(
    client: httpx.AsyncClient, conteudo: bytes, nome: str
) -> None:
    await login(client, await criar_escritorio_com_usuario())
    assert (await _enviar(client, conteudo, nome)).status_code == 415


async def test_extensao_nao_importa_pdf_renomeado_para_txt(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    response = await _enviar(client, PDF_MINIMO, "extrato.txt", "text/plain")
    assert response.status_code == 201
    assert response.json()["mime"] == "application/pdf"


async def test_arquivo_acima_do_limite(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await login(client, await criar_escritorio_com_usuario())
    monkeypatch.setattr(get_settings(), "upload_max_mb", 1)
    grande = b"a" * (1024 * 1024 + 1)
    assert (await _enviar(client, grande, "grande.txt")).status_code == 413


async def test_duplicado_devolve_existente(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    primeiro = await _enviar(client, TXT, "a.txt")
    segundo = await _enviar(client, TXT, "outro-nome.txt")
    assert (primeiro.status_code, segundo.status_code) == (201, 200)
    assert primeiro.json()["id"] == segundo.json()["id"]
    lista = (await client.get("/inbox")).json()
    assert lista["total"] == 1


async def test_nome_com_path_traversal_nao_afeta_armazenamento(client: httpx.AsyncClient) -> None:
    u = await criar_escritorio_com_usuario()
    await login(client, u)
    response = await _enviar(client, TXT, "../../../etc/passwd.txt")
    assert response.status_code == 201
    assert response.json()["nome_original"] == "passwd.txt"
    base = Path(get_settings().upload_dir).resolve()
    for arquivo in base.rglob("*"):
        assert arquivo.resolve().is_relative_to(base)


async def test_download_autenticado_com_headers_seguros(client: httpx.AsyncClient) -> None:
    await login(client, await criar_escritorio_com_usuario())
    documento = (await _enviar(client, TXT, "extrato.txt")).json()
    response = await client.get(f"/inbox/{documento['id']}/arquivo")
    assert response.status_code == 200
    assert response.content == TXT
    assert response.headers["content-disposition"].startswith("attachment")
    assert response.headers["x-content-type-options"] == "nosniff"
    client.cookies.clear()
    assert (await client.get(f"/inbox/{documento['id']}/arquivo")).status_code == 401
