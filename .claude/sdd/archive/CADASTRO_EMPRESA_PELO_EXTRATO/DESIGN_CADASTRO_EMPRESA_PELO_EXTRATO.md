# DESIGN: Cadastro de empresa a partir do extrato PGDAS-D

> Desenho técnico para cadastrar e vincular, em um clique e com confirmação humana, a empresa de um
> extrato cujo CNPJ ainda não está na carteira.

## Metadata

| Atributo | Valor |
|---|---|
| **Feature** | CADASTRO_EMPRESA_PELO_EXTRATO |
| **Data** | 2026-09-22 |
| **Autor** | design |
| **DEFINE** | [DEFINE_CADASTRO_EMPRESA_PELO_EXTRATO.md](./DEFINE_CADASTRO_EMPRESA_PELO_EXTRATO.md) |
| **Status** | ✅ Shipped (2026-09-22) |

---

## Architecture Overview

```text
┌──────────────────────────────── apps/web ────────────────────────────────┐
│ inbox/page.tsx (upload)          inbox/[id]/page.tsx (detalhe)            │
│        │ DocumentoOut.sugestao_cadastro != null                           │
│        └──────────────┬───────────────────────┘                          │
│             <CadastroPeloExtrato>  ──reusa──▶  <EmpresaForm>             │
│                       │  (CNPJ só leitura; nome e sujeita pré-preenchidos)│
│                       │ POST /inbox/{id}/cadastrar-empresa  (CompanyIn)   │
│                       │ 409 cnpj_ja_cadastrado ─▶ POST /inbox/{id}/link   │
└───────────────────────┼──────────────────────────────────────────────────┘
                        ▼
┌──────────────────────────────── apps/api ────────────────────────────────┐
│ api/inbox.py  ── valida I/O, mapeia exceções → 404/409/422               │
│        │                                                                  │
│        ▼                                                                  │
│ agents/parser_pgdas.py                                                    │
│   cadastrar_e_vincular()                                                  │
│     pré-checagens (sem trace, sem escrita):                               │
│       estado ∈ {needs_review, parsed} · CNPJ lido válido ·                │
│       CNPJ do corpo = CNPJ lido · CNPJ não existe no escritório           │
│     tracer.run(gatilho="cadastro_pelo_extrato")  ── uma transação ──┐     │
│       span tool   : resultado da busca por CNPJ                     │     │
│       span decide : companies.adicionar (flush)                     │     │
│                     _decidir_vinculo → _aplicar_vinculo (§3.8)      │     │
│                     record_decision                                 │     │
│       span render : texto com disclaimer                            │     │
│       finish → COMMIT  (exceção → ROLLBACK + trace de erro)  ◀──────┘     │
│        │                                                                  │
│ parsing/pgdas.py  (upload, antes de tudo isso)                            │
│   campos fiscais (CAMPOS, pesos inalterados)                              │
│   + PA em intervalo  + anexo de linha estruturada                         │
│   + Identificacao{nome_empresarial, sujeita_fator_r} (fora da confiança)  │
└──────────────┬─────────────────────────────────────┬─────────────────────┘
               ▼                                     ▼
     Postgres (RLS por firm_id)            Langfuse self-hosted
     companies · pgdas_documents ·         mesmo trace_id, spans
     monthly_movements · agent_traces ·    tool|decide|render,
     agent_decisions                       CNPJ mascarado
```

---

## Components

| Componente | Papel | Tecnologia |
|---|---|---|
| `parsing/pgdas.py` | Lê nome empresarial, PA em intervalo, anexo de linha estruturada e a sugestão de `sujeita_fator_r` | Python 3.12, `re`, `Decimal` |
| `agents/parser_pgdas.py` | `sugestao_cadastro()` (regra de quando oferecer) e `cadastrar_e_vincular()` (orquestração com trace) | Python, SQLAlchemy async, `tracing.tracer` |
| `repositories/companies.py` | `adicionar()`: insere a empresa **sem commit**, dentro da transação do run | SQLAlchemy async |
| `api/inbox.py` | `DocumentoOut.sugestao_cadastro` e `POST /inbox/{id}/cadastrar-empresa` | FastAPI, Pydantic v2 |
| `components/inbox/CadastroPeloExtrato.tsx` | Bloco "Esse CNPJ não está na sua carteira" + formulário + tratamento de 409 | Next.js 16, React 19, TanStack Query |
| `components/empresas/EmpresaForm.tsx` | Aceita valores iniciais parciais, CNPJ só leitura e `sujeita_fator_r` indefinido | React |
| Fixtures `pdf_declaratorio_*` | Os 4 PDFs de `pdf/com_cnpj/` com `expected.json` | pytest |

---

## Key Decisions

### Decision 1: Empresa e vínculo na mesma transação do `tracer.run`

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** `companies.criar` faz `commit` sozinho; o `tracer.run` também comita, no `finish`. Usar `criar` deixaria a empresa gravada mesmo se o vínculo falhasse — o estado intermediário que o DEFINE proíbe (RF-07).

**Escolha:** nova função `companies.adicionar(session, firm_id, dados)`, que faz `session.add` + `flush` e traduz a violação de `uq_companies_firm_cnpj` em `CnpjDuplicado`. O commit fica a cargo do `run.finish()`. `criar` não muda.

**Justificativa:** o `tracer.run` já garante "exceção → rollback de tudo + trace de erro preservado"; basta não comitar antes dele.

**Alternativas rejeitadas:**
1. Parâmetro `commit: bool` em `criar` — muda a assinatura usada por `POST /companies` e mistura dois contratos numa função.
2. `begin_nested()` (savepoint) — resolve o duplicado, mas não o problema real, que é o commit antecipado.

