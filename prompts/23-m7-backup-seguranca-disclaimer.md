# 23 — M7 · Backup, retenção, segurança e disclaimer (T-701 a T-704)

Branch sugerida: `feat/m7-endurecimento`
Pré-condição: M6 fechado.

## Contexto
- `docs/tasks.md` → T-701 a T-704.
- `docs/prd.md` → §8 (retenção de 24 meses, backup diário, segurança, conformidade).
- `docs/plan.md` → §4 (retenção), §7.1 (Langfuse self-hosted).
- `CLAUDE.md` → §5.3, §5.4 (nada destrutivo fora do ambiente local), §3.14, §7 (gate de segurança obrigatório no M7).

## Execute (ciclo §8 por tarefa)
1. **T-701 — backup:**
   - script `infra/backup/backup.sh` com `pg_dump` da app, `pg_dump` do Postgres do Langfuse, backup do ClickHouse (método oficial atual — consulte a doc) e tar de `/data/uploads`;
   - destino configurável, rotação (7 diários, 4 semanais, 12 mensais);
   - agendável via cron/systemd timer (documentar, **não** instalar em servidor remoto sem pedido);
   - **teste de restore** num ambiente local descartável: subir banco vazio, restaurar e conferir contagens de empresas, movimentos, traces e documentos.
2. **T-702 — retenção:**
   - varrer o código atrás de qualquer `DELETE` ou expurgo em traces, movimentos e documentos (não pode existir);
   - configurar e documentar a retenção do projeto Langfuse ≥ 24 meses.
3. **T-703 — segurança:**
   - revisar upload (magic bytes, traversal, tamanho), CSRF (SameSite + checagem de `Origin` em métodos mutáveis) e headers (`CSP`, `X-Frame-Options`, `Referrer-Policy`, `HSTS` fora de dev);
   - varredura de segredos no repositório (ex.: `gitleaks`, se disponível);
   - logs sem CNPJ ou valores de cliente;
   - rodar `/security-review`; achados altos corrigidos nesta tarefa, médios e baixos listados.
4. **T-704 — disclaimer:** teste automatizado que visita todas as rotas autenticadas do web e confirma o disclaimer; teste de API que confirma o disclaimer em 100% das respostas de agente.

## Não pode
- Rodar backup, restore ou cron em servidor real sem pedido explícito.
- Apagar dados para "testar" retenção.

## Gates
`make lint`, `make test`, `/security-review`, restore local verificado.

## Pronto quando
T-701 a T-704 `[x]` e o relatório com: evidência do restore (contagens antes e depois), resultado do security review e da varredura de segredos.
