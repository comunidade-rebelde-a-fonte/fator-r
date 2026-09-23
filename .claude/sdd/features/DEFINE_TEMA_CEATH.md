# DEFINE: Tema visual inspirado no ceath.io

> Aplicar ao frontend do Fator R um tema escuro com a identidade visual do ceath.io, centralizado em tokens e primitivos, sem mudar comportamento.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TEMA_CEATH |
| **Date** | 2026-09-23 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |
| **Source** | `.claude/sdd/features/BRAINSTORM_TEMA_CEATH.md` |

---

## Problem Statement

O frontend do Fator R (`apps/web`) usa o visual padrão do Tailwind (fundo branco, tons `zinc`). São 148 classes de paleta fixas, mais 12 `text-white`, espalhadas em 21 arquivos. Não há identidade visual, e mudar o tema exige editar tela por tela. O escritório quer o estilo do ceath.io (escuro, off-white quente, laranja) sem perder legibilidade em telas densas nem alterar nenhum fluxo.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Analista ou sócio do escritório | Usa carteira, grade mensal, inbox e simulador por horas | Visual genérico e sem identidade. Precisa ler números e o semáforo com clareza em uso prolongado. |
| Quem mantém o frontend | Implementa telas e tarefas do `docs/tasks.md` | Cores fixas em 21 arquivos. Não existe um lugar único para o tema nem componentes base de botão, card, input e tabela. |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1. Tokens de tema centralizados em `app/globals.css` (`:root` + `@theme inline`) com a paleta ceath aprovada |
| **MUST** | G2. Nenhuma classe de paleta fixa do Tailwind em `app/` e `components/`. Tudo via tokens semânticos. |
| **MUST** | G3. Semáforo, `Badge` e estados (`Carregando`, `Vazio`, `Erro`) nas cores da marca, sempre com texto e legíveis (AA) |
| **MUST** | G4. Disclaimer do PGDAS-D continua componente único, fixo e visível em todas as telas (CLAUDE.md §3.14) |
| **MUST** | G5. Zero mudança de comportamento: textos, `data-testid`, `role`, rotas e fluxos idênticos. E2E verdes sem editar testes. |
| **MUST** | G6. Inter (corpo) e Oswald (títulos e números de destaque) servidas pelo próprio app, sem requisição externa em runtime |
| **SHOULD** | G7. Primitivos `Button`, `Card`, `Input`/`Select`/`Textarea`, `Tabela`, `PageHeader` em `components/ui/`, usados pelas telas |
| **SHOULD** | G8. Cabeçalho com "Fator R" em Oswald e espaço opcional para `public/brand/logo.svg` |
| **COULD** | G9. Leve `radial-gradient` laranja/vermelho (~3%) no fundo do login, como no ceath |

---

## Design Tokens (aprovados no brainstorm)

| Token | Valor | Uso | Contraste sobre `bg` / `panel` |
|---|---|---|---|
| `bg` | `#050505` | fundo da página | — |
| `panel` | `#090909` | cards, header, tabelas | — |
| `panel-2` | `#0c0a09` | linha zebrada, hover, inputs | — |
| `line` | `rgba(255,255,255,.09)` | bordas e divisórias | — |
| `text` | `#f4f0eb` | texto principal | 17,97 / 17,55 |
| `muted` | `#aaa39c` | texto secundário, rótulos | 8,18 / 7,99 |
| `accent` | `#ff8619` | ação primária, nav ativa, foco, semáforo **amarelo** | 8,42 / 8,23 |
| `accent-soft` | `#ffb15a` | hover do destaque | 11,34 / 11,08 |
| `danger` | `#ff293d` | erro, ação destrutiva, semáforo **vermelho** | 5,47 / 5,34 |
| `danger-soft` | `#ff6672` | texto de erro em fundo tingido | 7,18 / 7,01 |
| `ok` | `#3ddc84` | semáforo **verde**, sucesso | 11,42 / 11,16 |
| `eyebrow` | `#e8b47e` | rótulo pequeno em maiúsculas acima do título | 10,93 / 10,68 |

