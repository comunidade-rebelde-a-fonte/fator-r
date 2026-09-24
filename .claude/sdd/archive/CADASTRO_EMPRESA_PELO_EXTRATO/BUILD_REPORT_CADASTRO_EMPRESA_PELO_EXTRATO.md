# BUILD REPORT: Cadastro de empresa a partir do extrato PGDAS-D

## Metadata

| Atributo | Valor |
|---|---|
| **Feature** | CADASTRO_EMPRESA_PELO_EXTRATO (marco M8) |
| **Data** | 2026-09-22 |
| **DEFINE** | [DEFINE_CADASTRO_EMPRESA_PELO_EXTRATO.md](./DEFINE_CADASTRO_EMPRESA_PELO_EXTRATO.md) |
| **DESIGN** | [DESIGN_CADASTRO_EMPRESA_PELO_EXTRATO.md](./DESIGN_CADASTRO_EMPRESA_PELO_EXTRATO.md) |
| **Status** | ✅ Shipped (2026-09-22) — marco M8 fechado no `/workflow:ship` |
| **Commit** | Nenhum (CLAUDE.md §5.5: só com pedido do usuário) |

---

## Summary

Quando o CNPJ do extrato não está na carteira, o documento continua em `needs_review`, mas o
resultado do upload e o detalhe do documento passam a oferecer **Cadastrar e vincular**. O botão
abre o formulário de empresa com o CNPJ travado e o nome e o enquadramento lidos do extrato. Ao
confirmar, `POST /inbox/{id}/cadastrar-empresa` cria a empresa, vincula o documento e lança a
receita do PA numa transação só, dentro de `tracer.run(gatilho="cadastro_pelo_extrato")`. Nada é
gravado sem a confirmação do analista.

O parser (`2026.09.2`) passou a ler três coisas novas:
- o nome empresarial;
- a sugestão de `sujeita_fator_r`, tirada da linha do fator r;
- o PA no formato de intervalo.

O anexo agora é lido primeiro das linhas estruturadas. Nenhuma das 10 fixtures antigas mudou.

---

## Tarefas executadas

| Tarefa | Entrega | Verificação |
|---|---|---|
| T-801 | `Identificacao`, `_nome_empresarial`, `_sugestao_sujeita_fator_r`, `_RE_PA_INTERVALO`, `_anexo` estruturado, `PARSER_VERSION 2026.09.2` | 20 casos unitários novos; `tests/parsing` 48/48 |
| T-802 | 4 fixtures `pdf_declaratorio_*` com valor verdadeiro, `lacunas_conhecidas` e `identificacao`; `test_fixtures.py`, `parser_experiment.py`, README | 14/14 fixtures; acerto 91,1% |
| T-803 | `companies.adicionar` (sem commit), `sugestao_cadastro`, `_decidir_vinculo` (extraído de `vincular_manual`), `cadastrar_e_vincular` | testes de agente via API; `vincular_manual` sem regressão |
| T-804 | `SugestaoCadastroOut`, `DocumentoOut.sugestao_cadastro`, `CadastroPeloExtratoOut`, rota nova com `detail.codigo`; `api/companies._dados` → `dados_empresa` | `test_inbox_cadastro.py` 15/15; isolamento 22/22; `make api-types` |
| T-805 | `EmpresaForm` (valores parciais, CNPJ só leitura, Sim/Não), `CadastroPeloExtrato`, bloco no upload e no detalhe, nome lido no detalhe | `tsc`, eslint, prettier; E2E |
| T-806 | `test_cadastro_pelo_extrato_no_langfuse`; `e2e/cadastro-pelo-extrato.spec.ts` (3 cenários) | `-m langfuse` 6/6; Playwright 16/16; `e2e_langfuse` 3/3 |
| T-807 | PRD v0.3 (§7.6), Registro de decisões 2026-09-22, M8 em `tasks.md` | — |

---

## Arquivos

**Criados:**
- `apps/api/tests/api/test_inbox_cadastro.py`
- `apps/api/fixtures/pgdas/pdf_declaratorio_{fator_r_abaixo_28,comercio_sem_fator_r,servico_sem_fator_r,fator_r_acima_28}/` (`documento.pdf` + `expected.json`)
- `apps/web/components/inbox/CadastroPeloExtrato.tsx`
- `apps/web/e2e/cadastro-pelo-extrato.spec.ts`
- `apps/api/scripts/preencher_cnpj_ficticio.py` (da sessão anterior; gera `pdf/com_cnpj/`)

