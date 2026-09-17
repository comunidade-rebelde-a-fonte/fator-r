# 21 — M6 · Cliente Claude, plan, validador de render e guarda do corrigir (T-605 a T-608)

Branch sugerida: `feat/m6-simulador-agentes`

## Contexto
- `docs/tasks.md` → T-605 a T-608.
- `docs/prd.md` → §7.8 (agentes: linguagem natural no escritório, cálculo fora do modelo), §7.9 (`corrigir` com simulador no trace).
- `docs/plan.md` → §2.1 (modelo), §7.3 (guardas).
- `CLAUDE.md` → **§3.1, §3.11, §3.12**, §4.4 (Anthropic mockado nos testes), §5.2 (não mandar números para o LLM calcular), §5.3 (dado mínimo para a Anthropic).
- **Antes de codar:** consulte a doc atual da API Anthropic (tool use, modelo `claude-sonnet-5`) e do Langfuse para Anthropic.

## Execute (ciclo §8 por tarefa)
1. **T-605 (`agents/llm.py`):**
   - cliente Anthropic único com timeout, retry exponencial (máx. 2), `max_tokens` baixo e temperatura baixa;
   - prompts versionados em `agents/prompts/*.md` com `PROMPT_VERSION` enviado como metadata do trace;
   - sem chave: erro claro na inicialização em `prod`; em `test`, o cliente é sempre mock.
2. **T-606 — span `plan`:**
   - tool use com uma ferramenta `classificar_intencao` → `status_empresa | simular | explicar | priorizar` + parâmetros (`company_ref`, `pa`, `meta`);
   - a entrada para o LLM é **só a mensagem do usuário + a lista de nomes das empresas do escritório** (sem valores financeiros);
   - saída validada com Pydantic;
   - se falhar (erro, timeout ou JSON inválido), usa classificador por palavras-chave, registrado no span como `fallback=true`.
3. **T-607 — validador do `render`:**
   - o LLM recebe **a decisão estruturada já calculada** e redige;
   - o validador extrai todos os números do texto (formatos BR: `R$ 1.234,56`, `28,5%`, `12 meses`) e confere contra os valores da decisão formatados;
   - qualquer número sem correspondência faz a resposta usar o template determinístico, com o span marcado `render_rejeitado=true` e os números órfãos listados;
   - o texto final **sempre** termina com o disclaimer do PGDAS-D.
4. **T-608 — guarda do `decide`:** uma decisão com `veredito=corrigir` ou recomendação de correção sem `simulation_id` existente no mesmo escritório levanta erro de domínio; o run termina `error` e nada é gravado.

## Testes obrigatórios (Anthropic mockado)
- **Intenção:** as quatro intenções, fallback por erro, fallback por JSON inválido.
- **Payload:** o que vai para o LLM no `plan` não contém valores monetários (asserção no payload mockado).
- **Validador:** texto com todos os números válidos passa; um número inventado cai no template; percentual arredondado diferente cai no template.
- **Guarda:** `corrigir` sem simulação é rejeitado; `corrigir` com simulação de outro escritório também é rejeitado.
- **Disclaimer:** presente em 100% das respostas.

## Gates
`make lint`, `make test`, `pytest -m langfuse` (generation mockada aparece aninhada).

## Pronto quando
T-605 a T-608 `[x]` e o relatório com os exemplos de render aceito e render rejeitado.
