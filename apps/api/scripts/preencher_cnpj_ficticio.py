"""Cria versões dos exemplos de PGDAS-D da pasta `pdf/` com CNPJ fictício preenchido.

Os exemplos da pasta `pdf/` vêm com os campos de identificação mascarados (`XX.XXX.XXX/XXXX-XX`,
`XX/XX/XXXX`, número da declaração, recibo e autenticação). Sem CNPJ o inbox nunca liga o extrato
a uma empresa; este script troca as máscaras por valores fictícios (CNPJ com dígitos verificadores
corretos) preservando o layout e todos os valores do documento.

Uso: uv run python scripts/preencher_cnpj_ficticio.py
Saída: pdf/com_cnpj/<mesmo nome>.pdf + pdf/com_cnpj/indice.md
"""

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfWriter

from fator_r.core.cnpj import cnpj_valido, formatar_cnpj

RAIZ = Path(__file__).resolve().parents[3]
ORIGEM = RAIZ / "pdf"
DESTINO = ORIGEM / "com_cnpj"

_PESOS_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_DV2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


@dataclass(frozen=True)
class Identidade:
    """Dados de identificação fictícios de um exemplo."""

    arquivo: str
    base_cnpj: str  # 12 dígitos (raiz + ordem do estabelecimento), sem DV
    abertura: str
    municipio_uf: str
    declaracao: str
    recibo: str
    autenticacao: str
    transmissao: str


IDENTIDADES = (
    Identidade(
        arquivo="01_servico_fator_r_abaixo_28.pdf",
        base_cnpj="123456780001",
        abertura="12/03/2019",
        municipio_uf="SAO PAULO / SP",
        declaracao="20260914000000001",
        recibo="35.26.10001.0000001-1",
        autenticacao="A1B2C.D3E4F.G5H6I.J7K8L",
        transmissao="14/09/2026 09:12:33",
    ),
    Identidade(
        arquivo="02_comercio_sem_fator_r.pdf",
        base_cnpj="234567890001",
        abertura="05/07/2017",
        municipio_uf="CAMPINAS / SP",
        declaracao="20260914000000002",
        recibo="35.26.10002.0000002-2",
        autenticacao="B2C3D.E4F5G.H6I7J.K8L9M",
        transmissao="14/09/2026 09:31:07",
    ),
    Identidade(
        arquivo="03_servico_sem_fator_r.pdf",
        base_cnpj="345678900001",
        abertura="22/01/2021",
        municipio_uf="BELO HORIZONTE / MG",
        declaracao="20260914000000003",
        recibo="31.26.10003.0000003-3",
        autenticacao="C3D4E.F5G6H.I7J8K.L9M0N",
        transmissao="14/09/2026 10:02:55",
    ),
    Identidade(
        arquivo="04_servico_fator_r_acima_28.pdf",
        base_cnpj="456789010001",
        abertura="30/09/2016",
        municipio_uf="CURITIBA / PR",
        declaracao="20260914000000004",
        recibo="41.26.10004.0000004-4",
        autenticacao="D4E5F.G6H7I.J8K9L.M0N1O",
        transmissao="14/09/2026 10:44:18",
    ),
)


def _digito(numeros: str, pesos: tuple[int, ...]) -> str:
    resto = sum(int(n) * p for n, p in zip(numeros, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_com_dv(base: str) -> str:
    """Completa os 12 primeiros dígitos com os dois verificadores."""
    dv1 = _digito(base, _PESOS_DV1)
    dv2 = _digito(base + dv1, _PESOS_DV2)
    digitos = base + dv1 + dv2
    if not cnpj_valido(digitos):  # pragma: no cover - guarda de sanidade do script
        raise SystemExit(f"CNPJ gerado inválido para a base {base}")
    return digitos


def substituicoes(identidade: Identidade) -> list[tuple[bytes, bytes]]:
    """Máscara -> valor fictício. A ordem importa: o mais específico vem primeiro."""
    cnpj = formatar_cnpj(cnpj_com_dv(identidade.base_cnpj))
    pares = (
        ("XX/XX/XXXX XX:XX:XX", identidade.transmissao),
        ("XX.XXX.XXX/XXXX-XX", cnpj),
        ("XX.XX.XXXXX.XXXXXXX-X", identidade.recibo),
        ("XXXXX.XXXXX.XXXXX.XXXXX", identidade.autenticacao),
        ("XXXXXXXXXXXXXXXXX", identidade.declaracao),
        ("XX/XX/XXXX", identidade.abertura),
        ("MUNICIPIO ANONIMIZADO / XX", identidade.municipio_uf),
    )
    return [(antigo.encode("cp1252"), novo.encode("cp1252")) for antigo, novo in pares]


def preencher(origem: Path, destino: Path, identidade: Identidade) -> int:
    """Reescreve o PDF trocando as máscaras; devolve quantas trocas foram feitas."""
    writer = PdfWriter(clone_from=str(origem))
    trocas = 0
    for pagina in writer.pages:
        conteudo = pagina.get_contents()
        if conteudo is None:  # pragma: no cover - página sem fluxo de conteúdo
            continue
        dados = conteudo.get_data()
        for antigo, novo in substituicoes(identidade):
            trocas += dados.count(antigo)
            dados = dados.replace(antigo, novo)
        conteudo.set_data(dados)
        pagina.replace_contents(conteudo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as saida:
        writer.write(saida)
    return trocas


def sobrou_mascara(caminho: Path) -> list[str]:
    """Linhas do PDF gerado que ainda contêm máscara (`XX`), para conferência."""
    import pdfplumber

    restantes: list[str] = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            for linha in (pagina.extract_text() or "").splitlines():
                if re.search(r"X{2,}", linha):
                    restantes.append(linha.strip())
    return restantes


def main() -> None:
    linhas_indice = [
        "# Exemplos de PGDAS-D com CNPJ fictício",
        "",
        "Gerado por `apps/api/scripts/preencher_cnpj_ficticio.py` a partir dos PDFs de `pdf/`.",
        "Os valores (RPA, RBT12, FS12, Fator r, DAS) são os mesmos do original; só a identificação",
        "mascarada foi preenchida. Documentos fictícios, sem validade fiscal.",
        "",
        "| Arquivo | CNPJ | Abertura | Município/UF |",
        "|---|---|---|---|",
    ]
    for identidade in IDENTIDADES:
        origem = ORIGEM / identidade.arquivo
        if not origem.exists():
            raise SystemExit(f"Não encontrei {origem}")
        destino = DESTINO / identidade.arquivo
        trocas = preencher(origem, destino, identidade)
        restantes = sobrou_mascara(destino)
        cnpj = formatar_cnpj(cnpj_com_dv(identidade.base_cnpj))
        aviso = f"  ATENÇÃO: ainda há máscara em {len(restantes)} linha(s)" if restantes else ""
        print(f"{identidade.arquivo}: {trocas} trocas · CNPJ {cnpj}{aviso}")
        for linha in restantes:
            print(f"    {linha}")
        linhas_indice.append(
            f"| `{identidade.arquivo}` | {cnpj} | {identidade.abertura} "
            f"| {identidade.municipio_uf} |"
        )
    (DESTINO / "indice.md").write_text("\n".join(linhas_indice) + "\n", encoding="utf-8")
    print(f"\n{len(IDENTIDADES)} arquivos em {DESTINO}")


if __name__ == "__main__":
    main()
