# 12 — M3 · Tela da carteira + fechamento do M3 🏁 (T-306)

Branch sugerida: `feat/m3-carteira`

## Contexto
- `docs/tasks.md` → T-306 e **Aceite M3**.
- `docs/prd.md` → §7.5 (colunas mínimas, KPIs, ordenação), §13 (semáforo).
- `CLAUDE.md` → §6.1 (UI), §6.2, §10.2.

## Execute
1. **T-306:**
   - página `/carteira` com seletor de PA (padrão: competência corrente);
   - faixa de KPIs;
   - tabela com as colunas mínimas da PRD §7.5 (ação sugerida, nome, Fator R, anexo, RBT12, FS12, reforço mensal, economia 12 meses) e semáforo com cor + texto (acessível, não só cor);
   - ordenação padrão vinda da API, com clique no nome levando à ficha;
   - estados de carregando, vazio ("nenhuma empresa sujeita a Fator R") e erro.
2. **Verifique no navegador** com a carga do T-304 e com o seed normal.
3. **Fechamento do M3 (etapa 8)**, com evidência:
   - o semáforo separa <28%, 28–30% e ≥30% (casos de fronteira do seed visíveis);
   - empresa inativa ou não sujeita não aparece;
   - KPIs corretos, incluindo os honorários;
   - 200 empresas em menos de 1 s (saída do `pytest -m perf`).
4. **Regressão:** aceites de M0 a M2.

## Gates
`make lint`, `make test`, `pytest -m perf`, `tsc --noEmit`, build e navegador.

## Pronto quando
- T-306 `[x]`.
- Tabela "Aceite M3 → evidência".
- **Pergunta final:** "Confirma o fechamento do M3?"
