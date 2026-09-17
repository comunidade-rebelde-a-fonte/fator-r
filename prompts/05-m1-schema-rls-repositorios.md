# 05 — M1 · Schema, RLS, repositórios e utilitários (T-101 a T-105)

Branch sugerida: `feat/m1-cadastro-movimentos`
Pré-condição: M0 fechado e confirmado por mim.

## Contexto
- `docs/tasks.md` → T-101 a T-105.
- `docs/plan.md` → §3 (isolamento em duas camadas), §4 (`companies`, `monthly_movements`), §2.2-3 (`inicio_atividade`).
- `CLAUDE.md` → §3.13 (isolamento), §5.2 (`Decimal`, sem `BYPASSRLS`), §5.4 (migração nova, nunca editar a aplicada).

## Execute (ciclo §8 por tarefa)
1. **T-101:** migração `companies` com todos os campos da Plano §4 (incluindo `inicio_atividade`, `pacote` como enum, `honorario_mensal numeric(14,2)`) e único `(firm_id, cnpj)`.
2. **T-102:** migração `monthly_movements`:
   - `competencia date` com CHECK de dia 1;
   - valores `numeric(14,2)` com CHECK ≥ 0;
   - `folha_mes` como coluna gerada (`pro_labore + salarios + cpp + fgts`);
   - enum `origem` (`manual|pgdas|folha|agente`);
   - único e índice `(company_id, competencia)`;
   - `firm_id` na tabela;
   - `pgdas_document_id` nullable sem FK por enquanto (a tabela nasce no M5; registre isso).
3. **T-103 — RLS:**
   - `ENABLE` e `FORCE ROW LEVEL SECURITY` em todas as tabelas com `firm_id`;
   - policy `firm_id = current_setting('app.firm_id')::uuid`;
   - role da aplicação separada do owner das migrações, sem `BYPASSRLS`;
   - `SET LOCAL app.firm_id` por transação na dependência de sessão do T-010;
   - login e seed usam caminho explícito e documentado.
4. **T-104:** `repositories/` com `firm_id` obrigatório em toda função pública. Nenhum acesso ao banco fora dessa camada.
5. **T-105 (`core/`):**
   - validação de CNPJ com dígitos verificadores, normalização só para dígitos e formatação;
   - `parse_competencia("YYYY-MM") -> date` e `format_competencia`;
   - helpers de `Decimal` (quantização só para saída).

## Testes obrigatórios
- **CNPJ:** válidos, inválidos, com e sem máscara, todos os dígitos iguais.
- **Competência:** mês inválido, formato errado.
- **RLS:** com `app.firm_id` = A, um `SELECT` cru não retorna linhas de B; sem `app.firm_id`, não retorna nada ou dá erro.
- **Coluna gerada** `folha_mes` confere.

## Gates
`make lint`, `make test`, migração do zero (`make down && make up && make migrate && make seed`).

## Pronto quando
T-101 a T-105 `[x]` e o relatório da etapa 7 com a estratégia de roles e RLS explicada em 3–5 linhas.
