# 09 — M2 · Motor Fator R (T-203 a T-205)

Branch sugerida: `feat/m2-motor`

## Contexto
- `docs/tasks.md` → T-203, T-204, T-205; pré-requisitos **P-05** e **P-07**.
- `docs/plan.md` → §5.1 (todos os passos), §2.2-3, §2.2-6.
- `docs/prd.md` → §5 (contexto legal), §7.4 (saída obrigatória).
- `CLAUDE.md` → §3.1 a §3.7, §3.15, §5.2.

## Bloqueios
- **P-05** (proporcionalização para empresa com menos de 12 meses): se não resolvido, implemente todo o resto e deixe a proporcionalização atrás de uma função isolada que devolve `dados_insuficientes` com motivo `"empresa_nova_regra_pendente"`. Não invente a fórmula. Avise no relatório.
- **P-07** (planilha manual): **T-205 não pode ser marcada `[x]` sem ela.** Se faltar, pare T-205 e peça.

## Execute (ciclo §8)
1. **T-204 primeiro (etapa 4).** Testes tabelados (`pytest.mark.parametrize`) cobrindo:
   - fator 27,99% / 28,00% / 29,99% / 30,00% → anexo e semáforo;
   - RBT12 = 0 → `dados_insuficientes`, sem anexo, alíquota nem economia;
   - empresa com 1, 5 e 12 meses de atividade;
   - mês faltante (conta nos faltantes, soma zero);
   - política de CPP ligada e desligada muda a FS12;
   - troca de vigência de tabela entre dois PAs;
   - RBT12 mudando de faixa;
   - gap zero quando FS12 ≥ mínima;
   - economia ≥ 0.
2. **T-203 (`domain/fator_r.py`):**
   - `calcular(company, pa, movimentos, tabelas, politica, meta) -> ResultadoFatorR`, em dataclass imutável;
   - todos os campos da PRD §7.4 + semáforo + política de CPP usada + vigência da tabela + meses preenchidos e faltantes;
   - só `Decimal`, sem I/O, sem arredondar internamente.
3. **T-205:** teste de aceite com os dados da planilha P-07 (2 empresas × 12 meses × 2 PAs consecutivos) em `tests/domain/test_aceite_planilha.py`. Os valores esperados vêm da planilha, não do motor.

## Regras críticas
- Corte legal **sempre 0,28**; a meta (0,30) só afeta semáforo e `folha_min_meta`.
- Nenhum valor de alíquota ou faixa no código: vem de `tabelas`.
- FS12 = pró-labore + salários + FGTS + (CPP se a política mandar). Nada além.

## Gates
`make lint`, `mypy --strict`, `make test` (cobertura de `domain/fator_r.py` ≥ 95% de linhas e branches).

## Pronto quando
T-203, T-204 e T-205 `[x]`, ou bloqueios explícitos. Relatório com a tabela de casos testados.
