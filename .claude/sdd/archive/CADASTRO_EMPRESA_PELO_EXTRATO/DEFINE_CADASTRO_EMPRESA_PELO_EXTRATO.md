# DEFINE: Cadastro de empresa a partir do extrato PGDAS-D

> Quando o extrato enviado ao inbox é de um CNPJ que não está na carteira, o analista cadastra a
> empresa e vincula o documento em um clique, com o formulário pré-preenchido pelo extrato.

## Metadata

| Atributo | Valor |
|---|---|
| **Feature** | CADASTRO_EMPRESA_PELO_EXTRATO |
| **Data** | 2026-09-22 |
| **Autor** | define (a partir de `BRAINSTORM_CADASTRO_EMPRESA_PELO_EXTRATO.md`) |
| **Status** | ✅ Shipped (2026-09-22) |
| **Clarity Score** | 14/15 |
| **Origem** | Pedido do usuário; não está em `docs/tasks.md` (entra como tarefas novas — ver "Impacto em documentos") |

---

## Problem Statement

Quando o analista sobe um extrato PGDAS-D de uma empresa que ainda não está na carteira, o documento
para em `needs_review` (`cnpj_nao_encontrado`) e o único caminho é sair do inbox, cadastrar a empresa
na tela de Empresas redigitando CNPJ e nome, e voltar ao inbox para vincular à mão — por isso
extratos de clientes novos ficam represados sem receita lançada.

---

## Target Users

| Usuário | Papel | Dor |
|---|---|---|
| Analista do escritório | Opera o inbox e mantém a carteira | Três telas e redigitação de CNPJ e nome a cada cliente novo; risco de erro de digitação no CNPJ |
| Sócio/responsável do escritório | Acompanha a carteira e o priorizador | Clientes novos entram tarde na carteira, sem receita, e somem do semáforo e do priorizador |

---

## Goals

| Prioridade | Objetivo |
|---|---|
| **MUST** | Cadastrar a empresa e vincular o documento sem sair do inbox, com confirmação humana antes de qualquer escrita |
| **MUST** | Formulário pré-preenchido com CNPJ (travado), nome empresarial e sugestão de `sujeita_fator_r` lidos do extrato |
| **MUST** | Empresa já cadastrada continua sendo vinculada automaticamente, sem regressão |
| **MUST** | Receita do PA criada após o cadastro, quando PA e RPA forem lidos, respeitando a §3.8 |
| **MUST** | Parser lê o PA no formato de intervalo do layout declaratório (`01/08/2026 a 31/08/2026`) |
| **SHOULD** | O mesmo bloco de cadastro aparece no resultado do upload, não só no card/detalhe do inbox |
| **SHOULD** | CNPJ cadastrado por outra pessoa no meio do caminho vira oferta de "vincular à empresa existente" |
| **COULD** | Texto do agente (`render`) após o cadastro cita a empresa criada e o movimento gerado |

---

## Success Criteria

- [ ] **4 de 4** PDFs de `pdf/com_cnpj/` com `nome_empresarial` e `pa = 2026-08` extraídos corretamente.
- [ ] **4 de 4** PDFs com a sugestão de `sujeita_fator_r` esperada (01 → `true`, 02 → `false`, 03 → `false`, 04 → `true`).
- [ ] Confiança dos 4 PDFs sobe de 0,35–0,45 para **0,60–0,70**, sem nenhuma mudança de peso.
- [ ] **0 regressões** nas 10 fixtures sintéticas existentes: campos idênticos e confiança dentro da faixa de cada `expected.json`.
- [ ] Do upload até empresa criada + documento `linked`: **no máximo 2 interações** do analista ("Cadastrar e vincular" → "Confirmar").
- [ ] **100%** das chamadas do endpoint novo gravam trace local e no Langfuse com o mesmo `trace_id` e `gatilho=cadastro_pelo_extrato`.
- [ ] **0** escritas (empresa, vínculo ou movimento) sem confirmação humana quando o CNPJ é desconhecido.
- [ ] Gates verdes: `make lint`, `make test`, `pytest apps/api/tests/api -k isolation`, `pytest apps/api/tests/parsing`, `make parser-experiment`, `pytest -m langfuse` e `make e2e`.

