# 15 — M4 · API e tela de observabilidade + fechamento do M4 🏁 (T-409, T-410)

Branch sugerida: `feat/m4-observabilidade`

## Contexto
- `docs/tasks.md` → T-409, T-410 e **Aceite M4**.
- `docs/prd.md` → §7.9 (painel), §13 (trace consultável com spans, nota humana).
- `docs/plan.md` → §7.4 (painel: KPIs locais + custo via Langfuse), §9 (tela 6).
- `CLAUDE.md` → §6.1, §6.2, §10.4.

## Execute
1. **T-409:**
   - `GET /observability/summary`: corridas em 24 h e totais, pendências sem nota humana, acerto ouro, acerto humano e, por agente, volume, latência média, confiança média, erros e reviews, tudo do Postgres. Custo e tokens do Claude vêm da API de métricas do Langfuse, com cache de 5 min e fallback `null` se ele estiver fora;
   - `GET /traces?agente=&status=&sem_nota=` paginado;
   - `GET /traces/{id}`: resumo local + spans lidos da API do Langfuse (se ele estiver fora, mostra o resumo e o aviso "spans indisponíveis") + evals + `langfuse_url`;
   - `POST /traces/{id}/human-eval`.
2. **T-410:**
   - página `/observabilidade` com cards, tabela por agente e lista de traces com filtros;
   - detalhe do trace: timeline de spans (nome, duração, status), evals ouro por campo, formulário de nota humana (`acerto/parcial/erro`, comentário obrigatório em `erro` validado no front **e** no back) e botão "abrir no Langfuse".
3. **Verifique no navegador** usando corridas do agente `echo`.
4. **Fechamento do M4 (etapa 8)**, com evidência:
   - corrida do `echo` aparece no Langfuse com o mesmo `trace_id` e os spans `plan → tool → decide → render`;
   - nota humana gravada no Postgres e visível como `human_eval` no Langfuse;
   - nota `erro` sem comentário recusada na API e no banco;
   - com o Langfuse parado, a corrida grava `agent_traces` com `langfuse_sync=failed` e a tela continua funcionando.
5. **Regressão:** aceites de M0 a M2 (e M3, se já fechado).

## Gates
`make lint`, `make test`, `pytest -m langfuse`, isolamento, `tsc --noEmit`, build e navegador.

## Pronto quando
- T-409 e T-410 `[x]`.
- Tabela "Aceite M4 → evidência".
- **Pergunta final:** "Confirma o fechamento do M4?"
