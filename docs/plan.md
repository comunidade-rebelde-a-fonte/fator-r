# Plano de Implementação — Plataforma Fator R (v1)

Base: `docs/prd.md` v0.1 (2026-09-16)
Status: proposta para aprovação
Escopo: Fase 1 do PRD (v1 escritório)

## 1. Contexto

O PRD define o que construir e deixa a stack de fora. Este plano fecha a stack, o modelo de dados, a arquitetura dos agentes e da observabilidade, e quebra a v1 em marcos. Cada marco termina com critérios que batem com as regras de aceite do PRD (§13).

O repositório está vazio: só `docs/prd.md`. Não há código para reaproveitar.

## 2. Decisões tomadas

### 2.1 Stack

| Camada | Escolha |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic |
| Banco | PostgreSQL 16 |
| Frontend | Next.js (App Router, TypeScript), Tailwind, TanStack Query |
| Autenticação | Sessão do FastAPI em cookie httpOnly + SameSite=Lax, senha com argon2 |
| PDF | `pdfplumber` com fallback `pypdf`; upload aceita só PDF e TXT |
| LLM | Anthropic SDK, `claude-sonnet-5`, só para roteamento de intenção e redação do texto |
| Observabilidade de agentes | **Langfuse** self-hosted (SDK Python v4, baseado em OpenTelemetry) + `opentelemetry-instrumentation-anthropic` |
| Arquivos | Volume em disco (`/data/uploads/{firm_id}/{sha256}`), fora da web root, servido só por endpoint autenticado |
| Infra | Docker Compose (api, web, db), `pg_dump` diário |
| Testes | pytest + pytest-asyncio (backend), Playwright (fluxos críticos) |

### 2.2 Ajustes ao PRD, adotados como decisão

1. **RPA vai para o mês do PA.** O extrato do PA 09/2026 cria a receita de `2026-09`, não de `2026-08`. Isso segue a §7.3: a competência é o mês da receita. O texto da §7.6 deve ser corrigido.
2. **A nota ouro ignora movimentos criados pelo parser.** A comparação só usa competências com `origem ∈ {manual, folha}`. Se a janela usar algum movimento `origem=pgdas`, o eval fica como `ouro_indisponivel`.
3. **Data de início de atividade** entra no cadastro da empresa. O motor diferencia empresa nova (menos de 12 meses, cálculo proporcional) de mês sem lançamento (dado faltante).
4. **Tabelas dos Anexos III e V têm vigência por data** (`vigencia_inicio` e `vigencia_fim`). O motor escolhe a tabela pelo PA, então recalcular PA antigo continua certo, e 2027 entra como nova vigência.
5. **Piso de economia** é um valor absoluto por escritório (padrão R$ 6.000). Um piso proporcional ao porte fica para a Fase 2.
6. **Política de CPP**: um campo `cpp_das_integra_fs12` (bool) por escritório, editável só por seed ou admin na v1. A UI de configuração fica para a Fase 2, como o PRD prevê. O cálculo e a ficha mostram a política ativa.

## 3. Arquitetura

```
web (Next.js) ──HTTP/cookie──> api (FastAPI)
                                 ├─ domain/      motor, simulador, tabelas (Python puro, sem I/O)
                                 ├─ parsing/     extrator PGDAS-D (determinístico)
                                 ├─ agents/      parser_pgdas, consultor, priorizador
                                 ├─ tracing/     wrapper Langfuse + registro local de traces e evals
                                 ├─ repositories/ acesso ao banco sempre com firm_id
                                 └─ api/         rotas
                               ──> Postgres (RLS por firm_id)
                               ──> /data/uploads
                               ──> Anthropic API (só plan e render)
                               ──> Langfuse (web + worker, com Postgres, ClickHouse, Redis e MinIO próprios)
```

Princípios:
- `domain/` não importa banco nem LLM. Tudo em `Decimal`, arredondamento `ROUND_HALF_EVEN` só na exibição.
- Isolamento em duas camadas:
  - os repositórios exigem `firm_id`;
  - o Postgres tem RLS com `current_setting('app.firm_id')`, definido por transação no middleware.
- Nenhuma rota de agente grava decisão fora de `tracing.run()`. O banco garante: `trace_id NOT NULL` com FK nas tabelas de decisão.

### 3.1 Estrutura do repositório

```
apps/api/        src/fator_r/{domain,parsing,agents,tracing,repositories,api,core}
                 alembic/  tests/{domain,parsing,agents,api}  fixtures/pgdas/
apps/web/        app/(auth)/login  app/(app)/{carteira,empresas,inbox,agentes,observabilidade}
docs/            prd.md  plan.md
infra/langfuse/  docker-compose.langfuse.yml  .env.example
docker-compose.yml  Makefile
```

## 4. Modelo de dados

