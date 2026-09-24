# BRAINSTORM: Cadastro de empresa a partir do extrato PGDAS-D

> Exploração para alinhar intenção e abordagem antes de capturar requisitos (Fase 0)

## Metadata

| Atributo | Valor |
|---|---|
| **Feature** | CADASTRO_EMPRESA_PELO_EXTRATO |
| **Data** | 2026-09-22 |
| **Autor** | brainstorm (sessão com o usuário) |
| **Status** | ✅ Shipped (2026-09-22) |
| **Idioma** | pt-BR (domínio em português, conforme CLAUDE.md §10.1) |

---

## Ideia inicial

**Pedido do usuário:** "quando subir o pgdas verificar se a empresa já tem cadastro, se tiver coloca
na empresa de destino e se não tiver cadastra a empresa..."

**Contexto levantado no código:**

- `POST /inbox/pgdas` (`apps/api/src/fator_r/api/inbox.py`) recebe o arquivo e chama
  `parser_pgdas.receber_documento`.
- O agente (`apps/api/src/fator_r/agents/parser_pgdas.py`) já faz o "se tiver, coloca na empresa":
  span `tool` busca `companies.obter_por_cnpj(session, firm_id, cnpj)`; span `decide` vincula quando
  a empresa existe e a confiança ≥ limiar do escritório, e `_aplicar_vinculo` cria **só a receita do
  PA** (`origem=pgdas`), nunca folha, nunca sobrescrevendo movimento existente.
- Quando o CNPJ não está na carteira: `status=needs_review`, `motivo=cnpj_nao_encontrado`, **sem
  escrita** (regra §3.9 do CLAUDE.md). O analista precisa sair do inbox, cadastrar a empresa em
  Empresas e voltar para usar `POST /inbox/{id}/link`.
- Já existe `parser_pgdas.vincular_manual` (gatilho `vinculo_manual`, com trace e
  `record_decision`), reaproveitável pelo fluxo novo.
- O parser (`apps/api/src/fator_r/parsing/pgdas.py`, `PARSER_VERSION=2026.09.1`) extrai
  `cnpj, pa, rbt12, rpa, fs12, fator_r, das, anexo`. **Não extrai nome empresarial.**
- `CompanyIn` (`api/companies.py`) exige `nome` e `sujeita_fator_r`; o resto é opcional.

**Conclusão do levantamento:** metade do pedido já está implementada. A lacuna é só o caminho
"CNPJ desconhecido → cadastrar empresa" sem sair da tela.

**Contexto técnico para o /define:**

| Aspecto | Observação | Implicação |
|---|---|---|
| Onde o código vive | `apps/api/src/fator_r/{api,agents,parsing,repositories}` + `apps/web/app/(app)/inbox` | Camadas já definidas na Plano §3.1 |
| Regras aplicáveis | CLAUDE.md §3.8 (extrato só cria receita do PA), §3.9 (needs_review sem escrita), §3.10 (sem trace não há decisão), §3.13 (firm_id + RLS) | Guardas obrigatórias no `decide` e no repositório |
| Banco | Usa `companies` e `pgdas_documents` como estão | **Sem migração** |
| Observabilidade | `tracing/` já padroniza spans `plan\|parse\|tool\|decide\|render` | Gatilho novo `cadastro_pelo_extrato` |

---

## Perguntas de descoberta

| # | Pergunta | Resposta | Impacto |
|---|---|---|---|
| 1 | Cadastro automático, com 1 clique ou híbrido por confiança? | **1 clique com confirmação** | A escrita continua sendo decisão humana; a §3.9 do contrato fica intacta e não precisa de mudança na PRD |
| 2 | O que vem pré-preenchido no formulário? | **CNPJ + nome + enquadramento** | O parser passa a ler nome empresarial e a sugerir `sujeita_fator_r` pelo anexo; mexe em `parsing/` |
| 3 | Como decidir que "já tem cadastro"? | **CNPJ exato (14 dígitos)** | Mantém o casamento atual; matriz e filial continuam sendo empresas distintas |
| 4 | Que amostras ancoram a leitura? | **Os 4 PDFs de `pdf/com_cnpj/`** | Fixtures novas com nome empresarial real de layout; não depende de extrato de cliente |

