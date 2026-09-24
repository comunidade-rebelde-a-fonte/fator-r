"""Dataset `pgdas_extratos` no Langfuse + experimento da versão atual do parser (T-513).

O dataset guarda só o nome da fixture e o expected.json: o texto dos extratos nunca sai da
máquina. Uso: make parser-experiment (exige make up-langfuse).
"""

import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "true")

from langfuse import Evaluation

from fator_r.core.settings import get_settings
from fator_r.core.uploads import detectar_mime
from fator_r.parsing.pgdas import CAMPOS, PARSER_VERSION, parse, resultado_vazio
from fator_r.parsing.texto import extrair_texto
from fator_r.tracing.client import criar_cliente

DATASET = "pgdas_extratos"
PASTA = Path(__file__).resolve().parents[1] / "fixtures" / "pgdas"


def _igual(obtido: Any, esperado: Any) -> bool:
    if obtido is None or esperado is None:
        return bool(obtido == esperado)
    try:
        return Decimal(str(obtido)) == Decimal(str(esperado))
    except ArithmeticError:
        return bool(obtido == esperado)


def task(*, item: Any, **_: Any) -> dict[str, Any]:
    nome = item.input["fixture"]
    documento = next((PASTA / nome).glob("documento.*"))
    conteudo = documento.read_bytes()
    texto = extrair_texto(conteudo, detectar_mime(conteudo))
    resultado = resultado_vazio(texto.motivo) if texto.motivo else parse(texto.texto)
    return {"campos": resultado.campos, "confianca": str(resultado.confianca)}


def avaliar_campos(*, output: Any, expected_output: Any, **_: Any) -> list[Evaluation]:
    avaliacoes = [
        Evaluation(
            name=f"campo_{campo}",
            value=1.0 if _igual(output["campos"][campo], expected_output["campos"][campo]) else 0.0,
        )
        for campo in CAMPOS
    ]
    acertos = sum(a.value for a in avaliacoes)  # type: ignore[misc]
    avaliacoes.append(Evaluation(name="acerto_campos", value=acertos / len(CAMPOS)))
    return avaliacoes


def main() -> None:
    langfuse = criar_cliente(get_settings())
    try:
        langfuse.get_dataset(DATASET)
    except Exception:
        langfuse.create_dataset(
            name=DATASET, description="Extratos PGDAS-D (só nome da fixture e campos esperados)"
        )
    pastas = sorted(p for p in PASTA.iterdir() if (p / "expected.json").exists())
    for pasta in pastas:
        esperado = json.loads((pasta / "expected.json").read_text())
        langfuse.create_dataset_item(
            dataset_name=DATASET,
            id=f"pgdas-{pasta.name}",
            input={"fixture": pasta.name},
            expected_output={"campos": esperado["campos"]},
            metadata={
                "sintetica": esperado.get("sintetica", True),
                # Campos que o documento tem e o parser ainda não lê: contam como erro.
                "lacunas_conhecidas": sorted(esperado.get("lacunas_conhecidas", {})),
            },
        )
    dataset = langfuse.get_dataset(DATASET)
    carimbo = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    resultado = dataset.run_experiment(
        name=f"parser-{PARSER_VERSION}",
        run_name=f"parser-{PARSER_VERSION}-{carimbo}",
        description="Parser determinístico contra as fixtures",
        task=task,
        evaluators=[avaliar_campos],
        metadata={"parser_version": PARSER_VERSION},
    )
    langfuse.flush()
    notas = [
        e.value
        for item in resultado.item_results
        for e in item.evaluations
        if e.name == "acerto_campos"
    ]
    media = sum(notas) / len(notas) if notas else 0  # type: ignore[arg-type]
    sys.stdout.write(
        f"Dataset {DATASET}: {len(pastas)} itens · experimento parser-{PARSER_VERSION} "
        f"· acerto médio {media:.1%}\n"
    )


if __name__ == "__main__":
    main()