Valores monetários em `numeric(14,2)`, percentuais em `numeric(7,6)`. Toda tabela de negócio tem `firm_id`.

| Tabela | Campos principais | Restrições |
|---|---|---|
| `firms` | nome, `meta_operacional` (0,30), `limiar_confianca_parser` (0,40), `piso_economia_anual` (6000), `cpp_das_integra_fs12`, `tolerancia_ouro_pct` | |
| `users` | firm_id, email, senha_hash, nome, ativo | email único |
| `sessions` | user_id, token_hash, expira_em | |
| `companies` | nome, cnpj, cnae, atividade, sujeita_fator_r, qtd_socios, contato, pacote (`monitoramento\|correcao\|retainer`), honorario_mensal, ativo, notas, **inicio_atividade** | único (firm_id, cnpj) |
| `monthly_movements` | company_id, competencia (date, dia 1), receita_bruta, pro_labore, salarios, cpp, fgts, `folha_mes` (coluna gerada), origem (`manual\|pgdas\|folha\|agente`), observacao, pgdas_document_id? | único (company_id, competencia) |
| `simples_tables` | anexo (`III\|V`), faixa, rbt12_ate, aliquota_nominal, parcela_deduzir, vigencia_inicio, vigencia_fim | |
| `pgdas_documents` | company_id?, arquivo_path, sha256, mime, texto_extraido, campos_json, confianca, status (`received\|parsed\|needs_review\|linked\|rejected`), trace_id | único (firm_id, sha256) |
| `simulations` | company_id, pa, parametros_json, resultado_json, veredito, **trace_id NOT NULL** | |
| `agent_traces` | **id = trace_id do Langfuse** (32 hex), agente, gatilho, user_id, company_id?, entrada_json, saida_json, decisao_json, status (`ok\|error\|needs_review`), confianca, latencia_ms, langfuse_sync (`pending\|ok\|failed`), criado_em | Registro local mínimo; spans ficam no Langfuse |
| `agent_decisions` | trace_id NOT NULL, agente, tipo, dados_json | Decisão estruturada de toda corrida de agente (Registro de decisões 2026-09-17) |
| `evals_gold` | trace_id, campo, esperado, obtido, dentro_tolerancia, status (`ok\|erro\|ouro_indisponivel`) | |
| `evals_human` | trace_id, user_id, nota (`acerto\|parcial\|erro`), comentario | CHECK: comentário obrigatório quando `nota = 'erro'` |

Tabelas de negócio usam soft delete via `ativo`. Nenhum job apaga traces ou movimentos, o que cobre a retenção mínima de 24 meses. No Langfuse, a retenção do projeto também fica em 24 meses ou mais, e o backup diário cobre o Postgres e o ClickHouse dele.

## 5. Módulos de domínio

### 5.1 Motor Fator R (`domain/fator_r.py`)

`calcular(company, pa, movimentos, tabelas, politica) -> ResultadoFatorR`

1. **Janela:** de `pa − 12 meses` até `pa − 1 mês`.
2. **Meses válidos:** só contam os meses a partir de `inicio_atividade`. Um mês válido sem movimento é **faltante**.
3. **Empresa com menos de 12 meses:** RBT12 e FS12 são proporcionalizados pela média dos meses de atividade × 12. No primeiro mês de atividade, a base são os valores do próprio PA (Res. CGSN 140/2018, arts. 22 e 26). A fórmula vai ser conferida contra a Resolução antes do merge.
4. **FS12:** soma de pró-labore, salários, CPP e FGTS. A CPP entra conforme a política do escritório.
5. **Sem receita:** se RBT12 = 0, o status é `dados_insuficientes` e anexo e alíquotas voltam `None`.
6. **Fator e anexo:** `fator = FS12 / RBT12`. Anexo III se `fator ≥ 0,28`, senão Anexo V.
7. **Folha mínima:** `folha_min_28 = 0,28·RBT12` e `folha_min_meta = meta·RBT12`.
8. **Gap:** `gap_12m = max(0, folha_min_28 − FS12)` e `reforco_mensal = gap_12m / 12`. Os mesmos valores são calculados para a meta.
9. **Alíquota efetiva:** `(RBT12·nominal − PD) / RBT12`, com a tabela vigente no PA.
10. **Economia:** `economia_12m = (efetiva_V − efetiva_III) · RBT12`, usando RBT12 como proxy da receita dos próximos 12 meses.
11. **Semáforo:** vermelho abaixo de 0,28; amarelo de 0,28 até abaixo da meta; verde a partir da meta.

A saída também traz: janela, meses preenchidos e faltantes, política de CPP usada e a vigência da tabela.

### 5.2 Simulador (`domain/simulador.py`)

Entradas: resultado do motor, meta (0,30), fração de pró-labore (1,0), INSS do sócio (0,11), IRRF marginal (0,275), horizonte em meses (12), piso de economia do escritório.

