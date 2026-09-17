# Tarefas — Plataforma Fator R (v1)

Base: `docs/prd.md` v0.2 e `docs/plan.md`
Convenção: `[ ]` pendente · `[x]` feito · **Dep.** = tarefas que precisam estar prontas antes
Referências: `PRD §x` e `Plano §x`

Cada marco só fecha quando todos os itens de **Aceite** passam.

---

## Pré-requisitos (fora do código)

- [x] **P-01** Corrigir a PRD §7.6: o RPA vai para a competência do próprio PA. Registrar no PRD as decisões da Plano §2.2.
- [x] **P-02** Confirmar com o escritório piloto se a CPP do DAS integra a FS12 (PRD §5 e §16). Define o seed de `cpp_das_integra_fs12`.
- [ ] **P-03** Conseguir 5 a 10 extratos PGDAS-D reais e anonimizá-los. **Bloqueia o M5.**
- [ ] **P-04** Conferir as faixas, alíquotas nominais e parcelas a deduzir dos Anexos III e V contra a LC 123/2006 (redação LC 155/2016).
- [ ] **P-05** Conferir a regra de proporcionalização para empresa com menos de 12 meses contra a Res. CGSN 140/2018, arts. 22 e 26.
- [ ] **P-06** Definir o servidor que roda a aplicação e o Langfuse (aplicação + ~4 GB de RAM a mais) e quem acessa a UI do Langfuse.
- [ ] **P-07** Montar uma planilha manual de referência com 2 empresas × 12 competências e o Fator R esperado em 2 PAs consecutivos (base do aceite do M2).

---

## M0 — Fundação

- [x] **T-001** Criar o monorepo: `apps/api`, `apps/web`, `infra/langfuse`, `Makefile`, `.editorconfig`, `.gitignore`, `.env.example`.
- [x] **T-002** Esqueleto da api: FastAPI, Pydantic v2 settings, SQLAlchemy 2 async, Alembic, `GET /health`. Ferramentas: `uv`, `ruff`, `mypy`, `pytest`. **Dep.** T-001
- [x] **T-003** Esqueleto do web: Next.js App Router + TS, Tailwind, TanStack Query, cliente HTTP com `credentials: include`. **Dep.** T-001
- [x] **T-004** `docker-compose.yml` com `api`, `web`, `db` (Postgres 16) e volume `/data/uploads` fora da web root. **Dep.** T-002, T-003
- [x] **T-005** `infra/langfuse/docker-compose.langfuse.yml`: langfuse-web, langfuse-worker, postgres, clickhouse, redis e minio. Senhas vêm do `.env`; projeto `dev` e chaves criados por `LANGFUSE_INIT_*`.
- [x] **T-006** Metas do `make`: `up`, `down`, `migrate`, `seed`, `test`, `lint`, `e2e`. **Dep.** T-004, T-005
- [x] **T-007** CI (GitHub Actions): lint + mypy + pytest com Postgres de serviço, e lint + typecheck + build do web. **Dep.** T-002, T-003
- [x] **T-008** Migração: `firms`, `users`, `sessions`. **Dep.** T-002
- [x] **T-009** Auth:
  - `POST /auth/login|logout` e `GET /auth/me`;
  - senha argon2;
  - token de sessão aleatório com hash no banco, cookie httpOnly + SameSite=Lax + Secure fora de dev;
  - expiração;
  - rate limit simples no login.

  **Dep.** T-008
- [x] **T-010** Middleware de sessão que injeta `user` e `firm_id` no request. Rotas protegidas por padrão. **Dep.** T-009
- [x] **T-011** Seed: um escritório (meta 0,30, limiar 0,40, piso 6000, política de CPP conforme P-02, tolerância ouro) e um usuário. **Dep.** T-008
- [x] **T-012** Web: tela de login, layout autenticado com navegação (Carteira, Empresas, Inbox, Agentes, Observabilidade), redirecionamento sem sessão e **rodapé fixo com o disclaimer do PGDAS-D** (PRD §8). **Dep.** T-003, T-009