**Consequências:**
- Qualquer erro depois do `flush` (vínculo, `record_decision`) desfaz também a empresa.
- `adicionar` só pode ser chamada dentro de um fluxo que comita depois; isso fica na docstring.

---

### Decision 2: Pré-checagens fora do trace; corrida vira trace de erro

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** 409 e 422 previsíveis (estado inválido, CNPJ divergente, CNPJ já cadastrado) não são decisões de agente. Se acontecerem dentro do `tracer.run`, cada um vira trace `status=error` e polui a taxa de erro do painel de observabilidade.

**Escolha:** `cadastrar_e_vincular` valida estado, CNPJ lido, CNPJ do corpo e existência na carteira **antes** de abrir o run, do mesmo jeito que `vincular_manual` já faz com o estado. Só a corrida real (outro analista grava o mesmo CNPJ entre a checagem e o `flush`) acontece dentro do run: `IntegrityError` → rollback + trace de erro → a API responde 409 com o `company_id` que ganhou a corrida.

**Justificativa:** §3.10 exige trace para **decisão**; uma rejeição de entrada não decide nada. A corrida, por outro lado, deixa registro de verdade.

**Alternativas rejeitadas:**
1. Tudo dentro do run — trace de erro para cada 409 comum.
2. Lock de linha/tabela — desproporcional para um caso raro, que o `UNIQUE (firm_id, cnpj)` já resolve.

**Consequências:**
- Um SELECT por CNPJ a mais por chamada (desprezível).
- A corrida gera um trace `error` com `saida_json.erro = "CnpjDuplicado"` — esperado e explicável.

---

### Decision 3: Identificação separada dos campos fiscais

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** `CAMPOS` alimenta a confiança (`PESOS`), a nota ouro (`ouro_pgdas`), o experimento no Langfuse (`parser_experiment.py`) e a comparação campo a campo de `test_fixtures.py`. O DEFINE (D-02) exige que o nome fique fora da confiança e da nota ouro.

**Escolha:** `ResultadoParse` ganha `identificacao: Identificacao`, um dataclass com `nome_empresarial: str | None` e `sujeita_fator_r: bool | None`. O agente grava isso em `campos_json["_identificacao"]`, no mesmo padrão de `_confianca_campos` e `_motivos`. `Campo`, `CAMPOS` e `PESOS` **não mudam**.

**Justificativa:** nenhum consumidor atual de `CAMPOS` precisa saber da mudança, o que dá regressão zero por construção.

**Alternativas rejeitadas:**
1. `nome_empresarial` em `CAMPOS` com peso 0 — entraria na nota ouro (`gold_nome_empresarial`) e no experimento, e exigiria `expected` de nome nas 10 fixtures antigas.
2. Um segundo parser só de identificação — duplicaria `normalizar` e a leitura do texto.

**Consequências:**
- Documentos antigos não têm `_identificacao`; a sugestão sai com `nome_empresarial = null` e `sujeita_fator_r = null` — compatível, só sem pré-preenchimento.
- O detalhe do documento na web passa a mostrar o nome lido.

---

### Decision 4: PA em intervalo como regra adicional, aceita só dentro do mesmo mês

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** o layout declaratório traz `Periodo de Apuracao: 01/08/2026 a 31/08/2026`; as regex atuais esperam `MM/AAAA` (D-01).

**Escolha:** `_RE_PA_INTERVALO` é tentada **depois** das regex atuais. Aceita só quando mês e ano do início e do fim são iguais e o mês está entre 1 e 12. Senão, `pa = None`.

**Justificativa:** se as regex atuais casam primeiro, nenhuma fixture existente muda de resultado. O PA é a competência onde a receita será gravada (§3.4, §3.8), então um intervalo que atravessa meses é ambíguo e não deve virar competência.

**Alternativas rejeitadas:**
1. Usar sempre o mês do início — gravaria receita na competência errada num extrato atípico.
2. Tornar o formato de data opcional na regex atual — mexe numa regra que já funciona.

**Consequências:** a confiança dos 4 PDFs sobe 0,25 (peso do PA): 0,45 → 0,70 e 0,35 → 0,60.

---

### Decision 5: Sugestão de `sujeita_fator_r` pela linha do fator r

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** D-03 do DEFINE — "Anexo III" sozinho não diz se a atividade é sujeita ao fator r.

**Escolha:**

| Situação no extrato | Sugestão |
|---|---|
| `fator_r` lido como número | `true` |
| Linha `Fator r ... Não se aplica` (com ou sem acento) | `false` |
| Nenhum dos dois | `null` (o analista escolhe) |

**Justificativa:** usa só o que o próprio documento afirma, e a leitura numérica do fator r já existe e é testada.

**Alternativas rejeitadas:** mapear pelo anexo, ambíguo pelo motivo acima.

**Consequências:** na dúvida, a sugestão fica nula e o formulário não deixa confirmar sem escolha (AT-009).

---

### Decision 6: Anexo lido primeiro das linhas estruturadas ⚠ acréscimo de escopo pequeno

| Atributo | Valor |
|---|---|
| **Status** | Accepted — **sinalizado ao usuário** |
| **Data** | 2026-09-22 |

**Contexto:** medido no PDF 02 (comércio, Anexo I): `_anexo` devolve `III`, porque o primeiro "Anexo III" do texto está no parágrafo explicativo ("…direciona as atividades sujeitas ao fator r para o Anexo III"). Isso tem três efeitos:
- o bloco de cadastro mostraria "Anexo III" para um comércio;
- a fixture teria de registrar um valor errado como esperado;
- a nota ouro compara `anexo`.

