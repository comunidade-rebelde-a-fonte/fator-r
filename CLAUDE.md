# CLAUDE.md — Contrato de Execução do Projeto Fator R

Este arquivo é o **contrato de execução** do projeto. Vale para toda sessão de agente (Claude ou outro) e para qualquer pessoa que implemente tarefas deste repositório. Se algo aqui conflitar com um pedido pontual do usuário, **o pedido do usuário prevalece**, e o desvio deve ser registrado (ver §9).

---

## 1. Fontes da verdade (em ordem de precedência)

1. **Instrução explícita do usuário** na sessão.
2. **`docs/prd.md`**: o que construir e o que não construir, e as regras de domínio.
3. **`docs/plan.md`**: como construir (stack, arquitetura, modelo de dados, fórmulas, Langfuse).
4. **`docs/tasks.md`**: o que fazer agora, em que ordem, com que dependências e critérios de aceite.
5. **Este `CLAUDE.md`**: regras de execução, limites e definição de pronto.

Regras:
- Documentos em conflito: vale o de maior precedência, e o conflito é apontado ao usuário **antes** de implementar.
- Nada fora desses documentos entra no código sem aprovação (ver §9).
- O código nunca é fonte da verdade para regra de domínio. Se o código divergir do PRD ou do plano, o código está errado até decisão em contrário.

---

## 2. Escopo do projeto

**Dentro (v1, Fase 1 do PRD):**
- cadastro de empresas;
- movimentos mensais;
- motor Fator R;
- carteira;
- inbox PGDAS-D;
- simulador;
- agentes `parser_pgdas`, `consultor` e `priorizador`;
- observabilidade com Langfuse;
- pacotes comerciais na carteira.

**Fora (não implementar, nem parcialmente, nem "já deixando pronto"):**
- login, portal ou acesso de cliente final;
- white-label, app mobile ou WhatsApp;
- transmissão de PGDAS-D, emissão de DAS ou débito automático;
- integração eSocial, NFS-e ou certificado digital;
- folha de pagamento completa;
- planejamento de Lucro Presumido/Real;
- importação OFX/ERP;
- teto de INSS e múltiplos sócios no simulador (Fase 2);
- papéis analista vs sócio (Fase 2);
- UI de configuração da política de CPP (Fase 2);
- OCR de PDF escaneado (Fase 2).

---

## 3. Regras de domínio invioláveis

Violar qualquer item abaixo **bloqueia o merge**, mesmo com testes verdes.

1. **Cálculo não passa por LLM.** Fator R, RBT12, FS12, anexo, alíquotas, gap, economia e veredito do simulador são calculados só por `domain/` (Python puro, `Decimal`). O LLM só classifica intenção (`plan`) e redige texto (`render`) a partir de uma decisão já calculada.
2. **O parse é determinístico.** A extração do PGDAS-D é por regras (regex e heurísticas). O LLM nunca extrai campos de documento na v1.
3. **Fator R = FS12 ÷ RBT12; ≥ 0,28 → Anexo III; < 0,28 → Anexo V.** O corte legal é sempre 28%. A meta de 30% é só operacional (semáforo e simulador).
4. **Janela** = os 12 meses anteriores ao PA (PA−12 a PA−1). A competência do movimento é o mês da receita ou folha.
5. **RBT12 = 0 → `dados_insuficientes`.** Nunca inventar anexo, alíquota ou economia.
6. **FS12 só com remuneração com INSS**, mais CPP e FGTS recolhidos. Nunca aceitar como FS12 a distribuição de lucros, pró-labore sem INSS, PAT, VT, reembolso, NF de PJ ou verba indenizatória.
7. **Política de CPP é única por escritório** e aparece no cálculo e na ficha. Nunca vira escolha por empresa ou por analista.
8. **O extrato PGDAS-D nunca escreve campos de folha.** Pode criar só a **receita** (RPA), **na competência do próprio PA**, e só se a competência ainda não existir. Nunca sobrescreve movimento existente.
9. **Confiança < limiar do escritório ou CNPJ não encontrado → `needs_review`.** Sem escrita automática.
10. **Sem trace, não há decisão.** Toda decisão de agente é gravada via `record_decision(run, ...)` dentro de `tracer.run(...)`; o banco exige `trace_id NOT NULL`.
11. **`corrigir` só com simulação persistida no trace.** Sem `simulation_id`, o `decide` rejeita.
12. **Número no texto do agente precisa existir na decisão estruturada.** Se não existir, a resposta usa o template.
13. **Isolamento por escritório:** toda consulta tem `firm_id` no repositório **e** RLS no Postgres. Dado de um escritório nunca aparece para outro.
14. **Disclaimer permanente:** toda tela e toda resposta de agente deixam claro que o PGDAS-D da Receita Federal prevalece.
15. **Tabelas do Simples têm vigência por data.** O motor escolhe a tabela pelo PA; nunca usar valores fixos no código.
16. **A nota ouro ignora movimentos `origem=pgdas`**, para o parser não se avaliar contra dados que ele mesmo criou.

