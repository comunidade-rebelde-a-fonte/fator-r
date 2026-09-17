# Fator R — comandos do projeto (ver CLAUDE.md §7).
SHELL := /bin/bash
.DEFAULT_GOAL := help

APP_COMPOSE := docker compose
LF_COMPOSE  := docker compose --env-file infra/langfuse/.env -f infra/langfuse/docker-compose.langfuse.yml
API_DIR     := apps/api
WEB_DIR     := apps/web

.PHONY: help up down up-app up-langfuse migrate seed seed-carga test test-perf test-langfuse lint e2e api-types parser-experiment backup backup-teste-restore

help: ## Lista os alvos
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

up: up-langfuse up-app ## Sobe Langfuse + aplicação (api, web, db)

up-app: ## Sobe só a aplicação
	@test -f .env || { echo "Crie o .env a partir do .env.example"; exit 1; }
	$(APP_COMPOSE) up -d --build

up-langfuse: ## Sobe só o Langfuse local
	@test -f infra/langfuse/.env || { echo "Crie infra/langfuse/.env a partir do .env.example"; exit 1; }
	$(LF_COMPOSE) up -d
	@echo "Aguardando Langfuse..."; for i in $$(seq 1 60); do curl -sf localhost:$${LANGFUSE_WEB_PORT:-3100}/api/public/health >/dev/null && { echo "Langfuse OK"; exit 0; }; sleep 3; done; echo "Langfuse não respondeu"; exit 1

down: ## Derruba aplicação e Langfuse (volumes preservados)
	$(APP_COMPOSE) down
	$(LF_COMPOSE) down

OWNER_URL = postgresql+asyncpg://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@db:5432/$${POSTGRES_DB}

migrate: ## Aplica migrações (role dona) e habilita a role da aplicação
	set -a && . ./.env && set +a && $(APP_COMPOSE) run --rm --build \
		-e DATABASE_OWNER_URL="$(OWNER_URL)" -e APP_DB_PASSWORD \
		api sh -c "alembic upgrade head && python -m fator_r.db_roles"

seed: ## Popula escritório e usuário iniciais (idempotente; SEED_* no .env)
	set -a && . ./.env && set +a && $(APP_COMPOSE) run --rm --build \
		-e DATABASE_OWNER_URL="$(OWNER_URL)" \
		-e SEED_FIRM_NOME -e SEED_USER_EMAIL -e SEED_USER_NOME -e SEED_USER_PASSWORD \
		api python -m fator_r.seed

seed-carga: ## Escritório separado com 200 empresas × 24 meses (teste de performance)
	set -a && . ./.env && set +a && $(APP_COMPOSE) run --rm --build \
		-e DATABASE_OWNER_URL="$(OWNER_URL)" -e SEED_CARGA_PASSWORD api python -m fator_r.seed_carga

backup: ## Backup (app, Langfuse Postgres + ClickHouse, uploads) em ./backups com rotação
	infra/backup/backup.sh

backup-teste-restore: ## Restaura o backup mais recente em bancos descartáveis e compara contagens
	infra/backup/testar_restore.sh "$$(ls -1d backups/diario/*/ | sort | tail -1)"

test: ## Testes da api (pytest; sem perf e langfuse)
	cd $(API_DIR) && uv run pytest

test-langfuse: ## Integração com o Langfuse local (exige make up-langfuse)
	cd $(API_DIR) && uv run pytest -m langfuse

parser-experiment: ## Dataset pgdas_extratos + experimento do parser no Langfuse local
	set -a && . infra/langfuse/.env && set +a && cd $(API_DIR) && \
		LANGFUSE_HOST=http://localhost:$${LANGFUSE_WEB_PORT:-3100} LANGFUSE_TRACING_ENABLED=true ENV=dev \
		uv run python scripts/parser_experiment.py

test-perf: ## Teste de performance da carteira
	cd $(API_DIR) && uv run pytest -m perf -s

lint: ## Lint, formatação e tipos (api + web)
	cd $(API_DIR) && uv run ruff check src tests alembic scripts && uv run ruff format --check src tests alembic scripts && uv run mypy --strict src
	cd $(WEB_DIR) && pnpm lint && pnpm format:check && pnpm typecheck

api-types: ## Gera tipos TS do web a partir do OpenAPI da api
	cd $(API_DIR) && uv run python scripts/export_openapi.py ../web/lib/api/openapi.json
	cd $(WEB_DIR) && pnpm gen:api && pnpm exec prettier --write lib/api >/dev/null

e2e: ## Aceite da v1 em ambiente limpo: Playwright (PRD §13) + traces no Langfuse (T-706)
	@echo "Ambiente limpo: banco da aplicação local recriado (dados de dev serão apagados)."
	$(APP_COMPOSE) down -v
	$(MAKE) up-langfuse
	LLM_PROVIDER=fake $(APP_COMPOSE) up -d --build
	@set -a && . ./.env && set +a && for i in $$(seq 1 60); do \
		curl -sf "localhost:$${API_PORT}/health" >/dev/null 2>&1 && break; sleep 2; done
	$(MAKE) migrate
	$(MAKE) seed
	set -a && . ./.env && set +a && cd $(WEB_DIR) && E2E_API_URL=$${NEXT_PUBLIC_API_URL} pnpm exec playwright test
	cd $(API_DIR) && uv run pytest -m e2e_langfuse