Contrastes calculados com a fórmula WCAG 2.x em 2026-09-23. Todos ≥ 4,5:1, inclusive sobre o tingido de 12% da própria cor (o menor é `danger` = 4,90).

**Achado:** texto branco sobre o gradiente do botão do ceath (`#f78b22` → `#9d3a06`) tem **2,42:1 no topo**, abaixo do AA. O botão primário precisa de outra combinação (ver Constraints e Open Questions).

---

## Success Criteria

- [ ] **SC-1.** `grep -rEn '\b(bg|text|border|ring|divide|outline|from|to|fill|stroke|placeholder)-(zinc|gray|slate|neutral|stone|red|amber|green|emerald|yellow|blue|orange|sky|indigo|rose|violet|lime|teal|cyan|purple|pink|fuchsia)-[0-9]+' apps/web/app apps/web/components` retorna **0** linhas (hoje são 148).
- [ ] **SC-2.** `grep -rEn '\b(bg|text|border)-(white|black)\b'` nos mesmos diretórios retorna **0** linhas (hoje são 12).
- [ ] **SC-3.** Os 12 tokens da tabela existem em `:root` e estão expostos via `@theme inline` (utilitários `bg-panel`, `text-muted`, `border-line`, `text-accent` etc. funcionam).
- [ ] **SC-4.** Todo par texto/fundo usado no tema tem contraste **≥ 4,5:1**, inclusive o texto do botão primário em **todo** o gradiente ou fundo.
- [ ] **SC-5.** Foco de teclado visível (anel `accent`, ≥ 3:1 sobre o fundo) em links, botões, inputs e selects.
- [ ] **SC-6.** Nenhuma requisição a `fonts.googleapis.com` ou `fonts.gstatic.com` na aba Network ao carregar qualquer tela.
- [ ] **SC-7.** `make lint` verde (eslint + prettier --check + `tsc --noEmit`).
- [ ] **SC-8.** `make e2e` verde (`aceite-v1.spec.ts`, `cadastro-pelo-extrato.spec.ts`) com **0** arquivos de teste alterados (`git diff --stat apps/web/e2e` vazio).
- [ ] **SC-9.** Conferência manual no navegador contra a API real das 12 páginas listadas em AT-007, nos estados carregando, vazio e erro. Evidência com print de cada tela.
- [ ] **SC-10.** Decisão registrada em `docs/plan.md` → "Registro de decisões" (CLAUDE.md §9).

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Tema aplicado | App rodando com a API | Abro `/login` e `/carteira` | Fundo `#050505`, texto `#f4f0eb`, títulos de página em Oswald maiúsculo, corpo em Inter |
| AT-002 | Semáforo vermelho | Empresa com Fator R < 28% | Vejo a carteira | Selo com texto "Vermelho · < 28% (Anexo V)", cor `danger`, fundo tingido e borda. Não se confunde com botão. |
| AT-003 | Semáforo amarelo vs botão primário | Carteira com empresa "amarelo" e botão primário na tela | Comparo os dois | Selo: translúcido, com borda e texto do estado. Botão: preenchido, texto de ação em maiúsculas. Formas distintas. |
| AT-004 | Dados insuficientes | Empresa com RBT12 = 0 | Vejo a carteira ou a ficha | Selo neutro "Dados insuficientes" (`muted`/`line`), nunca laranja, vermelho ou verde |
| AT-005 | Estado de erro | API fora do ar | Abro uma tela com dados | `Erro` (`data-testid="estado-erro"`) em `danger-soft` sobre fundo tingido, com "Tentar de novo" funcionando |
| AT-006 | Disclaimer | Qualquer tela, inclusive login e rolagem longa da grade mensal | Rolo até o fim | `data-testid="disclaimer-pgdas"` fixo no rodapé, texto legível (`text` sobre `panel`, linha `accent` no topo), texto idêntico ao atual |
| AT-007 | Cobertura de telas | Seed local carregado | Percorro `/login`, `/carteira`, `/empresas`, `/empresas/nova`, `/empresas/[id]`, `/empresas/[id]/editar`, `/inbox`, `/inbox/[id]`, `/agentes`, `/observabilidade`, `/observabilidade/traces/[id]` e `/` (redirect) | Todas no tema escuro, sem sobra de fundo branco ou texto escuro sobre escuro |
| AT-008 | Regressão E2E | Ambiente limpo | `make e2e` | 100% verde, sem editar nenhum spec |
| AT-009 | Fontes locais | DevTools → Network | Recarrego qualquer tela | Nenhuma requisição a domínio do Google Fonts. Fontes servidas de `/_next/static/media/`. |
| AT-010 | Logo opcional ausente | `public/brand/logo.svg` não existe | Abro qualquer tela autenticada | Cabeçalho mostra "Fator R" em Oswald, sem imagem quebrada nem erro 404 no console |
| AT-011 | Logo opcional presente | Coloco `public/brand/logo.svg` | Recarrego | Cabeçalho mostra o logo com `alt="Fator R"`, no lugar do texto |
| AT-012 | Teclado | Navegação só por Tab | Percorro a nav, os formulários e as tabelas | Anel de foco `accent` visível em todo elemento focável |
| AT-013 | Grade mensal densa | Ficha de empresa com 12+ competências | Leio a grade | Números em Inter com `tabular-nums`, linhas separadas por `line`, sem Oswald nas células |

