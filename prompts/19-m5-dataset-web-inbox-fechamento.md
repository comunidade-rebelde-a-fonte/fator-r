# 19 — M5 · Dataset Langfuse, tela da inbox + fechamento do M5 🏁 (T-513, T-514)

Branch sugerida: `feat/m5-inbox-parser`

## Contexto
- `docs/tasks.md` → T-513, T-514 e **Aceite M5**.
- `docs/prd.md` → §7.6, §7.9 (≥ 80% ouro), §13.
- `docs/plan.md` → §7.4 (dataset `pgdas_extratos`), §9 (tela 4).
- `CLAUDE.md` → §6.2, §7 (gate de segurança obrigatório no M5).

## Execute
1. **T-513:**
   - `make parser-experiment`: cria ou atualiza o dataset `pgdas_extratos` no Langfuse local a partir de `fixtures/pgdas/` (sem texto bruto de extratos reais: só o `expected.json` e um identificador) e roda a versão atual do parser como experimento com nome `parser-<PARSER_VERSION>`;
   - consulte a doc atual de datasets e experimentos do Langfuse (context7).
2. **T-514:**
   - `/inbox` com upload (arrastar e soltar, aceitando só PDF/TXT no seletor, com o back validando de novo) e lista por status com contadores;
   - detalhe com campos extraídos + confiança por campo, empresa vinculada, motivo do `needs_review`, ações vincular (seletor de empresa) e rejeitar (motivo), link para baixar o original e link para o trace;
   - estados de carregando, vazio e erro.
3. **Verifique no navegador:** upload vinculado, upload `needs_review`, vínculo manual, rejeição.
4. **Segurança:** rode `/security-review` focado em upload, download e inbox. Achado alto é corrigido antes de fechar.
5. **Fechamento do M5 (etapa 8)**, com evidência:
   - extrato texto com CNPJ conhecido vincula sozinho e não sobrescreve folha já lançada;
   - extrato sem CNPJ da carteira fica `needs_review`;
   - receita criada na competência do PA; competência existente não é alterada;
   - parser ≥ 80% de acerto ouro nas fixtures de extrato texto (saída do T-508 / experimento T-513). Se as fixtures reais ainda faltarem (P-03), **o marco não fecha**: reporte;
   - texto bruto do PDF não aparece no Langfuse (inspeção de um trace).
6. **Regressão:** aceites de M0 a M4.

## Gates
`make lint`, `make test`, `pytest -m langfuse`, `make parser-experiment`, isolamento, `/security-review`, build e navegador.

## Pronto quando
- T-513 e T-514 `[x]`.
- Tabela "Aceite M5 → evidência" + resumo do security review.
- **Pergunta final:** "Confirma o fechamento do M5?"
