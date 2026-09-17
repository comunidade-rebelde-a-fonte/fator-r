# Plataforma Fator R

Monitoramento de Fator R do Simples Nacional para escritórios de contabilidade: cadastro
multi-empresa, série mensal, motor de cálculo determinístico, carteira com semáforo, inbox do
extrato PGDAS-D, simulador de correção, agentes (parser, consultor, priorizador) e observabilidade
com Langfuse self-hosted.

> Esta plataforma não é a apuração oficial. O PGDAS-D da Receita Federal prevalece.

- Produto: [`docs/prd.md`](docs/prd.md)
- Implementação e **Registro de decisões**: [`docs/plan.md`](docs/plan.md)
- Tarefas e aceites: [`docs/tasks.md`](docs/tasks.md)
- Contrato de execução (regras para quem desenvolve): [`CLAUDE.md`](CLAUDE.md)

## Arquitetura em uma frase

`apps/web` (Next.js 16) conversa por cookie de sessão com `apps/api` (FastAPI). A api usa
Postgres com RLS por escritório e calcula tudo em `domain/` (Python puro, `Decimal`). O Claude só
classifica o pedido e redige o texto a partir de decisões já calculadas. Toda corrida de agente tem
trace local e no Langfuse, com o mesmo `trace_id`.

## Pré-requisitos

| Ferramenta | Versão usada |
|---|---|
| Docker + Docker Compose | 29 / v5 |
| Python + [uv](https://docs.astral.sh/uv/) | 3.12 / 0.12 |
| Node + pnpm | 22+ / 10 |
| make, git | qualquer recente |
| Google Chrome | para o E2E (Playwright usa o Chrome instalado) |

Memória: aplicação ~1 GB; Langfuse (Postgres, ClickHouse, Redis, MinIO) ~4 GB a mais.

## Primeira execução (local)

```bash
cp .env.example .env                              # troque todos os change-me
cp infra/langfuse/.env.example infra/langfuse/.env  # idem (ENCRYPTION_KEY: openssl rand -hex 32)
# LANGFUSE_PUBLIC_KEY/SECRET_KEY do .env da raiz = os mesmos de infra/langfuse/.env

make up        # Langfuse + api + web + db
make migrate   # migrações (role dona) + habilita a role da aplicação (fator_r_app)
make seed      # escritório piloto + usuário + tabelas do Simples (idempotente)
```

- Web: http://localhost:3000 (usuário e senha: `SEED_USER_EMAIL` / `SEED_USER_PASSWORD` do `.env`)
- API: http://localhost:`API_PORT` (`/health`; não há `/docs` público)
- Langfuse: http://localhost:3100 (`LANGFUSE_ADMIN_EMAIL` / `LANGFUSE_ADMIN_PASSWORD` de
  `infra/langfuse/.env`; cadastro aberto desativado)

### Variáveis principais (`.env`)