---

## 4. O que PODE

### 4.1 Código e arquitetura
- Implementar qualquer tarefa de `docs/tasks.md` com as dependências (**Dep.**) concluídas.
- Criar arquivos, módulos e testes dentro da estrutura da Plano §3.1 (`apps/api`, `apps/web`, `infra/langfuse`, `docs`).
- Refatorar código **tocado pela tarefa corrente** quando isso deixa a entrega mais simples, sem mudar o comportamento de outras tarefas.
- Criar helpers internos, fixtures e dados sintéticos de teste.
- Escolher detalhes de implementação que o plano não fixa (nome de função interna, organização de componentes, bibliotecas de UI menores) seguindo o padrão já existente no repo.

### 4.2 Banco
- Criar migrações Alembic novas para o que a tarefa exige.
- Criar índices e constraints coerentes com a Plano §4.
- Rodar migrações e seeds no ambiente local (`make migrate`, `make seed`).

### 4.3 Dependências
- Adicionar as dependências **já previstas no plano**: FastAPI, Pydantic, SQLAlchemy, Alembic, argon2, pdfplumber, pypdf, anthropic, langfuse, opentelemetry-instrumentation-anthropic, APScheduler, pytest, Playwright, Next.js, Tailwind e TanStack Query.
- Adicionar bibliotecas utilitárias pequenas e mantidas (ex.: um componente de tabela), registrando o motivo no resumo da tarefa.

### 4.4 Execução local
- Subir e derrubar os containers locais (`make up`/`down`), rodar testes, lint, typecheck, E2E e experimentos do parser.
- Usar o Langfuse **local/dev** e criar datasets, scores e traces de teste nele.
- Chamar a API da Anthropic em desenvolvimento com prompts curtos. Nos testes automatizados o cliente é **sempre mockado**.

### 4.5 Documentação
- Marcar tarefas como concluídas em `docs/tasks.md`.
- Atualizar `README.md` e comentários de código.
- Registrar desvios e decisões na seção **Registro de decisões** ao final de `docs/plan.md`.

---

## 5. O que NÃO PODE

### 5.1 Escopo
- Implementar nada da lista "Fora" da §2, nem stubs, rotas vazias ou flags para isso.
- Pular a ordem de dependências de `docs/tasks.md` sem aprovação.
- Fechar tarefa ou marco com critério de aceite pendente, "parcial" ou "a verificar depois".
- Mudar fórmula, limiar, piso, meta, corte legal ou regra da §3 por conta própria.

### 5.2 Código
- Colocar cálculo tributário fora de `domain/` (em rota, componente React, SQL, prompt ou LLM).
- Usar `float` para dinheiro ou percentual no backend. Só `Decimal` / `numeric`.
- Fixar alíquotas, faixas ou parcelas a deduzir no código.
- Consultar o banco sem `firm_id` ou criar role/conexão com `BYPASSRLS` para a aplicação.
- Gravar decisão de agente fora de `tracer.run` / `record_decision`.
- Mandar ao LLM números para ele calcular, ou usar a saída dele como valor persistido de domínio.
- Desligar, pular ou marcar como `xfail`/`skip` teste existente para "passar a CI".
- Silenciar erro com `except: pass` ou `# type: ignore` / `# noqa` sem justificativa em comentário.
- Deixar `print`, código comentado morto, TODO sem tarefa correspondente ou segredo no código.