**Escolha:** `_anexo` procura primeiro em linhas estruturadas — as que começam com `Fator r`, `Enquadramento` ou `Atividade`:
- se alguma dessas linhas cita um anexo, esse é o resultado: `III`/`V`, ou `None` quando for I, II ou IV;
- só sem linha estruturada é que vale a primeira menção no texto livre, como hoje.

**Justificativa:** nas 10 fixtures atuais o anexo já vem de linha estruturada (`Atividade: … Anexo III`, `Enquadramento: Anexo III`), então não há regressão. No layout declaratório, isso corrige o PDF 02 e mantém os PDFs 01, 03 e 04.

**Alternativas rejeitadas:**
1. Registrar `III` como esperado no PDF 02 — seria gravar um bug dentro da fixture.
2. Ampliar `anexo` para I–V — muda o domínio de um campo que a nota ouro e o consultor já usam.

**Consequências:** mais um ponto coberto por teste unitário. Se o usuário vetar, sai do build e o PDF 02 fica com `anexo` em `lacunas_conhecidas` (Decision 7).

---

### Decision 7: Fixtures do layout declaratório com lacunas conhecidas declaradas

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** `test_fixture` compara todos os `CAMPOS` com `expected.json`. Nos 4 PDFs, RBT12, FS12 e DAS estão no documento, mas ficaram para a T-504 (D-01). Registrar `null` como verdade mentiria sobre o documento; registrar o valor real faria o teste falhar.

**Escolha:** `expected.json` ganha, só nas fixtures novas, a chave opcional `"lacunas_conhecidas": {"rbt12": "T-504", "fs12": "T-504", "das": "T-504"}`. O `campos` guarda o **valor verdadeiro** do documento. Para campo em lacuna, `test_fixture` exige que o parser devolva `None` — nunca um valor errado. A métrica de acerto continua contando a lacuna como erro.

**Justificativa:**
- não pula teste nem campo (CLAUDE.md §5.2): a asserção é mais estrita — "não invente";
- a fixture continua dizendo a verdade sobre o documento;
- quando a T-504 passar a ler o campo, o teste quebra e obriga a retirar a lacuna.

**Alternativas rejeitadas:**
1. `campos` com `null` — esconde o que falta.
2. `xfail` — proibido pelo contrato.

**Consequências:**
- `test_fixtures.py` e `scripts/parser_experiment.py` passam a ler a chave nova.
- O experimento no Langfuse mostra essas lacunas como erro, o que é honesto.

---

### Decision 8: Regra de oferta da sugestão no agente, não na API

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** "oferecer cadastro só com `needs_review` + `cnpj_nao_encontrado` + CNPJ válido" é regra de negócio; pela Plano §3.1, `api/` só valida entrada e saída.

**Escolha:** `parser_pgdas.sugestao_cadastro(documento) -> SugestaoCadastro | None`. `DocumentoOut.de()` só serializa o resultado.

**Consequências:** a regra é testável sem HTTP. A listagem (`GET /inbox`) também devolve a sugestão, sem consulta extra ao banco.

---

### Decision 9: Erros com `detail` estruturado

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** o endpoint tem dois 409 de natureza diferente, e o front precisa do `company_id` num deles.

**Escolha:** `detail = {"codigo": ..., "mensagem": ..., "company_id"?: ...}` com os códigos `documento_em_estado_invalido`, `cnpj_ja_cadastrado`, `extrato_sem_cnpj_valido` e `cnpj_divergente`. O 404 continua com o texto usado hoje.

**Alternativas rejeitadas:** distinguir pelo texto da mensagem — frágil e sem tipo.

**Consequências:** o front lê `detail.codigo`. As rotas antigas continuam devolvendo string (sem mudança).

---

### Decision 10: UI reusa `EmpresaForm`; `sujeita_fator_r` vira escolha Sim/Não

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** o fluxo aprovado usa os mesmos campos do cadastro normal. Hoje `sujeita_fator_r` é um checkbox marcado por padrão, o que não permite o estado "não escolhido" (AT-009).

**Escolha:**
- `EmpresaForm` recebe `inicial` parcial, com `sujeita_fator_r: boolean | null`, mais a prop `cnpjSomenteLeitura`;
- o campo passa a ser um par de rádios Sim/Não **em todas as telas**, e "Salvar" fica desabilitado enquanto for `null`;
- em "Nova empresa" o padrão continua `true`, então o comportamento não muda.

**Alternativas rejeitadas:**
1. Formulário novo só para o inbox — duplica validação de CNPJ, honorário e competência.
2. Checkbox em uma tela e rádio em outra — dois modos para o mesmo campo.

**Consequências:** mudança visual pequena em "Nova empresa" e "Editar empresa" (checkbox → rádio). Nenhum E2E depende do checkbox (conferido).

---

### Decision 11: Entrega como marco M8 em `docs/tasks.md`

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-22 |

**Contexto:** a v1 (M0–M7) está fechada; o contrato exige tarefa registrada antes de implementar (CLAUDE.md §8, etapa 1).

**Escolha:** seção nova **M8 — Cadastro de empresa pelo extrato**, com T-801 a T-807 e "Aceite M8" = AT-001 a AT-014 do DEFINE. `PARSER_VERSION` sobe de `2026.09.1` para `2026.09.2`.

---

## File Manifest