| Variável | Para quê |
|---|---|
| `ENV` | `dev` local. **Sem valor, a api assume `prod`** (cookie Secure, sem rotas de dev) |
| `POSTGRES_*` | role dona do banco (migrações e seed) |
| `APP_DB_USER` / `APP_DB_PASSWORD` | role da aplicação, sujeita a RLS |
| `API_PORT`, `WEB_PORT`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS` | portas e origem do web |
| `SEED_*`, `SEED_CARGA_PASSWORD` | usuário do seed e do escritório de carga |
| `LANGFUSE_*` | chaves e endereços do Langfuse local |
| `ANTHROPIC_API_KEY` | Claude. Vazia em dev: agentes usam classificador por palavras e templates |
| `LLM_PROVIDER` | `anthropic` ou `fake` (só dev/test; usado no E2E) |
| `FORWARDED_ALLOW_IPS` | IP/rede do proxy reverso em produção (IP real do cliente no rate limit) |

## Comandos

| Comando | O que faz |
|---|---|
| `make up` / `make down` | sobe/derruba Langfuse + aplicação (volumes preservados) |
| `make migrate` / `make seed` | migrações / seed idempotente |
| `make seed-carga` | escritório separado com 200 empresas × 24 meses |
| `make lint` | ruff, mypy `--strict`, eslint, prettier, `tsc` |
| `make test` | pytest da api (sem perf e sem Langfuse) |
| `make test-perf` | carteira com 200 empresas (< 1 s) |
| `make test-langfuse` | integração com o Langfuse local (exige `make up-langfuse`) |
| `make e2e` | **aceite da v1**: recria o banco local, sobe com `LLM_PROVIDER=fake`, roda o Playwright (um teste por item da PRD §13) e confere os traces no Langfuse |
| `make parser-experiment` | dataset `pgdas_extratos` + experimento do parser no Langfuse |
| `make api-types` | regenera os tipos TypeScript do web a partir do OpenAPI da api |
| `make backup` | backup completo em `./backups` com rotação |
| `make backup-teste-restore` | restaura o último backup em bancos descartáveis e compara contagens |

Para rodar só a api ou só o web fora do Docker: `cd apps/api && uv run uvicorn fator_r.main:app`
e `cd apps/web && pnpm dev` (ajuste `DATABASE_URL`/`NEXT_PUBLIC_API_URL`).

## Testes e qualidade

- **Unitários/integração da api**: `make test`. Usam o banco `fator_r_test` (criado e migrado
  automaticamente) com a role da aplicação, para exercitar o RLS de verdade. O Anthropic é sempre
  simulado.
- **Isolamento entre escritórios**: `tests/api/test_isolation.py` percorre todas as rotas pelo
  schema OpenAPI; rota nova sem cenário registrado faz o teste falhar.
- **Parser**: `pytest tests/parsing` contra `apps/api/fixtures/pgdas/` (hoje só fixtures
  sintéticas; ver pendências).
- **E2E**: `make e2e` (apaga os dados do banco local de dev).

## Langfuse

- Self-hosted, projeto `dev`, SDK Python v4. Nunca usar Langfuse Cloud.
- Spans por corrida: `plan → parse/tool → decide → render`; tags `agente`, `gatilho`,
  `firm:<id>`. Scores `gold_<campo>`, `gold_acerto`, `human_eval`.
- O que não vai para o Langfuse: texto do PDF, CNPJ/CPF (mascarados), lista de empresas.
- Retenção: o projeto não tem `retentionDays` (ilimitado). A PRD pede 24 meses ou mais.
- A UI do Langfuse mostra traces de **todos** os escritórios: acesso só para administradores.
- Se o Langfuse cair, os agentes continuam; o trace local fica `langfuse_sync=failed` e um job
  reenvia o resumo a cada 5 min.

## Backup e restore

`infra/backup/backup.sh` gera, por execução, `app.dump`, `langfuse-postgres.dump`,
`langfuse-clickhouse.zip` (BACKUP nativo), `uploads.tar.gz` e `SHA256SUMS`, mantendo 7 diários,
4 semanais e 12 mensais. Exemplo de agendamento (cron do host, 02:30):

```cron
30 2 * * * cd /caminho/Fator-R && infra/backup/backup.sh >> /var/log/fator-r-backup.log 2>&1
```

`make backup-teste-restore` valida o último backup: restaura em bancos temporários (Postgres da
aplicação e do Langfuse, ClickHouse) e compara contagens e arquivos com a origem.

## Deploy (exigências antes de produção)

1. `ENV=prod`, `ANTHROPIC_API_KEY` definida e `LLM_PROVIDER=anthropic`.
2. Proxy reverso com TLS na frente de web e api, com `FORWARDED_ALLOW_IPS` apontando para ele e
   limite de corpo também no proxy (ex.: `client_max_body_size 11m`).
3. Portas de banco, Redis e ClickHouse sem exposição externa (o compose já as prende em
   `127.0.0.1`).
4. Acesso à UI do Langfuse restrito a administradores.
5. Backups cifrados (age/gpg) antes de sair da máquina; restore testado periodicamente.
6. Revisar os riscos aceitos no Registro de decisões de 2026-09-17 (`docs/plan.md`).

## Pendências conhecidas (ver `docs/tasks.md`)

| Item | Bloqueio |
|---|---|
| P-03 / T-504 / T-508 | extratos PGDAS-D reais anonimizados para medir o parser de verdade |
| P-04 / T-201 | conferir o CSV das faixas dos Anexos III e V contra a LC 123/2006 |
| P-05 / T-203 | regra de proporcionalização para empresa com menos de 12 meses (hoje: `dados_insuficientes`) |
| P-06 | servidor de produção e acessos ao Langfuse |
| P-07 / T-205 | planilha manual de referência (2 empresas × 12 meses × 2 PAs) |
| T-707 | conferência de uma empresa real contra o extrato PGDAS-D |
| M6 | tokens e custo reais do Claude no Langfuse (falta `ANTHROPIC_API_KEY`) |