---

## Out of Scope

- Tema claro e alternância claro/escuro.
- Logo, imagens e assets do ceath (só o espaço opcional `public/brand/logo.svg`, fornecido pelo usuário).
- Hero, imagens de fundo, brilhos (`text-shadow`, glow) e animações (`translateY` no hover).
- Biblioteca de componentes (shadcn/ui, Radix etc.).
- Mudanças de texto, fluxo, rota, layout de informação, API ou backend.
- Seções numeradas e padrões de landing page.
- Qualquer item da lista "Fora" do CLAUDE.md §2.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Domínio | CLAUDE.md §10.2: nenhum cálculo tributário no front | Mudança só de apresentação. Rótulos do semáforo vêm da API ou de mapa existente, sem lógica nova. |
| Domínio | CLAUDE.md §3.14: disclaimer permanente, componente único | `Disclaimer.tsx` muda só as classes. Texto e `data-testid` intactos. |
| Segurança/LGPD | CLAUDE.md §5.3: sem serviço externo não previsto | Fontes via `next/font` (self-hosted no build), nunca `<link>` para Google Fonts |
| Dependências | CLAUDE.md §4.3: sem dependência grande nova | `next/font` já vem com o Next. Nenhum pacote novo previsto. |
| Técnico | `apps/web/AGENTS.md`: Next 16 tem mudanças incompatíveis | Design e build consultam `node_modules/next/dist/docs/` para `next/font` e `metadata` |
| Técnico | Tailwind v4 (`@import "tailwindcss"`, `@theme inline`), sem `tailwind.config` | Tokens declarados em CSS, não em config JS |
| Técnico | E2E selecionam por `data-testid`, `role` e texto | Preservar os três. A troca de classes não afeta os seletores. |
| Acessibilidade | Botão primário do ceath (branco sobre `#f78b22`→`#9d3a06`) tem 2,42:1 | O design escolhe uma combinação ≥ 4,5:1 (ex.: texto `#050505` sobre `accent` sólido = 8,42:1, ou gradiente mais escuro) |
| Governança | Mudança fora de `docs/tasks.md`, feita por pedido explícito do usuário | Registrar em `docs/plan.md` → "Registro de decisões" na mesma entrega |
| Git | CLAUDE.md §5.5 | Sem commit, branch ou PR sem pedido do usuário |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `apps/web/app/globals.css`, `apps/web/app/layout.tsx`, `apps/web/app/(app)/**`, `apps/web/app/(auth)/**`, `apps/web/components/**`, `apps/web/public/brand/` (opcional) | Só frontend. `apps/api` intocado. |
| **KB Domains** | Nenhum domínio de `.claude/kb/` cobre frontend. Referências: docs do Next 16 em `node_modules/next/dist/docs/`, Tailwind v4 `@theme`. | Consultar no /design |
| **IaC Impact** | None | Sem infraestrutura. O Dockerfile do web não muda (fontes entram no build). |

