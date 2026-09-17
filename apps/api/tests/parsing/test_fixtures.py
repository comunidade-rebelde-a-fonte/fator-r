"""Parser contra as fixtures (T-508): campo a campo e faixa de confiança."""

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from fator_r.core.uploads import detectar_mime
from fator_r.parsing.pgdas import CAMPOS, ResultadoParse, parse, resultado_vazio
from fator_r.parsing.texto import extrair_texto

PASTA = Path(__file__).resolve().parents[2] / "fixtures" / "pgdas"
FIXTURES = sorted(p for p in PASTA.iterdir() if p.is_dir() and (p / "expected.json").exists())


def processar(pasta: Path) -> tuple[ResultadoParse, dict[str, Any]]:
    documento = next(pasta.glob("documento.*"))
    conteudo = documento.read_bytes()
    texto = extrair_texto(conteudo, detectar_mime(conteudo))
    resultado = resultado_vazio(texto.motivo) if texto.motivo else parse(texto.texto)
    return resultado, json.loads((pasta / "expected.json").read_text())


def _igual(obtido: str | None, esperado: str | None) -> bool:
    if obtido is None or esperado is None:
        return obtido == esperado
    try:
        return Decimal(obtido) == Decimal(esperado)
    except ArithmeticError:
        return obtido == esperado


@pytest.mark.parametrize("pasta", FIXTURES, ids=lambda p: p.name)
def test_fixture(pasta: Path) -> None:
    resultado, esperado = processar(pasta)
    for campo in CAMPOS:
        assert _igual(resultado.campos[campo], esperado["campos"][campo]), (
            f"{pasta.name}.{campo}: obtido={resultado.campos[campo]} "
            f"esperado={esperado['campos'][campo]}"
        )
    assert Decimal(str(esperado["confianca_min"])) <= resultado.confianca, resultado
    assert resultado.confianca <= Decimal(str(esperado["confianca_max"])), resultado
    if esperado.get("motivo"):
        assert esperado["motivo"] in resultado.motivos


def test_acerto_por_campo_e_meta_de_80_por_cento() -> None:
    acertos: Counter[str] = Counter()
    totais: Counter[str] = Counter()
    por_tipo = {"sinteticas": [0, 0], "reais": [0, 0]}
    for pasta in FIXTURES:
        resultado, esperado = processar(pasta)
        tipo = "sinteticas" if esperado.get("sintetica", True) else "reais"
        for campo in CAMPOS:
            ok = _igual(resultado.campos[campo], esperado["campos"][campo])
            acertos[campo] += ok
            totais[campo] += 1
            por_tipo[tipo][0] += ok
            por_tipo[tipo][1] += 1
    print("\nAcerto do parser por campo:")
    for campo in CAMPOS:
        print(f"  {campo:8s} {acertos[campo]}/{totais[campo]}")
    for tipo, (ok, total) in por_tipo.items():
        taxa = f"{ok / total:.1%}" if total else "sem fixtures"
        print(f"  {tipo}: {taxa}")
    ok, total = por_tipo["sinteticas"]
    assert ok / total >= 0.80


def test_parsing_nao_usa_llm() -> None:
    fontes = Path(__file__).resolve().parents[2] / "src" / "fator_r" / "parsing"
    for arquivo in fontes.glob("*.py"):
        assert "anthropic" not in arquivo.read_text(), arquivo.name