---

## Inventário de amostras

| Tipo | Local | Qtd | Notas |
|---|---|---|---|
| Arquivos de entrada | `pdf/com_cnpj/` | 4 | PDF com camada de texto, CNPJ fictício com DV válido, gerados por `apps/api/scripts/preencher_cnpj_ficticio.py` |
| Cenários cobertos | idem | 4 | Fator r < 28% (Anexo V), Fator r > 28% (Anexo III), comércio Anexo I, serviço Anexo III sem fator r |
| Verdade de referência | `pdf/com_cnpj/indice.md` | 4 | CNPJ, nome empresarial e enquadramento esperados por arquivo |
| Código de referência | `apps/api/fixtures/pgdas/*/expected.json` | 10 | Formato de fixture já usado pelos testes de `parsing/` |
| Amostra não utilizável | `pdf/declaracao_anonimizada.pdf` | 1 | Só imagem, sem camada de texto (OCR é Fase 2) |

**Como as amostras serão usadas:**

- Viram fixtures `real_layout_<n>/` (ou `pdf_layout_declaratorio/`) com `expected.json`.
- Ancoram as regex novas de nome empresarial e as existentes de PA/RBT12/FS12, que **hoje falham
  nesse layout** (medido: CNPJ e RPA saem certos, PA/RBT12/FS12/DAS não são encontrados; confiança
  0,35–0,45).
- Servem de massa para o teste E2E do fluxo de cadastro.

---

## Abordagens exploradas

### Abordagem A: Cadastro em 1 clique a partir do `needs_review` ⭐ Escolhida

**Descrição:** o documento continua caindo em `needs_review` com `cnpj_nao_encontrado`, mas a UI
(card do inbox **e** resultado do upload) oferece "Cadastrar e vincular" com um formulário
pré-preenchido pelo que o parser leu. Confirmar dispara um endpoint que cria a empresa e vincula o
documento na mesma transação.

**Prós:**
- Não altera nenhuma regra do contrato: a escrita continua sendo decisão humana (§3.9).
- Reaproveita `vincular_manual`, que já grava trace e decisão.
- Sem migração de banco.
- O analista resolve tudo numa tela só — que é a dor original.

**Contras:**
- Ainda exige um clique por documento (não serve para lote grande).
- Depende de o parser ler o nome empresarial para o pré-preenchimento valer a pena.

**Por que foi escolhida:** entrega o ganho real (fim do vai-e-volta entre telas) sem tocar em regra
de domínio nem em esquema de banco.

---

### Abordagem B: Cadastro automático sem confirmação

**Descrição:** com CNPJ válido e confiança ≥ limiar, o sistema cria a empresa sozinho e já vincula.

**Prós:**
- Melhor caso para carga inicial de muitos extratos.
- Zero interação por documento.

**Contras:**
- Contraria a §3.9 do CLAUDE.md ("CNPJ não encontrado → needs_review, sem escrita automática");
  exigiria decisão registrada e atualização da PRD.
- Cadastra empresa com nome e enquadramento saídos do parser sem ninguém conferir — e
  `sujeita_fator_r` errado muda anexo, alíquota e economia estimada.
- Limpar cadastro duplicado/errado depois é pior do que confirmar antes (§5.4: desativação é lógica,
  não se apaga).

---

### Abordagem C: Híbrido por confiança

**Descrição:** automático acima de um limiar alto (ex.: 0,90 com CNPJ válido e nome lido), com
confirmação no resto.

**Prós:**
- Reduz cliques nos casos fáceis.

**Contras:**
- Mais um limiar por escritório para configurar, explicar e testar.
- Herda o conflito com a §3.9 no ramo automático.
- Só faz sentido depois de o parser estar medido contra extratos reais (P-03 em aberto).

---

## Abordagem selecionada