**Aceite M0**
- [x] `make up` sobe api, web, db e Langfuse; `/health` responde 200; a UI do Langfuse abre.
- [x] Login e logout funcionam; rota protegida sem cookie devolve 401.
- [x] Não existe rota nem tela de cadastro ou login de cliente (PRD §13).
- [x] CI verde. *(verificações locais; CI remota pendente até existir o repositório — Registro de decisões 2026-09-17)*

---

## M1 — Cadastro e movimentos

- [x] **T-101** Migração `companies` com todos os campos da Plano §4, incluindo `inicio_atividade`, e único (firm_id, cnpj). **Dep.** T-008
- [x] **T-102** Migração `monthly_movements`: `folha_mes` como coluna gerada, único (company_id, competencia), índice (company_id, competencia), enum de origem. **Dep.** T-101
- [x] **T-103** Isolamento no banco:
  - RLS em todas as tabelas com `firm_id` (policy `firm_id = current_setting('app.firm_id')::uuid`);
  - `SET LOCAL app.firm_id` por transação no middleware;
  - role da aplicação sem `BYPASSRLS`.

  **Dep.** T-010, T-101
- [x] **T-104** Camada `repositories/` com `firm_id` obrigatório na assinatura. **Dep.** T-103
- [x] **T-105** Utilitários `core/`: validação e normalização de CNPJ (dígitos verificadores), parsing de competência `YYYY-MM` para date dia 1, dinheiro em `Decimal`.
- [x] **T-106** API de empresas: `GET|POST /companies` (filtros ativo e sujeita_fator_r) e `GET|PATCH /companies/{id}`. Desativar em vez de apagar. **Dep.** T-104, T-105
- [x] **T-107** API de movimentos: `GET /companies/{id}/movements?de=&ate=` e `PUT /companies/{id}/movements/{competencia}` (upsert, `origem=manual`). Valores ≥ 0. **Dep.** T-104
- [x] **T-108** Web: lista de empresas (busca, filtros, badge do pacote) e formulário de cadastro/edição. **Dep.** T-106
- [x] **T-109** Web: grade mensal de 12+ competências editável na ficha, com a origem de cada linha visível e a folha do mês calculada. **Dep.** T-107
- [x] **T-110** Testes de isolamento parametrizados: dois escritórios; o usuário A recebe 404 em qualquer recurso do B, em todos os endpoints. **Dep.** T-106, T-107

**Aceite M1**
- [x] CNPJ duplicado no mesmo escritório é recusado; CNPJ igual em outro escritório é aceito.
- [x] Upsert por (empresa, competência) não duplica linha.
- [x] Os testes de isolamento passam, inclusive com uma query crua sem filtro (RLS barra).

---

## M2 — Motor Fator R e tabelas

- [ ] **T-201** Migração `simples_tables` com vigência. Seed a partir de `fixtures/simples_tables_2018.csv` já conferido. **Dep.** P-04 *(implementado; aguarda conferência do CSV — P-04)*
- [x] **T-202** `domain/janela.py`: janela do PA (PA−12 a PA−1), meses válidos a partir de `inicio_atividade`, preenchidos × faltantes.
- [ ] **T-203** `domain/fator_r.py` com a lógica da Plano §5.1 *(implementado exceto proporcionalização de empresa nova, que devolve `empresa_nova_regra_pendente` até P-05)*:
  - proporcionalização (P-05);
  - política de CPP;
  - `dados_insuficientes` quando RBT12 = 0;
  - anexo;
  - folha mínima 28% e meta;
  - gap e reforço mensal;
  - alíquota efetiva pela tabela vigente;
  - economia de 12 meses;
  - semáforo.

  **Dep.** T-202
- [x] **T-204** Testes unitários tabelados do motor:
  - fronteiras 27,99 / 28,00 / 29,99 / 30,00%;
  - RBT12 = 0;
  - empresa com 1, 5 e 12 meses;
  - mês faltante;
  - CPP ligada e desligada;
  - troca de vigência;
  - mudança de faixa do RBT12.

  **Dep.** T-203