---

## Acceptance Tests

| ID | Cenário | Dado | Quando | Então |
|---|---|---|---|---|
| AT-001 | Caminho feliz | Escritório sem empresa com CNPJ 12.345.678/0001-95 | Analista sobe `01_servico_fator_r_abaixo_28.pdf` e confirma o formulário pré-preenchido | Empresa criada com esse CNPJ e o nome confirmado; documento `linked`; movimento de 2026-08 com receita 10.000,00, `origem=pgdas`, folha zerada |
| AT-002 | Empresa já cadastrada (regressão) | Empresa com CNPJ 45.678.901/0001-75 na carteira | Analista sobe `04_servico_fator_r_acima_28.pdf` | Vinculado automaticamente, sem formulário (confiança 0,70 ≥ limiar 0,40) |
| AT-003 | CNPJ cadastrado no meio do caminho | Documento em `needs_review`; outra sessão cadastra o mesmo CNPJ | Analista confirma o formulário | 409 com o `company_id` existente; nenhuma empresa nova; documento continua `needs_review`; UI oferece vincular à existente |
| AT-004 | CNPJ divergente | Documento com CNPJ lido A | Corpo da requisição traz CNPJ B | 422; nada é criado |
| AT-005 | Documento em estado final | Documento `linked` ou `rejected` | Chamada ao endpoint de cadastro | 409; nada é criado |
| AT-006 | Isolamento entre escritórios | Documento do escritório A | Usuário do escritório B chama o endpoint com o id do documento | 404; nenhuma empresa criada em nenhum escritório |
| AT-007 | PA não lido | Extrato sem PA legível, CNPJ válido e desconhecido | Analista confirma o cadastro | Empresa criada, documento `linked`, `movimento=sem_rpa`, nenhum movimento criado |
| AT-008 | CNPJ não lido ou com DV inválido | Extrato sem CNPJ ou com DV inválido | Documento aparece no inbox | Bloco de cadastro **não** aparece; segue o fluxo atual (vincular a existente ou rejeitar) |
| AT-009 | Sugestão de enquadramento indeterminada | Extrato sem linha de fator r | Formulário abre | `sujeita_fator_r` sem valor pré-marcado; "Confirmar" desabilitado até o analista escolher |
| AT-010 | PA em intervalo inválido | Texto com `Periodo de Apuracao: 01/08/2026 a 30/09/2026` | Parse | `pa = null` (intervalo atravessa meses) |
| AT-011 | Trace | Qualquer chamada bem-sucedida do endpoint | Consulta ao trace local e ao Langfuse | Mesmo `trace_id`; `gatilho=cadastro_pelo_extrato`; spans `tool`, `decide`, `render`; `record_decision` com `document_id`, `company_id`, `movimento`, `competencia` |
| AT-012 | Upload mostra o bloco | Upload de CNPJ desconhecido | Resultado do upload renderiza | Bloco "Esse CNPJ não está na sua carteira" com o botão "Cadastrar e vincular" e o disclaimer do PGDAS-D |
| AT-013 | Regressão do parser | 10 fixtures sintéticas atuais | `pytest apps/api/tests/parsing` | Campos e faixas de confiança iguais aos de hoje; só `parser_version` muda |
| AT-014 | Nota ouro | Documento vinculado pelo cadastro | Avaliação ouro roda | Campos de identificação (`nome_empresarial`, sugestão) não geram `gold_<campo>` nem entram em `gold_acerto` |

---

## Requisitos funcionais