**Modificados:**
- api: `parsing/pgdas.py`, `agents/parser_pgdas.py`, `repositories/companies.py`, `api/inbox.py`, `api/companies.py`, `scripts/parser_experiment.py`, `fixtures/pgdas/README.md`
- testes: `tests/parsing/test_pgdas_unit.py`, `tests/parsing/test_fixtures.py`, `tests/api/test_isolation.py`, `tests/integration/test_langfuse.py`
- web: `app/(app)/inbox/page.tsx`, `app/(app)/inbox/[id]/page.tsx`, `components/empresas/EmpresaForm.tsx`, `lib/api/{inbox.ts,types.ts,openapi.json,schema.d.ts}`
- docs: `docs/prd.md`, `docs/plan.md`, `docs/tasks.md`

Sem migração. Sem dependência nova.

---

## Gates (CLAUDE.md §7), com resultado real

| Gate | Resultado |
|---|---|
| `make lint` (ruff, mypy `--strict`, eslint, prettier, `tsc`) | ✅ |
| `make test` | ✅ 313 passed (antes: 268) |
| `pytest tests/api -k isolation` | ✅ 22 passed (rota nova coberta pelo varredor OpenAPI) |
| `pytest tests/parsing` | ✅ 48 passed; 10 fixtures antigas sem mudança |
| `make parser-experiment` | ✅ dataset 14 itens, experimento `parser-2026.09.2`, acerto médio 91,1% |
| `make test-langfuse` (`-m langfuse`) | ✅ 6 passed |
| `make api-types` | ✅ regenerado |
| `make e2e` | ✅ Playwright 16/16 (13 do aceite v1 + 3 do M8) e `e2e_langfuse` 3/3 |
| Migração do zero | não se aplica (sem migração) |
| Performance da carteira | não se aplica (`/portfolio` intocado) |

---

## Aceite M8 (DEFINE AT-001 a AT-014)

| AT | Evidência |
|---|---|
| AT-001 caminho feliz | `test_cadastro_cria_empresa_vincula_e_cria_receita_do_pa`, `test_pdf_declaratorio_ponta_a_ponta` (PDF 01 → 2026-08, R$ 10.000,00), E2E cenário 1 |
| AT-002 sem regressão | `test_pdf_declaratorio_de_empresa_ja_cadastrada_vincula_sozinho` (confiança 0,70) + E2E §13.3 |
| AT-003 CNPJ cadastrado no meio do caminho | `test_cnpj_ja_cadastrado_devolve_company_id_e_permite_vincular`, `test_corrida_no_cadastro_desfaz_tudo_e_deixa_trace_de_erro`, E2E cenário 2 |
| AT-004 CNPJ divergente | `test_cnpj_divergente_e_recusado_sem_escrita` |
| AT-005 estado final | `test_documento_em_estado_final_e_recusado` |
| AT-006 isolamento | `test_documento_de_outro_escritorio_da_404` + varredor de isolamento |
| AT-007 PA não lido | `test_sem_pa_vincula_sem_criar_receita` |
| AT-008 CNPJ ausente/DV inválido | `test_sem_cnpj_valido_nao_ha_sugestao_e_cadastro_e_recusado` (2 casos) |
| AT-009 sugestão indeterminada | `EmpresaForm`: rádio sem seleção + botão desabilitado; parser devolve `None` (`test_sugestao_sujeita_fator_r`) — **sem teste de UI dedicado** |
| AT-010 PA atravessando meses | `test_pa_em_intervalo_so_dentro_do_mesmo_mes` |
| AT-011 trace | `test_trace_e_decisao_do_cadastro` (local) + `test_cadastro_pelo_extrato_no_langfuse` (Langfuse, CNPJ mascarado) + E2E cenário 1 |
| AT-012 bloco no upload | E2E cenários 1 e 3 (inclui disclaimer) |
| AT-013 regressão do parser | `tests/parsing` com as 10 fixtures antigas |
| AT-014 nota ouro | `test_trace_e_decisao_do_cadastro`: `EvalGold.campo ⊆ CAMPOS` |

Critério de "no máximo 2 interações": o E2E faz exatamente 2 cliques ("Cadastrar e vincular" →
"Confirmar cadastro e vínculo").

---

## Desvios e achados