- [ ] **T-205** Teste de aceite contra a planilha P-07: 2 empresas × 12 meses, 2 PAs consecutivos. **Dep.** T-203, P-07 *(bloqueado: aguarda planilha P-07)*
- [x] **T-206** `GET /companies/{id}/fator-r?pa=YYYY-MM`: carrega movimentos, tabela e política e chama o motor. **Dep.** T-203, T-107
- [x] **T-207** Web, ficha da empresa: seletor de PA; cards de Fator R, anexo, RBT12, FS12, folha mínima 28/30, gap, reforço mensal, alíquotas III/V e economia; janela com meses faltantes destacados; política de CPP e vigência da tabela visíveis. **Dep.** T-206

**Aceite M2**
- [ ] O Fator R do PA coincide com a planilha manual nas 2 empresas (PRD §13). *(bloqueado: P-07)*
- [x] Trocar o PA move a janela (mês que entra e mês que sai) sem recálculo manual (PRD §13).
- [x] RBT12 = 0 mostra "dados insuficientes" sem anexo nem alíquota.

---

## M3 — Carteira

- [x] **T-301** `domain/carteira.py`: recebe empresas e movimentos em lote e devolve linhas + KPIs (monitoradas, no V, no limite, seguras, economia em jogo, honorários). Ordena vermelho → amarelo → verde e, dentro de cada grupo, por maior economia. **Dep.** T-203
- [x] **T-302** Ação sugerida por linha: vermelho = "reunião de correção", amarelo = "vigiar / simular", verde = "manter", dados insuficientes = "completar lançamentos". **Dep.** T-301
- [x] **T-303** `GET /portfolio?pa=`: só empresas ativas e sujeitas a Fator R; **uma** consulta para todos os movimentos da janela. PA padrão = competência corrente. **Dep.** T-301, T-104
- [x] **T-304** Seed de carga: 200 empresas × 24 meses para teste de performance. **Dep.** T-102
- [x] **T-305** Teste de performance: `/portfolio` com 200 empresas em menos de 1 s. **Dep.** T-303, T-304
- [x] **T-306** Web, carteira: seletor de PA, faixa de KPIs, tabela com semáforo e as colunas mínimas da PRD §7.5, link para a ficha. **Dep.** T-303

**Aceite M3**
- [x] O semáforo separa <28%, 28–30% e ≥30% (PRD §13).
- [x] Empresa inativa ou não sujeita a Fator R não aparece.
- [x] Os KPIs somam certo, incluindo os honorários dos pacotes (PRD §9).
- [x] 200 empresas em menos de 1 s.

---

## M4 — Tracing e observabilidade (Langfuse)

- [x] **T-401** Dependências: `langfuse` (SDK Python v3), `opentelemetry-instrumentation-anthropic`. Settings `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_TRACING_ENABLED`. **Dep.** T-005
- [x] **T-402** Migrações `agent_traces` (id = trace_id de 32 hex, `langfuse_sync`), `evals_gold` e `evals_human` (CHECK do comentário em `erro`). FK `trace_id NOT NULL` preparada para `simulations` e `pgdas_documents`. **Dep.** T-101
- [x] **T-403** `tracing/tracer.py`, contexto `tracer.run(...)`:
  - gera o trace_id com `langfuse.create_trace_id()`;
  - grava `agent_traces` na transação;
  - abre a observation raiz com `trace_context`;
  - `propagate_attributes` com user, empresa e tags `agente`, `gatilho`, `firm:<id>`;
  - `run.span(nome)` limitado a `plan|parse|tool|decide|render`;
  - `run.finish(...)` preenche status, confiança, latência e decisão.

  **Dep.** T-401, T-402