| Atributo | Valor |
|---|---|
| **Escolhida** | Abordagem A |
| **Confirmação do usuário** | 2026-09-22, nesta sessão |
| **Ajuste pedido na validação** | O botão de cadastrar aparece **também na tela de upload**, não só no card do inbox |
| **Motivo** | Resolve a dor sem mexer em regra de domínio nem em banco |

---

## Decisões tomadas

| # | Decisão | Justificativa | Alternativa rejeitada |
|---|---|---|---|
| 1 | Cadastro sempre com confirmação humana | Preserva §3.9 e evita cadastro errado difícil de desfazer | Criação automática |
| 2 | Parser passa a ler nome empresarial e a sugerir `sujeita_fator_r` pelo anexo | Sem isso o "1 clique" vira "digitar tudo de novo" | Formulário só com CNPJ |
| 3 | Casamento por CNPJ exato de 14 dígitos | Sem ambiguidade entre matriz e filial; mantém o comportamento atual | Casar por raiz (8 dígitos) |
| 4 | Nenhuma consulta a API externa de CNPJ | §5.3: CNPJ de cliente não vai para serviço externo não previsto | Receita/BrasilAPI para nome e CNAE |
| 5 | CNPJ travado no formulário | É a chave do casamento; CNPJ errado se resolve rejeitando o documento | CNPJ editável |
| 6 | Sem migração de banco | `companies` e `pgdas_documents` bastam; o nome lido vive no `campos_json` | Novo estado "empresa rascunho" |
| 7 | Um único endpoint cria + vincula | Evita estado intermediário (empresa criada e documento solto) se o segundo passo falhar | Duas chamadas do front |
| 8 | Fixtures a partir de `pdf/com_cnpj/` | Ancoram o parser num layout diferente do sintético, sem dado de cliente | Esperar P-03 |

---

## Features removidas (YAGNI)

| Sugestão | Motivo da remoção | Dá para voltar depois? |
|---|---|---|
| Cadastro automático sem confirmação | Conflita com §3.9 e com a escolha do usuário | Sim, com decisão registrada |
| Consulta a API pública de CNPJ (nome, CNAE, endereço) | Proibido pela §5.3 | Não, sem mudar a política de dados |
| Casar matriz e filial pela raiz do CNPJ | Misturaria receita de estabelecimentos no mesmo RBT12 | Sim |
| Aviso "existe empresa com a mesma raiz" | Mais uma tela de decisão para um caso ainda não observado | Sim |
| Estado "empresa em rascunho / incompleta" | Exigiria migração e ciclo de vida novo | Sim |
| Cadastro em lote (vários extratos de uma vez) | Não é o gargalo; depende do fluxo de um funcionar | Sim |
| **Importar os 12 meses da seção "Receitas Brutas Anteriores" do extrato** | A §3.8 permite só a receita do PA; mudaria regra de domínio | Sim, com decisão registrada e PRD atualizada |
| Preencher pacote comercial e honorário automaticamente | Não há de onde inferir; é dado comercial do escritório | Sim |

---

## Validações incrementais

| Seção | Apresentada | Retorno do usuário | Ajustado? |
|---|---|---|---|
| Fluxo ponta a ponta (upload → casamento → cadastro → vínculo → receita do PA) | ✅ | "Quero o botão também no upload" | Sim — o resultado do upload passa a oferecer o cadastro |
| Escopo, cortes YAGNI e requisitos | ✅ | Aguardando confirmação explícita (falha na ferramenta de pergunta) | — |

---

## Requisitos sugeridos para o /define

### Problema (rascunho)

Quando o extrato PGDAS-D é de uma empresa que ainda não está na carteira, o analista precisa
abandonar o inbox, cadastrar a empresa em outra tela e voltar para vincular o documento na mão.

### Usuários-alvo (rascunho)

| Usuário | Dor |
|---|---|
| Analista do escritório | Troca de tela e redigitação de CNPJ e nome a cada empresa nova |
| Sócio/responsável | Documentos parados em `needs_review` por atrito operacional, não por dúvida real |

### Requisitos

