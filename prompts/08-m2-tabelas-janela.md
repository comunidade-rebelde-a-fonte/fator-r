# 08 — M2 · Tabelas do Simples e janela (T-201, T-202)

Branch sugerida: `feat/m2-motor`
Pré-condição: M1 fechado.

## Contexto
- `docs/tasks.md` → T-201, T-202; pré-requisito **P-04**.
- `docs/plan.md` → §2.2-4 (vigência), §5.1 passos 1–2, §5.3.
- `docs/prd.md` → §5, §7.3 (competência vs PA).
- `CLAUDE.md` → §3.4, §3.15, §5.2 (nada de alíquota fixa no código), §8 etapa 1.

## Bloqueio
**T-201 depende de P-04** (faixas conferidas contra a LC 123/2006).
- Se P-04 não estiver `[x]`: **pare T-201**, me mostre o CSV proposto (Anexo III e V, 6 faixas cada, `rbt12_ate`, `aliquota_nominal`, `parcela_deduzir`, `vigencia_inicio=2018-01-01`) com a fonte citada, e peça a minha conferência.
- T-202 não depende de P-04 e pode seguir.

## Execute (ciclo §8 por tarefa)
1. **T-201:**
   - migração `simples_tables` com CHECK `vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio`;
   - `fixtures/simples_tables_2018.csv`;
   - seed idempotente a partir do CSV;
   - função de repositório `tabela_vigente(anexo, data)` que falha explicitamente se não houver vigência.
2. **T-202 (`domain/janela.py`, Python puro):**
   - `janela(pa) -> (inicio, fim)` com PA−12 a PA−1;
   - `meses_validos(janela, inicio_atividade)`;
   - `classificar(meses_validos, movimentos) -> preenchidos, faltantes`.

## Testes obrigatórios (antes ou junto — etapa 4)
- **Janela:** PA de janeiro (vira o ano), PA 09/2026 = 2025-09..2026-08 (exemplo do PRD).
- **`inicio_atividade`:** dentro da janela, antes da janela, igual ao PA.
- **Faltantes:** mês válido sem movimento conta como faltante; mês antes do início de atividade **não** conta.
- **Vigência:** data exatamente no início, no fim e sem vigência.

## Gates
`make lint`, `make test`, migração do zero + seed.

## Pronto quando
T-201 (se P-04 ok) e T-202 `[x]` e o relatório da etapa 7 entregue. Se T-201 ficar bloqueada, diga isso explicitamente.