- [x] **T-404** Guarda "sem trace não grava": helper `record_decision(run, ...)` é o único caminho de escrita das decisões de agente. Teste garante que uma escrita fora de `run` falha. **Dep.** T-403
- [x] **T-405** Instrumentação do Claude: `AnthropicInstrumentor().instrument()` no startup. As generations aparecem aninhadas no span corrente. **Dep.** T-401
- [x] **T-406** Mascaramento `mask_otel_spans`: remove o texto bruto do PDF e trunca payloads acima de N KB antes do export. **Dep.** T-403
- [x] **T-407** Monitor de exportação: marca `langfuse_sync=ok|failed`; um job reenvia ou alerta os `failed`. Langfuse fora do ar não quebra o agente. **Dep.** T-403
- [x] **T-408** Serviço de scores: `scores.gold(trace_id, campos)` e `scores.human(trace_id, nota, comentario)` gravam localmente e espelham com `langfuse.create_score` (BOOLEAN/NUMERIC para ouro, CATEGORICAL para humano). **Dep.** T-403
- [x] **T-409** API: `GET /observability/summary` (KPIs locais da PRD §7.9 + custo e tokens via API de métricas do Langfuse com cache de 5 min), `GET /traces?agente=&status=&sem_nota=`, `GET /traces/{id}` (resumo local + spans lidos da API do Langfuse + evals), `POST /traces/{id}/human-eval`. **Dep.** T-408
- [x] **T-410** Web, observabilidade: cards, tabela por agente, lista de traces filtrável. Detalhe com timeline de spans, evals, formulário de nota (comentário obrigatório em `erro`) e link "abrir no Langfuse". **Dep.** T-409
- [x] **T-411** Agente fictício `echo` só para dev/teste, para exercitar tracer, spans e scores de ponta a ponta antes dos agentes reais. **Dep.** T-403

**Aceite M4**
- [x] Uma corrida do `echo` aparece no Langfuse com o mesmo `trace_id` e spans `plan → tool → decide → render` (PRD §13).
- [x] Nota humana gravada no Postgres e visível como score `human_eval` no Langfuse (PRD §13).
- [x] Nota `erro` sem comentário é recusada (API e banco).
- [x] Com o Langfuse parado, a corrida grava `agent_traces` com `langfuse_sync=failed`.

---

## M5 — Inbox PGDAS-D e agente `parser_pgdas`

- [x] **T-501** Migração `pgdas_documents` (único firm_id+sha256, `trace_id NOT NULL`). **Dep.** T-402
- [x] **T-502** Upload `POST /inbox/pgdas`:
  - multipart, só PDF/TXT validados por magic bytes e não só pela extensão;
  - tamanho máximo;
  - arquivo gravado em `/data/uploads/{firm_id}/{sha256}`;
  - duplicado devolve o documento existente.

  **Dep.** T-501
- [x] **T-503** Download autenticado do original: `GET /inbox/{id}/arquivo`, sem URL pública. **Dep.** T-502
- [ ] **T-504** Fixtures `fixtures/pgdas/`: extratos sintéticos (texto e PDF) + anonimizados de P-03, cada um com `expected.json`. **Dep.** P-03 *(10 sintéticas prontas; faltam as reais — P-03)*
- [x] **T-505** `parsing/pgdas.py` — extração de texto: pdfplumber → pypdf. PDF sem texto vira `needs_review` com motivo "sem camada de texto". **Dep.** T-504
- [x] **T-506** `parsing/pgdas.py` — campos: regex para CNPJ, PA, RBT12, RPA, FS12, Fator R, DAS e anexo; números no formato BR; confiança por campo. **Dep.** T-505
- [x] **T-507** Confiança por documento: pesos (CNPJ e PA maiores) + bônus de consistência (Fator R ≈ FS12/RBT12). `PARSER_VERSION` constante. **Dep.** T-506
- [ ] **T-508** Testes do parser contra as fixtures (campos e confiança mínima/máxima). **Dep.** T-507 *(testes prontos e verdes nas 10 fixtures sintéticas; falta rodar com fixtures reais — P-03)*
- [x] **T-509** Agente `parser_pgdas`:
  - `tracer.run(gatilho=upload)`;
  - span `parse` → span `tool` (match de CNPJ no escritório) → span `decide`;
  - status `linked` quando confiança ≥ limiar e CNPJ encontrado; senão `needs_review`;
  - render por template.

  **Dep.** T-404, T-507