| # | Arquivo | Ação | Propósito | Responsável | Depende de |
|---|---|---|---|---|---|
| 1 | `docs/tasks.md` | Modificar | Seção M8 (T-801..T-807) + Aceite M8 | build | — |
| 2 | `docs/plan.md` | Modificar | Registro de decisões 2026-09-22 (decisões do BRAINSTORM + D-01..D-04 + Decisions 1–11) | build | — |
| 3 | `docs/prd.md` | Modificar | §7.6: PA em intervalo, identificação no extrato, cadastro pelo extrato com confirmação | build | — |
| 4 | `apps/api/src/fator_r/parsing/pgdas.py` | Modificar | `Identificacao`, `_nome_empresarial`, `_sugestao_sujeita`, `_RE_PA_INTERVALO`, `_anexo` estruturado, `PARSER_VERSION` | @python-developer | 1 |
| 5 | `apps/api/tests/parsing/test_pgdas_unit.py` | Modificar | Casos novos de nome, PA em intervalo, sugestão e anexo | @test-generator | 4 |
| 6 | `apps/api/fixtures/pgdas/pdf_declaratorio_{fator_r_abaixo_28,comercio_sem_fator_r,servico_sem_fator_r,fator_r_acima_28}/` | Criar | `documento.pdf` (cópia de `pdf/com_cnpj/`) + `expected.json` | build | 4 |
| 7 | `apps/api/tests/parsing/test_fixtures.py` | Modificar | `lacunas_conhecidas` + asserção de `identificacao` quando declarada | @test-generator | 6 |
| 8 | `apps/api/scripts/parser_experiment.py` | Modificar | Respeitar `lacunas_conhecidas` na comparação | build | 6 |
| 9 | `apps/api/fixtures/pgdas/README.md` | Modificar | Seção "Layout declaratório" e significado de `lacunas_conhecidas` | build | 6 |
| 10 | `apps/api/src/fator_r/repositories/companies.py` | Modificar | `adicionar()` sem commit | @python-developer | — |
| 11 | `apps/api/src/fator_r/agents/parser_pgdas.py` | Modificar | `_identificacao` em `campos_json`, `SugestaoCadastro`, `sugestao_cadastro()`, exceções, `_decidir_vinculo()` (extraída de `vincular_manual`), `cadastrar_e_vincular()` | @python-developer | 4, 10 |
| 12 | `apps/api/tests/agents/test_parser_pgdas.py` | Modificar | Cadastro feliz, corrida (`IntegrityError` → trace de erro e nada gravado), decisão registrada, regressão de `vincular_manual` | @test-generator | 11 |
| 13 | `apps/api/src/fator_r/api/inbox.py` | Modificar | `SugestaoCadastroOut`, `DocumentoOut.sugestao_cadastro`, `CadastroPeloExtratoOut`, rota `POST /{document_id}/cadastrar-empresa` | @python-developer | 11 |
| 14 | `apps/api/tests/api/test_inbox_cadastro.py` | Criar | 201, 404, 409 (estado e duplicado com `company_id`), 422 (divergente e sem CNPJ), sugestão só no caso certo, movimento criado | @test-generator | 13 |
| 15 | `apps/api/tests/api/test_isolation.py` | Modificar | `CORPOS[("POST", "/inbox/{document_id}/cadastrar-empresa")]` | @test-generator | 13 |
| 16 | `apps/api/tests/integration/…` (suíte `-m langfuse`) | Modificar | Trace `cadastro_pelo_extrato` com spans `tool/decide/render` e o mesmo `trace_id` | @test-generator | 13 |
| 17 | `apps/web/lib/api/openapi.json`, `schema.d.ts` | Regenerar | `make api-types` | build | 13 |
| 18 | `apps/web/lib/api/types.ts` | Modificar | Aliases `SugestaoCadastro`, `CadastroPeloExtratoOut` | build | 17 |
| 19 | `apps/web/lib/api/inbox.ts` | Modificar | `cadastrarEmpresaPeloExtrato()` | build | 18 |
| 20 | `apps/web/components/empresas/EmpresaForm.tsx` | Modificar | `inicial` parcial, `cnpjSomenteLeitura`, rádio Sim/Não com estado `null` | build | 18 |
| 21 | `apps/web/components/inbox/CadastroPeloExtrato.tsx` | Criar | Bloco + formulário + 409 → "Vincular à empresa existente" | build | 19, 20 |
| 22 | `apps/web/app/(app)/inbox/page.tsx` | Modificar | Renderiza o bloco quando `ultimo.sugestao_cadastro` | build | 21 |
| 23 | `apps/web/app/(app)/inbox/[id]/page.tsx` | Modificar | Renderiza o bloco no detalhe; mostra o nome empresarial lido | build | 21 |
| 24 | `apps/web/e2e/cadastro-pelo-extrato.spec.ts` | Criar | Upload de CNPJ desconhecido → cadastrar → `linked` + receita + trace | @test-generator | 22 |

**Sem migração.** `companies` já tem `UNIQUE (firm_id, cnpj)` (`20260917_0002_companies.py`), e `pgdas_documents.campos_json` é JSONB.

---

## Code Patterns

### Pattern 1 — Parser: identificação, PA em intervalo e anexo estruturado (`parsing/pgdas.py`)