Contas:
- **Reforço:** `reforco_12m = gap_meta` e `reforco_mensal = reforco_12m / 12`.
- **Pró-labore extra:** `pl_extra = reforco · fracao`.
- **Custo:** `custo = pl_extra · (inss + irrf)` no horizonte. A CPP não entra no custo porque, nos Anexos III e V, já está dentro do DAS.
- **Economia no horizonte:** `economia_h = economia_12m · horizonte / 12`.
- **Líquido:** `liquido = economia_h − custo`.

Veredito:
- `ja_na_meta` quando `fator ≥ meta`;
- `nao_forcar` quando `economia_12m < piso` **ou** `liquido ≤ 0`;
- `corrigir` nos demais casos.

O teto do INSS e múltiplos sócios ficam fora da v1, como diz o PRD. Na tela aparece o aviso "INSS sem teto na v1".

### 5.3 Tabelas

O seed das tabelas dos Anexos III e V (LC 123/2006, redação da LC 155/2016, vigência desde 2018-01-01) sai de um arquivo versionado `fixtures/simples_tables_2018.csv`. Esse CSV tem de ser conferido contra o texto legal antes do seed.

## 6. Parser PGDAS-D (`parsing/pgdas.py`)

- Extração do texto: `pdfplumber`. Se não vier texto, o PDF é tratado como imagem e marcado `needs_review` (sem OCR na v1).
- Campos: CNPJ, PA, RBT12, RPA, FS12, Fator R, valor do DAS e anexo, cada um por regex com variantes de rótulo e formato BR (`1.234,56`).
- Confiança por documento: média ponderada dos campos encontrados. CNPJ e PA pesam mais. Há bônus quando o Fator R extraído bate com FS12/RBT12 extraídos, dentro da tolerância.
- Vínculo: CNPJ normalizado procurado em `companies` do escritório.
- Status:
  - `linked` quando a confiança está no limiar ou acima **e** o CNPJ foi encontrado;
  - `needs_review` nos demais casos.
- Escrita: só com `linked` e RPA presente, e só quando não existe movimento da competência do PA. Cria um movimento `origem=pgdas` com receita apenas. **Nunca escreve campos de folha.**
- Fixtures: extratos de texto sintéticos e, quando houver, extratos reais anonimizados em `fixtures/pgdas/`, cada um com um JSON esperado.

## 7. Agentes e tracing

### 7.1 Langfuse como camada de observabilidade

**Divisão de responsabilidades:**

| Onde | O que guarda | Por quê |
|---|---|---|
| **Langfuse** | Trace completo: spans `plan → parse/tool → decide → render`, generations do Claude (prompt, resposta, tokens, custo, latência), scores, datasets e experimentos | Tracing de LLM pronto, com UI de spans, custo e comparação entre versões |
| **Postgres da aplicação** | `agent_traces` (resumo), `evals_gold`, `evals_human` | Garantias do PRD no banco: FK `trace_id NOT NULL` nas decisões, CHECK do comentário em `erro`, isolamento por `firm_id` e painel rápido |

O Langfuse é **self-hosted** na mesma infra (web, worker, Postgres, ClickHouse, Redis e MinIO, via `infra/langfuse/docker-compose.langfuse.yml`). CNPJ e dados financeiros de clientes não saem para SaaS de terceiros (LGPD). Há um projeto Langfuse por ambiente (`dev`, `prod`). A UI do Langfuse é para quem mantém a plataforma; o contador usa as telas da aplicação.

### 7.2 Contrato do tracing (`tracing/`)

```python
from langfuse import get_client, propagate_attributes

langfuse = get_client()

async with tracer.run(agente, gatilho, user, company, entrada) as run:
    # run.trace_id = langfuse.create_trace_id(); grava agent_traces antes de qualquer decisão
    with langfuse.start_as_current_observation(
        as_type="span", name=agente, trace_context={"trace_id": run.trace_id}
    ), propagate_attributes(
        user_id=str(user.id), session_id=str(company.id) if company else None,
        tags=[agente, gatilho, f"firm:{user.firm_id}"],
    ):
        with run.span("plan"): ...      # chamada ao Claude vira generation automaticamente
        with run.span("tool"): ...      # motor / simulador / parser
        with run.span("decide"): ...
        with run.span("render"): ...
    return run.finish(decisao=..., texto=..., confianca=..., status=...)
```

