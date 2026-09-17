# 07 — M1 · Telas de empresas e grade mensal + fechamento do M1 🏁 (T-108, T-109)

Branch sugerida: `feat/m1-cadastro-movimentos`

## Contexto
- `docs/tasks.md` → T-108, T-109 e **Aceite M1**.
- `docs/plan.md` → §9 (telas 3).
- `CLAUDE.md` → §6.1 (UI), §6.2, §10.2 (sem cálculo no front, pt-BR).

## Execute
1. **Tipos da API:** gere os tipos TS a partir do OpenAPI do FastAPI (script em `apps/web`, ex.: `openapi-typescript`), se ainda não existir.
2. **T-108:**
   - lista de empresas com busca, filtros ativo e sujeita a Fator R, e badge do pacote;
   - formulário de cadastro e edição com máscara e validação de CNPJ;
   - honorário em R$;
   - botão desativar/reativar;
   - estados de carregando, vazio e erro (inclusive o 409 de CNPJ duplicado).
3. **T-109:**
   - ficha da empresa com a grade mensal (últimas 12 competências + navegação para anteriores);
   - célula editável por campo (receita, pró-labore, salários, CPP, FGTS);
   - `folha_mes` exibida como veio da API (**não** somada no front);
   - origem de cada linha visível (badge `manual/pgdas/folha/agente`);
   - salva via `PUT` por competência.
4. **Verifique no navegador:** criar empresa, duplicar CNPJ, editar, desativar, lançar 12 competências, editar uma competência existente.
5. **Fechamento do M1 (etapa 8)**, com evidência por item:
   - CNPJ duplicado no mesmo escritório é recusado; o mesmo CNPJ em outro escritório é aceito;
   - upsert por (empresa, competência) não duplica linha;
   - os testes de isolamento passam, inclusive a query crua barrada por RLS.
6. **Regressão:** rode de novo os aceites do M0.

## Gates
`make lint`, `make test`, `tsc --noEmit`, build do web, isolamento e verificação no navegador.

## Pronto quando
- T-108 e T-109 `[x]`.
- Tabela "Aceite M1 → evidência".
- **Pergunta final:** "Confirma o fechamento do M1?"
