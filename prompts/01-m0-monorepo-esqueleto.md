# 01 — M0 · Monorepo e esqueletos (T-001 a T-004)

Branch sugerida (só se eu pedir commit): `feat/m0-fundacao`

## Contexto
- `docs/tasks.md` → M0: T-001, T-002, T-003, T-004.
- `docs/plan.md` → §2.1 (stack), §3 e §3.1 (estrutura).
- `CLAUDE.md` → §8 (ciclo), §10.1 e §10.2 (convenções).

## Execute
Siga o ciclo do `CLAUDE.md` §8 para **cada** tarefa, em ordem. Pule as que já estiverem `[x]`.

1. **T-001:**
   - monorepo com `apps/api`, `apps/web`, `infra/langfuse`, `Makefile` (mínimo, completado no prompt 02), `.editorconfig`, `.gitignore` e `.env.example`;
   - o `.gitignore` cobre `.env`, `/data`, `node_modules`, `.venv`, caches e `fixtures/pgdas/real/`.
2. **T-002 (api):**
   - projeto `uv` em `apps/api` com layout `src/fator_r/{core,api,domain,parsing,agents,tracing,repositories}`;
   - FastAPI com `GET /health`;
   - settings Pydantic v2 lidas do ambiente;
   - engine SQLAlchemy 2 async;
   - Alembic configurado (sem migrações ainda);
   - ruff, mypy `--strict` e pytest com um teste de `/health`.
3. **T-003 (web):**
   - Next.js App Router + TypeScript estrito, Tailwind, TanStack Query;
   - cliente HTTP com `credentials: "include"` e base URL por env;
   - página inicial placeholder;
   - eslint, prettier e `tsc --noEmit`.
4. **T-004 (compose):**
   - `docker-compose.yml` com `db` (Postgres 16 com healthcheck), `api` e `web`;
   - volume nomeado montado em `/data/uploads` só no container `api`, fora de qualquer pasta pública do web.

## Regras críticas
- Nenhum segredo real: só `.env.example` com placeholders.
- Não antecipe auth, modelos ou telas: isso é dos prompts 03 e 04.
- Só dependências previstas em `CLAUDE.md` §4.3, mais tooling de lint e test.

## Gates
- `uv run ruff check`, `uv run ruff format --check`, `uv run mypy --strict src` e `uv run pytest` em `apps/api`.
- `lint`, `tsc --noEmit` e `build` em `apps/web`.
- `docker compose up -d` sobe os três serviços; `curl localhost:<porta>/health` devolve 200.

## Pronto quando
T-001 a T-004 `[x]` com a checklist do `CLAUDE.md` §6.1 completa e o relatório da etapa 7 entregue.