| ID | Requisito | Camada |
|---|---|---|
| RF-01 | Extrair `nome_empresarial` dos rótulos "Nome empresarial" (com e sem acento, `:` opcional) | `parsing/` |
| RF-02 | Extrair o PA também no formato `Período de Apuração: DD/MM/AAAA a DD/MM/AAAA`, aceitando só quando início e fim caem no mesmo mês/ano | `parsing/` |
| RF-03 | Sugerir `sujeita_fator_r`: `true` quando o fator r foi lido como número; `false` quando o extrato diz explicitamente "não se aplica"; `null` nos demais casos | `parsing/` |
| RF-04 | `nome_empresarial` e a sugestão **não entram** na confiança nem na nota ouro (mesmo tratamento do `anexo`, que já tem peso 0) | `parsing/`, `agents/` |
| RF-05 | `PARSER_VERSION` sobe (mudança de regra de extração) | `parsing/` |
| RF-06 | `DocumentoOut` devolve um bloco de sugestão de cadastro **somente** quando `status=needs_review`, `motivo=cnpj_nao_encontrado` e CNPJ lido com DV válido | `api/` |
| RF-07 | `POST /inbox/{document_id}/cadastrar-empresa`, corpo = `CompanyIn`, cria a empresa e vincula o documento **na mesma transação**; resposta com documento e empresa | `api/`, `agents/`, `repositories/` |
| RF-08 | Guardas: CNPJ do corpo = CNPJ lido (senão 422); documento em `needs_review` ou `parsed` (senão 409); CNPJ já existente no escritório → 409 com `company_id`; documento de outro escritório → 404 | `api/`, `agents/` |
| RF-09 | A criação do movimento segue `_aplicar_vinculo` sem alteração: só receita, só na competência do PA, só se PA e RPA existirem, nunca sobrescreve | `agents/` |
| RF-10 | Tudo dentro de `tracer.run(agente="parser_pgdas", gatilho="cadastro_pelo_extrato")` com `record_decision` | `agents/`, `tracing/` |
| RF-11 | UI: bloco de cadastro no resultado do upload e no detalhe do documento, com o formulário de empresa pré-preenchido, CNPJ só leitura, estados de carregando/erro/409 e disclaimer | `apps/web` |
| RF-12 | Fixtures: os 4 PDFs de `pdf/com_cnpj/` viram fixtures com `expected.json` (`"sintetica": true`, pois a identificação é fictícia) | `fixtures/pgdas/` |
| RF-13 | Tipos do front regenerados a partir do OpenAPI (`make api-types`) | `apps/web` |

---

## Out of Scope

- Cadastro automático, sem confirmação humana (preserva a §3.9).
- Consulta de CNPJ em API pública — Receita, BrasilAPI ou similar (proibido pela §5.3).
- Casamento por raiz de CNPJ, tratamento de matriz/filial e aviso de "mesma raiz".
- CNPJ editável no formulário de cadastro pelo extrato.
- Leitura de **RBT12, FS12 e DAS** do layout declaratório — fica para a T-504.
- Importar os 12 meses de "Receitas Brutas Anteriores" do extrato (mudaria a §3.8).
- Estado "empresa em rascunho/incompleta" e qualquer migração de banco.
- Cadastro em lote e OCR de PDF escaneado (Fase 2).
- Preenchimento de pacote comercial e honorário a partir do extrato.

---

## Constraints

