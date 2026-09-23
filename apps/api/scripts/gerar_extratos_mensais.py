"""Gera extratos fictícios dos meses seguintes a partir dos PDFs de `pdf/com_cnpj/`.

Cada PDF de PA 08/2026 vira também PA 09, 10 e 11/2026, com o mesmo layout: o texto do próprio PDF
é reescrito (período, meses das tabelas 2.2/2.3, RBA, data de transmissão, número da declaração,
recibo e autenticação). Os valores mensais continuam iguais aos do original, então RBT12, FS12 e
Fator r se mantêm. Documentos fictícios, sem validade fiscal.

Uso: uv run python scripts/gerar_extratos_mensais.py
Saída: pdf/com_cnpj/AAAA-MM/<mesmo nome>.pdf (08/2026 = cópia do original) + indice_mensal.md
"""

import calendar
import re
import shutil
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from pypdf import PdfWriter

from fator_r.core.competencia import somar_meses

RAIZ = Path(__file__).resolve().parents[3]
ORIGEM = RAIZ / "pdf" / "com_cnpj"
PA_BASE = date(2026, 8, 1)
MESES_SEGUINTES = 3

_RE_MES_TABELA = re.compile(rb"\((\d{2})/(\d{4})\) Tj")


@dataclass(frozen=True)
class Original:
    arquivo: str
    receita_mensal: Decimal
    declaracao: str
    recibo: str
    autenticacao: str
    transmissao: str


ORIGINAIS = (
    Original(
        "01_servico_fator_r_abaixo_28.pdf",
        Decimal("10000"),
        "20260914000000001",
        "35.26.10001.0000001-1",
        "A1B2C.D3E4F.G5H6I.J7K8L",
        "14/09/2026 09:12:33",
    ),
    Original(
        "02_comercio_sem_fator_r.pdf",
        Decimal("12000"),
        "20260914000000002",
        "35.26.10002.0000002-2",
        "B2C3D.E4F5G.H6I7J.K8L9M",
        "14/09/2026 09:31:07",
    ),
    Original(
        "03_servico_sem_fator_r.pdf",
        Decimal("12000"),
        "20260914000000003",
        "31.26.10003.0000003-3",
        "C3D4E.F5G6H.I7J8K.L9M0N",
        "14/09/2026 10:02:55",
    ),
    Original(
        "04_servico_fator_r_acima_28.pdf",
        Decimal("10000"),
        "20260914000000004",
        "41.26.10004.0000004-4",
        "D4E5F.G6H7I.J8K9L.M0N1O",
        "14/09/2026 10:44:18",
    ),
)


def reais(valor: Decimal) -> str:
    """Formato do extrato: 1.234,56."""
    inteiro, centavos = f"{valor:.2f}".split(".")
    return f"{int(inteiro):,}".replace(",", ".") + "," + centavos


def periodo(pa: date) -> str:
    ultimo = calendar.monthrange(pa.year, pa.month)[1]
    return f"01/{pa:%m/%Y} a {ultimo:02d}/{pa:%m/%Y}"


def trocas(original: Original, deslocamento: int) -> list[tuple[bytes, bytes]]:
    """Textos fixos que mudam de um PA para o outro (o mais específico primeiro)."""
    pa = somar_meses(PA_BASE, deslocamento)
    envio = somar_meses(pa, 1)
    sufixo = f"{deslocamento:01d}"
    rba_antigo = original.receita_mensal * PA_BASE.month
    rba_novo = original.receita_mensal * pa.month
    hora = original.transmissao.split(" ")[1]
    pares = (
        (periodo(PA_BASE), periodo(pa)),
        (original.transmissao, f"14/{envio:%m/%Y} {hora}"),
        (original.declaracao, f"{envio:%Y%m}14{original.declaracao[8:-1]}{sufixo}"),
        (original.recibo, original.recibo[:-1] + sufixo),
        (original.autenticacao, original.autenticacao[:-1] + sufixo),
        (f"({reais(rba_antigo)}) Tj", f"({reais(rba_novo)}) Tj"),
    )
    return [(a.encode("cp1252"), b.encode("cp1252")) for a, b in pares]


def deslocar_meses(dados: bytes, deslocamento: int) -> bytes:
    """Meses das tabelas 2.2 e 2.3 (células "MM/AAAA") andam junto com o PA."""

    def novo(match: re.Match[bytes]) -> bytes:
        mes = somar_meses(date(int(match.group(2)), int(match.group(1)), 1), deslocamento)
        return f"({mes:%m/%Y}) Tj".encode()

    return _RE_MES_TABELA.sub(novo, dados)


def gerar(original: Original, deslocamento: int, destino: Path) -> None:
    writer = PdfWriter(clone_from=str(ORIGEM / original.arquivo))
    rba = f"({reais(original.receita_mensal * PA_BASE.month)}) Tj".encode("cp1252")
    for numero, pagina in enumerate(writer.pages, start=1):
        conteudo = pagina.get_contents()
        if conteudo is None:  # pragma: no cover - página sem fluxo de conteúdo
            continue
        dados = conteudo.get_data()
        if numero == 1 and dados.count(rba) != 2:
            raise SystemExit(f"{original.arquivo}: RBA esperado 2x na página 1")
        for antigo, novo in trocas(original, deslocamento):
            dados = dados.replace(antigo, novo)
        conteudo.set_data(deslocar_meses(dados, deslocamento))
        pagina.replace_contents(conteudo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as saida:
        writer.write(saida)


def main() -> None:
    linhas = [
        "# Extratos fictícios por mês",
        "",
        "Gerado por `apps/api/scripts/gerar_extratos_mensais.py`. Mesmo CNPJ e mesmos valores",
        "mensais do original; muda o PA, a janela das tabelas e a receita acumulada no ano (RBA).",
        "Suba na ordem dos meses para simular o fluxo mensal. Sem validade fiscal.",
        "",
        "| Pasta | PA | Tabelas 2.2/2.3 (janela) |",
        "|---|---|---|",
    ]
    for deslocamento in range(MESES_SEGUINTES + 1):
        pa = somar_meses(PA_BASE, deslocamento)
        pasta = ORIGEM / f"{pa:%Y-%m}"
        for original in ORIGINAIS:
            destino = pasta / original.arquivo
            if deslocamento == 0:
                pasta.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ORIGEM / original.arquivo, destino)
            else:
                gerar(original, deslocamento, destino)
        inicio, fim = somar_meses(pa, -12), somar_meses(pa, -1)
        linhas.append(f"| `{pa:%Y-%m}/` | {pa:%m/%Y} | {inicio:%m/%Y} a {fim:%m/%Y} |")
        print(f"{pasta.relative_to(RAIZ)}: {len(ORIGINAIS)} extratos (PA {pa:%m/%Y})")
    (ORIGEM / "indice_mensal.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