```python
PARSER_VERSION = "2026.09.2"

_RE_PA_INTERVALO = re.compile(
    r"Per[ií]odo\s+de\s+Apura[cç][aã]o(?:\s*\(PA\))?\s*[:\-]?\s*"
    r"\d{2}/(\d{2})/(\d{4})\s+a\s+\d{2}/(\d{2})/(\d{4})",
    re.IGNORECASE,
)
_RE_NOME = re.compile(r"^Nome\s+empresarial\s*:?\s*(\S.{0,199})$", re.IGNORECASE)
_RE_FATOR_NAO_SE_APLICA = re.compile(r"Fator\s*r\s*[:=]?\s*N[aã]o\s+se\s+aplica", re.IGNORECASE)
_RE_LINHA_ESTRUTURADA = re.compile(r"^(?:Fator\s*r|Enquadramento|Atividade)\b", re.IGNORECASE)
_RE_QUALQUER_ANEXO = re.compile(r"\bAnexo\s+(I{1,3}|IV|V)(?![IVX])", re.IGNORECASE)


@dataclass(frozen=True)
class Identificacao:
    """Dados de cadastro lidos do extrato. Fora da confiança e da nota ouro (DEFINE D-02)."""

    nome_empresarial: str | None = None
    sujeita_fator_r: bool | None = None


@dataclass(frozen=True)
class ResultadoParse:
    campos: dict[Campo, str | None]
    confianca_campos: dict[Campo, Decimal]
    confianca: Decimal
    motivos: tuple[str, ...] = field(default_factory=tuple)
    parser_version: str = PARSER_VERSION
    identificacao: Identificacao = field(default_factory=Identificacao)


def _pa(linhas: list[str]) -> str | None:
    for regex in _RE_PA:
        for linha in linhas:
            if (match := regex.search(linha)) and 1 <= int(match.group(1)) <= 12:
                return f"{match.group(2)}-{match.group(1)}"
    for linha in linhas:  # layout declaratório: "01/08/2026 a 31/08/2026"
        if match := _RE_PA_INTERVALO.search(linha):
            mes_ini, ano_ini, mes_fim, ano_fim = match.groups()
            if (mes_ini, ano_ini) == (mes_fim, ano_fim) and 1 <= int(mes_ini) <= 12:
                return f"{ano_ini}-{mes_ini}"
    return None


def _anexo(linhas: list[str]) -> str | None:
    """Anexo III/V. Linha estruturada manda; texto livre só se não houver nenhuma."""
    for linha in linhas:
        if _RE_LINHA_ESTRUTURADA.match(linha) and (match := _RE_QUALQUER_ANEXO.search(linha)):
            anexo = match.group(1).upper()
            return anexo if anexo in ("III", "V") else None
    for linha in linhas:
        if match := _RE_ANEXO.search(linha):
            return match.group(1).upper()
    return None


def _nome_empresarial(linhas: list[str]) -> str | None:
    for linha in linhas:
        if (match := _RE_NOME.match(linha)) and (nome := match.group(1).strip()):
            return nome
    return None


def _sugestao_sujeita(linhas: list[str], fator_r: str | None) -> bool | None:
    if fator_r is not None:
        return True
    if any(_RE_FATOR_NAO_SE_APLICA.search(linha) for linha in linhas):
        return False
    return None

# em parse(): ... return ResultadoParse(campos, confianca_campos, confianca, tuple(motivos),
#     identificacao=Identificacao(_nome_empresarial(linhas),
#                                 _sugestao_sujeita(linhas, campos["fator_r"])))
```

### Pattern 2 — Repositório sem commit (`repositories/companies.py`)

```python
async def adicionar(session: AsyncSession, firm_id: uuid.UUID, dados: dict[str, Any]) -> Company:
    """Insere sem commit: só para fluxos que comitam depois (ex.: dentro de tracer.run)."""
    company = Company(firm_id=firm_id, **dados)
    session.add(company)
    try:
        await session.flush()
    except IntegrityError as exc:
        if "uq_companies_firm_cnpj" in str(exc.orig):
            raise CnpjDuplicado from exc
        raise
    return company
```

### Pattern 3 — Orquestração no agente (`agents/parser_pgdas.py`)

```python
class ExtratoSemCnpjValido(ValueError):
    pass


class CnpjDivergente(ValueError):
    pass


class CnpjJaCadastrado(ValueError):
    def __init__(self, company_id: uuid.UUID) -> None:
        super().__init__("CNPJ já cadastrado neste escritório")
        self.company_id = company_id


@dataclass(frozen=True)
class SugestaoCadastro:
    cnpj: str
    nome_empresarial: str | None
    sujeita_fator_r: bool | None


def sugestao_cadastro(documento: PgdasDocument) -> SugestaoCadastro | None:
    """Só oferece cadastro para CNPJ válido que não está na carteira (DEFINE RF-06, D-04)."""
    cnpj = documento.campos_json.get("cnpj")
    if (
        documento.status != "needs_review"
        or documento.motivo != "cnpj_nao_encontrado"
        or not cnpj
        or not cnpj_valido(cnpj)
    ):
        return None
    ident = documento.campos_json.get("_identificacao") or {}
    return SugestaoCadastro(cnpj, ident.get("nome_empresarial"), ident.get("sujeita_fator_r"))


async def _decidir_vinculo(
    run: tracer.AgentRun, session: AsyncSession, documento: PgdasDocument,
    company: Company, *, tipo: str, extra: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Movimento]:
    """Vínculo + receita do PA (§3.8) + decisão gravada. Usada pelo vínculo manual e pelo cadastro."""
    movimento = await _aplicar_vinculo(session, documento, company)
    documento.trace_id = run.trace_id
    decisao = {
        "document_id": documento.id,
        "status": documento.status,
        "company_id": company.id,
        "movimento": movimento,
        "competencia": documento.campos_json.get("pa"),
        "origem_decisao": "analista",
        **(extra or {}),
    }
    await tracer.record_decision(run, tipo=tipo, dados=decisao)
    return decisao, movimento


async def cadastrar_e_vincular(
    session: AsyncSession, user: AuthenticatedUser, documento: PgdasDocument,
    dados_empresa: dict[str, Any],
) -> tuple[ResultadoAgente, Company]:
    if documento.status not in ("needs_review", "parsed"):
        raise DocumentoEmEstadoInvalido(f"Documento em '{documento.status}' não pode ser vinculado")
    lido = documento.campos_json.get("cnpj")
    if not lido or not cnpj_valido(lido):
        raise ExtratoSemCnpjValido("O extrato não tem CNPJ válido para cadastrar")
    if dados_empresa["cnpj"] != lido:
        raise CnpjDivergente("O CNPJ do cadastro precisa ser o mesmo do extrato")
    if (existente := await companies.obter_por_cnpj(session, user.firm_id, lido)) is not None:
        raise CnpjJaCadastrado(existente.id)

    ident = documento.campos_json.get("_identificacao") or {}
    async with tracer.run(
        session, agente=AGENTE, gatilho="cadastro_pelo_extrato",
        firm_id=user.firm_id, user_id=user.id,
        entrada={"document_id": documento.id, "cnpj": lido},
    ) as run:
        with run.span("tool", input={"cnpj": lido}) as span:
            span.update(output={"cnpj_na_carteira": False})
        with run.span("decide") as span:
            company = await companies.adicionar(session, user.firm_id, dados_empresa)
            run.trace.company_id = company.id
            decisao, movimento = await _decidir_vinculo(
                run, session, documento, company,
                tipo="pgdas_cadastro_pelo_extrato",
                extra={
                    "empresa_criada": True,
                    "nome_igual_extrato": dados_empresa["nome"] == ident.get("nome_empresarial"),
                    "sujeita_igual_sugestao": (
                        None if ident.get("sujeita_fator_r") is None
                        else dados_empresa["sujeita_fator_r"] == ident["sujeita_fator_r"]
                    ),
                },
            )
            span.update(output=decisao)
        with run.span("render") as span:
            texto_final = com_disclaimer(
                f"Empresa {company.nome} cadastrada a partir do extrato. "
                + _texto_base(documento, movimento, company)
            )
            span.update(output={"texto": texto_final})
        await run.finish(decisao=decisao, texto=texto_final, status="ok")
    acerto = await _avaliar_ouro(session, user, documento)
    return ResultadoAgente(documento, False, run.trace_id, texto_final, acerto), company
```

