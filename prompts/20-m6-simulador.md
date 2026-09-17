# 20 — M6 · Simulador de correção (T-601 a T-604)

Branch sugerida: `feat/m6-simulador-agentes`
Pré-condição: M5 fechado.

## Contexto
- `docs/tasks.md` → T-601 a T-604.
- `docs/prd.md` → §7.7 (simulador, regra do piso), §13 (veredito persistido no trace).
- `docs/plan.md` → §5.2, §2.2-5 (piso absoluto).
- `CLAUDE.md` → §3.1, §3.10, §3.11, §2 (teto de INSS e múltiplos sócios estão **fora**).

## Execute (ciclo §8 por tarefa)
1. **T-602 primeiro (etapa 4).** Testes tabelados:
   - fator ≥ meta → `ja_na_meta`;
   - economia_12m < piso → `nao_forcar`, mesmo com líquido positivo;
   - líquido ≤ 0 → `nao_forcar`;
   - economia ≥ piso e líquido > 0 → `corrigir`;
   - fração de pró-labore 0 e 1;
   - horizonte 6 e 12;
   - INSS e IRRF editáveis;
   - `dados_insuficientes` do motor propagado sem veredito inventado.
2. **T-601 (`domain/simulador.py`):**
   - `simular(resultado_fator_r, meta, fracao_pro_labore, inss, irrf, horizonte_meses, piso) -> ResultadoSimulacao`;
   - fórmulas da Plano §5.2;
   - só `Decimal`;
   - saída com todos os campos da PRD §7.7 + veredito.
3. **T-603:**
   - migração `simulations` (`trace_id NOT NULL`, `firm_id` + RLS);
   - `POST /companies/{id}/simulations {pa, meta?, fracao?, inss?, irrf?, horizonte?}` dentro de `tracer.run(agente="consultor", gatilho="ficha")`:
     - span `tool`: motor + simulador;
     - span `decide`: veredito;
     - span `render`: template;
     - persistência via `record_decision`;
   - resposta `{resultado, veredito, simulation_id, trace_id}`.
4. **T-604:**
   - bloco "Simulador" na ficha com parâmetros editáveis (padrões do escritório), resultado, **veredito em destaque**, aviso fixo "INSS sem teto na v1", link para o trace e histórico das últimas simulações da empresa;
   - nenhum cálculo no front.

## Gates
`make lint`, `make test` (cobertura de `domain/simulador.py` ≥ 95%), `pytest -m langfuse`, isolamento, build e navegador.

## Pronto quando
T-601 a T-604 `[x]` e o relatório com um exemplo de cada veredito (entrada → saída → `trace_id`).
