# 10 — M2 · Endpoint Fator R e ficha + fechamento do M2 🏁 (T-206, T-207)

Branch sugerida: `feat/m2-motor`

## Contexto
- `docs/tasks.md` → T-206, T-207 e **Aceite M2**.
- `docs/prd.md` → §7.4, §13 (itens 1 e 2).
- `docs/plan.md` → §8, §9 (ficha).
- `CLAUDE.md` → §3.1, §3.5, §3.7, §3.14, §10.2.

## Execute
1. **T-206:**
   - `GET /companies/{id}/fator-r?pa=YYYY-MM` (PA padrão = competência corrente);
   - carrega movimentos da janela, tabela vigente e política do escritório via repositórios e chama `domain.fator_r.calcular`;
   - a rota não faz conta;
   - resposta com decimais como string e `status` (`ok|dados_insuficientes`);
   - teste de isolamento incluído automaticamente pelo teste parametrizado do T-110 (confirme).
2. **T-207 — ficha da empresa:**
   - seletor de PA;
   - cards de Fator R, anexo, RBT12, FS12, folha mínima 28% e 30%, gap e reforço mensal, alíquota efetiva III e V, economia em 12 meses;
   - janela com meses preenchidos e faltantes destacados;
   - **política de CPP ativa e vigência da tabela visíveis**;
   - estado `dados_insuficientes` sem anexo nem alíquota;
   - formatação pt-BR;
   - editar a grade (T-109) atualiza o resultado.
3. **Verifique no navegador:** com 2 empresas × 12 competências, trocar o PA para frente e para trás e ver a janela mudar.
4. **Fechamento do M2 (etapa 8)**, com evidência:
   - Fator R do PA = planilha manual nas 2 empresas (saída do T-205 + print da ficha);
   - trocar o PA move a janela (mês que entra e mês que sai) sem recálculo manual;
   - RBT12 = 0 mostra "dados insuficientes" sem anexo nem alíquota.
5. **Regressão:** aceites do M0 e M1.

## Gates
`make lint`, `make test`, isolamento, `tsc --noEmit`, build e navegador.

## Pronto quando
- T-206 e T-207 `[x]`.
- Tabela "Aceite M2 → evidência".
- **Pergunta final:** "Confirma o fechamento do M2?"

> Depois do M2, as trilhas M3 (prompts 11–12) e M4 (prompts 13–15) podem rodar em paralelo.