- **O ID é único nos dois lados.** O `trace_id` é gerado com `langfuse.create_trace_id()` (32 hex) e é o mesmo em `agent_traces.id` e no Langfuse. O link "abrir no Langfuse" sai direto dele.
- **Sem trace, não grava.** A linha de `agent_traces` é criada na mesma transação que qualquer escrita de decisão. Se falhar, faz rollback de tudo. O envio ao Langfuse é assíncrono (batch do SDK) e não bloqueia a transação; `langfuse_sync` registra falhas de exportação para reenvio ou alerta.
- **Claude instrumentado.** `AnthropicInstrumentor().instrument()` no startup, então toda chamada ao Claude aparece como generation aninhada no span `plan` ou `render`, com tokens e custo.
- **Mascaramento.** O hook `mask_otel_spans` do SDK remove o texto bruto do PDF e trunca payloads grandes antes da exportação. O texto completo fica só em `pgdas_documents`.
- **Metadados em todo trace:** `firm_id`, `company_id`, `pa`, versão do parser, versão da tabela do Simples e política de CPP.
- **Testes:** `LANGFUSE_TRACING_ENABLED=false` nos testes unitários; o registro local continua funcionando.
- Toda resposta de agente segue o formato `{texto, decisao, trace_id}`.

### 7.3 Agentes

| Agente | plan | tool | decide | render |
|---|---|---|---|---|
| `parser_pgdas` | sem LLM (gatilho = upload) | parse e match de CNPJ | status, vínculo, movimento criado ou não | template |
| `consultor` | LLM classifica a intenção (`status_empresa\|simular\|explicar`) e extrai os parâmetros | motor e simulador (simulação persistida) | anexo, gap, veredito | LLM redige a partir da decisão |
| `priorizador` | LLM, ou gatilho da rotina semanal sem LLM | carteira do PA | fila de vermelhos e amarelos ordenada por economia | LLM ou template |

Guardas:
- O LLM só recebe a decisão estruturada. Um validador confere se todo número no texto aparece na decisão; se não aparecer, usa o template e registra no span.
- Uma recomendação `corrigir` sem `simulation_id` no trace é rejeitada pelo `decide`.
- Rotina semanal: job simples (APScheduler dentro da api) que roda o `priorizador` todo domingo.

### 7.4 Evals

- **Ouro:** roda depois de todo `parser_pgdas` com status `linked`. Compara CNPJ, PA, RBT12, FS12, Fator R e anexo com o motor sobre a série lançada, excluindo movimentos `origem=pgdas` (decisão 2.2-2), com a tolerância do escritório. O resultado é gravado em `evals_gold` e enviado ao Langfuse como scores: um `gold_<campo>` (BOOLEAN) por campo e um `gold_acerto` (NUMERIC, 0–1) no trace.
- **Humano:** a nota é dada na tela da aplicação, gravada em `evals_human` (com o CHECK do comentário) e espelhada no Langfuse com `langfuse.create_score(name="human_eval", value="acerto|parcial|erro", data_type="CATEGORICAL", trace_id=..., comment=...)`.
- **Regressão do parser:** as fixtures de `fixtures/pgdas/` viram um **dataset do Langfuse** (`pgdas_extratos`). Cada mudança no parser roda um experimento contra o dataset, e a comparação entre versões fica na UI do Langfuse. A CI roda o mesmo conjunto localmente via pytest.
- **Painel da aplicação:** os KPIs do PRD (corridas 24 h e totais, pendências sem nota, acerto ouro e humano, volume, latência, confiança, erros e reviews por agente) saem do Postgres local. Custo e tokens do Claude vêm do Langfuse, pela API de métricas, com cache de 5 min.

## 8. API (resumo)

```
POST /auth/login  POST /auth/logout  GET /auth/me
GET|POST /companies  GET|PATCH /companies/{id}
GET /companies/{id}/movements  PUT /companies/{id}/movements/{competencia}
GET /companies/{id}/fator-r?pa=YYYY-MM
POST /companies/{id}/simulations
GET /portfolio?pa=YYYY-MM                 # carteira + KPIs
POST /inbox/pgdas (multipart)  GET /inbox  GET /inbox/{id}  POST /inbox/{id}/link|reject
POST /agents/{consultor|priorizador}/chat
GET /observability/summary  GET /traces?agente=  GET /traces/{id}  POST /traces/{id}/human-eval
```

Performance da carteira: uma consulta que carrega os movimentos da janela de todas as empresas ativas, com o motor rodando em memória. Meta: menos de 1 s com 200 empresas × 12 meses. Índice em `monthly_movements(company_id, competencia)`.

## 9. Frontend (telas)

1. **Login**
2. **Carteira:**
   - seletor de PA;
   - KPIs: monitoradas, no V, no limite, seguras, economia em jogo, honorários;
   - tabela com semáforo e ordenação padrão do PRD.
3. **Empresas:** lista, cadastro e ficha. A ficha mostra o resultado do motor, a política de CPP, a grade de 12 meses editável e o simulador.
4. **Inbox PGDAS-D:** upload, lista por status e detalhe com campos extraídos e confiança. O detalhe permite vincular ou rejeitar manualmente.
5. **Agentes:** chat do consultor (no contexto da ficha) e do priorizador. Cada resposta traz link para o trace.
6. **Observabilidade:** cards (corridas em 24 h e no total, pendências sem nota, acerto ouro, acerto humano, custo do Claude), tabela por agente e lista de traces com filtro. O detalhe do trace mostra o resumo, os spans (lidos da API do Langfuse), os evals, o formulário de nota e o link "abrir no Langfuse".

