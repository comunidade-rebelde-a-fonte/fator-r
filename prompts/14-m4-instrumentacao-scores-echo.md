# 14 — M4 · Instrumentação, mascaramento, sync, scores e agente echo (T-405 a T-408, T-411)

Branch sugerida: `feat/m4-observabilidade`

## Contexto
- `docs/tasks.md` → T-405, T-406, T-407, T-408, T-411.
- `docs/plan.md` → §7.2 (instrumentação, mascaramento, sync), §7.4 (scores).
- `CLAUDE.md` → §4.4 (Anthropic mockado nos testes), §5.3 (LGPD), §10.4 (nomes de scores).
- Consulte a doc atual do Langfuse (context7) para `mask_otel_spans` e `create_score`.

## Execute (ciclo §8 por tarefa). Ordem recomendada: T-411 cedo, para exercitar o resto.
1. **T-411:**
   - agente `echo` em `agents/echo.py`, registrado **só** quando `ENV in {dev, test}`;
   - percorre `plan → tool → decide → render` sem LLM e grava uma decisão trivial via `record_decision`;
   - endpoint `POST /agents/echo/run`, também só em dev/test.
2. **T-405:**
   - `AnthropicInstrumentor().instrument()` no startup;
   - teste com cliente Anthropic **mockado no nível HTTP** (ex.: `respx`) confirmando que a generation fica aninhada no span corrente, sem chamada real.
3. **T-406:**
   - hook `mask_otel_spans` que remove atributos com texto bruto de PDF (chave conhecida, ex.: `texto_extraido`) e trunca qualquer payload acima de `TRACE_PAYLOAD_MAX_KB`;
   - teste com um span contendo texto grande.
4. **T-407:**
   - export com sucesso marca `langfuse_sync=ok`; falha marca `failed`;
   - job periódico (APScheduler) reprocessa os `failed` e loga alerta sem dado de cliente;
   - teste com o Langfuse desligado: o agente conclui, e `agent_traces` fica `failed`.
5. **T-408 (`tracing/scores.py`):**
   - `gold(trace_id, resultados_por_campo)` grava `evals_gold` e envia `gold_<campo>` (BOOLEAN) e `gold_acerto` (NUMERIC 0–1);
   - `human(trace_id, user, nota, comentario)` grava `evals_human` e envia `human_eval` (CATEGORICAL);
   - nota `erro` sem comentário gera erro de domínio (422) antes do banco.

## Gates
`make lint`, `make test`, `pytest -m langfuse` (com o Langfuse local de pé e outra rodada com ele parado).

## Pronto quando
T-405 a T-408 e T-411 `[x]`, relatório com `trace_id` do echo, prints ou links dos scores na UI local do Langfuse e evidência do mascaramento.