`nome_igual_extrato` e `sujeita_igual_sugestao` medem, com dado real, as premissas A-001 e A-004 do DEFINE sem enviar o nome ao Langfuse: só booleanos entram na decisão.

`vincular_manual` passa a chamar `_decidir_vinculo(..., tipo="pgdas_vinculo_manual")`, com a mesma decisão de hoje — é um refactor sem mudança de comportamento, coberto pelos testes existentes.

### Pattern 4 — Rota (`api/inbox.py`)

```python
class SugestaoCadastroOut(BaseModel):
    cnpj: str
    cnpj_formatado: str
    nome_empresarial: str | None
    sujeita_fator_r: bool | None


class DocumentoOut(BaseModel):
    ...
    sugestao_cadastro: SugestaoCadastroOut | None = None
    # em de(): s = parser_pgdas.sugestao_cadastro(d)
    #   sugestao_cadastro = SugestaoCadastroOut(cnpj=s.cnpj, cnpj_formatado=formatar_cnpj(s.cnpj),
    #       nome_empresarial=s.nome_empresarial, sujeita_fator_r=s.sujeita_fator_r) if s else None


class CadastroPeloExtratoOut(BaseModel):
    documento: DocumentoOut
    empresa: CompanyOut


def _erro(status_code: int, codigo: str, mensagem: str, **extra: object) -> HTTPException:
    return HTTPException(status_code, {"codigo": codigo, "mensagem": mensagem, **extra})


@router.post(
    "/{document_id}/cadastrar-empresa",
    response_model=CadastroPeloExtratoOut,
    status_code=status.HTTP_201_CREATED,
)
async def cadastrar_empresa_pelo_extrato(
    document_id: uuid.UUID, payload: CompanyIn, user: CurrentUser, session: FirmSession
) -> CadastroPeloExtratoOut:
    documento = await documento_do_escritorio(session, user.firm_id, document_id)
    try:
        resultado, empresa = await parser_pgdas.cadastrar_e_vincular(
            session, user, documento, dados_empresa(payload)
        )
    except parser_pgdas.DocumentoEmEstadoInvalido as exc:
        raise _erro(409, "documento_em_estado_invalido", str(exc)) from exc
    except parser_pgdas.CnpjJaCadastrado as exc:
        raise _erro(409, "cnpj_ja_cadastrado", str(exc), company_id=str(exc.company_id)) from exc
    except companies.CnpjDuplicado as exc:  # corrida: trace de erro já gravado pelo tracer
        vencedora = await companies.obter_por_cnpj(session, user.firm_id, payload.cnpj)
        raise _erro(
            409, "cnpj_ja_cadastrado", "CNPJ já cadastrado neste escritório",
            company_id=str(vencedora.id) if vencedora else None,
        ) from exc
    except parser_pgdas.ExtratoSemCnpjValido as exc:
        raise _erro(422, "extrato_sem_cnpj_valido", str(exc)) from exc
    except parser_pgdas.CnpjDivergente as exc:
        raise _erro(422, "cnpj_divergente", str(exc)) from exc
    return CadastroPeloExtratoOut(
        documento=DocumentoOut.de(resultado.documento, resultado.texto),
        empresa=CompanyOut.de(empresa),
    )
```

`dados_empresa(payload)` é o `_dados` de `api/companies.py`, promovido a função pública com o mesmo corpo, para não duplicar a conversão de `inicio_atividade`.

### Pattern 5 — Bloco na web (`components/inbox/CadastroPeloExtrato.tsx`)