**Rodapé fixo em todas as telas:** "Esta plataforma não é a apuração oficial. O PGDAS-D da Receita Federal prevalece."

## 10. Marcos

| # | Marco | Entregas | Aceite (PRD §13) |
|---|---|---|---|
| M0 | Fundação | Compose, esqueleto da api e do web, Alembic, CI com lint e testes, seed de escritório e usuário | `make up` sobe tudo; login funciona; não existe rota de cliente |
| M1 | Cadastro e movimentos | companies, movements (upsert), RLS, telas de empresas e grade mensal | Teste de isolamento: usuário do escritório A recebe 404 nos recursos do B |
| M2 | Motor e tabelas | `domain/fator_r.py`, seed de tabelas, endpoint e ficha | Com 2 empresas × 12 meses, o motor bate com a planilha manual; trocar o PA move a janela |
| M3 | Carteira | endpoint `/portfolio`, KPIs, semáforo, ordenação | Semáforo separa <28%, 28–30% e ≥30%; 200 empresas em menos de 1 s |
| M4 | Tracing e observabilidade | Langfuse self-hosted no compose, `tracing/` com SDK v3 e instrumentação Anthropic, `agent_traces` e evals locais, espelhamento de scores, painel e detalhe do trace, nota humana | Trace com spans visível no Langfuse com o mesmo `trace_id` da aplicação; nota humana gravada localmente e como score; nota `erro` sem comentário é rejeitada |
| M5 | Inbox e `parser_pgdas` | upload, parser, vínculo, movimento de receita, eval ouro | Extrato com CNPJ conhecido vincula sozinho e não mexe na folha; CNPJ desconhecido cai em `needs_review` |
| M6 | Simulador, consultor e priorizador | simulador, integração Claude, validador de números, rotina semanal | Simulador devolve um dos 3 vereditos e o persiste no trace; "o que priorizar" retorna a fila com `trace_id` |
| M7 | Endurecimento | disclaimer, backup diário, retenção, testes E2E Playwright, revisão de segurança do upload | Todos os itens da §13 passam no E2E |

## 11. Verificação

- **Unitários de domínio:** casos tabelados para o motor, incluindo:
  - fronteiras 27,99% / 28,00% / 29,99% / 30,00%;
  - RBT12 = 0;
  - empresa com 1, 5 e 12 meses;
  - mês faltante;
  - política de CPP ligada e desligada;
  - troca de vigência de tabela.

  Para o simulador: os três vereditos e o piso.
- **Parser:** cada fixture de `fixtures/pgdas/` confere o JSON esperado e a confiança mínima ou máxima. Acompanhar a métrica de acerto ouro (meta ≥ 80% em extrato de texto).
- **API:** testes de isolamento entre escritórios em todos os endpoints (parametrizados). Upload rejeita outros MIME e arquivos acima do tamanho máximo.
- **Langfuse (integração):** com o compose do Langfuse de pé, rodar um agente e buscar o trace pela API pública do Langfuse pelo `trace_id`. Conferir os spans `plan/tool/decide/render`, a generation do Claude, os scores `gold_*` e `human_eval`, e que o texto bruto do PDF não aparece (mascaramento). Com o Langfuse fora do ar, o agente ainda grava o `agent_traces` e marca `langfuse_sync=failed`.
- **Agentes:** o cliente Anthropic é mockado nos testes. Verificar que:
  - sem trace não há escrita;
  - `corrigir` sem simulação é rejeitado;
  - texto com número inventado cai no template.
- **E2E (Playwright):** o roteiro da §13 completo, com login, 2 empresas e 12 competências, troca de PA, upload vinculado, upload `needs_review`, simulação, pergunta ao priorizador, nota humana e disclaimer visível.
- **Manual:** conferir a conta de uma empresa real do escritório piloto contra o extrato PGDAS-D do mesmo PA.

## 12. Pendências (não bloqueiam o M0–M4)

- Confirmar com o escritório piloto se a CPP do DAS entra na FS12 (define o valor do seed).
- Conseguir 5 a 10 extratos PGDAS-D reais anonimizados antes do M5.
- Conferir o CSV das tabelas e a fórmula de proporcionalização contra a LC 123 e a Res. CGSN 140.
- Limiar do parser (0,40) e piso (R$ 6.000): manter como padrão configurável e revisar após 90 dias.
- Langfuse: definir o servidor (a stack pede ClickHouse, Redis e MinIO, então conte ~4 GB de RAM a mais) e quem terá acesso à UI dele.
- Corrigir no PRD a §7.6 (mês do RPA) e registrar as decisões da §2.2.

