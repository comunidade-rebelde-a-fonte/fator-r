# BRAINSTORM: Tema visual inspirado no ceath.io

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TEMA_CEATH |
| **Date** | 2026-09-23 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** "aplique o estilo do sistema com base nesse site https://ceath.io/"

**Context Gathered:**
- `apps/web` é Next.js 16 + Tailwind v4 + TanStack Query. O `globals.css` só define `--background: #fff` e `--foreground: #171717`. Não há tokens de tema.
- Há cerca de 150 classes de cor fixas em uns 24 arquivos. As mais usadas: `text-zinc-500` (35), `border-zinc-300` (21), `text-red-700` (13), `bg-zinc-900` (12). Os estados usam `emerald`, `amber`, `red` e `sky`.
- Os primitivos já existem, mas são poucos: `components/ui/Badge.tsx` (mapa `CORES`), `components/ui/Estado.tsx` (`Carregando`, `Vazio`, `Erro`), `components/AppNav.tsx`, `components/Disclaimer.tsx` (componente único, regra §3.14) e `components/fator-r/SemaforoBadge.tsx`.
- Os E2E (`e2e/aceite-v1.spec.ts`, `e2e/cadastro-pelo-extrato.spec.ts`) não usam seletor de classe nem de CSS. Selecionam por `data-testid`, `role` e texto. Trocar estilo não deve quebrá-los.
- `public/` está vazio. Não existe `public/brand/`.
- `apps/web/AGENTS.md` avisa que esta versão do Next.js tem mudanças incompatíveis. Antes de mexer em `next/font` ou no layout, é preciso consultar `node_modules/next/dist/docs/`.

**Referência extraída do CSS público do ceath.io** (`/wp-content/themes/ceath-theme/assets/ceath/css/ceath.css`):

| Elemento | Valor no ceath.io |
|---|---|
| Fundo | `--bg:#050505`, `body #020202` com `radial-gradient` laranja/vermelho a ~3% |
| Painéis | `--panel:#090909`, `--panel-2:#0c0a09` |
| Texto | `--text:#f4f0eb` (off-white quente), `--muted:#aaa39c`; nav `#cec7c1` |
| Linhas | `--line:rgba(255,255,255,.09)`, header `rgba(255,255,255,.075)` |
| Destaque | `--orange:#ff8619`, `--orange-soft:#ffb15a`, eyebrow `#e8b47e` |
| Secundária | `--red:#ff293d`, `--red-soft:#ff6672` |
| Fontes | Inter 400–800 (corpo); Oswald 500–700 maiúsculo (títulos, `line-height:.9`) |
| Botão primário | `linear-gradient(180deg,#f78b22,#9d3a06)`, borda `#ff8619`, `radius 4px`, maiúsculo, `letter-spacing .055em`, `font-weight 800` |
| Botão secundário | borda `rgba(255,134,25,.65)`, fundo `rgba(255,134,25,.05)`, hover `.12` |
| Eyebrow | `.74rem`, maiúsculo, `letter-spacing .18em`, traço laranja de 32px com brilho |
| Cards | `radius 10–16px`, `box-shadow 0 20px 60px -30px rgba(0,0,0,.8), inset 0 1px 0 rgba(255,255,255,.04)` |
| Header | 76px, `border-bottom` de 1px, nav `.84rem` com `opacity .82` |

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `apps/web/app/globals.css`, `apps/web/app/layout.tsx`, `apps/web/components/**`, `apps/web/app/(app)/**`, `apps/web/app/(auth)/**` | Só frontend, sem mudança em `apps/api` |
| Relevant KB Domains | Tailwind v4 `@theme`, `next/font` (Next 16) | Tokens como utilitários (`bg-panel`, `text-muted`, `text-accent`) |
| IaC Patterns | N/A | Sem infraestrutura |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Quão fiel ao ceath.io? (escuro adaptado, réplica fiel, claro com identidade, claro e escuro) | **Tema escuro adaptado** | Paleta e fontes do ceath com densidade de ferramenta. Oswald só em título de página e números de destaque. Sem hero nem brilhos de marketing. |
| 2 | Laranja/vermelho da marca e o semáforo | **Marca completa**: laranja e vermelho da marca também no semáforo e nos erros | Vermelho = `#ff293d`, amarelo = `#ff8619`. Risco de confundir botão laranja com "amarelo". Mitigação na Decisão 4. |
| 3 | Material de referência além do CSS público | **Só o estilo** (sem logo ceath obrigatório) | O nome continua "Fator R". Nenhum asset do ceath é copiado. |
| 4 | Abordagem de implementação | **A: Tokens + primitivos** | Tokens semânticos no `globals.css` e primitivos em `components/ui/`. As telas trocam as classes fixas. |
| 5 | Logo | **Espaço opcional** | O cabeçalho mostra "Fator R" em Oswald. Se `public/brand/logo.svg` existir, o logo substitui o texto. |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `https://ceath.io/` (HTML + `ceath.css`, 51 KB) | 1 | Tokens e componentes extraídos. Tabela acima. |
| Output examples | N/A | 0 | Sem mockup. A referência visual é o próprio site. |
| Ground truth | N/A | 0 | — |
| Related code | `apps/web/components/ui/{Badge,Estado}.tsx`, `AppNav.tsx`, `Disclaimer.tsx`, `SemaforoBadge.tsx` | 5 | Pontos centrais que concentram boa parte da troca |

