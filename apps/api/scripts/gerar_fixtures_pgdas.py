"""Gera as fixtures SINTÉTICAS de extrato PGDAS-D (T-504).

Layout inspirado no "Extrato do Simples Nacional"; não substitui extratos reais (P-03).
Uso: uv run python scripts/gerar_fixtures_pgdas.py
"""

import json
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "fixtures" / "pgdas"

PADRAO = """Extrato do Simples Nacional
Período de Apuração (PA): 09/2026
Data de abertura no CNPJ: 15/03/2019
CNPJ Matriz: 11.222.333/0001-81
Nome empresarial: CLINICA EXEMPLO LTDA
Regime de Apuração: Competência
Optante pelo Simples Nacional: Sim

2) Informações da Declaração
2.1) Discriminativo de Receitas
Valores Declarados                     Mercado Interno   Mercado Externo   Total
Receita Bruta do PA (RPA) - Competência   50.000,00   0,00   50.000,00
Receita bruta acumulada nos doze meses anteriores ao PA (RBT12)   600.000,00   0,00   600.000,00
Receita bruta acumulada no ano-calendário corrente (RBA)   400.000,00   0,00   400.000,00

2.3) Folha de Salários Anteriores (R$)
Total de Folhas de Salários Anteriores (R$)   180.000,00

2.8) Cálculo do Valor Devido
Estabelecimento: 11.222.333/0001-81
Atividade: Prestação de serviços sujeitos ao Fator r - Anexo III
Fator r: 0,30
Valor Total do Débito Declarado (R$): 5.280,00
"""

COMPLETO = {
    "cnpj": "11222333000181",
    "pa": "2026-09",
    "rbt12": "600000.00",
    "rpa": "50000.00",
    "fs12": "180000.00",
    "fator_r": "0.30",
    "das": "5280.00",
    "anexo": "III",
}

FIXTURES: dict[str, dict[str, object]] = {
    "txt_padrao": {"texto": PADRAO, "esperado": COMPLETO, "confianca": [0.95, 1.0]},
    "txt_rotulos_alternativos": {
        "texto": """PGDAS-D - Declaração
PA: 09/2026
CNPJ: 11222333000181
RPA: 50.000,00
RBT12: 600.000,00
Folha de salários (FS12): 180.000,00
Fator R = 30,00%
Enquadramento: Anexo III
Total do DAS: 5.280,00
""",
        "esperado": {**COMPLETO, "fator_r": "0.3000"},
        "confianca": [0.95, 1.0],
    },
    "txt_espacamento_irregular_latin1": {
        "texto": PADRAO.replace("   ", "\t \t").replace(": ", " :   ").replace("\n", "\r\n"),
        "encoding": "latin-1",
        "esperado": COMPLETO,
        "confianca": [0.95, 1.0],
    },
    "txt_cnpj_dv_invalido": {
        "texto": PADRAO.replace("11.222.333/0001-81", "11.222.333/0001-82"),
        "esperado": {**COMPLETO, "cnpj": "11222333000182"},
        "confianca": [0.85, 0.95],
    },
    "txt_sem_cnpj": {
        "texto": "\n".join(linha for linha in PADRAO.splitlines() if "11.222.333" not in linha),
        "esperado": {**COMPLETO, "cnpj": None},
        "confianca": [0.80, 0.90],
    },
    "txt_parcial_sem_folha_e_fator": {
        "texto": "\n".join(
            linha
            for linha in PADRAO.splitlines()
            if "Folhas de Salários Anteriores (R$)" not in linha and not linha.startswith("Fator r")
        ),
        "esperado": {**COMPLETO, "fs12": None, "fator_r": None},
        "confianca": [0.70, 0.85],
    },
    "txt_anexo_v": {
        "texto": PADRAO.replace("180.000,00", "120.000,00")
        .replace("Fator r: 0,30", "Fator r: 0,20")
        .replace("Anexo III", "Anexo V")
        .replace("5.280,00", "8.925,00"),
        "esperado": {
            **COMPLETO,
            "fs12": "120000.00",
            "fator_r": "0.20",
            "anexo": "V",
            "das": "8925.00",
        },
        "confianca": [0.95, 1.0],
    },
    "txt_sem_relacao": {
        "texto": "Ata de reunião de sócios\nAssunto: aumento de pró-labore\nSem valores.\n",
        "esperado": {k: None for k in COMPLETO},
        "confianca": [0.0, 0.05],
    },
    "pdf_com_texto": {"texto": PADRAO, "pdf": True, "esperado": COMPLETO, "confianca": [0.95, 1.0]},
    "pdf_sem_camada_texto": {
        "pdf_sem_texto": True,
        "esperado": {k: None for k in COMPLETO},
        "confianca": [0.0, 0.0],
        "motivo": "sem_camada_texto",
    },
}


def _escapar(linha: str) -> bytes:
    bruto = linha.encode("cp1252", errors="replace")
    return bruto.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def pdf(linhas: list[str] | None) -> bytes:
    """PDF mínimo (Helvetica/WinAnsi). Sem linhas: só um desenho, sem camada de texto."""
    if linhas is None:
        conteudo = b"0.5 w 40 700 m 300 700 l S"
    else:
        conteudo = (
            b"BT /F1 9 Tf 40 770 Td 11 TL "
            + b" ".join(b"(" + _escapar(linha) + b") Tj T*" for linha in linhas)
            + b" ET"
        )
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(conteudo)).encode() + b" >>\nstream\n" + conteudo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    saida = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objetos, start=1):
        offsets.append(len(saida))
        saida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        saida += f"{off:010d} 00000 n \n".encode()
    saida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(saida)


def main() -> None:
    for nome, spec in FIXTURES.items():
        pasta = DESTINO / nome
        pasta.mkdir(parents=True, exist_ok=True)
        for antigo in pasta.glob("documento.*"):
            antigo.unlink()
        if spec.get("pdf_sem_texto"):
            (pasta / "documento.pdf").write_bytes(pdf(None))
        elif spec.get("pdf"):
            (pasta / "documento.pdf").write_bytes(pdf(str(spec["texto"]).splitlines()))
        else:
            encoding = str(spec.get("encoding", "utf-8"))
            (pasta / "documento.txt").write_bytes(str(spec["texto"]).encode(encoding))
        esperado = {
            "sintetica": True,
            "campos": spec["esperado"],
            "confianca_min": spec["confianca"][0],  # type: ignore[index]
            "confianca_max": spec["confianca"][1],  # type: ignore[index]
            "motivo": spec.get("motivo"),
        }
        (pasta / "expected.json").write_text(
            json.dumps(esperado, indent=2, ensure_ascii=False) + "\n"
        )
    print(f"{len(FIXTURES)} fixtures em {DESTINO}")


if __name__ == "__main__":
    main()