**Inventário atual (2026-09-23):** 21 arquivos com classes de paleta fixas:
- **Páginas (10):** `agentes`, `carteira`, `empresas`, `empresas/[id]`, `inbox`, `inbox/[id]`, `observabilidade`, `observabilidade/traces/[id]`, `(auth)/login`, `(app)/layout`.
- **Componentes (11):** `AppNav`, `Disclaimer`, `EmConstrucao`, `agentes/Chat`, `empresas/EmpresaForm`, `empresas/GradeMensal`, `fator-r/PainelFatorR`, `inbox/CadastroPeloExtrato`, `simulador/Simulador`, `ui/Badge`, `ui/Estado`.

Mais `SemaforoBadge`, `StatusDocumentoBadge` e `StatusTraceBadge`, que usam `Badge` indiretamente.

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | A Seção 2 do brainstorm (primitivos, telas, fora de escopo, aceite) foi aceita, já que o usuário seguiu para o /define sem objeção | Escopo de primitivos ou telas precisaria de ajuste | [ ] Confirmar na revisão deste doc |
| A-002 | Os E2E não dependem de cor, classe ou fonte | Precisaria ajustar seletores, o que é proibido sem aprovação | [x] `grep` em `e2e/` sem `toHaveClass`/`toHaveCSS`/seletor de classe |
| A-003 | `next/font/google` no Next 16 baixa as fontes no build e serve localmente | Usar `next/font/local` com arquivos `.woff2` em `app/fonts/` | [ ] Verificar em `node_modules/next/dist/docs/` no /design |
| A-004 | O build de produção (Dockerfile) tem acesso à rede para baixar as fontes | Build offline falha. Usar `next/font/local` com arquivos versionados. | [ ] |
| A-005 | O `Badge` "roxo" (`violet`) e o "azul" (`sky`) atuais têm uso sem significado de domínio e podem virar neutro ou `accent` | Algum estado perderia distinção visual | [ ] Mapear usos no /design |
| A-006 | Os analistas usam monitores comuns. O tema escuro não prejudica impressão (não há tela de impressão no v1). | Precisaria de `@media print` claro | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Estado atual medido (148 classes, 21 arquivos) e alvo definido |
| Users | 2 | Personas claras. Sem teste com usuário real do escritório (aceitável para mudança visual). |
| Goals | 3 | MUST/SHOULD/COULD priorizados e ligados às decisões do brainstorm |
| Success | 3 | Critérios checáveis por grep, contraste numérico, gates e E2E |
| Scope | 3 | Fora de escopo explícito e alinhado à YAGNI do brainstorm |
| **Total** | **14/15** | |

---

## Open Questions

1. **Botão primário** (decisão de design, não bloqueia): o gradiente do ceath com texto branco não passa no AA. Proposta padrão para o /design: **fundo `accent` sólido (ou gradiente `#ff8619`→`#d75b08`) com texto `#050505`**, contraste 8,42:1 no sólido. A alternativa é manter o texto branco com gradiente escurecido (`#c2530a`→`#9d3a06`), a validar ≥ 4,5:1.
2. **A-001:** confirmar a Seção 2 do brainstorm ao revisar este documento.

Nenhuma bloqueia o Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-23 | define-agent | Versão inicial a partir de BRAINSTORM_TEMA_CEATH.md, com inventário medido e contrastes calculados |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_TEMA_CEATH.md`