```tsx
"use client";

import { useState } from "react";

import { EmpresaForm } from "@/components/empresas/EmpresaForm";
import { ApiError } from "@/lib/api";
import { cadastrarEmpresaPeloExtrato, vincularDocumento } from "@/lib/api/inbox";
import type { CadastroPeloExtratoOut, DocumentoOut } from "@/lib/api/types";

type Conflito = { company_id: string | null };

function conflitoDe(error: unknown): Conflito | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  const d = error.detail as { codigo?: string; company_id?: string | null } | null;
  return d?.codigo === "cnpj_ja_cadastrado" ? { company_id: d.company_id ?? null } : null;
}

export function CadastroPeloExtrato({
  documento,
  onConcluido,
}: {
  documento: DocumentoOut;
  onConcluido: (r: { documento: DocumentoOut }) => void;
}) {
  const [aberto, setAberto] = useState(false);
  const [conflito, setConflito] = useState<Conflito | null>(null);
  const s = documento.sugestao_cadastro;
  if (!s) return null;

  return (
    <div data-testid="cadastro-pelo-extrato" className="rounded border border-amber-300 bg-amber-50 p-3 text-sm">
      <p className="font-medium">Esse CNPJ não está na sua carteira ({s.cnpj_formatado}).</p>
      {!aberto && (
        <button type="button" className="mt-2 rounded bg-zinc-900 px-3 py-1.5 text-white" onClick={() => setAberto(true)}>
          Cadastrar e vincular
        </button>
      )}
      {aberto && (
        <EmpresaForm
          inicial={{ nome: s.nome_empresarial ?? "", cnpj_formatado: s.cnpj_formatado, sujeita_fator_r: s.sujeita_fator_r }}
          cnpjSomenteLeitura
          rotuloSalvar="Confirmar cadastro e vínculo"
          onSalvar={async (dados) => {
            try {
              const r: CadastroPeloExtratoOut = await cadastrarEmpresaPeloExtrato(documento.id, dados);
              onConcluido(r);
            } catch (error) {
              setConflito(conflitoDe(error));
              throw error; // EmpresaForm mostra a mensagem padrão
            }
          }}
        />
      )}
      {conflito?.company_id && (
        <button
          type="button"
          className="mt-2 underline"
          onClick={async () => onConcluido({ documento: await vincularDocumento(documento.id, conflito.company_id!) })}
        >
          Vincular à empresa já cadastrada
        </button>
      )}
    </div>
  );
}
```

O disclaimer do PGDAS-D já vem do layout autenticado (componente único, CLAUDE.md §10.2). O bloco não repete o aviso.

---

## Data Flow

```text
1. POST /inbox/pgdas ─▶ parse (subprocesso isolado) ─▶ campos + _identificacao em campos_json
2. decide (inalterado): CNPJ fora da carteira → needs_review / cnpj_nao_encontrado
3. DocumentoOut.de(): sugestao_cadastro = parser_pgdas.sugestao_cadastro(doc)   (sem I/O)
4. Web: bloco + EmpresaForm (CNPJ travado) → analista confirma
5. POST /inbox/{id}/cadastrar-empresa {CompanyIn}
     pré-checagens → 404 | 409 | 422, sem trace e sem escrita
     tracer.run → adicionar(flush) → _aplicar_vinculo → record_decision → finish(COMMIT)
6. Resposta 201 {documento(linked, texto_agente), empresa}; a web invalida ["inbox"], ["documento", id], ["empresas"]
```

---

## Integration Points

| Sistema | Tipo | Como |
|---|---|---|
| Postgres | Interno | Mesma sessão `FirmSession` (RLS via `app.firm_id` no `after_begin`); `UNIQUE (firm_id, cnpj)` resolve a corrida |
| Langfuse (self-hosted) | Interno | `tracer.run` já existente; o CNPJ no span `tool` é mascarado por `mask_otel_spans`; o nome da empresa não vai na decisão |
| Anthropic | — | **Não participa**: parse determinístico e texto por template (§3.1, §3.2) |

---

## Testing Strategy

| Tipo | Escopo | Arquivo | Ferramenta | Cobre |
|---|---|---|---|---|
| Unitário | `_pa` em intervalo (mesmo mês, meses diferentes, mês 13), `_nome_empresarial` (com/sem acento, sem `:`, vazio, 200+ caracteres), `_sugestao_sujeita` (número, "não se aplica", nada), `_anexo` (estruturado III/V, estruturado I → `None`, sem estruturado → texto livre) | `tests/parsing/test_pgdas_unit.py` | pytest | RF-01..RF-03, AT-010 |
| Fixtures | 4 PDFs declaratórios (campos verdadeiros + lacunas + identificação) e 10 fixtures atuais sem mudança | `tests/parsing/test_fixtures.py` | pytest | Critérios 1–4, AT-013 |
| Agente | `cadastrar_e_vincular`: caminho feliz, PA ausente (`sem_rpa`), cada pré-checagem, corrida via `IntegrityError` (nenhuma empresa, documento intacto, trace `error`), decisão com `nome_igual_extrato`; `vincular_manual` sem regressão | `tests/agents/test_parser_pgdas.py` | pytest + banco de teste com RLS | RF-07..RF-10, AT-007 |
| API | 201 com corpo; 404 outro escritório; 409 estado e duplicado com `company_id`; 422 divergente e sem CNPJ; `sugestao_cadastro` presente só no caso certo; movimento 2026-08 `origem=pgdas` com folha zero | `tests/api/test_inbox_cadastro.py` | pytest + httpx | AT-001, AT-003..AT-006, AT-008 |
| Isolamento | Rota nova no varredor por OpenAPI | `tests/api/test_isolation.py` | pytest `-k isolation` | §3.13 |
| Nota ouro | Documento vinculado pelo cadastro não gera `gold_nome_*` | `tests/agents/test_parser_pgdas.py` | pytest | AT-014 |
| Langfuse | Trace `cadastro_pelo_extrato`, spans `tool/decide/render`, mesmo `trace_id` local/Langfuse | suíte `-m langfuse` | pytest + Langfuse local | AT-011 |
| E2E | Upload de TXT com CNPJ desconhecido → bloco no resultado → confirmar → `linked` + receita na grade da empresa + `trace_id`; conflito 409 oferece vincular | `e2e/cadastro-pelo-extrato.spec.ts` | Playwright | AT-001, AT-003, AT-012, critério de ≤ 2 interações |

