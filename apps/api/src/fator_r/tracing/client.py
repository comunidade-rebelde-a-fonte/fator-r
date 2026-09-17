"""Único ponto de contato com o Langfuse (CLAUDE.md §10.1).

- Cliente self-hosted configurado por Settings.
- Exporter monitorado: registra, por trace, se a exportação deu certo (T-407).
- Mascaramento na exportação: remove texto bruto de PDF e trunca payloads (T-406).
"""

import base64
import json
import re
import threading
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from langfuse import Langfuse
from langfuse.types import MaskOtelSpansParams, MaskOtelSpansResult, OtelSpanPatch
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from fator_r.core.settings import Settings, get_settings

CAMPOS_SENSIVEIS = frozenset({"texto_extraido", "arquivo_bytes", "conteudo_arquivo"})
MARCA_TRUNCADO = "…[truncado]"
# CNPJ com ou sem máscara vira ***<4 últimos dígitos> em tudo que vai para o Langfuse.
_RE_CNPJ = re.compile(r"\b\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}\b")
_RE_CPF = re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}\b")


def mascarar_cnpj(texto: str) -> str:
    """Mascara CNPJ e CPF (com ou sem pontuação) deixando só os 4 últimos dígitos."""

    def _mascara(m: re.Match[str]) -> str:
        return "***" + re.sub(r"\D", "", m.group(0))[-4:]

    return _RE_CPF.sub(_mascara, _RE_CNPJ.sub(_mascara, texto))


class ExportStatus:
    """Resultado de exportação por trace_id, consumido pelo job de sync."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status: dict[str, bool] = {}

    def registrar(self, trace_ids: set[str], sucesso: bool) -> None:
        with self._lock:
            for trace_id in trace_ids:
                # Uma falha de qualquer span do trace vence um sucesso anterior no mesmo ciclo.
                self._status[trace_id] = self._status.get(trace_id, True) and sucesso

    def drenar(self) -> dict[str, bool]:
        with self._lock:
            atual, self._status = self._status, {}
        return atual


export_status = ExportStatus()


class MonitoredSpanExporter(SpanExporter):
    def __init__(self, inner: SpanExporter, status: ExportStatus = export_status) -> None:
        self._inner = inner
        self._status = status

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        trace_ids = {f"{s.context.trace_id:032x}" for s in spans if s.context is not None}
        try:
            resultado = self._inner.export(spans)
        except Exception:
            self._status.registrar(trace_ids, sucesso=False)
            raise
        self._status.registrar(trace_ids, sucesso=resultado == SpanExportResult.SUCCESS)
        return resultado

    def shutdown(self) -> None:
        self._inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._inner.force_flush(timeout_millis)


def _limpar_payload(valor: Any, max_chars: int) -> Any:
    if isinstance(valor, dict):
        return {
            k: ("[removido]" if k in CAMPOS_SENSIVEIS else _limpar_payload(v, max_chars))
            for k, v in valor.items()
        }
    if isinstance(valor, list):
        return [_limpar_payload(v, max_chars) for v in valor]
    if isinstance(valor, str):
        valor = mascarar_cnpj(valor)
        if len(valor) > max_chars:
            return valor[:max_chars] + MARCA_TRUNCADO
    return valor


def mascarar_atributo(valor: Any, max_bytes: int) -> Any:
    """Remove campos sensíveis de payloads JSON e trunca textos grandes."""
    if not isinstance(valor, str):
        return valor
    texto = valor
    try:
        dados = json.loads(valor)
    except (ValueError, TypeError):
        dados = None
    if isinstance(dados, dict | list):
        texto = json.dumps(_limpar_payload(dados, max_bytes), ensure_ascii=False)
    else:
        texto = mascarar_cnpj(texto)
    if len(texto.encode()) > max_bytes:
        texto = texto.encode()[:max_bytes].decode(errors="ignore") + MARCA_TRUNCADO
    return texto


def criar_mascara(max_kb: int) -> Any:
    max_bytes = max_kb * 1024

    def mask_otel_spans(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult:
        patches: dict[Any, OtelSpanPatch | None] = {}
        for identificador, span in params.spans.items():
            alterados = {}
            for chave, valor in span.attributes.items():
                novo = mascarar_atributo(valor, max_bytes)
                if novo != valor:
                    alterados[chave] = novo
            if alterados:
                patches[identificador] = OtelSpanPatch(set_attributes=alterados)
        return MaskOtelSpansResult(span_patches=patches)

    return mask_otel_spans


def criar_cliente(settings: Settings, status: ExportStatus = export_status) -> Langfuse:
    if not settings.langfuse_tracing_enabled:
        return Langfuse(tracing_enabled=False)
    public_key = settings.langfuse_public_key or ""
    secret_key = settings.langfuse_secret_key or ""
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    exporter = OTLPSpanExporter(
        endpoint=f"{settings.langfuse_host}/api/public/otel/v1/traces",
        headers={
            "Authorization": f"Basic {auth}",
            "x-langfuse-sdk-name": "python",
            "x-langfuse-public-key": public_key,
        },
        timeout=settings.langfuse_export_timeout_s,
    )
    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        base_url=settings.langfuse_host,
        environment=settings.env,
        span_exporter=MonitoredSpanExporter(exporter, status),
        mask_otel_spans=criar_mascara(settings.trace_payload_max_kb),
    )


_override: Langfuse | None = None


@lru_cache
def _cliente_padrao() -> Langfuse:
    return criar_cliente(get_settings())


def get_langfuse() -> Langfuse:
    return _override if _override is not None else _cliente_padrao()


def usar_cliente(cliente: Langfuse | None) -> None:
    """Troca o cliente (testes de integração, ex.: Langfuse fora do ar)."""
    global _override
    _override = cliente


def novo_trace_id() -> str:
    return Langfuse.create_trace_id()


def url_do_trace(trace_id: str) -> str:
    s = get_settings()
    return f"{s.langfuse_public_url}/project/{s.langfuse_project_id}/traces/{trace_id}"


def instrumentar_anthropic() -> None:
    """Chamadas ao Claude viram generations aninhadas no span corrente (T-405)."""
    from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

    instrumentor = AnthropicInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument()
