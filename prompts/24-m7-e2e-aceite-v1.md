# 24 — M7 · E2E, integração Langfuse, conferência real e aceite da v1 🏁 (T-705 a T-708)

Branch sugerida: `feat/m7-endurecimento`

## Contexto
- `docs/tasks.md` → T-705 a T-708, **Aceite M7 / v1**, pré-requisitos P-01..P-07.
- `docs/prd.md` → **§13 (regras de aceite, todas)**, §7.9 (qualidade mínima).
- `CLAUDE.md` → **§6.3 (v1 pronta)**, §7, §8 etapa 8.

## Execute (ciclo §8 por tarefa)
1. **T-705 — E2E Playwright (`make e2e`)** num ambiente limpo (`make down && make up && make migrate && make seed`), **um teste por item da PRD §13**, com nome que referencia o item:
   1. login;
   2. cadastrar 2 empresas e lançar 12 competências cada;
   3. Fator R do PA confere com os valores da planilha P-07;
   4. trocar o PA e ver a janela mudar;
   5. upload de extrato texto com CNPJ conhecido vincula e não altera a folha;
   6. extrato sem CNPJ da carteira → `needs_review`;
   7. semáforo <28 / 28–30 / ≥30;
   8. simulação com veredito e link para o trace;
   9. priorizador devolve fila com `trace_id` (Anthropic mockado **no servidor** em modo e2e);
   10. nota humana no trace;
   11. disclaimer visível;
   12. nenhuma rota de login ou cadastro de cliente.
2. **T-706 (`pytest -m langfuse`)** com o Langfuse local de pé:
   - buscar pela API pública os traces gerados no E2E;
   - conferir spans `plan/tool/decide/render`, generation, scores `gold_*` e `human_eval`;
   - confirmar que o texto bruto do PDF está ausente.
3. **T-707 — conferência manual real:**
   - **peça-me** os dados de uma empresa real do escritório piloto (12 competências + extrato PGDAS-D do mesmo PA);
   - lance, rode o motor e compare RBT12, FS12, Fator R e anexo com o extrato;
   - divergência → investigar a causa (política de CPP, proporcionalização, dado lançado) e reportar. **Não ajuste o motor para bater sem a minha aprovação** (§9).
4. **T-708 — `README.md`:**
   - pré-requisitos, setup local, variáveis de ambiente (referência ao `.env.example`);
   - comandos `make`, testes, E2E e `make parser-experiment`;
   - acesso ao Langfuse local;
   - backup e restore;
   - link para `CLAUDE.md` e `docs/`.

## Aceite da v1 (CLAUDE.md §6.3), com evidência por item
- [ ] M0 a M7 prontos (M7 depende deste prompt).
- [ ] E2E cobre e passa **todos** os itens da PRD §13 (saída do `make e2e`).
- [ ] P-01 a P-07 resolvidos ou com decisão registrada no "Registro de decisões".
- [ ] Parser ≥ 80% de acerto ouro nas fixtures de extrato texto.
- [ ] Restore de backup testado (T-701); security review sem achado alto aberto (T-703).
- [ ] Conferência manual real batendo (T-707).
- [ ] Suíte completa: `make lint test`, `pytest -m perf`, `pytest -m langfuse` e `make e2e` verdes.

## Pronto quando
- T-705 a T-708 `[x]`.
- Relatório final da v1: tabela "PRD §13 → teste E2E → resultado", tabela "CLAUDE.md §6.3 → evidência", pendências para a Fase 2 e riscos remanescentes (PRD §14).
- **Pergunta final:** "Confirma o aceite da v1?"