**How samples will be used:**
- Os valores do `ceath.css` viram os tokens do `@theme`.
- Os E2E existentes servem de regressão: o comportamento não pode mudar.

---

## Approaches Explored

### Approach A: Tokens semânticos + primitivos ⭐ Recommended

**Description:** Tokens (`bg`, `panel`, `panel-2`, `line`, `text`, `muted`, `accent`, `accent-soft`, `danger`, `danger-soft`, `ok`, `warn`) em `:root` e expostos via `@theme inline`. Primitivos novos: `Button`, `Card`, `Input`/`Select`, `Tabela`, `PageHeader`. As telas passam a usar tokens e primitivos.

**Pros:**
- O tema fica num lugar só. Trocar a paleta depois é mexer em um arquivo.
- Os nomes são semânticos (`text-muted`, e não `text-zinc-500`), então o código não mente sobre a cor.
- Os primitivos reduzem classes repetidas nas ~24 telas.

**Cons:**
- Toca muitos arquivos, e o diff é grande, embora mecânico.
- Exige conferir cada tela no navegador.

**Why Recommended:** É a única opção que deixa o tema sustentável sem dependência nova. Foi escolhida pelo usuário.

### Approach B: Remapear a paleta padrão do Tailwind

**Description:** Redefinir `zinc-*`, `red-*` etc. no `@theme` com os valores escuros, sem tocar nas telas.

**Pros:** diff pequeno e rápido.
**Cons:** as classes passam a mentir (`text-zinc-900` vira texto claro), o que atrapalha a manutenção. Os contrastes ficam imprevisíveis e não há primitivos.

### Approach C: Biblioteca de componentes (shadcn/ui ou similar)

**Description:** Adotar uma biblioteca e estilizá-la com o tema ceath.

**Pros:** componentes acessíveis prontos.
**Cons:** é uma dependência grande fora do previsto no plano (CLAUDE.md §4.3 e §9) e exagero para o tamanho do app.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A: Tokens semânticos + primitivos |
| **User Confirmation** | 2026-09-22 (pergunta "Abordagem") |
| **Reasoning** | Tema centralizado, sem dependência nova, nomes semânticos |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Só tema escuro, sem alternância | Escolha do usuário. Metade do custo de teste. | Claro e escuro com seletor |
| 2 | Paleta ceath: `bg #050505`, `panel #090909`/`#0c0a09`, `line rgba(255,255,255,.09)`, `text #f4f0eb`, `muted #aaa39c`, `accent #ff8619` (hover `#ffb15a`), `danger #ff293d` (suave `#ff6672`) | Valores do `ceath.css` | Paleta própria "inspirada" |
| 3 | Semáforo com a marca: vermelho `#ff293d`, amarelo `#ff8619`, verde `#3ddc84` (o ceath não tem verde, então foi proposto e aprovado na Validação 1) | Escolha "marca completa" | Tons próprios de semáforo separados do laranja |
| 4 | Selo de estado sempre com texto, fundo translúcido (~12%) e borda da cor. Botão primário em gradiente sólido. Os dois nunca têm a mesma forma. | Evita confundir botão laranja com semáforo "amarelo" e não depende só de cor (acessibilidade) | Selo sólido igual ao botão |
| 5 | Inter no corpo, Oswald maiúsculo só em `PageHeader` e números de destaque (Fator R, RBT12, FS12) | O app é denso. Oswald em tabela prejudica leitura. | Oswald em todos os títulos (réplica fiel) |
| 6 | Fontes via `next/font`, hospedadas no próprio app | Sem requisição ao Google em runtime (LGPD/§5.3, nenhuma chamada a serviço externo não previsto) | `<link>` para fonts.googleapis.com como no ceath |
| 7 | Nome "Fator R" em Oswald. Espaço opcional para `public/brand/logo.svg`. | Resposta do usuário | Logo obrigatório ou "Fator R by ceath" |
| 8 | Disclaimer PGDAS-D continua fixo no rodapé, em componente único. Fundo `panel`, linha `accent` no topo, texto `text`. | Regra §3.14: nunca pode sumir nem perder legibilidade | Tirar o fixo ou reduzir contraste |
| 9 | Nenhuma mudança de comportamento, texto, `data-testid`, `role` ou rota | Os E2E seguem como regressão | Aproveitar para redesenhar fluxos |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Tema claro e alternância | Usuário escolheu só o escuro. Dobraria a conferência visual. | Sim (os tokens já permitem) |
| Hero, imagens de fundo, gradientes radiais e brilhos (`text-shadow`, glow) | Marketing, não ferramenta. Distrai em uso prolongado. | Sim, na tela de login |
| Animações (`translateY` no hover etc.) | Sem ganho para o trabalho do analista | Sim |
| Biblioteca de componentes | Dependência grande fora do plano | Não, sem aprovação (§9) |
| Logo ou assets do ceath copiados | "Só o estilo". Evita uso indevido de marca de terceiros. | Sim, via `public/brand/` |
| Redesenho de layout, navegação ou fluxos | Fora do pedido (é estilo, não UX) | Sim, como feature separada |
| Números ceath (01–05), seções numeradas | Padrão de landing page | Não |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Abordagem (A/B/C) | ✅ | Aprovada a A (tokens + primitivos) | Não |
| Seção 1: Identidade visual (tokens, tipografia, semáforo, disclaimer) | ✅ | **Aprovado** | Não |
| Seção 2: Componentes e escopo (primitivos, telas, fora, aceite, governança) | ✅ | Sem objeção explícita. Confirmar no /define. | — |
| Logo | ✅ | Espaço opcional | Sim (antes estava "só estilo" ou "tenho logo") |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
A interface do Fator R usa o visual padrão do Tailwind (claro, zinc) com cores fixas espalhadas pelas telas. Ela deve adotar a identidade visual do ceath.io num tema escuro, centralizado em tokens, sem mudar comportamento.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Analista ou sócio do escritório contábil | Visual genérico, sem identidade. Uso prolongado em telas densas (carteira, grade mensal). |
| Quem mantém o frontend | Cores fixas em ~24 arquivos. Não há como mudar o tema num lugar só. |