### 5.3 Dados e segurança (LGPD)
- Commitar `.env`, chaves (Anthropic, Langfuse), dumps de banco ou extratos PGDAS-D **reais** (mesmo anonimizados, só em `fixtures/pgdas/` e após revisão do usuário).
- Enviar CNPJ, dados financeiros de clientes ou texto bruto de PDF a serviços externos que não sejam os previstos: Anthropic só com a decisão estruturada mínima; Langfuse **self-hosted** e mascarado.
- Usar Langfuse Cloud ou outro SaaS de observabilidade.
- Servir arquivo enviado por URL pública ou gravá-lo dentro da web root.
- Aceitar upload validado só pela extensão.
- Criar endpoint sem autenticação, fora `/health` e `/auth/login`.

### 5.4 Banco e infraestrutura
- Editar migração já aplicada/commitada; corrige-se com uma migração nova.
- Rodar `DROP`, `TRUNCATE`, `DELETE` em massa, `alembic downgrade` ou reset de volume em qualquer ambiente que não seja o local descartável, sem aprovação explícita.
- Apagar traces, movimentos ou documentos (retenção mínima de 24 meses). A desativação é lógica.
- Mexer em ambiente de produção ou servidor remoto sem pedido explícito.

### 5.5 Git
- Fazer commit, push, abrir PR, dar merge, rebase ou force-push **sem pedido do usuário**.
- Commitar direto em `main`.
- Reescrever histórico já publicado.
- Usar `--no-verify` para pular hooks.

---

## 6. Definição de PRONTO

### 6.1 Tarefa pronta (`T-xxx`)
Uma tarefa só é marcada `[x]` quando **todos** os itens abaixo são verdadeiros:

- [ ] **Escopo:** faz exatamente o que a descrição da tarefa em `docs/tasks.md` pede, nada da lista "Fora".
- [ ] **Dependências:** todas as **Dep.** estavam `[x]` antes de começar.
- [ ] **Regras de domínio:** nenhuma violação da §3.
- [ ] **Testes:** a lógica nova tem teste automatizado. Em `domain/` e `parsing/`, os testes cobrem os casos de fronteira listados no plano ou nas tarefas. Endpoint novo tem teste de isolamento entre escritórios.
- [ ] **Gates verdes** (§7): lint, typecheck, testes unitários e de integração do módulo afetado.
- [ ] **Migração**, se houver: aplica do zero (`make migrate` em banco vazio) e não quebra os dados de seed.
- [ ] **Tracing**, se a tarefa envolver agente: a corrida gera trace local + trace no Langfuse com o mesmo `trace_id` e os spans esperados.
- [ ] **UI**, se houver: a tela funciona no navegador contra a api real, mostra o disclaimer e trata os estados de carregando, vazio e erro.
- [ ] **Segurança:** sem segredo no código, sem endpoint aberto e sem dado de cliente em log.
- [ ] **Docs:** `docs/tasks.md` atualizado e desvio registrado (§9), se houver.
- [ ] **Relatório** entregue ao usuário (§8, etapa 7).

### 6.2 Marco pronto (`M0`–`M7`)
- [ ] Todas as tarefas do marco estão `[x]`.
- [ ] **Todos** os itens de "Aceite Mx" em `docs/tasks.md` foram verificados, com a evidência registrada no relatório (saída de teste, print ou trace_id).
- [ ] A suíte completa passa (`make lint test`), não só a do marco.
- [ ] Nenhuma regressão nos aceites dos marcos anteriores.
- [ ] O usuário foi informado e confirmou o fechamento do marco.