| Tipo | Restrição | Impacto |
|---|---|---|
| Domínio | CLAUDE.md §3.2 — parse determinístico, sem LLM | Nome e PA saem por regex; o LLM não participa |
| Domínio | §3.8 — extrato cria só a receita do PA, nunca folha, nunca sobrescreve | `_aplicar_vinculo` é reaproveitado sem mudança |
| Domínio | §3.9 — CNPJ não encontrado → `needs_review`, sem escrita automática | Toda escrita nasce de um POST explícito do analista |
| Domínio | §3.10 — sem trace não há decisão | Endpoint novo dentro de `tracer.run` + `record_decision` |
| Domínio | §3.13 — `firm_id` no repositório e RLS | Endpoint entra no teste de isolamento por rota do OpenAPI |
| Domínio | §3.16 — nota ouro ignora `origem=pgdas` | Campos de identificação ficam fora da nota ouro |
| Dados | §5.3 — CNPJ e dados do cliente não saem para serviço não previsto | Sem enriquecimento externo; nome só do próprio extrato |
| Técnico | Sem migração | Usa `companies` (com `UNIQUE (firm_id, cnpj)`) e `pgdas_documents.campos_json` |
| Técnico | `mypy --strict`, `Decimal`, camadas da Plano §3.1 | Regra de negócio fora de `api/` e do React |
| Processo | Feature fora de `docs/tasks.md` | Exige tarefas novas e entrada no Registro de decisões antes do build (CLAUDE.md §9) |

---

## Technical Context

| Aspecto | Valor | Notas |
|---|---|---|
| **Local de implantação** | `apps/api/src/fator_r/{parsing,agents,api,repositories}`, `apps/api/fixtures/pgdas/`, `apps/api/tests/{parsing,api,agents}`, `apps/web/app/(app)/inbox/`, `apps/web/e2e/` | Estrutura da Plano §3.1; nenhum diretório novo |
| **Domínios de KB** | `python`, `pydantic`, `testing` | Padrões de modelo Pydantic e pytest |
| **Impacto de IaC** | Nenhum | Sem serviço, container, variável de ambiente ou migração nova |

**Pontos de reuso já identificados:**

| O quê | Onde |
|---|---|
| Casamento por CNPJ | `repositories/companies.obter_por_cnpj` |
| Criação de empresa | `repositories/companies.criar` |
| Vínculo + receita do PA | `agents/parser_pgdas.vincular_manual` → `_aplicar_vinculo` |
| Estados válidos e erro 409 | `parser_pgdas.DocumentoEmEstadoInvalido` |
| Validação de CNPJ | `core/cnpj.normalizar_cnpj` / `cnpj_valido` |
| Schema de entrada | `api/companies.CompanyIn` |
| Resultado do upload na UI | `apps/web/app/(app)/inbox/page.tsx` (`data-testid="resultado-upload"`) |

---

## Contrato de API (rascunho para o /design)

**`DocumentoOut.sugestao_cadastro`** (novo, opcional):

| Campo | Tipo | Observação |
|---|---|---|
| `cnpj` | `string` (14 dígitos) | Sempre com DV válido |
| `cnpj_formatado` | `string` | `12.345.678/0001-95` |
| `nome_empresarial` | `string \| null` | Como lido do extrato |
| `sujeita_fator_r` | `boolean \| null` | `null` = analista precisa escolher |

**`POST /inbox/{document_id}/cadastrar-empresa`**

| Status | Quando |
|---|---|
| 201 | Empresa criada e documento vinculado; corpo `{documento, empresa}` |
| 404 | Documento inexistente ou de outro escritório |
| 409 | Documento fora de `needs_review`/`parsed`, ou CNPJ já cadastrado (corpo traz `company_id`) |
| 422 | Corpo inválido, CNPJ inválido ou diferente do lido no extrato |

---

## Assumptions

| ID | Premissa | Se estiver errada | Validada? |
|---|---|---|---|
| A-001 | O extrato real traz o rótulo "Nome empresarial" como nos exemplos | Nome vem vazio e o analista digita; o fluxo continua funcionando | [ ] depende de P-03 |
| A-002 | O PA declaratório vem como intervalo dentro de um único mês | `pa = null` → `sem_rpa`; receita lançada à mão | [x] nos 4 exemplos |
| A-003 | O primeiro CNPJ do texto é o da matriz (é o que o parser já usa) | Cadastro com CNPJ de estabelecimento; exige revisão do casamento | [x] nos 4 exemplos (matriz = estabelecimento) |
| A-004 | "Fator r = Não se aplica" é a forma estável de atividade não sujeita | Sugestão vira `null` e o analista escolhe; nada quebra | [ ] depende de P-03 |
| A-005 | Clientes novos chegam em volume baixo (unidades por mês por escritório) | Cadastro em lote volta à pauta | [ ] |
| A-006 | O limiar padrão do escritório segue 0,40 | Com limiar maior, PDFs a 0,60 deixam de vincular sozinhos após o cadastro | [x] seed atual |