## 13. Registro de decisões

Formato e regras em `CLAUDE.md` §9. Entradas mais recentes no topo.

### 2026-09-22 — Grade mensal: folha do PGDAS-D numa célula única
- Contexto: no teste manual, as linhas vindas do extrato mostravam a folha em "Salários + 13º/férias" e 0,00 em pró-labore, CPP e FGTS, campos que o PGDAS-D não tem.
- Decisão: só a tela. Em linhas `origem=pgdas`, as quatro colunas de folha viram uma célula "Folha declarada no PGDAS-D: R$ X" (ou "Folha não informada no extrato"), com "Detalhar folha" para abrir os campos; salvar a linha a torna manual, como antes. O dado continua em `salarios` (§3.8) e o motor não muda. Alternativas rejeitadas: coluna `folha_declarada` no banco (migração + mudança no motor) e folha única para todos (conflita com §3.6/§3.7).
- Aprovado por: Alfredo (opção "Só a tela")
- Impacto: T-810, `apps/web/components/empresas/GradeMensal.tsx`.

### 2026-09-22 — Carteira: aumento de folha rotulado
- Contexto: no teste manual, a célula "Reforço mensal (28% · meta)" mostrava "R$ 966,67 · R$ 1.166,67" sem dizer o que era cada número.
- Decisão: coluna "Aumento de folha por mês", com duas linhas rotuladas ("+ R$ X para chegar a 28% (Anexo III)" e "+ R$ Y para a meta de N%"); "já atinge 28%" e "já na meta" quando o valor é zero. Os valores continuam vindo do motor (`reforco_mensal_28` e `reforco_mensal_meta`); o front só rotula. A meta vem do escritório (`meta_operacional` por linha em `/portfolio`), nunca fixa em 30% na tela.
- Aprovado por: Alfredo (escolheu a opção "Aumento rotulado")
- Impacto: T-809, `api/portfolio.py`, `apps/web/app/(app)/carteira/page.tsx`.

### 2026-09-22 — Extrato passa a lançar os 12 meses anteriores (receita e folha) — altera a regra §3.8
- Contexto: ao testar o M8, o usuário importou o extrato e só a competência do PA foi lançada, embora o extrato traga as tabelas "Receitas Brutas Anteriores" e "Folha de Salários Anteriores" dos 12 meses da janela. Opções apresentadas: só receitas (recomendada), receitas e folha, ou manter. Riscos informados: a folha do extrato é um total e o sistema guarda pró-labore, salários, CPP e FGTS separados (§3.6, §3.8).
- Decisão (escolha do usuário: receitas **e** folha):
  - com as tabelas no extrato, grava os meses PA−12 a PA−1, só em competências vazias, nunca sobrescreve, `origem=pgdas`, em todos os caminhos de vínculo (automático, manual e cadastro pelo extrato);
  - só grava série que confere: meses = janela do PA e soma = RBT12 / FS12 declarados (tolerância R$ 0,01); se não conferir, nada dos meses anteriores é gravado e o motivo vai para a decisão e para o texto;
  - folha declarada inteira no campo `salarios`, com pró-labore, CPP e FGTS zerados e observação "total declarado no PGDAS-D, sem divisão". Não se inventa rateio. Com CPP zerada, a política de CPP do escritório não soma nada a esses meses e a FS12 fica igual à declarada;
  - atividade que o extrato diz não ter fator r: folha zero; sujeita ao fator r (ou indeterminada) sem folha conferida: nenhum mês anterior é gravado, para não criar folha zero falsa;
  - para conferir as tabelas, o parser (`2026.09.3`) passou a ler RBT12 e "Total FS12" no layout declaratório; as lacunas desses dois campos saíram das fixtures (resta o DAS → T-504);
  - data de abertura no CNPJ pré-preenche o início de atividade no cadastro pelo extrato (editável).
- Consequência aceita: empresa com meses `origem=pgdas` na janela fica com a nota ouro indisponível (§3.16), porque o parser não pode ser avaliado contra o que ele mesmo lançou.
- Aprovado por: Alfredo (resposta à pergunta de 2026-09-22)
- Impacto: `CLAUDE.md` §3.8, PRD §7.6 (v0.3), `parsing/pgdas.py`, `agents/parser_pgdas.py`, `api/inbox.py`, web (cadastro pelo extrato), fixtures `pdf_declaratorio_*`, T-808.