### 6.3 v1 pronta
- [ ] M0 a M7 prontos.
- [ ] O E2E (T-705) cobre e passa **todos** os itens da PRD §13.
- [ ] Os pré-requisitos P-01 a P-07 estão resolvidos ou têm decisão registrada.
- [ ] Parser ≥ 80% de acerto ouro nas fixtures de extrato de texto.
- [ ] Restore de backup testado; revisão de segurança sem achado alto aberto.
- [ ] Conferência manual de uma empresa real contra o PGDAS-D (T-707) batendo.

---

## 7. Gates de qualidade (comandos)

| Gate | Comando | Obrigatório em |
|---|---|---|
| Lint + format | `make lint` (ruff, eslint, prettier --check) | toda tarefa |
| Typecheck | `mypy --strict apps/api/src` e `tsc --noEmit` | toda tarefa |
| Testes unitários | `make test` (pytest) | toda tarefa |
| Isolamento entre escritórios | `pytest apps/api/tests/api -k isolation` | toda tarefa com endpoint |
| Migração do zero | `make down && make up && make migrate && make seed` | toda tarefa com migração |
| Parser vs fixtures | `pytest apps/api/tests/parsing` + `make parser-experiment` | toda tarefa em `parsing/` |
| Performance da carteira | `pytest -m perf` (200 empresas < 1 s) | M3 e mudanças em `/portfolio` |
| Integração Langfuse | `pytest -m langfuse` (com o Langfuse local de pé) | M4+ e mudanças em `tracing/` ou `agents/` |
| E2E | `make e2e` (Playwright) | fechamento de marco com UI; obrigatório no M7 |
| Segurança | `/security-review` | M5 (upload) e M7 |

Enquanto o M0 não cria um comando, a tarefa que o introduz é responsável por criá-lo. Gate que não roda conta como **gate falho**, não como gate ignorado.

---

## 8. Etapas de execução (ciclo obrigatório por tarefa)

Toda tarefa segue **estas etapas, nesta ordem**. Nenhuma pode ser pulada.

**Etapa 1 — Selecionar**
- Pegar a **próxima tarefa `[ ]`** em `docs/tasks.md` com todas as **Dep.** `[x]`, na ordem do documento, ou a tarefa indicada pelo usuário.
- Se a tarefa depender de um pré-requisito `P-xx` não resolvido: **parar** e avisar o usuário. Seguir só com dados sintéticos quando a própria tarefa permitir (ex.: T-504 com fixtures sintéticas).

**Etapa 2 — Entender**
- Ler a tarefa, a seção correspondente do `plan.md` e a seção do `prd.md` referenciada.
- Ler o código já existente que será tocado. Reusar utilitários de `core/`, `repositories/`, `domain/` e `tracing/` antes de criar novos.
- Listar os critérios de aceite da tarefa e do marco que ela afeta.

**Etapa 3 — Checar conflitos**
- Se houver ambiguidade, conflito entre documentos ou necessidade de sair do escopo: **parar e perguntar ao usuário** (§9). Não adivinhar regra de domínio.

**Etapa 4 — Testar primeiro onde houver regra**
- Para `domain/`, `parsing/`, guardas de agente e isolamento: escrever os testes com os casos do plano **antes** ou junto da implementação.

**Etapa 5 — Implementar**
- Mudança mínima que cumpre a tarefa, seguindo as convenções (§10).
- Sem antecipar tarefas futuras.

**Etapa 6 — Verificar**
- Rodar os gates da §7 aplicáveis.
- Se falhar: corrigir a causa, nunca o teste. Se a falha vier de outra tarefa, registrar e avisar.
- Para UI: abrir no navegador e exercitar o fluxo. Para agentes: conferir o trace no Langfuse.
- Percorrer a checklist da §6.1 item a item.

**Etapa 7 — Registrar e relatar**
- Marcar `[x]` em `docs/tasks.md`, só se a §6.1 estiver completa.
- Registrar desvios e decisões em `docs/plan.md` → "Registro de decisões".
- Relatar ao usuário, de forma curta:
  - tarefa;
  - o que foi feito;
  - arquivos principais;
  - gates rodados com resultado real (inclusive falhas);
  - pendências e desvios;
  - próxima tarefa sugerida.