---

## Clarity Score Breakdown

| Elemento | Nota | Justificativa |
|---|---|---|
| Problema | 3 | Dor, causa (`cnpj_nao_encontrado` sem saída na tela) e efeito (receita represada) medidos no código |
| Usuários | 2 | Analista bem definido; a dor do sócio é indireta e não foi quantificada |
| Objetivos | 3 | MUST/SHOULD/COULD separados e ligados a regras do contrato |
| Sucesso | 3 | Critérios numéricos (4/4, 0 regressões, ≤ 2 interações, 100% com trace) e 14 testes de aceite |
| Escopo | 3 | Nove exclusões explícitas, incluindo o limite de parser decidido nesta fase |
| **Total** | **14/15** | |

---

## Decisões desta fase (complementam o BRAINSTORM)

| # | Decisão | Motivo |
|---|---|---|
| D-01 | O parser passa a ler **só o PA** do layout declaratório; RBT12, FS12 e DAS ficam para a T-504 | Escolha do usuário: o mínimo para a receita do PA entrar sem misturar duas entregas |
| D-02 | `nome_empresarial` fica **fora** da confiança e da nota ouro | Dar peso deslocaria a confiança de todo documento e poderia inverter `linked` ↔ `needs_review` em fluxos que hoje funcionam; o `anexo` já segue esse padrão (peso 0). **Corrige o BRAINSTORM**, que previa "peso próprio" |
| D-03 | A sugestão de `sujeita_fator_r` vem da **linha do fator r**, não do anexo | "Anexo III" sozinho é ambíguo: aparece tanto em serviço sujeito (PDF 04) quanto não sujeito (PDF 03). **Corrige o BRAINSTORM**, que previa mapear pelo anexo |
| D-04 | Bloco de cadastro só com CNPJ lido e DV válido | O CNPJ é travado no formulário; sem CNPJ confiável não há o que travar |

---

## Impacto em documentos do projeto (antes do /build)

| Documento | Mudança |
|---|---|
| `docs/prd.md` | §7.6: caminho "CNPJ desconhecido → cadastrar pelo extrato"; leitura de PA em intervalo |
| `docs/tasks.md` | Tarefas novas (parser, endpoint, UI, fixtures, E2E) com Dep. nas T-50x concluídas |
| `docs/plan.md` | Registro de decisões com as 8 decisões do BRAINSTORM + D-01 a D-04 |
| `apps/api/fixtures/pgdas/README.md` | Nova seção para as fixtures do layout declaratório |

---

## Open Questions

Nenhuma bloqueante — pronto para o Design. Pendências conhecidas, sem impacto no escopo:

- A-001 e A-004 só se confirmam com extratos reais (P-03). Se falharem, o fluxo degrada para
  "analista digita", sem quebrar.

---

## Revision History

| Versão | Data | Autor | Mudanças |
|---|---|---|---|
| 1.0 | 2026-09-22 | define | Versão inicial a partir do BRAINSTORM; inclui leitura do PA (D-01) e corrige peso do nome (D-02) e origem da sugestão de enquadramento (D-03) |
| 1.1 | 2026-09-22 | ship | Entregue e arquivado. Iterações pós-build: meses anteriores do extrato (T-808), carteira rotulada (T-809), folha do PGDAS-D em célula única (T-810) |

---

## Next Step

**Pronto para:** `/workflow:design .claude/sdd/features/DEFINE_CADASTRO_EMPRESA_PELO_EXTRATO.md`