1. **Regex do nome empresarial (corrigido durante o build).** A versão do DESIGN tinha dois
   problemas, e os testes pegaram ambos:
   - com o `:` opcional, a linha `"Nome empresarial:"` virava o nome `":"`;
   - o `.{0,199}$` recusava nomes longos em vez de cortá-los.

   Passou a capturar a linha inteira e cortar em 200 caracteres (limite de `CompanyIn.nome`).
2. **Harness de integração do Langfuse (problema anterior ao M8, não corrigido).** O SDK v4 mantém
   um recurso por `public_key` (`LangfuseResourceManager._instances`). Assim, só o primeiro cliente
   criado no processo recebe o `ExportStatus` do fixture `langfuse_real`, e a flag
   `langfuse_sync == "ok"` só pode ser conferida no primeiro teste. Confirmado: o teste existente do
   `echo` falha se rodar depois do teste do Claude. O teste novo do M8 prova o AT-011 pela API
   pública do Langfuse (mesmo `trace_id`, spans, tags e mascaramento), que é a evidência mais forte.
   **Pendente:** decidir se o harness deve ser corrigido (ex.: fixture de sessão com um único
   cliente/status).
3. **Refactor de `vincular_manual`** para `_decidir_vinculo`: mesma decisão gravada, testes
   existentes verdes.
4. **`make e2e` recriou o banco local**, como documentado. Ele foi migrado e populado pelo próprio
   alvo e ficou com os dados de teste do E2E. Depois disso, a aplicação voltou para
   `LLM_PROVIDER=anthropic` (`make up-app`) e o login foi conferido (200).

---

## Pendências

- Fechar formalmente o M8 exige confirmação do usuário (CLAUDE.md §6.2).
- AT-009 coberto só por lógica e parser, sem teste de UI dedicado para o rádio sem seleção.
- Achado 2 (harness do Langfuse) aguarda decisão.
- RBT12, FS12 e DAS do layout declaratório seguem para a T-504, declarados como `lacunas_conhecidas`.

---

## Next Step

`/workflow:ship .claude/sdd/features/DEFINE_CADASTRO_EMPRESA_PELO_EXTRATO.md` depois da confirmação
do usuário.

---

## Adendo — T-808: meses anteriores do extrato (2026-09-22)

Pedido pelo usuário depois do teste manual. Ele escolheu "receitas e folha", contra a recomendação de
importar só as receitas. A decisão altera a §3.8 do `CLAUDE.md` e a PRD §7.6, e está registrada no
Registro de decisões.

- Parser `2026.09.3`: lê as tabelas 2.2 e 2.3, o RBT12 e o "Total FS12" do layout declaratório e a
  data de abertura; confere as séries (janela do PA e soma igual ao total declarado).
- Agente: grava os 12 meses anteriores só em competências vazias. A folha vai inteira em
  `salarios`, com CPP/FGTS/pró-labore zerados e observação. Atividade sem fator r entra com folha
  zero. Série que não confere não é gravada, e o motivo vai para a decisão e para o texto.
- Web: início de atividade pré-preenchido com a data de abertura.
- Gates:
  - `make lint` ✅
  - `make test` ✅ 324
  - isolamento ✅ 22
  - `-m langfuse` ✅ 6
  - experimento `parser-2026.09.3` ✅ 96,4% (antes 91,1%)
  - `make e2e` ✅ 16/16 + 3/3
  - fumaça no ambiente rodando: PDF 01 → 13 movimentos, FS12 = 24.000, Fator R 0,20, Anexo V ✅
- Consequência aceita: empresa com meses `origem=pgdas` na janela fica com a nota ouro indisponível
  (§3.16).

---

## Adendo final — T-809, T-810 e gates de fechamento (2026-09-22)

- **T-809** Carteira: coluna "Aumento de folha por mês" com valores rotulados; `/portfolio` devolve
  `meta_operacional` por linha; espaçamento entre colunas.
- **T-810** Grade mensal: linhas `origem=pgdas` mostram "Folha declarada no PGDAS-D" numa célula só,
  com "Detalhar folha"; cabeçalhos espaçados. Só tela.

| Gate de fechamento | Resultado |
|---|---|
| `make lint` | ✅ |
| `make test` | ✅ 324 passed |
| `make test-perf` | ✅ |
| isolamento | ✅ 22 passed |
| `make e2e` (após T-809/T-810) | ✅ Playwright 16/16 + `e2e_langfuse` 3/3 |

O E2E recria o banco local. Os dados de teste do usuário (4 empresas, 6 extratos, 54 movimentos,
6 arquivos) foram salvos com `pg_dump` + `tar` antes e restaurados depois, e conferidos.