### 2026-09-22 — M8: cadastro de empresa a partir do extrato PGDAS-D
- Contexto: extrato de CNPJ fora da carteira parava em `needs_review` (`cnpj_nao_encontrado`) e obrigava o analista a cadastrar a empresa em outra tela e voltar para vincular. Especificação completa em `.claude/sdd/archive/CADASTRO_EMPRESA_PELO_EXTRATO/`.
- Decisão:
  - cadastro **só com confirmação humana**, em um clique a partir do inbox e do resultado do upload; a §3.9 continua valendo (nenhuma escrita automática para CNPJ desconhecido);
  - casamento continua por CNPJ exato de 14 dígitos; sem casamento por raiz, sem consulta de CNPJ em serviço externo (§5.3) e sem CNPJ editável no formulário;
  - endpoint único `POST /inbox/{id}/cadastrar-empresa`: pré-checagens (estado, CNPJ lido válido, CNPJ igual ao lido, CNPJ ainda não cadastrado) fora do trace; criação da empresa (`companies.adicionar`, sem commit), vínculo, receita do PA (§3.8 inalterada) e decisão numa transação só, dentro de `tracer.run(gatilho="cadastro_pelo_extrato")`;
  - parser (`PARSER_VERSION 2026.09.2`) lê nome empresarial e sugere `sujeita_fator_r` pela linha do fator r (número → sim; "não se aplica" → não; senão, sem sugestão). Ambos ficam **fora** da confiança e da nota ouro;
  - parser lê o PA no formato de intervalo (`01/08/2026 a 31/08/2026`) só quando início e fim são do mesmo mês; RBT12, FS12 e DAS desse layout ficam para a T-504;
  - anexo passa a ser lido primeiro de linha estruturada (`Fator r`, `Enquadramento`, `Atividade`), para não pegar "Anexo III" de parágrafo explicativo (sinalizado ao usuário como acréscimo de escopo);
  - fixtures do layout declaratório guardam o valor verdadeiro e declaram `lacunas_conhecidas`; para esses campos o teste exige `None`;
  - na web, o Fator R do formulário de empresa passa de checkbox para Sim/Não em todas as telas (padrão continua "Sim").
- Aprovado por: Alfredo (respostas no brainstorm e no define; pediu o build do design)
- Impacto: `docs/tasks.md` (M8, T-801..T-807), PRD §7.6, `parsing/pgdas.py`, `agents/parser_pgdas.py`, `repositories/companies.py`, `api/inbox.py`, `apps/web` (inbox e formulário de empresa), fixtures `pdf_declaratorio_*`.

### 2026-09-17 — Revisão de segurança final (M7) e riscos aceitos
- Contexto: segunda revisão por subagente (sem commits para o `/security-review`). Nenhum achado alto; as correções do M5 foram confirmadas como efetivas.
- Decisão: corrigidos M2 (validador do render: números por extenso, sinal, números colados em letra, veredito contraditório), M3 (o `plan` envia só a mensagem ao Anthropic; a empresa é resolvida localmente; o `render` recebe só a decisão calculada, sem CNPJ), B1 (PA inválido vindo do LLM é descartado), B2 (senhas de ClickHouse e Redis fora da linha de comando), B3 (`trap` de limpeza no teste de restore), B4 (`AUTH_DISABLE_SIGNUP` no Langfuse), B5 (no máximo 2 extrações de PDF simultâneas) e B7 (máscara de CPF e CNPJ com espaços). Também T-703: FKs compostas por firm_id, CSRF por Origin, headers e CSP.
- Riscos aceitos na v1 (uso interno):
  - M1: sem proxy configurado, o rate limit enxerga o IP do gateway Docker e degrada para limite por e-mail. Exigência de deploy: proxy reverso e `FORWARDED_ALLOW_IPS` com o IP do proxy (P-06).
  - B6: funções de sistema `rotina_escritorios` e `tracing_marcar_sync` acessíveis à role da aplicação, sem acesso HTTP e com impacto só em metadados.
  - Sessões com INSERT/DELETE direto pela role da aplicação (sem SQL injection conhecido).
  - Backups sem criptografia em repouso: cifrar antes de copiar para fora da máquina (P-06).
- Aprovado por: Alfredo (pediu para concluir até o prompt 24)
- Impacto: T-703, README (seção de deploy), P-06.

### 2026-09-17 — Revisão de segurança do M5 por subagente e correções
- Contexto: o `/security-review` exige repositório git com mudanças commitadas; o repositório não tem commits.
- Decisão: revisão de segurança feita por subagente, lendo os arquivos diretamente. Achados altos e médios corrigidos no M5, com testes de regressão (`tests/api/test_seguranca_revisao_m5.py`):
  - A1: limite de corpo (middleware ASGI, antes da autenticação);
  - A2: regex com quantificadores limitados e linhas truncadas;
  - M1: extração e parse em processo separado, com timeout, teto de páginas, texto e memória;
  - M2: CNPJ mascarado em tudo que vai para o Langfuse;
  - M3: rate limit por par IP+e-mail, teto por IP, sem criar chave na consulta, limpeza periódica, `--proxy-headers`;
  - B4: ENV padrão `prod`.
  Achados baixos (B1 role dedicada para jobs de trace; B2 sessões só por função; B3 FKs compostas por firm_id; B5 checagem de Origin; B6 arquivo órfão; B7 permissão da pasta base) ficam para a T-703.
