# 18 — M5 · Agente parser_pgdas, escrita de receita e nota ouro (T-509 a T-512)

Branch sugerida: `feat/m5-inbox-parser`

## Contexto
- `docs/tasks.md` → T-509 a T-512.
- `docs/prd.md` → §7.6 (status, limiar, escrita condicionada), §7.9 (eval ouro), §13 (itens 3 e 4).
- `docs/plan.md` → §2.2-1 (RPA na competência do PA), §2.2-2 (ouro sem `origem=pgdas`), §6, §7.3, §7.4.
- `CLAUDE.md` → **§3.8, §3.9, §3.10, §3.16** (as quatro regras centrais deste prompt).

## Execute (ciclo §8 por tarefa)
1. **T-509 — agente `parser_pgdas`,** disparado ao fim do upload (continua o run do T-502):
   - span `parse`: `parsing.pgdas.parse(texto)`;
   - span `tool`: match do CNPJ extraído entre as empresas **do escritório**;
   - span `decide`: `linked` se `confianca ≥ firm.limiar_confianca_parser` **e** CNPJ encontrado; senão `needs_review` com motivo;
   - span `render`: texto por template para o contador;
   - grava `pgdas_documents` (campos_json, confiança, status, company_id) via `record_decision`.
2. **T-510 — escrita de receita,** só se `linked` **e** RPA presente:
   - cria `monthly_movements` com `origem=pgdas`, **competência = PA do extrato**, apenas `receita_bruta` preenchida (folha zerada), `pgdas_document_id` apontando o documento;
   - **se a competência já existir, não altera nada** e registra `movimento_existente` na decisão;
   - nunca escreve pró-labore, salários, CPP nem FGTS.
3. **T-511 — eval ouro** logo após `linked`:
   - roda o motor sobre a série **excluindo** movimentos `origem=pgdas`;
   - compara CNPJ, PA, RBT12, FS12, Fator R e anexo com os extraídos, usando `firm.tolerancia_ouro_pct`;
   - janela com movimento `pgdas` ou faltante que impeça a comparação vira `ouro_indisponivel`;
   - grava via `scores.gold`.
4. **T-512:**
   - `POST /inbox/{id}/link {company_id}` roda um **novo** `tracer.run(gatilho="vinculo_manual")` e aplica a mesma regra de escrita do T-510;
   - `POST /inbox/{id}/reject {motivo}` roda um novo run com status `rejected`.

## Testes obrigatórios (etapa 4, antes de implementar)
- Extrato com CNPJ conhecido e confiança alta: `linked` + receita criada na competência do PA.
- Mesmo caso com a competência já lançada manualmente: nada muda, folha intacta (comparar a linha antes e depois).
- CNPJ desconhecido: `needs_review`, nenhuma escrita.
- Confiança abaixo do limiar: `needs_review`.
- CNPJ de empresa de **outro** escritório: `needs_review` (isolamento).
- Ouro com série manual completa: scores `gold_*` corretos; ouro com movimento `pgdas` na janela: `ouro_indisponivel`.
- Vínculo manual e rejeição geram traces novos.

## Gates
`make lint`, `make test`, `pytest -m langfuse`, isolamento.

## Pronto quando
T-509 a T-512 `[x]` e o relatório com os `trace_id` de um caso `linked` e um `needs_review` no Langfuse local.
