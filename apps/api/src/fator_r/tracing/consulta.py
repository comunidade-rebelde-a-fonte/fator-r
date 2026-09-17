"""Leitura da API pública do Langfuse v4 (modo events: v2/observations, v3/scores, v2/metrics)."""

import json
from datetime import datetime
from typing import Any

import httpx

from fator_r.core.settings import Settings, get_settings


class LangfuseIndisponivel(RuntimeError):
    pass


class LangfuseConsulta:
    def __init__(self, settings: Settings | None = None, timeout_s: float = 5.0) -> None:
        s = settings or get_settings()
        self._base = s.langfuse_host
        self._auth = (s.langfuse_public_key or "", s.langfuse_secret_key or "")
        self._timeout = timeout_s

    async def _get(self, caminho: str, params: dict[str, Any]) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http:
                resposta = await http.get(f"{self._base}{caminho}", params=params, auth=self._auth)
                resposta.raise_for_status()
                return resposta.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LangfuseIndisponivel(type(exc).__name__) from exc

    async def observacoes(self, trace_id: str) -> list[dict[str, Any]]:
        dados = await self._get(
            "/api/public/v2/observations",
            {"traceId": trace_id, "fields": "basic,io,usage,metrics,trace_context", "limit": 200},
        )
        return list(dados.get("data", []))

    async def scores(self, trace_id: str) -> list[dict[str, Any]]:
        dados = await self._get(
            "/api/public/v3/scores",
            {"traceId": trace_id, "fields": "details,subject", "limit": 100},
        )
        return list(dados.get("data", []))

    async def custo_e_tokens(
        self, desde: datetime, ate: datetime, tag_escritorio: str
    ) -> dict[str, Any]:
        """Custo e tokens das generations do escritório no período (view observations)."""
        query = {
            "view": "observations",
            "metrics": [
                {"measure": "totalCost", "aggregation": "sum"},
                {"measure": "totalTokens", "aggregation": "sum"},
            ],
            "dimensions": [],
            "filters": [
                {
                    "column": "tags",
                    "operator": "any of",
                    "value": [tag_escritorio],
                    "type": "arrayOptions",
                },
            ],
            "fromTimestamp": desde.isoformat(),
            "toTimestamp": ate.isoformat(),
        }
        dados = await self._get("/api/public/v2/metrics", {"query": json.dumps(query)})
        linha = (dados.get("data") or [{}])[0]
        return {
            "custo_total": linha.get("sum_totalCost"),
            "tokens_total": linha.get("sum_totalTokens"),
        }