- Aprovado por: Alfredo (pediu para concluir até o prompt 24)
- Impacto: T-514/M5, T-703.

### 2026-09-17 — Langfuse SDK v4, tabela agent_decisions e sync por funções dedicadas
- Contexto: o SDK instalado é o Langfuse Python 4.15 (servidor 4.37), não o v3 citado no plano. As tabelas de decisão (`simulations`, `pgdas_documents`) só chegam no M5/M6, mas a guarda "sem trace não grava" precisa ser testável no M4.
- Decisão: (1) usar o SDK v4 (mesma API: `start_as_current_observation`, `propagate_attributes`, `create_score`, `mask_otel_spans`); (2) criar `agent_decisions` (firm_id, trace_id NOT NULL, agente, tipo, dados_json), onde todo agente grava sua decisão estruturada via `record_decision`; (3) o status de exportação vem de um exporter que envolve o OTLP, e o job de sync usa funções `SECURITY DEFINER` específicas (`tracing_*`), sem role dona.
- Aprovado por: decisão técnica dentro do escopo (CLAUDE.md §4.1); nenhuma regra de domínio muda
- Impacto: T-401..T-411; `docs/plan.md` §2.1 (SDK) e §4 (nova tabela).

### 2026-09-17 — RLS com role da aplicação separada, sem FORCE
- Contexto: o prompt 05 pedia `ENABLE` + `FORCE ROW LEVEL SECURITY`. Com `FORCE`, a role dona também fica sujeita ao RLS, o que bloqueia o caminho explícito de migrações, seed e funções de login quando a dona não é superusuária.
- Decisão: a api conecta com `fator_r_app` (sem BYPASSRLS, sem ser dona das tabelas, sem DELETE em dados de negócio). RLS `ENABLE` sem `FORCE`. O login lê usuários só pelas funções `SECURITY DEFINER` `auth_find_user` e `auth_session_user`. Migrações e seed usam a role dona (`DATABASE_OWNER_URL`).
- Aprovado por: decisão técnica dentro do escopo (CLAUDE.md §4.1); o isolamento exigido pelo §3.13 fica igual para a api
- Impacto: T-103, `make migrate` (também habilita a role), testes (`tests/api/test_rls.py`).

### 2026-09-17 — Execução contínua dos prompts 05 a 24
- Contexto: o contrato pede confirmação do usuário a cada fechamento de marco.
- Decisão: o usuário confirmou o M0 e autorizou seguir até o prompt 24 sem parar a cada marco. Tarefas bloqueadas por pré-requisito (P-03, P-04, P-05, P-07) ou por dados reais (T-707) ficam `[ ]`, com o motivo registrado, e a execução segue no que não depende delas.
- Aprovado por: Alfredo
- Impacto: prompts 05 a 24; o fechamento formal dos marcos com pendência fica para depois dos pré-requisitos.

### 2026-09-17 — CI do M0 fechada com verificações locais
- Contexto: o aceite do M0 pede "CI verde", mas o repositório ainda não tem commits nem remoto no GitHub.
- Decisão: fechar o M0 com `make lint`, `make test` e `actionlint` no workflow, rodados localmente. A CI remota fica pendente até existir o repositório.
- Aprovado por: Alfredo
- Impacto: aceite do M0 (`docs/tasks.md`), prompt 04.

### 2026-09-17 — Tolerância da nota ouro = 1%
- Contexto: `firms.tolerancia_ouro_pct` não tinha valor definido em nenhum documento.
- Decisão: seed com 0,01 (1%).
- Aprovado por: Alfredo
- Impacto: T-011 (seed), T-511 (eval ouro).

### 2026-09-17 — P-02 resolvido: a CPP do DAS integra a FS12
- Contexto: PRD §5 e §16 deixavam a política de CPP para o escritório piloto.
- Decisão: confirmado pelo escritório piloto que a CPP embutida no DAS entra na FS12. Seed com `cpp_das_integra_fs12 = true`.
- Aprovado por: Alfredo
- Impacto: T-011 (seed), motor (T-203), ficha (T-207).

### 2026-09-16 — Stack, LLM, Langfuse e ajustes ao PRD
- Contexto: o PRD não define stack e tinha inconsistências (mês do RPA, nota ouro que avaliava o parser contra dados criados por ele mesmo, empresa nova, tabelas sem vigência).
- Decisão: FastAPI + Next.js + Postgres; Claude só em `plan`/`render`; Langfuse self-hosted; ajustes da §2.2 adotados.
- Aprovado por: Alfredo
- Impacto: `docs/plan.md`, `docs/tasks.md` (P-01 corrige a PRD §7.6).