**Gates (CLAUDE.md §7):**
- `make lint`;
- `mypy --strict apps/api/src` e `tsc --noEmit`;
- `make test`;
- `pytest apps/api/tests/api -k isolation`;
- `pytest apps/api/tests/parsing` e `make parser-experiment`;
- `pytest -m langfuse`;
- `make api-types` sem diff pendente;
- `make e2e`.

**Atenção:** `make e2e` recria o banco local (`down -v`); depois dele, rodar `make migrate && make seed`.

---

## Validação prévia das regras (2026-09-22)

As regex do Pattern 1 foram rodadas, antes do build, contra o texto real extraído por
`parsing/texto.extrair_texto`:

| Amostra | PA (intervalo) | Nome empresarial | Sugestão `sujeita_fator_r` | Anexo hoje → proposto |
|---|---|---|---|---|
| `01_servico_fator_r_abaixo_28` | 2026-08 | EMPRESA DE SERVICOS A - ANONIMIZADA | `true` | V → V |
| `02_comercio_sem_fator_r` | 2026-08 | EMPRESA DE COMERCIO B - ANONIMIZADA | `false` | **III → `None`** (corrigido) |
| `03_servico_sem_fator_r` | 2026-08 | EMPRESA DE SERVICOS C - ANONIMIZADA | `false` | III → III |
| `04_servico_fator_r_acima_28` | 2026-08 | EMPRESA DE SERVICOS D - ANONIMIZADA | `true` | III → III |
| 10 fixtures sintéticas | nenhum casamento com a regex de intervalo | "CLINICA EXEMPLO LTDA" em 7; `None` em `txt_rotulos_alternativos`, `txt_sem_relacao` e `pdf_sem_camada_texto` | — | **0 mudanças** |

Conclusão: as Decisions 4, 5 e 6 entregam os critérios 1 e 2 do DEFINE sem alterar nenhuma
fixture existente.

---

## Rollout e compatibilidade

| Aspecto | Efeito |
|---|---|
| Banco | Sem migração |
| Documentos já existentes | Sem `_identificacao`: sugestão aparece (se `cnpj_nao_encontrado`) sem nome nem enquadramento pré-preenchidos |
| `PARSER_VERSION` | `2026.09.2` só em documentos novos; os antigos mantêm a versão com que foram lidos |
| Deduplicação por SHA-256 | Reenviar o mesmo arquivo devolve o documento antigo (não reprocessa) — comportamento atual mantido |
| Rotas existentes | Sem mudança de contrato; `DocumentoOut` só ganha campo opcional |
| Telas existentes | "Nova empresa"/"Editar empresa": checkbox de Fator R vira rádio Sim/Não, com o mesmo padrão |

---

## Riscos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Rótulo "Nome empresarial" diferente no extrato real (A-001) | Média | Sugestão sai nula e o analista digita; `nome_igual_extrato` mede a taxa real |
| Mudança em `_anexo` afetar extrato real sem linha estruturada | Baixa | Sem linha estruturada, o comportamento é idêntico ao de hoje; teste unitário explícito |
| Refactor de `vincular_manual` alterar a decisão gravada | Baixa | Mesmo `tipo` e mesmos campos; testes atuais de `vincular_manual` continuam verdes |
| 409 da corrida devolver `company_id` nulo (empresa vencedora de outro escritório? impossível pelo `UNIQUE (firm_id, cnpj)`) | Muito baixa | O front trata `company_id` nulo mostrando só a mensagem |

---

## Tarefas propostas para `docs/tasks.md` (M8)

| ID | Tarefa | Dep. |
|---|---|---|
| T-801 | Parser: `Identificacao` (nome empresarial + sugestão de `sujeita_fator_r`), PA em intervalo, anexo estruturado, `PARSER_VERSION 2026.09.2`, testes unitários | T-507 |
| T-802 | Fixtures `pdf_declaratorio_*` com `lacunas_conhecidas`; `test_fixtures.py`, `parser_experiment.py` e README | T-801, T-508 |
| T-803 | `companies.adicionar` + `parser_pgdas.sugestao_cadastro` + `cadastrar_e_vincular` (com `_decidir_vinculo`), testes do agente | T-801, T-512 |
| T-804 | API: `sugestao_cadastro` no `DocumentoOut`, `POST /inbox/{id}/cadastrar-empresa`, testes de API e isolamento, `make api-types` | T-803 |
| T-805 | Web: `EmpresaForm` (inicial parcial, CNPJ só leitura, rádio Sim/Não) + `CadastroPeloExtrato` no upload e no detalhe | T-804, T-514 |
| T-806 | Integração Langfuse (`-m langfuse`) e E2E `cadastro-pelo-extrato.spec.ts` | T-805 |
| T-807 | Documentação: PRD §7.6, Registro de decisões no `plan.md`, README se preciso | T-801..T-806 |

**Aceite M8** = AT-001 a AT-014 do DEFINE, com evidência (saída de teste, print ou `trace_id`).

---

## Revision History

| Versão | Data | Autor | Mudanças |
|---|---|---|---|
| 1.0 | 2026-09-22 | design | Versão inicial |
| 1.1 | 2026-09-22 | ship | Entregue e arquivado. Divergências do desenho registradas no BUILD_REPORT (regex do nome; teste Langfuse pela API pública) e iterações T-808..T-810 no Registro de decisões |

---

## Next Step

**Pronto para:** `/workflow:build .claude/sdd/features/DESIGN_CADASTRO_EMPRESA_PELO_EXTRATO.md`
