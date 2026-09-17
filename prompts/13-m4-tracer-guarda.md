# 13 — M4 · Tracer Langfuse e guarda "sem trace não grava" (T-401 a T-404)

Branch sugerida: `feat/m4-observabilidade`
Pré-condição: M2 fechado (pode correr em paralelo ao M3).

## Contexto
- `docs/tasks.md` → T-401 a T-404.
- `docs/plan.md` → §7.1 e §7.2 (contrato do tracing), §4 (`agent_traces`, `evals_gold`, `evals_human`).
- `docs/prd.md` → §7.9, §8 (observabilidade).
- `CLAUDE.md` → §3.10, §5.3, §10.4.
- **Antes de codar:** consulte a documentação atual do SDK Python do Langfuse (context7: `/langfuse/langfuse-docs`) para `get_client`, `start_as_current_observation`, `trace_context`, `propagate_attributes` e `create_trace_id`. Não confie em memória.

## Execute (ciclo §8 por tarefa)
1. **T-401:**
   - dependências `langfuse` e `opentelemetry-instrumentation-anthropic`;
   - settings `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` e `LANGFUSE_TRACING_ENABLED`, apontando para o Langfuse **local** do prompt 02;
   - cliente inicializado uma vez no lifespan do FastAPI, com `flush` no shutdown.
2. **T-402:**
   - migrações `agent_traces` (id `char(32)` hex, `langfuse_sync` enum), `evals_gold` e `evals_human` (CHECK: `nota <> 'erro' OR comentario IS NOT NULL AND length(trim(comentario)) > 0`);
   - todas com `firm_id` e RLS.
3. **T-403 (`tracing/tracer.py`):** context manager async `tracer.run(agente, gatilho, user, company, entrada)` que:
   - gera `trace_id` com `create_trace_id()`;
   - insere `agent_traces` na transação corrente;
   - abre a observation raiz com `trace_context={"trace_id": ...}`;
   - aplica `propagate_attributes` (user_id, session_id = company, tags `agente`, `gatilho`, `firm:<id>`) e a metadata da CLAUDE.md §10.4;
   - oferece `run.span(nome)`, restrito a `plan|parse|tool|decide|render` (`ValueError` fora disso);
   - fecha com `run.finish(decisao, texto, confianca, status)`, que atualiza latência, status e saída;
   - em exceção: status `error`, rollback das escritas de decisão, trace local preservado numa transação separada.
4. **T-404:**
   - `tracing.record_decision(run, model, **valores)` como **único** caminho de escrita para tabelas de decisão;
   - FKs `trace_id NOT NULL`;
   - teste que tenta gravar decisão sem `run` e espera falha, tanto por API Python quanto por SQL direto (constraint).

## Testes obrigatórios
- Com `LANGFUSE_TRACING_ENABLED=false`: o trace local é criado, spans válidos e inválidos, `finish`, exceção dentro do run.
- `@pytest.mark.langfuse` com o Langfuse local de pé: o trace existe no Langfuse com o mesmo id e tags (busca pela API pública).

## Gates
`make lint`, `make test`, `pytest -m langfuse`, migração do zero.

## Pronto quando
T-401 a T-404 `[x]` e o relatório com um `trace_id` de exemplo visível na UI local do Langfuse.
