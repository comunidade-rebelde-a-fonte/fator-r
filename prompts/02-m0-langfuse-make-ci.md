# 02 — M0 · Langfuse local, Makefile e CI (T-005 a T-007)

Branch sugerida: `feat/m0-fundacao`

## Contexto
- `docs/tasks.md` → T-005, T-006, T-007.
- `docs/plan.md` → §7.1 (Langfuse self-hosted).
- `CLAUDE.md` → §5.3 (sem Langfuse Cloud), §7 (gates).
- Pré-requisito P-06 (servidor): não bloqueia o ambiente **local**; só registre se ainda estiver pendente.

## Execute (ciclo §8 por tarefa)
1. **T-005:**
   - `infra/langfuse/docker-compose.langfuse.yml` com `langfuse-web`, `langfuse-worker`, `postgres`, `clickhouse`, `redis` e `minio` (bucket criado no start);
   - todas as senhas via `infra/langfuse/.env` (commitar só o `.env.example`);
   - `LANGFUSE_INIT_*` criando org, projeto `dev` e chaves públicas/secretas locais;
   - portas internas ligadas em `127.0.0.1`;
   - consulte a documentação atual do Langfuse (context7) antes de fixar imagens e variáveis.
2. **T-006 (`Makefile`):**
   - `up` e `down` (app + Langfuse), `migrate`, `seed`, `test`, `lint`, `e2e`;
   - alvos ainda sem implementação real falham com mensagem clara ("disponível a partir de T-xxx"), nunca passam em silêncio.
3. **T-007 (GitHub Actions):**
   - job api: uv, ruff, mypy e pytest com serviço Postgres 16;
   - job web: install, lint, typecheck e build;
   - sem segredos no workflow.

## Regras críticas
- Langfuse **self-hosted** apenas. Nada de chave de Langfuse Cloud.
- As portas do Langfuse não podem conflitar com api, web e db do prompt 01.

## Gates
- `make up` sobe app + Langfuse; a UI do Langfuse abre e aceita login com o usuário do `LANGFUSE_INIT_*`.
- `make lint` e `make test` passam.
- Workflow validado com `actionlint`, se disponível; senão, revisão manual do YAML.

## Pronto quando
T-005 a T-007 `[x]`, relatório com as portas usadas e o passo a passo de acesso ao Langfuse local.
