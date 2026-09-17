"""T-706: traces gerados pelo E2E conferidos na API pública do Langfuse.

Roda por `make e2e` (depois do Playwright), que grava apps/web/e2e/.saida/traces.json.
"""

import asyncio
import json
from pathlib import Path

import pytest

from fator_r.tracing.consulta import LangfuseConsulta
from tests.integration.test_langfuse import _settings

pytestmark = pytest.mark.e2e_langfuse
SAIDA = Path(__file__).resolve().parents[4] / "apps/web/e2e/.saida/traces.json"


def _traces() -> dict[str, str]:
    assert SAIDA.exists(), "Rode o E2E antes (make e2e): traces.json não encontrado"
    return dict(json.loads(SAIDA.read_text()))


async def _observacoes(
    consulta: LangfuseConsulta, trace_id: str, minimo: int
) -> list[dict[str, object]]:
    obs: list[dict[str, object]] = []
    for _ in range(90):
        obs = await consulta.observacoes(trace_id)
        if len(obs) >= minimo:
            break
        await asyncio.sleep(1)
    return obs


async def test_spans_do_e2e_no_langfuse() -> None:
    consulta = LangfuseConsulta(_settings())
    traces = _traces()
    esperados = {
        "parser_linked": {"parser_pgdas", "parse", "tool", "decide", "render"},
        "simulacao": {"consultor", "tool", "decide", "render"},
        "priorizador": {"priorizador", "plan", "tool", "decide", "render"},
    }
    for nome, spans in esperados.items():
        obs = await _observacoes(consulta, traces[nome], len(spans))
        assert spans <= {str(o["name"]) for o in obs}, nome
        assert all(o["traceId"] == traces[nome] for o in obs)


async def test_scores_ouro_e_nota_humana_do_e2e() -> None:
    consulta = LangfuseConsulta(_settings())
    trace_id = _traces()["parser_linked"]
    nomes: set[str] = set()
    for _ in range(90):
        nomes = {str(s["name"]) for s in await consulta.scores(trace_id)}
        if "human_eval" in nomes and any(n.startswith("gold_") for n in nomes):
            break
        await asyncio.sleep(1)
    assert "human_eval" in nomes
    assert {"gold_cnpj"} <= nomes


async def test_texto_bruto_do_extrato_nao_esta_no_langfuse() -> None:
    consulta = LangfuseConsulta(_settings())
    obs = await _observacoes(consulta, _traces()["parser_linked"], 5)
    bruto = json.dumps(obs, ensure_ascii=False)
    assert "Discriminativo de Receitas" not in bruto
    assert "Nome empresarial" not in bruto
