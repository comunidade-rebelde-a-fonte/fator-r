# DESIGN: Tema visual inspirado no ceath.io

> Technical design for implementing TEMA_CEATH

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TEMA_CEATH |
| **Date** | 2026-09-23 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_TEMA_CEATH.md](./DEFINE_TEMA_CEATH.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ apps/web (só frontend; apps/api intocado)                                │
│                                                                          │
│  app/fonts.ts ──(next/font/google, baixado no build, servido em          │
│                  /_next/static/media → CSP font-src 'self' já cobre)     │
│        │ --font-inter / --font-oswald                                    │
│        ▼                                                                 │
│  app/layout.tsx  <html class={inter.variable oswald.variable}>           │
│        │                                                                 │
│        ▼                                                                 │
│  app/globals.css                                                         │
│   ├─ @theme { --color-*: initial; ...tokens ceath... }  ← ÚNICA fonte    │
│   │     (zera a paleta padrão: zinc/red/... deixam de existir)           │
│   └─ @layer base { border-color=line, color-scheme dark, foco accent,    │
│                    tabular-nums em table, body bg/fg/font }              │
│        │ utilitários: bg-base bg-panel text-fg text-muted border-line    │
│        │              text-accent bg-danger/12 font-display ...          │
│        ▼                                                                 │
│  components/ui/  (primitivos)                                            │
│   Botao · Painel · Campo · Tabela · TituloPagina · Badge* · Estado*      │
│        │                                  (* já existem; só restyle)     │
│        ▼                                                                 │
│  Telas (app/(app)/**, app/(auth)/login) + componentes de domínio         │
│   trocam classes fixas → tokens/primitivos. Zero mudança de texto,       │
│   data-testid, role, rota ou fluxo.                                      │
│                                                                          │
│  Cabeçalho: app/(app)/layout.tsx (server) ──<Marca/> (server, fs)──┐     │
│             └─ components/AppShell.tsx ("use client", lógica atual) ◄┘   │
│                                                                          │
│  Guarda: scripts/verificar-tema.mjs no `pnpm lint` (make lint)           │
│          → falha se aparecer classe de paleta fixa                       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Tokens (`globals.css`) | Paleta ceath, fontes e regras base num só lugar | Tailwind v4 `@theme`, `@layer base` |
| Fontes (`app/fonts.ts`) | Inter (corpo) e Oswald (display) self-hosted | `next/font/google` (Next 16) |
| `Botao` + `classesBotao()` | Ação primária, secundária, fantasma e perigo. Função de classes para `<Link>` e `<label>`. | React + TS |
| `Painel` | Superfície (card/section) com `panel`, borda `line` e raio | React |
| `Campo` (`classesCampo`) | Classes de `input`/`select`/`textarea` com borda 3:1 e fundo `panel-2` | Constante TS |
| `Tabela` + `CabecalhoTabela` | `<table>` e `<thead>` no padrão do tema (linhas `line`, cabeçalho `muted` em maiúsculas) | React |
| `TituloPagina` | Eyebrow opcional, `h1` Oswald maiúsculo e slot de ações | React |
| `Badge` (existente) | Mesma API (`cor`). Só o mapa `CORES` muda para tons translúcidos com borda. | React |
| `Estado` (existente) | `Carregando`, `Vazio`, `Erro` com tokens. `data-testid` mantido. | React |
| `Marca` | "Fator R" em Oswald ou `public/brand/logo.svg`, se existir | Server component (`node:fs`) |
| `AppShell` | Lógica atual do layout autenticado (sessão, logout, nav), movida sem mudança | Client component |
| `verificar-tema.mjs` | Gate: nenhuma classe de paleta fixa em `app/` e `components/` | Node puro, sem dependência |

---

## Key Decisions

### Decision 1: Tokens direto em `@theme`, com paleta padrão zerada

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-23 |

**Context:** O DEFINE (SC-3) pede tokens em `:root` expostos via `@theme inline`. No Tailwind v4, `@theme { --color-x: ... }` já emite `--color-x` em `:root` e gera os utilitários. A indireção `:root` → `@theme inline` só serviria para alternar temas, e isso está fora de escopo.

**Choice:** Um bloco `@theme` com `--color-*: initial;` (remove zinc, red, white etc.) seguido dos tokens ceath e das fontes.

**Rationale:** Um lugar só. Classe de paleta esquecida deixa de gerar estilo, e o gate de lint (Decision 8) acusa a sobra. Satisfaz a intenção do SC-3: variáveis em `:root` e utilitários funcionando.

**Alternatives Rejected:**
1. `:root` + `@theme inline` (texto literal do SC-3): duplica cada token sem ganho, porque não haverá troca de tema.
2. Manter a paleta padrão: permite regressão silenciosa (`text-zinc-500` volta em tarefa futura).

**Consequences:**
- `bg-white`, `text-black` e cores padrão deixam de existir. Tarefas futuras usam só tokens.
- `transparent`, `current` e `inherit` continuam disponíveis (não vêm do tema). O build confirma.

---

### Decision 2: Nomes dos tokens (utilitários legíveis)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-23 |

**Context:** Os nomes `bg` e `text` do DEFINE gerariam `bg-bg` e `text-text`.

**Choice:**

| Token DEFINE | Variável | Valor | Utilitário típico |
|---|---|---|---|
| `bg` | `--color-base` | `#050505` | `bg-base` |
| `panel` | `--color-panel` | `#090909` | `bg-panel` |
| `panel-2` | `--color-panel-2` | `#0c0a09` | `bg-panel-2` |
| `line` | `--color-line` | `rgba(255,255,255,.09)` | `border-line` (padrão global) |
| — (novo) | `--color-line-strong` | `#6b655f` | `border-line-strong` (campos; 3,44:1 sobre `panel-2`) |
| `text` | `--color-fg` | `#f4f0eb` | `text-fg` |
| `muted` | `--color-muted` | `#aaa39c` | `text-muted` |
| `accent` | `--color-accent` | `#ff8619` | `bg-accent`, `text-accent`, `border-accent/60` |
| `accent-soft` | `--color-accent-soft` | `#ffb15a` | `hover:bg-accent-soft`, `text-accent-soft` |
| — (novo) | `--color-on-accent` | `#050505` | `text-on-accent` (texto sobre `accent`) |
| `danger` | `--color-danger` | `#ff293d` | `border-danger/60`, `bg-danger/12` |
| `danger-soft` | `--color-danger-soft` | `#ff6672` | `text-danger-soft` (todo texto de erro) |
| `ok` | `--color-ok` | `#3ddc84` | `text-ok`, `bg-ok/12` |
| `eyebrow` | `--color-eyebrow` | `#e8b47e` | `text-eyebrow` |
| — (novo) | `--color-info` | `#8fb7e8` | `Badge cor="azul"` (9,58:1) |
| — (novo) | `--color-extra` | `#c4a1ff` | `Badge cor="roxo"` (9,38:1) |

**Rationale:** Nomes semânticos e curtos. `info` e `extra` existem porque os usos atuais de `azul` e `roxo` distinguem categorias (resolve **A-005**):
- `azul`: pacote Monitoramento, origem `pgdas`, doc `parsed`, "sujeita a Fator R".
- `roxo`: pacote Correção, origem `agente`.

Fundir essas cores com neutro ou `accent` apagaria a distinção entre pacotes e origens na carteira e na grade. Os dois tons são frios e dessaturados e não competem com o semáforo.

**Alternatives Rejected:**
1. `azul`/`roxo` → neutro: perde a distinção de pacote e origem, que tem significado de negócio (pacotes comerciais da carteira).
2. `azul` → `accent`: colide com o semáforo "amarelo".

**Consequences:** Dois tons fora da paleta do ceath (como o verde `ok`). Ficam registrados no Registro de decisões.

---

### Decision 3: Fontes via `next/font/google` com variáveis CSS

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-23 |

**Context:** A-003/A-004. A doc local do Next 16 (`node_modules/next/dist/docs/01-app/01-getting-started/13-fonts.md`) confirma: *"Fonts are included as static assets and served from the same domain … no requests are sent to Google by the browser"*. O download acontece no build. O `Dockerfile` já precisa de rede no build (`pnpm install`).

**Choice:** `app/fonts.ts` exporta `inter` e `oswald`, ambas variáveis (sem `weight`), `subsets: ["latin"]` (cobre acentos do pt-BR), `display: "swap"`, `variable: "--font-inter" | "--font-oswald"`. O `<html>` recebe as duas `.variable`. `@theme` define `--font-sans` e `--font-display`.

**Rationale:** Zero requisição externa em runtime (§5.3). A CSP atual (`font-src 'self'`) já cobre. Nenhuma dependência nova.

**Alternatives Rejected:**
1. `<link>` para Google Fonts: viola §5.3 e a CSP.
2. `next/font/local` com `.woff2` versionados: só se o build ficar sem rede. Fica como plano B documentado (troca só o `app/fonts.ts`).

**Consequences:** A-003 e A-004 validadas. A primeira build baixa cerca de 100 KB de fontes, que ficam em cache no `.next`.

---

### Decision 4: Botão primário com fundo `accent` sólido e texto `on-accent`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted (padrão do DEFINE; o usuário não escolheu alternativa) |
| **Date** | 2026-09-23 |

**Context:** O gradiente do ceath com texto branco tem 2,42:1 (falha AA).

**Choice:**
- **primário:** `bg-accent text-on-accent hover:bg-accent-soft`, `rounded-[4px]`, maiúsculas, `tracking-[.055em]`, `font-bold`, `text-xs`.
- **secundário:** borda `accent/65`, fundo `accent/5`, hover `accent/12`, texto `fg`.
- **fantasma:** borda `line-strong`, texto `fg`, hover `panel-2`.
- **perigo:** borda `danger/60`, texto `danger-soft`, hover `danger/10`.

**Rationale:** 8,42:1 (normal) e 11,34:1 (hover). A forma sólida e retangular em maiúsculas diferencia o botão do selo translúcido "amarelo" (AT-003).

**Alternatives Rejected:**
1. Gradiente escurecido com texto branco: perde o tom laranja vivo da marca, e o contraste no topo fica no limite.
2. Gradiente do ceath original: falha AA.

**Consequences:** Reverter é trocar uma linha em `classesBotao`.

---

### Decision 5: Regra base de borda, `color-scheme` e foco

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-23 |

**Context:** No Tailwind v4, `border` sem cor usa `currentColor`. Há cerca de 40 usos de `border`, `border-b` e `border-t` sem cor (linhas de tabela, cartões). No escuro, todos ficariam em `#f4f0eb`, gritantes. Inputs nativos (`select`, `date`) e barras de rolagem ficariam claros sem `color-scheme`.

**Choice:** Em `@layer base`:
- `border-color: var(--color-line)` global;
- `color-scheme: dark` no `html`;
- `:focus-visible` com `outline` de 2px `accent` e `offset` de 2px (8,42:1 ≥ 3:1, SC-5);
- `table { font-variant-numeric: tabular-nums }` (AT-013);
- `::selection` em `accent/35`;
- links com `text-decoration-color: accent`.

**Rationale:** Resolve dezenas de ocorrências sem tocar cada uma. O foco fica consistente sem classe por elemento.

**Consequences:** Onde a borda precisa de destaque (campos), o primitivo aplica `border-line-strong` explicitamente.

---

### Decision 6: Logo opcional via server component + `AppShell`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-23 |

**Context:** `app/(app)/layout.tsx` é `"use client"` (usa `useMe` e o router). Um client component não consegue testar se `public/brand/logo.svg` existe sem gerar 404 no console (AT-010 proíbe).

**Choice:**
- Mover o corpo atual do layout, **sem alterar lógica**, para `components/AppShell.tsx` (`"use client"`), com a prop `marca: ReactNode`.
- `app/(app)/layout.tsx` vira server component: `return <AppShell marca={<Marca />}>{children}</AppShell>`.
- `Marca` (server) usa `existsSync(path.join(process.cwd(), "public/brand/logo.svg"))`. Com logo, renderiza `<img src="/brand/logo.svg" alt="Fator R" className="h-7 w-auto" />`. Sem logo, renderiza `<span className="font-display text-lg tracking-wide uppercase">Fator <span className="text-accent">R</span></span>`.

**Rationale:** Nenhum 404 e nenhuma flag de configuração. No Docker standalone, `public/` é copiado para `/app/public` e o `cwd` é `/app`. A CSP `img-src 'self'` cobre.

**Alternatives Rejected:**
1. `<img onError>` com fallback: gera 404 no console.
2. Variável `NEXT_PUBLIC_LOGO`: configuração extra para algo que o arquivo já expressa.

**Consequences:**
- Em produção, um logo adicionado exige rebuild ou restart (a página pode ser pré-renderizada). Em dev, basta recarregar.
- O texto "Fator R" do cabeçalho deixa de ser um nó de texto único ("Fator " + "R" em span). O conteúdo textual continua "Fator R", e nenhum E2E seleciona esse texto (verificado por grep no build).

---

### Decision 7: Primitivos com nomes em português e mudança mínima nas telas

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-23 |

**Context:** O DEFINE listou `Button/Card/Input/Tabela/PageHeader`. O repo nomeia componentes de UI em português (`Estado`, `Carregando`, `Vazio`, `Erro`, `GradeMensal`, `EmConstrucao`).

**Choice:** `Botao`, `Painel`, `classesCampo`, `Tabela`/`CabecalhoTabela`, `TituloPagina`. `Badge` mantém nome e API (`cor: cinza|azul|verde|amarelo|vermelho|roxo`), então `SemaforoBadge`, `StatusDocumentoBadge`, `StatusTraceBadge`, `Badges.tsx` e os usos inline **não mudam**.

**Rationale:** Consistência com o código existente. Não mexer nos mapas de status evita qualquer risco de mudar rótulo ou semântica de domínio.

**Consequences:** As telas trocam `className` de `<button>`, `<input>`, `<table>` e `<h1>` pelos primitivos, ou recebem classes de token direto quando o elemento é peculiar (`<label>` de upload, célula da grade).

---

### Decision 8: Gate automático contra regressão de paleta

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-23 |

**Context:** SC-1 e SC-2 precisam valer também depois desta entrega.

**Choice:** `apps/web/scripts/verificar-tema.mjs` (Node puro) percorre `app/` e `components/` (`.ts`/`.tsx`) com a regex do SC-1 mais `(bg|text|border)-(white|black)\b`. Lista `arquivo:linha` e sai com código 1 se achar algo. O script `lint` do `package.json` vira `eslint && node scripts/verificar-tema.mjs`. O `make lint` já chama `pnpm lint`.

**Rationale:** Gate falho = gate que não roda (CLAUDE.md §7). Sem dependência nova.

**Alternatives Rejected:** Regra ESLint customizada: mais código e configuração para o mesmo efeito.

---

## Class Mapping (referência para o build)

| Hoje | Novo | Observação |
|---|---|---|
| `text-zinc-500`, `text-zinc-600`, `text-zinc-400` | `text-muted` | |
| `text-zinc-700` | `text-fg` | nav inativa usa `text-muted hover:text-fg` |
| `border-zinc-200`, `border-zinc-300` (cartões) | `border-line` (ou só `border`) | |
| `border-zinc-300` em input/select/textarea | `classesCampo` | `border-line-strong bg-panel-2` |
| `bg-zinc-900 text-white` (botão) | `<Botao>` / `classesBotao()` | `variante="primario"` |
| `rounded border px-* py-*` (botão sem cor) | `<Botao variante="fantasma">` | |
| `bg-zinc-900 text-white` (filtro ativo, nav ativa) | `bg-accent/12 text-fg border-accent/60` | nav: `border-b-2 border-accent` (inset do ceath) |
| `bg-zinc-100`, `bg-zinc-50` | `bg-panel-2` | |
| `text-red-700`, `text-red-800` | `text-danger-soft` | |
| `border-red-*`, `bg-red-50/100` | `border-danger/50`, `bg-danger/12` | |
| `text-emerald-700`, `text-emerald-800` | `text-ok` | |
| `bg-emerald-100` | `bg-ok/12` | |
| `text-amber-700/800/900` | `text-accent-soft` | avisos (motivo, aviso-inss, CPP) |
| `bg-amber-50 border-amber-300` | `bg-accent/8 border-accent/40` | `CadastroPeloExtrato` |
| `border-sky-500 bg-sky-50` (arrastando) | `border-accent bg-accent/8` | dropzone do inbox |
| `bg-sky-50` (bolha do agente) | `bg-panel-2 border border-line` | analista: `bg-accent/8 border border-accent/25` |
| `h1.text-xl.font-semibold` | `<TituloPagina>` | `font-display text-3xl uppercase tracking-[-.01em] leading-none` |
| `h2.font-semibold` | `font-display text-lg tracking-wide uppercase` | seções (Movimentos, Fator R, Simulador) |
| `thead.border-b.text-xs.text-zinc-500.uppercase` | `<CabecalhoTabela>` | `text-muted text-[11px] tracking-[.1em]` |
| Números de destaque (Fator R %, RBT12, FS12 no `PainelFatorR`) | `font-display text-2xl` | células de tabela continuam em Inter |

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `apps/web/app/fonts.ts` | Create | Inter e Oswald via `next/font/google` | (general) | None |
| 2 | `apps/web/app/globals.css` | Modify | `@theme` (paleta zerada, tokens, fontes) e `@layer base` | (general) | 1 |
| 3 | `apps/web/app/layout.tsx` | Modify | Aplica `inter.variable oswald.variable` no `<html>` | (general) | 1, 2 |
| 4 | `apps/web/scripts/verificar-tema.mjs` | Create | Gate SC-1/SC-2 | (general) | None |
| 5 | `apps/web/package.json` | Modify | `lint`: `eslint && node scripts/verificar-tema.mjs` | (general) | 4 |
| 6 | `apps/web/components/ui/Botao.tsx` | Create | `Botao` e `classesBotao()` | (general) | 2 |
| 7 | `apps/web/components/ui/Painel.tsx` | Create | Superfície padrão | (general) | 2 |
| 8 | `apps/web/components/ui/Campo.ts` | Create | `classesCampo` | (general) | 2 |
| 9 | `apps/web/components/ui/Tabela.tsx` | Create | `Tabela` e `CabecalhoTabela` | (general) | 2 |
| 10 | `apps/web/components/ui/TituloPagina.tsx` | Create | `h1` Oswald, eyebrow e ações | (general) | 2 |
| 11 | `apps/web/components/ui/Badge.tsx` | Modify | Mapa `CORES` com tokens (API igual) | (general) | 2 |
| 12 | `apps/web/components/ui/Estado.tsx` | Modify | `Carregando`, `Vazio`, `Erro` com tokens | (general) | 2, 6 |
| 13 | `apps/web/components/Marca.tsx` | Create | Texto "Fator R" ou `public/brand/logo.svg` | (general) | 2 |
| 14 | `apps/web/components/AppShell.tsx` | Create | Corpo client do layout autenticado, movido sem mudança de lógica, restyled | (general) | 6, 13, 15, 16 |
| 15 | `apps/web/components/AppNav.tsx` | Modify | Nav em tokens (ativo `accent`) | (general) | 2 |
| 16 | `apps/web/components/Disclaimer.tsx` | Modify | `bg-panel`, `border-t border-accent/60`, `text-fg`. Texto e `data-testid` intactos. | (general) | 2 |
| 17 | `apps/web/app/(app)/layout.tsx` | Modify | Server: `<AppShell marca={<Marca/>}>` | (general) | 13, 14 |
| 18 | `apps/web/app/(auth)/login/page.tsx` | Modify | `Painel`, `classesCampo`, `Botao`. Título em Oswald. `radial-gradient` opcional (G9). | (general) | 6–8 |
| 19 | `apps/web/components/EmConstrucao.tsx` | Modify | `TituloPagina` e `text-muted` | (general) | 10 |
| 20 | `apps/web/app/(app)/carteira/page.tsx` | Modify | Título, filtros, tabela, textos de estado | (general) | 6–11 |
| 21 | `apps/web/app/(app)/empresas/page.tsx` | Modify | Título e ação "nova" (`classesBotao` no `Link`), filtros, tabela | (general) | 6–10 |
| 22 | `apps/web/app/(app)/empresas/nova/page.tsx` | Modify | `TituloPagina` (se houver `h1`) | (general) | 10 |
| 23 | `apps/web/app/(app)/empresas/[id]/page.tsx` | Modify | Título, seções, `Painel` | (general) | 7, 10 |
| 24 | `apps/web/app/(app)/empresas/[id]/editar/page.tsx` | Modify | `TituloPagina` (se houver `h1`) | (general) | 10 |
| 25 | `apps/web/components/empresas/EmpresaForm.tsx` | Modify | `classesCampo` (erro de CNPJ `border-danger`, somente leitura `bg-panel`), `Botao`, avisos | (general) | 6, 8 |
| 26 | `apps/web/components/empresas/GradeMensal.tsx` | Modify | Campos compactos, tabela, "salvo" `text-ok`, erro `text-danger-soft` | (general) | 8, 9 |
| 27 | `apps/web/components/fator-r/PainelFatorR.tsx` | Modify | Números em `font-display`, mapa faltante/preenchido/fora em tokens, `Painel` | (general) | 7, 8 |
| 28 | `apps/web/components/simulador/Simulador.tsx` | Modify | `classesCampo`, `Botao`, aviso INSS, tabela histórico | (general) | 6, 8, 9 |
| 29 | `apps/web/app/(app)/inbox/page.tsx` | Modify | Dropzone, `<label>` upload (`classesBotao`), filtros, tabela | (general) | 6, 9, 10 |
| 30 | `apps/web/app/(app)/inbox/[id]/page.tsx` | Modify | Motivo, mensagem, campos, `Botao` primário e perigo | (general) | 6, 8 |
| 31 | `apps/web/components/inbox/CadastroPeloExtrato.tsx` | Modify | Caixa de destaque `accent/8`, `Botao` | (general) | 6 |
| 32 | `apps/web/app/(app)/agentes/page.tsx` | Modify | Título, select, tabela | (general) | 8–10 |
| 33 | `apps/web/components/agentes/Chat.tsx` | Modify | Bolhas, campo, `Botao` | (general) | 6, 8 |
| 34 | `apps/web/app/(app)/observabilidade/page.tsx` | Modify | Título, filtros, tabela | (general) | 8–10 |
| 35 | `apps/web/app/(app)/observabilidade/traces/[id]/page.tsx` | Modify | Formulário de nota (`Painel`, `classesCampo`, `Botao`), textos de estado | (general) | 6–10 |
| 36 | `docs/plan.md` | Modify | Entrada no "Registro de decisões" (§13) | (general) | 1–35 |
| 37 | `.claude/sdd/reports/BUILD_REPORT_TEMA_CEATH.md` | Create | Relatório do build com gates e evidências | (general) | 36 |

**Total Files:** 37 (9 novos, 28 modificados). Sem mudança: `SemaforoBadge.tsx`, `StatusDocumentoBadge.tsx`, `StatusTraceBadge.tsx`, `empresas/Badges.tsx`, `app/page.tsx`, `next.config.ts`, `Dockerfile`, `e2e/**`, `apps/api/**`.

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| (general) | 1–37 | `.claude/agents/` não tem especialista de frontend React/Tailwind. O build executa direto. |
| @code-reviewer | revisão final | Conferir que nenhuma mudança alterou texto, `data-testid`, `role` ou lógica (diff só de `className` e estrutura do layout) |

---

## Code Patterns

### Pattern 1: `app/fonts.ts`

```ts
import { Inter, Oswald } from "next/font/google";

export const inter = Inter({ subsets: ["latin"], display: "swap", variable: "--font-inter" });
export const oswald = Oswald({ subsets: ["latin"], display: "swap", variable: "--font-oswald" });
```

`app/layout.tsx`: `<html lang="pt-BR" className={`${inter.variable} ${oswald.variable} h-full antialiased`}>`

### Pattern 2: `app/globals.css`

```css
@import "tailwindcss";

/* Tema único do app (identidade ceath.io). Registro de decisões 2026-09-23. */
@theme {
  --color-*: initial;

  --color-base: #050505;
  --color-panel: #090909;
  --color-panel-2: #0c0a09;
  --color-line: rgba(255, 255, 255, 0.09);
  --color-line-strong: #6b655f;
  --color-fg: #f4f0eb;
  --color-muted: #aaa39c;
  --color-eyebrow: #e8b47e;
  --color-accent: #ff8619;
  --color-accent-soft: #ffb15a;
  --color-on-accent: #050505;
  --color-danger: #ff293d;
  --color-danger-soft: #ff6672;
  --color-ok: #3ddc84;
  --color-info: #8fb7e8;
  --color-extra: #c4a1ff;

  --font-sans: var(--font-inter), system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-display: var(--font-oswald), Impact, sans-serif;
}

@layer base {
  *,
  ::before,
  ::after,
  ::backdrop,
  ::file-selector-button {
    border-color: var(--color-line);
  }
  html {
    color-scheme: dark;
  }
  body {
    background: var(--color-base);
    color: var(--color-fg);
    font-family: var(--font-sans);
  }
  :focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
  ::selection {
    background: color-mix(in srgb, var(--color-accent) 35%, transparent);
  }
  ::placeholder {
    color: var(--color-muted);
  }
  a {
    text-decoration-color: var(--color-accent);
    text-underline-offset: 3px;
  }
  table {
    font-variant-numeric: tabular-nums;
  }
}
```

### Pattern 3: `components/ui/Botao.tsx`

```tsx
import type { ButtonHTMLAttributes } from "react";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-[4px] border px-3 py-1.5 text-xs font-bold tracking-[.055em] uppercase transition-colors disabled:cursor-not-allowed disabled:opacity-60";

const VARIANTES = {
  primario: "border-accent bg-accent text-on-accent hover:bg-accent-soft",
  secundario: "border-accent/65 bg-accent/5 text-fg hover:bg-accent/12",
  fantasma: "border-line-strong text-fg hover:bg-panel-2",
  perigo: "border-danger/60 text-danger-soft hover:bg-danger/10",
} as const;

export type VarianteBotao = keyof typeof VARIANTES;

/** Classes do botão, para `<Link>` e `<label>` que precisam parecer botão. */
export function classesBotao(variante: VarianteBotao = "primario", extra = ""): string {
  return `${BASE} ${VARIANTES[variante]} ${extra}`.trim();
}

export function Botao({
  variante = "primario",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variante?: VarianteBotao }) {
  return <button type={type} className={classesBotao(variante, className)} {...props} />;
}
```

> **Atenção no build:** cada `<button>` existente mantém o `type` que tem hoje (`submit` nos formulários). O padrão `type="button"` só vale onde hoje não há `type` explícito **e** o botão não está dentro de um `<form>`. Se houver dúvida, passar o `type` atual explicitamente.

### Pattern 4: `Campo`, `Painel`, `Tabela`, `TituloPagina`

```ts
// components/ui/Campo.ts
export const classesCampo =
  "block w-full rounded-[4px] border border-line-strong bg-panel-2 px-2 py-1.5 text-fg";
```

```tsx
// components/ui/Painel.tsx
import type { HTMLAttributes } from "react";

export function Painel({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-[10px] border border-line bg-panel p-4 shadow-[0_20px_60px_-30px_rgba(0,0,0,.8),inset_0_1px_0_rgba(255,255,255,.04)] ${className}`}
      {...props}
    />
  );
}
```

```tsx
// components/ui/Tabela.tsx
import type { HTMLAttributes, TableHTMLAttributes } from "react";

export function Tabela({ className = "", ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return <table className={`w-full text-left text-sm ${className}`} {...props} />;
}

export function CabecalhoTabela({ className = "", ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={`border-b text-[11px] tracking-[.1em] text-muted uppercase ${className}`}
      {...props}
    />
  );
}
```

```tsx
// components/ui/TituloPagina.tsx
import type { ReactNode } from "react";

export function TituloPagina({
  children,
  eyebrow,
  acoes,
}: {
  children: ReactNode;
  eyebrow?: string;
  acoes?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="mb-2 flex items-center gap-2.5 text-[11px] font-extrabold tracking-[.18em] text-eyebrow uppercase before:h-px before:w-8 before:bg-accent">
            {eyebrow}
          </p>
        )}
        <h1 className="font-display text-3xl leading-none tracking-[-.01em] uppercase">{children}</h1>
      </div>
      {acoes}
    </div>
  );
}
```

> `TituloPagina` preserva o `<h1>` e o texto: `getByRole("heading", { name })` continua funcionando. A caixa alta é só CSS.

### Pattern 5: `Badge` (mesma API)

```tsx
const CORES = {
  cinza: "border-line-strong/60 bg-fg/5 text-muted",
  azul: "border-info/40 bg-info/12 text-info",
  verde: "border-ok/40 bg-ok/12 text-ok",
  amarelo: "border-accent/50 bg-accent/12 text-accent",
  vermelho: "border-danger/50 bg-danger/12 text-danger-soft",
  roxo: "border-extra/40 bg-extra/12 text-extra",
} as const;
// span: "inline-block rounded-full border px-2 py-0.5 text-xs font-medium" + CORES[cor]
```

Selo sem maiúsculas (o texto do selo é lido em frase: "Vermelho · < 28% (Anexo V)"). Forma de pílula com borda. O botão é retangular, sólido e em maiúsculas (AT-003).

### Pattern 6: `Marca` + `AppShell`

```tsx
// components/Marca.tsx (server component)
import { existsSync } from "node:fs";
import path from "node:path";

const LOGO = "/brand/logo.svg";

export function Marca() {
  if (existsSync(path.join(process.cwd(), "public", LOGO))) {
    // eslint-disable-next-line @next/next/no-img-element -- SVG local e opcional; next/image não agrega aqui
    return <img src={LOGO} alt="Fator R" className="h-7 w-auto" />;
  }
  return (
    <span className="font-display text-lg tracking-wide uppercase">
      Fator <span className="text-accent">R</span>
    </span>
  );
}
```

```tsx
// app/(app)/layout.tsx (server)
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { Marca } from "@/components/Marca";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell marca={<Marca />}>{children}</AppShell>;
}
```

`components/AppShell.tsx` recebe `{ marca, children }` e contém **exatamente** a lógica atual (`useMe`, redirect 401, `sair`, `Carregando`, erro com "Tentar de novo"). Mudam só:
- `<span className="font-semibold">Fator R</span>` → `{marca}`;
- as classes: header `h-16 border-b bg-base px-6`; botão "Sair" `<Botao variante="fantasma">`; `main` com `p-6`.

### Pattern 7: `scripts/verificar-tema.mjs`

```js
// Gate do tema (Registro de decisões 2026-09-23): nenhuma cor fixa fora dos tokens do globals.css.
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const RAIZES = ["app", "components"];
const PROIBIDO = new RegExp(
  String.raw`\b(bg|text|border|ring|divide|outline|from|to|fill|stroke|placeholder)-(zinc|gray|slate|neutral|stone|red|amber|green|emerald|yellow|blue|orange|sky|indigo|rose|violet|lime|teal|cyan|purple|pink|fuchsia)-\d+|\b(bg|text|border)-(white|black)\b`,
);

function* arquivos(dir) {
  for (const nome of readdirSync(dir)) {
    const caminho = path.join(dir, nome);
    if (statSync(caminho).isDirectory()) yield* arquivos(caminho);
    else if (/\.(tsx?|css)$/.test(nome)) yield caminho;
  }
}

const achados = [];
for (const raiz of RAIZES) {
  for (const arquivo of arquivos(raiz)) {
    readFileSync(arquivo, "utf8")
      .split("\n")
      .forEach((linha, i) => {
        if (PROIBIDO.test(linha)) achados.push(`${arquivo}:${i + 1}: ${linha.trim()}`);
      });
  }
}

if (achados.length) {
  console.error(`Cor fora do tema (use os tokens de app/globals.css):\n${achados.join("\n")}`);
  process.exit(1);
}
```

---

## Data Flow

```text
1. Build: next/font baixa Inter e Oswald → /_next/static/media (self-hosted)
   │
   ▼
2. Request: layout raiz aplica --font-inter/--font-oswald no <html>
   │
   ▼
3. globals.css: @theme gera utilitários de token; @layer base pinta body, bordas e foco
   │
   ▼
4. (app)/layout (server) resolve <Marca/> (fs) → AppShell (client) valida sessão como hoje
   │
   ▼
5. Telas renderizam com primitivos. Nenhum dado, cálculo ou texto muda.
   │
   ▼
6. Disclaimer (componente único) fixo no rodapé em todas as rotas
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Google Fonts | Só no **build** (`next/font/google`). Nenhuma chamada do navegador. | N/A |
| API Fator R | Inalterada | Inalterada (cookie de sessão) |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Gate de tema | SC-1, SC-2 | `scripts/verificar-tema.mjs` | `pnpm lint` / `make lint` | 0 achados |
| Lint + tipos + formato | Todo o web | — | `make lint` (eslint, verificar-tema, prettier --check, `tsc --noEmit`) | Verde |
| Regressão E2E | Fluxos da v1 e cadastro pelo extrato | `e2e/aceite-v1.spec.ts`, `e2e/cadastro-pelo-extrato.spec.ts` (**não editar**) | `make e2e` | 100% verde. `git diff --stat apps/web/e2e` vazio. |
| Build de produção | Fontes self-hosted, server component `Marca` | — | `pnpm build` (e `docker compose build web`) | Build ok |
| Contraste | SC-4, SC-5 | Tabela de tokens (DEFINE) + Decision 2/4/5 | Fórmula WCAG já calculada. Conferir no DevTools (Accessibility → Contrast) em botão, selo e campo. | Todos ≥ 4,5:1 (texto) e ≥ 3:1 (borda de campo, foco) |
| Fontes locais | SC-6, AT-009 | — | DevTools → Network, filtro `font` | Só `/_next/static/media/*` |
| Visual manual | AT-001…AT-013, SC-9 | As 12 rotas do AT-007 | Navegador contra a API local com seed. Print por tela. Estados vazio e erro (API parada), carregando. | Todas as telas |
| Logo | AT-010, AT-011 | `public/brand/logo.svg` (temporário, só para o teste; não versionar se não for fornecido) | Navegador + console | Sem 404. Troca texto ↔ logo. |
| Revisão do diff | G5 | Todos | @code-reviewer + `git diff` | Só `className`, imports de primitivos e o split `AppShell` |

**Sem testes unitários novos no web:** o projeto não tem runner de unidade no frontend. Adicionar vitest seria dependência nova só para classes CSS (YAGNI). O gate de tema cobre a regra verificável.

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Build sem rede (fontes) | Falha visível no `pnpm build`. Plano B: `next/font/local` com `.woff2` em `app/fonts/` (troca só `fonts.ts`). | Não |
| `logo.svg` ausente | `Marca` renderiza o texto. Sem 404. | N/A |
| `logo.svg` inválido ou corrompido | O navegador mostra o `alt="Fator R"`. Aceitável: arquivo é do usuário. | N/A |
| Classe de paleta esquecida | `verificar-tema.mjs` quebra o `make lint` com `arquivo:linha` | N/A |
| Utilitário removido por `--color-*: initial` usado em algum lugar (ex.: `bg-transparent`) | Confirmar no build. Se algum utilitário necessário sumir, declarar o token no `@theme` | N/A |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `public/brand/logo.svg` | arquivo (opcional) | ausente | Se existir, substitui o texto "Fator R" no cabeçalho |
| Tokens `--color-*` / `--font-*` | CSS (`app/globals.css`) | valores da Decision 2 | Única fonte do tema |

---

## Security Considerations

- Nenhuma requisição do navegador a terceiros: fontes self-hosted. CSP inalterada (`font-src 'self'`, `img-src 'self' data:`).
- `Marca` lê só um caminho fixo do disco (`public/brand/logo.svg`). Nenhum input do usuário entra no caminho.
- Nenhum endpoint, dado de cliente ou log novo.
- `Disclaimer` preservado (§3.14): mesmo texto, `role="contentinfo"`, `data-testid`, fixo.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | N/A (mudança só visual) |
| Metrics | N/A |
| Tracing | N/A. Langfuse e agentes intocados. |

---

## Governança (entrada para `docs/plan.md` §13)

```markdown
### 2026-09-23 — Tema visual do web inspirado no ceath.io
- Contexto: pedido do usuário para aplicar o estilo de https://ceath.io/ ao sistema. Não havia tarefa em `docs/tasks.md` nem tokens de tema (148 classes de cor fixas em 21 arquivos).
- Decisão: tema escuro único com tokens em `apps/web/app/globals.css` (paleta padrão do Tailwind zerada), fontes Inter e Oswald via `next/font` (self-hosted), primitivos em `components/ui/` e gate `scripts/verificar-tema.mjs` no `pnpm lint`. Semáforo nas cores da marca (vermelho `#ff293d`, amarelo `#ff8619`, verde `#3ddc84`), sempre com texto. Tons `info` (`#8fb7e8`) e `extra` (`#c4a1ff`) para pacotes e origens. Botão primário com texto escuro sobre laranja sólido (o gradiente do ceath com texto branco falha no WCAG AA). Logo opcional em `public/brand/logo.svg`.
- Aprovado por: Alfredo
- Impacto: só `apps/web` (sem mudança de comportamento, texto ou teste). Tarefas futuras de UI usam os tokens e primitivos. Classe de paleta fixa quebra o `make lint`. Artefatos: `.claude/sdd/features/{BRAINSTORM,DEFINE,DESIGN}_TEMA_CEATH.md`.
```

---

## Build Order

1. Arquivos 1–5: fundação e gate. Rodar `pnpm build` para confirmar fontes e `--color-*: initial`. O gate **vai falhar** até o fim, e isso é esperado.
2. Arquivos 6–13: primitivos e `Marca`.
3. Arquivos 14–17: shell, nav e disclaimer. Conferir sessão, logout e redirect 401 no navegador.
4. Arquivos 18–35: telas, uma por vez, conferindo no navegador.
5. Gates: `make lint` → `make e2e` → conferência visual (SC-9) → contraste (SC-4/5) → Network (SC-6).
6. Arquivos 36–37: registro de decisão e relatório.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-23 | design-agent | Versão inicial a partir de DEFINE_TEMA_CEATH.md. Resolve A-003, A-004 e A-005. Fecha a Open Question 1 com o padrão (texto escuro sobre `accent`). |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_TEMA_CEATH.md`