### Success Criteria (Draft)
- [ ] `globals.css` define os tokens da Decisão 2 e as cores do semáforo, expostos no `@theme inline`.
- [ ] Nenhuma classe de paleta fixa (`zinc|gray|slate|red|amber|green|emerald|yellow|sky|orange|violet-[0-9]+`) sobra em `app/` e `components/`. Checado por `grep`.
- [ ] Primitivos `Button`, `Card`, `Input`/`Select`, `Tabela`, `PageHeader` existem em `components/ui/` e são usados pelas telas.
- [ ] `Badge`, `Estado`, `SemaforoBadge`, `AppNav`, `Disclaimer` e o layout autenticado usam tokens.
- [ ] Inter e Oswald carregadas via `next/font`, sem requisição a `fonts.googleapis.com` em runtime.
- [ ] Contraste de texto normal ≥ 4,5:1 (WCAG AA) sobre `bg` e `panel`, inclusive `muted`, `accent` e as cores do semáforo.
- [ ] Disclaimer visível em todas as telas, inclusive login, com `data-testid="disclaimer-pgdas"` mantido.
- [ ] `make lint`, `tsc --noEmit` e `make e2e` verdes, sem alterar nenhum teste.
- [ ] Conferência no navegador de login, carteira, empresas (lista, ficha, grade mensal), inbox (lista, detalhe, cadastro pelo extrato), simulador, agentes e observabilidade, cada uma nos estados carregando, vazio e erro.
- [ ] Decisão registrada em `docs/plan.md` → "Registro de decisões".

### Constraints Identified
- CLAUDE.md §10.2: nenhum cálculo no front. A troca é só de apresentação.
- CLAUDE.md §3.14: disclaimer permanente e componente único.
- CLAUDE.md §5.3: nenhuma chamada a SaaS externo em runtime (daí as fontes self-hosted).
- CLAUDE.md §4.3: sem dependência grande nova. `next/font` já vem com o Next.
- `apps/web/AGENTS.md`: consultar `node_modules/next/dist/docs/` antes de usar `next/font` e layouts (Next 16 com mudanças incompatíveis).
- A mudança não está em `docs/tasks.md`. É pedido explícito do usuário, então precisa de registro em "Registro de decisões" (§9).

### Out of Scope (Confirmed)
- Tema claro e alternância de tema.
- Assets e logo do ceath (só o espaço opcional em `public/brand/`).
- Mudanças de fluxo, texto, rotas, API ou backend.
- Animações, hero, imagens decorativas.
- Qualquer item da lista "Fora" do CLAUDE.md §2.

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 7 |
| Validations Completed | 3 (+1 pendente de confirmação no /define) |
| Duration | ~1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_TEMA_CEATH.md`