- [x] **T-510** Escrita de receita: com `linked` e RPA presente, cria movimento `origem=pgdas` **na competência do PA**, só se a competência não existir. **Nunca** toca nos campos de folha. **Dep.** T-509
- [x] **T-511** Eval ouro automático após `linked`: motor sobre a série excluindo `origem=pgdas`; compara CNPJ, PA, RBT12, FS12, Fator R e anexo com tolerância; `ouro_indisponivel` quando não dá para comparar; grava via `scores.gold`. **Dep.** T-408, T-510
- [x] **T-512** Ações manuais: `POST /inbox/{id}/link` (escolher empresa, gera novo trace) e `POST /inbox/{id}/reject`. **Dep.** T-509
- [x] **T-513** Dataset `pgdas_extratos` no Langfuse a partir das fixtures + script `make parser-experiment` que roda a versão atual do parser como experimento. **Dep.** T-508, T-401
- [x] **T-514** Web, inbox: upload (arrastar e soltar), lista por status, detalhe com campos extraídos e confiança, vínculo/rejeição, link para o trace. **Dep.** T-512

**Aceite M5**
- [x] Extrato de texto com CNPJ conhecido vincula sozinho e não sobrescreve folha já lançada (PRD §13).
- [x] Extrato sem CNPJ da carteira fica `needs_review` (PRD §13).
- [x] Receita criada na competência do PA; competência existente não é alterada.
- [ ] Parser ≥ 80% de acerto ouro nas fixtures de extrato de texto (PRD §7.9). *(100% nas 10 fixtures sintéticas; falta medir com extratos reais — P-03)*
- [x] Texto bruto do PDF não aparece no Langfuse.

---

## M6 — Simulador, consultor e priorizador

- [x] **T-601** `domain/simulador.py` com a lógica da Plano §5.2 (reforço, pró-labore extra, custo INSS+IRRF, economia no horizonte, líquido, veredito com piso). **Dep.** T-203
- [x] **T-602** Testes do simulador: os três vereditos, piso de economia, líquido ≤ 0 e fração de pró-labore 0 e 1. **Dep.** T-601
- [x] **T-603** Migração `simulations` (`trace_id NOT NULL`). `POST /companies/{id}/simulations` roda dentro de `tracer.run(agente=consultor, gatilho=ficha)` e persiste a simulação no trace. **Dep.** T-601, T-404
- [x] **T-604** Web: simulador na ficha, com parâmetros editáveis, resultado, veredito em destaque, aviso "INSS sem teto na v1" e link para o trace. **Dep.** T-603
- [x] **T-605** Cliente Claude (`agents/llm.py`): Anthropic SDK, modelo `claude-sonnet-5`, timeout, retry, `max_tokens` baixo; prompts versionados em arquivo. **Dep.** T-405
- [x] **T-606** Span `plan` com LLM: classificação de intenção via tool use (`status_empresa|simular|explicar|priorizar`) e extração de parâmetros (empresa, PA, meta). Se falhar, usa regras de palavras-chave. **Dep.** T-605
- [x] **T-607** Validador do `render`: todo número do texto precisa existir na decisão estruturada; senão, usa template e anota no span. **Dep.** T-605
- [x] **T-608** Guarda do `decide`: recomendação `corrigir` sem `simulation_id` persistido é rejeitada (PRD §7.9). **Dep.** T-603
- [x] **T-609** Agente `consultor`: `POST /agents/consultor/chat` com contexto opcional da empresa; ferramentas motor e simulador; saída `{texto, decisao, trace_id}`. **Dep.** T-606, T-607, T-608
- [x] **T-610** Agente `priorizador`: `POST /agents/priorizador/chat`; ferramenta carteira do PA; decisão = fila vermelha e amarela ordenada por economia. **Dep.** T-303, T-606, T-607
- [x] **T-611** Rotina semanal: APScheduler dentro da api roda o `priorizador` todo domingo (`gatilho=rotina`, sem LLM no plan) e grava o resultado do trace. **Dep.** T-610
- [x] **T-612** Web, agentes: chat do consultor (painel lateral da ficha) e do priorizador; cada resposta com link para o trace; fila renderizada como tabela. **Dep.** T-609, T-610
- [x] **T-613** Testes dos agentes com o Anthropic mockado:
  - sem trace não grava;
  - `corrigir` sem simulação é rejeitado;
  - número inventado cai no template;
  - fallback de intenção.

  **Dep.** T-609, T-610

