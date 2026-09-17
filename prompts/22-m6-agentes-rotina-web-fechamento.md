# 22 — M6 · Consultor, priorizador, rotina semanal e telas + fechamento do M6 🏁 (T-609 a T-613)

Branch sugerida: `feat/m6-simulador-agentes`

## Contexto
- `docs/tasks.md` → T-609 a T-613 e **Aceite M6**.
- `docs/prd.md` → §7.8 (tabela de agentes, contrato de saída), §12 (histórias), §13.
- `docs/plan.md` → §7.3, §9 (tela 5).
- `CLAUDE.md` → §3.1, §3.10 a §3.12, §3.14, §6.2.

## Execute (ciclo §8 por tarefa)
1. **T-609 — `POST /agents/consultor/chat {mensagem, company_id?}`:**
   - `plan` (T-606);
   - `tool`: motor e/ou simulador conforme a intenção; **simular** persiste a simulação como no T-603;
   - `decide`: anexo, gap e veredito, com a guarda do T-608;
   - `render` (T-607);
   - resposta `{texto, decisao, trace_id}`.
2. **T-610 — `POST /agents/priorizador/chat {mensagem, pa?}`:**
   - `tool`: carteira do PA (reusa `domain/carteira.py`);
   - `decide`: fila só de vermelhos e amarelos, ordenada por economia;
   - `render` com validador;
   - resposta `{texto, decisao: {fila: [...]}, trace_id}`.
3. **T-611 — rotina semanal:**
   - job APScheduler aos domingos (horário configurável, fuso `America/Sao_Paulo`) que roda o priorizador para cada escritório com `gatilho="rotina"`;
   - `plan` sem LLM e `render` por template;
   - resultado consultável no trace;
   - idempotente na mesma semana.
4. **T-612 — telas:**
   - chat do consultor como painel lateral na ficha (com contexto da empresa);
   - página `/agentes` com o chat do priorizador;
   - fila renderizada como tabela clicável;
   - toda resposta com link "ver trace";
   - disclaimer visível;
   - estados de carregando e erro.
5. **T-613 — testes com Anthropic mockado:**
   - consultor e priorizador de ponta a ponta;
   - sem trace não grava;
   - `corrigir` sem simulação rejeitado;
   - número inventado cai no template;
   - fallback de intenção;
   - rotina semanal não duplica.

## Verificação real (dev, prompts curtos — CLAUDE.md §4.4)
- Com a chave da Anthropic em `.env` local, faça **uma** pergunta ao consultor ("como está a empresa X?") e **uma** ao priorizador ("o que priorizar esta semana?").
- Confira no Langfuse local a generation com tokens e custo aninhada no span.

## Fechamento do M6 (etapa 8), com evidência
- O simulador devolve `ja_na_meta`, `corrigir` ou `nao_forcar` e persiste no trace.
- "O que priorizar" devolve a fila com `trace_id`.
- A generation do Claude aparece no Langfuse com tokens e custo, aninhada no span.
- Nenhuma recomendação `corrigir` sem simulação no trace (teste + consulta SQL mostrando zero casos).
- Regressão: aceites de M0 a M5.

## Gates
`make lint`, `make test`, `pytest -m langfuse`, isolamento, `tsc --noEmit`, build e navegador.

## Pronto quando
- T-609 a T-613 `[x]`.
- Tabela "Aceite M6 → evidência".
- **Pergunta final:** "Confirma o fechamento do M6?"
