# 17 — M5 · Parser PGDAS-D determinístico (T-504 a T-508)

Branch sugerida: `feat/m5-inbox-parser`

## Contexto
- `docs/tasks.md` → T-504 a T-508; pré-requisito **P-03**.
- `docs/prd.md` → §7.6 (campos, confiança, limiar), §7.9 (meta ≥ 80%).
- `docs/plan.md` → §6.
- `CLAUDE.md` → §3.2 (parse sem LLM), §5.3 (extratos reais: só anonimizados, em `fixtures/pgdas/`, depois da minha revisão).

## Bloqueio
- **P-03** (extratos reais anonimizados): sem ele, **comece com fixtures sintéticas**. Ao menos 8, variando rótulos, espaçamento, números BR, campo ausente, CNPJ com e sem máscara, PDF com texto e PDF sem camada de texto.
- T-508 só é marcada `[x]` quando houver **também** fixtures reais revisadas por mim. Se faltarem, deixe T-508 `[ ]` e reporte o acerto só sobre as sintéticas.
- Nunca commite nem copie extrato real não anonimizado. Se eu enviar um, confirme a anonimização comigo antes de salvar.

## Execute (ciclo §8 por tarefa)
1. **T-504:**
   - `fixtures/pgdas/<nome>/` com `documento.(pdf|txt)` + `expected.json` (CNPJ, PA, RBT12, RPA, FS12, Fator R, DAS, anexo e faixa de confiança esperada);
   - `fixtures/pgdas/README.md` explica como anonimizar.
2. **T-505:**
   - `parsing/texto.py` com pdfplumber e fallback pypdf; TXT com detecção de encoding;
   - PDF sem texto devolve resultado com `motivo="sem_camada_texto"`.
3. **T-506:**
   - `parsing/pgdas.py`: regex por campo com variantes de rótulo, conversão de número BR para `Decimal`, PA `MM/AAAA` para competência;
   - confiança por campo (achado, formato válido, CNPJ com DV válido).
4. **T-507:**
   - confiança do documento = média ponderada (CNPJ e PA com peso maior) + bônus quando `|FatorR − FS12/RBT12| ≤ tolerância`;
   - `PARSER_VERSION` constante;
   - retorno em dataclass `ResultadoParse` com campos, confianças, confiança total, motivos e versão.
5. **T-508:**
   - `tests/parsing/test_fixtures.py` parametrizado por pasta: compara campo a campo com `expected.json` e verifica a faixa de confiança;
   - relatório de acerto por campo e total no final da execução.

## Regras críticas
- **Zero LLM** em `parsing/`. Nenhum import de `anthropic` nesse pacote (adicione um teste que verifica isso).
- O parser **não** decide vínculo nem grava nada: é função pura sobre o texto. Vínculo e escrita são do prompt 18.

## Gates
`make lint`, `make test`, `pytest apps/api/tests/parsing`.

## Pronto quando
T-504 a T-507 `[x]`; T-508 `[x]` só com fixtures reais. Relatório com a tabela de acerto por campo (sintéticas × reais).