**Aceite M6**
- [x] O simulador devolve `ja_na_meta`, `corrigir` ou `nao_forcar` e persiste no trace (PRD §13).
- [x] "O que priorizar" devolve a fila com `trace_id` (PRD §12).
- [ ] A generation do Claude aparece no Langfuse com tokens e custo, aninhada no span. *(aninhamento provado com API simulada no nível HTTP; tokens/custo reais pendentes: não há ANTHROPIC_API_KEY na máquina)*
- [x] Nenhuma recomendação `corrigir` sem simulação no trace.

---

## M7 — Endurecimento e aceite final

- [x] **T-701** Backup diário: `pg_dump` da aplicação + Postgres e ClickHouse do Langfuse + `/data/uploads`, com rotação. Testar o restore uma vez.
- [x] **T-702** Retenção: nenhum job apaga traces ou movimentos; retenção do projeto Langfuse ≥ 24 meses (PRD §8).
- [x] **T-703** Segurança:
  - revisão do upload (magic bytes, path traversal, tamanho);
  - CSRF (SameSite + header de origem);
  - headers de segurança;
  - segredos só no `.env`;
  - rodar `/security-review`.
- [x] **T-704** Revisar que o disclaimer do PGDAS-D aparece em todas as telas, inclusive ficha, simulador e respostas dos agentes (PRD §8 e §13).
- [x] **T-705** E2E com Playwright cobrindo a PRD §13:
  1. login;
  2. 2 empresas × 12 competências;
  3. Fator R confere;
  4. troca de PA;
  5. upload vinculado sem mexer na folha;
  6. upload `needs_review`;
  7. semáforo;
  8. simulação com veredito;
  9. pergunta ao priorizador;
  10. nota humana no trace;
  11. disclaimer visível;
  12. ausência de login de cliente.
- [x] **T-706** Integração com o Langfuse de pé: buscar o trace pela API pública e conferir spans, generation, scores `gold_*` e `human_eval`, e o mascaramento.
- [ ] **T-707** Conferência manual: uma empresa real do escritório piloto contra o extrato PGDAS-D do mesmo PA. *(pendente: precisa dos dados de uma empresa real do escritório piloto + extrato do mesmo PA)*
- [x] **T-708** README com setup local, variáveis de ambiente, como rodar testes, E2E e experimento do parser, e acesso ao Langfuse.

**Aceite M7 / v1**
- [x] Todos os itens da PRD §13 passam no E2E (T-705). *(13/13 Playwright + 3/3 traces no Langfuse; item de Fator R conferido contra conta manual no teste, não contra a planilha P-07)*
- [x] Restore de backup testado.
- [x] Revisão de segurança sem achado alto aberto. *(2 revisões por subagente; ver Registro de decisões)*

---

## Ordem sugerida e paralelismo

```
P-01..P-07 (em paralelo, contínuo)
M0 → M1 → M2 ─┬─> M3 ─────────────┐
              └─> M4 ──> M5 ──> M6 ┴─> M7
```

- M3 e M4 podem andar em paralelo depois do M2.
- O M5 depende de P-03 (extratos reais). As fixtures sintéticas destravam o início.
- O M6 usa M3 (carteira do priorizador) e M4 (tracing).