1. **Parser:** extrair `nome_empresarial` e mapear o anexo lido para sugestão de `sujeita_fator_r`
   (III ou V sujeitos ao fator r → `true`; I, II ou III sem fator r → `false`). Campo novo entra em
   `CAMPOS`/`PESOS` com peso próprio e reflete na confiança.
2. **API (leitura):** `DocumentoOut` passa a devolver, quando `status=needs_review` e
   `motivo=cnpj_nao_encontrado`, um bloco de sugestão com CNPJ formatado, nome lido e enquadramento
   sugerido.
3. **API (escrita):** `POST /inbox/{document_id}/cadastrar-empresa`, corpo `CompanyIn`, resposta com
   documento e empresa. Cria a empresa e chama `vincular_manual` na mesma transação.
4. **Guardas:** CNPJ do corpo tem de ser igual ao lido pelo parser (senão 422); CNPJ válido;
   documento em `needs_review` ou `parsed` (senão 409); CNPJ já cadastrado no escritório → 409 com
   o `company_id` existente, para o front oferecer vincular; toda consulta com `firm_id` + RLS.
5. **Trace:** o fluxo roda dentro de `tracer.run` com gatilho `cadastro_pelo_extrato`,
   `record_decision` com `{document_id, company_id, cnpj, origem_do_nome, movimento}`.
6. **Movimento:** inalterado — só a receita do PA, só se `pa` e `rpa` foram lidos, sem sobrescrever
   (§3.8). Sem PA lido, o documento fica `linked` com `movimento=sem_rpa`.
7. **UI:** bloco "Esse CNPJ não está na sua carteira" com o formulário pré-preenchido, no card do
   inbox **e** no resultado do upload; estados de carregando, erro e conflito (409); disclaimer do
   PGDAS-D visível.
8. **Testes:** `parsing/` com os 4 PDFs de `pdf/com_cnpj/` como fixtures; API com caminho feliz,
   409 duplicado, 409 estado inválido, 422 CNPJ divergente e isolamento entre escritórios; E2E do
   fluxo upload → cadastrar → documento `linked` com receita criada.

### Critérios de sucesso (rascunho)

- [ ] Subir um extrato de empresa não cadastrada e chegar em empresa criada + documento `linked` +
      receita do PA, sem sair da tela.
- [ ] Subir um extrato de empresa já cadastrada continua vinculando sozinho, como hoje (sem
      regressão).
- [ ] Nome empresarial lido corretamente nos 4 PDFs de `pdf/com_cnpj/`.
- [ ] Nenhuma escrita acontece sem confirmação humana quando o CNPJ é desconhecido.
- [ ] Trace no Langfuse com gatilho `cadastro_pelo_extrato` e os spans esperados.
- [ ] `make lint`, `make test`, `pytest -k isolation` e `make e2e` verdes.

### Restrições identificadas

- CLAUDE.md §3.8, §3.9, §3.10, §3.13; §5.3 (dados para fora); §10.1 (Decimal, camadas).
- Sem migração de banco.
- Cálculo permanece em `domain/`; o LLM não participa deste fluxo.
- Extratos reais só entram como fixture depois de anonimizados e revisados (P-03 segue aberto).

### Fora de escopo (confirmado)

- Cadastro automático sem confirmação.
- Consulta a API externa de CNPJ.
- Casamento por raiz de CNPJ e tratamento de filiais.
- Importação dos 12 meses de receita do extrato.
- Cadastro em lote e OCR de PDF escaneado (Fase 2).

---

## Impacto em documentos do projeto

| Documento | Mudança prevista |
|---|---|
| `docs/prd.md` | §7.6 ganha o fluxo "CNPJ desconhecido → cadastrar pelo extrato" |
| `docs/tasks.md` | Tarefas novas (parser, endpoint, UI, testes, E2E) com dependências |
| `docs/plan.md` | Entrada no **Registro de decisões** com as 8 decisões acima |
| `apps/api/fixtures/pgdas/README.md` | Menção às fixtures vindas de `pdf/com_cnpj/` |

---

**Próximo passo:** `/workflow:define .claude/sdd/features/BRAINSTORM_CADASTRO_EMPRESA_PELO_EXTRATO.md`
