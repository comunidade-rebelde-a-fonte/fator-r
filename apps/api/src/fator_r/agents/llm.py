"""Cliente do Claude para os agentes (T-605).

O LLM só classifica a intenção (span plan) e redige o texto a partir de uma decisão já calculada
(span render). Nenhum cálculo passa por aqui (CLAUDE.md §3.1).
"""

import json
from decimal import Decimal
from functools import lru_cache
from importlib import resources
from typing import Any, Literal, Protocol

from anthropic.types import (
    MessageParam,
    OutputConfigParam,
    ThinkingConfigDisabledParam,
    ToolChoiceToolParam,
    ToolParam,
)
from pydantic import BaseModel, Field, ValidationError, field_validator

from fator_r.core.settings import get_settings

PROMPT_VERSION = "2026.09.1"
MODELO_PADRAO = "claude-sonnet-5"

TipoIntencao = Literal["status_empresa", "simular", "explicar", "priorizar"]


class Intencao(BaseModel):
    intencao: TipoIntencao
    company_ref: str | None = None
    pa: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    meta: Decimal | None = Field(default=None, ge=Decimal("0.28"), lt=1)

    @field_validator("pa")
    @classmethod
    def _pa_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        from fator_r.core.competencia import CompetenciaInvalida, parse_competencia

        try:
            parse_competencia(valor)
        except CompetenciaInvalida:
            return None
        return valor if "2000-01" <= valor <= "2100-12" else None


class LLMIndisponivel(RuntimeError):
    pass


class ClienteLLM(Protocol):
    async def classificar(self, mensagem: str, empresas: list[str]) -> Intencao: ...

    async def redigir(self, decisao: dict[str, Any]) -> str: ...


def _prompt(nome: str) -> str:
    return (resources.files("fator_r.agents.prompts") / f"{nome}.md").read_text(encoding="utf-8")


FERRAMENTA_INTENCAO: ToolParam = {
    "name": "classificar_intencao",
    "description": "Registra a intenção do pedido do analista e os parâmetros citados.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "intencao": {
                "type": "string",
                "enum": ["status_empresa", "simular", "explicar", "priorizar"],
            },
            "company_ref": {"type": ["string", "null"]},
            "pa": {"type": ["string", "null"]},
            "meta": {"type": ["number", "null"]},
        },
        "required": ["intencao", "company_ref", "pa", "meta"],
        "additionalProperties": False,
    },
}


# Chamadas curtas de classificação/redação: sem thinking e esforço baixo (Claude Sonnet 5 não
# aceita temperature diferente do padrão).
SEM_THINKING: ThinkingConfigDisabledParam = {"type": "disabled"}
ESFORCO_BAIXO: OutputConfigParam = {"effort": "low"}
ESCOLHA_INTENCAO: ToolChoiceToolParam = {"type": "tool", "name": "classificar_intencao"}


class AnthropicLLM:
    def __init__(self, api_key: str, modelo: str = MODELO_PADRAO, http_client: Any = None) -> None:
        from anthropic import AsyncAnthropic

        self.modelo = modelo
        self._client = AsyncAnthropic(
            api_key=api_key, timeout=20.0, max_retries=2, http_client=http_client
        )

    async def classificar(self, mensagem: str, empresas: list[str]) -> Intencao:
        import anthropic

        # Só a mensagem do analista vai ao LLM: nenhuma lista de empresas, CNPJ ou valor.
        # A empresa citada é resolvida localmente (agents/etapas.py). Revisão de segurança M3.
        conteudo = f"Pedido: {mensagem}"
        mensagens: list[MessageParam] = [{"role": "user", "content": conteudo}]
        try:
            resposta = await self._client.messages.create(
                model=self.modelo,
                max_tokens=512,
                system=_prompt("plan"),
                thinking=SEM_THINKING,
                output_config=ESFORCO_BAIXO,
                tools=[FERRAMENTA_INTENCAO],
                tool_choice=ESCOLHA_INTENCAO,
                messages=mensagens,
            )
        except anthropic.APIError as exc:
            raise LLMIndisponivel(type(exc).__name__) from exc
        for bloco in resposta.content:
            if bloco.type == "tool_use" and bloco.name == "classificar_intencao":
                try:
                    return Intencao.model_validate(bloco.input)
                except ValidationError as exc:
                    raise LLMIndisponivel("intencao_invalida") from exc
        raise LLMIndisponivel(f"sem_tool_use ({resposta.stop_reason})")

    async def redigir(self, decisao: dict[str, Any]) -> str:
        """Recebe só a decisão já calculada (valores necessários ao texto; nunca CNPJ)."""
        import anthropic

        try:
            resposta = await self._client.messages.create(
                model=self.modelo,
                max_tokens=1024,
                system=_prompt("render"),
                thinking={"type": "disabled"},
                output_config={"effort": "low"},
                messages=[
                    {
                        "role": "user",
                        "content": "DECISÃO:\n"
                        + json.dumps(decisao, ensure_ascii=False, default=str),
                    }
                ],
            )
        except anthropic.APIError as exc:
            raise LLMIndisponivel(type(exc).__name__) from exc
        if resposta.stop_reason == "refusal":
            raise LLMIndisponivel("refusal")
        texto = "".join(b.text for b in resposta.content if b.type == "text").strip()
        if not texto:
            raise LLMIndisponivel("texto_vazio")
        return texto


class LLMDeterministico:
    """Sem chamada externa: classificação por palavras-chave e texto por template.

    Usado em ENV test e no E2E (LLM_PROVIDER=fake). Nunca em produção.
    """

    async def classificar(self, mensagem: str, empresas: list[str]) -> Intencao:
        from fator_r.agents.intencao import classificar_por_palavras

        return classificar_por_palavras(mensagem, empresas)

    async def redigir(self, decisao: dict[str, Any]) -> str:
        raise LLMIndisponivel("llm_deterministico_usa_template")


_override: ClienteLLM | None = None


@lru_cache
def _cliente_padrao() -> ClienteLLM:
    settings = get_settings()
    if settings.llm_provider == "fake" or settings.env == "test":
        if settings.env == "prod":
            raise RuntimeError("LLM_PROVIDER=fake não é permitido em produção")
        return LLMDeterministico()
    if not settings.anthropic_api_key:
        if settings.env == "prod":
            raise RuntimeError("ANTHROPIC_API_KEY ausente em produção")
        return LLMDeterministico()
    return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)


def get_llm() -> ClienteLLM:
    return _override if _override is not None else _cliente_padrao()


def usar_llm(cliente: ClienteLLM | None) -> None:
    global _override
    _override = cliente