**Etapa 8 — Fechar marco (quando for a última tarefa do marco)**
- Verificar cada item de "Aceite Mx" com evidência.
- Rodar a suíte completa e o E2E, se o marco tiver UI.
- Pedir confirmação ao usuário para considerar o marco fechado.
- Commit, PR e merge **só se o usuário pedir** (§5.5 e §10.3).

---

## 9. Controle de mudanças e bloqueios

**Parar e perguntar ao usuário quando:**
- a tarefa exigir algo da lista "Fora" (§2) ou violar a §3;
- houver conflito entre PRD, plano e tarefas;
- for preciso mudar fórmula, limiar, piso, meta, modelo de dados já migrado ou stack;
- uma dependência nova não prevista for grande (framework, serviço, banco);
- um pré-requisito `P-xx` bloquear a tarefa;
- um gate falhar por causa fora da tarefa e a correção não for trivial;
- houver qualquer ação destrutiva ou externa (§5.4, §5.5).

**Como registrar um desvio aprovado** (em `docs/plan.md`, seção "Registro de decisões"):

```
### AAAA-MM-DD — <título curto>
- Contexto: <o que motivou>
- Decisão: <o que foi decidido>
- Aprovado por: <usuário>
- Impacto: <tarefas/documentos afetados>
```

Se a decisão alterar regra do PRD, o PRD também é atualizado na mesma entrega.

---

## 10. Convenções

### 10.1 Backend (Python)
- Python 3.12, `uv`, `ruff` (lint + format), `mypy --strict`.
- Camadas:
  - `api/` só valida entrada e saída e chama serviços;
  - `domain/` sem I/O;
  - `repositories/` único acesso ao banco;
  - `agents/` orquestra `plan → tool → decide → render`;
  - `tracing/` único ponto de contato com o Langfuse.
- Dinheiro em `Decimal`; arredondamento só na serialização de saída.
- Competência como `date` no dia 1; na API, string `YYYY-MM`.
- Nomes de domínio em português, iguais ao PRD (`rbt12`, `fs12`, `competencia`, `pa`, `veredito`); infraestrutura em inglês.
- Erros de domínio como exceções próprias mapeadas para HTTP 4xx; nunca 500 por regra de negócio.

### 10.2 Frontend (Next.js)
- TypeScript estrito; tipos da API gerados a partir do OpenAPI do FastAPI.
- Nenhum cálculo tributário no front; ele só formata o que a API devolve.
- Formatação pt-BR (`R$ 1.234,56`, `28,00%`).
- Disclaimer do PGDAS-D no layout autenticado (componente único).

### 10.3 Git (quando o usuário pedir commit)
- Branch por marco: `feat/m<N>-<slug>` a partir de `main`.
- Commits pequenos, um por tarefa, no formato `T-xxx: <descrição imperativa>`.
- PR por marco com a checklist "Aceite Mx" preenchida e as evidências.

### 10.4 Langfuse
- Nome do trace = nome do agente; spans só `plan|parse|tool|decide|render`.
- Tags obrigatórias: `agente`, `gatilho`, `firm:<id>`. Metadata: `company_id`, `pa`, `parser_version`, `tabela_vigencia`, `politica_cpp`.
- Scores: `gold_<campo>` (BOOLEAN), `gold_acerto` (NUMERIC 0–1), `human_eval` (CATEGORICAL `acerto|parcial|erro`).
- Testes unitários com `LANGFUSE_TRACING_ENABLED=false`; integração com `pytest -m langfuse`.

---

## 11. Referência rápida

- Próxima tarefa: primeira `[ ]` em `docs/tasks.md` com as Dep. `[x]`.
- Na dúvida sobre regra de domínio: PRD §5 e §7 → Plano §5 → **perguntar**.
- Na dúvida sobre escopo: PRD §2.1, §3.1 e §10 → este arquivo, §2 → **perguntar**.
- Nunca: cálculo no LLM · folha a partir do extrato · decisão sem trace · consulta sem `firm_id` · commit sem pedido.
