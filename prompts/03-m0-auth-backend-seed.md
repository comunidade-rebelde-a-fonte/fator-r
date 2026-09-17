# 03 — M0 · Auth no backend e seed (T-008 a T-011)

Branch sugerida: `feat/m0-fundacao`

## Contexto
- `docs/tasks.md` → T-008, T-009, T-010, T-011.
- `docs/plan.md` → §2.1 (auth), §4 (`firms`, `users`, `sessions`), §2.2-6 (política de CPP).
- `CLAUDE.md` → §5.3 (endpoints sem auth só `/health` e `/auth/login`), §10.1.
- **P-02 (política de CPP):**
  - se estiver resolvido, use o valor decidido no seed;
  - se não, **pare antes de T-011** e pergunte. Posso autorizar um valor provisório, e aí você registra no "Registro de decisões".

## Execute (ciclo §8 por tarefa)
1. **T-008:** migração Alembic de `firms` (com `meta_operacional`, `limiar_confianca_parser`, `piso_economia_anual`, `cpp_das_integra_fs12`, `tolerancia_ouro_pct`, tipos `numeric` da Plano §4), `users` e `sessions`. IDs UUID.
2. **T-009:**
   - `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`;
   - argon2 para senha;
   - token aleatório de 32+ bytes, com só o hash no banco;
   - cookie httpOnly, SameSite=Lax e Secure fora de dev;
   - expiração configurável;
   - rate limit simples por IP e e-mail no login;
   - mensagem de erro genérica (não revela se o e-mail existe).
3. **T-010:** dependência/middleware que resolve a sessão, injeta `user` e `firm_id` e devolve 401 por padrão. As únicas rotas públicas são `/health` e `/auth/login`.
4. **T-011:**
   - `make seed` idempotente: 1 escritório com os padrões do plano (0,30 / 0,40 / 6000 / CPP conforme P-02 / tolerância) e 1 usuário;
   - a senha do usuário vem do env, não do código.

## Testes obrigatórios
- Login certo, senha errada, usuário inativo, sessão expirada, logout invalida o token.
- Rota protegida sem cookie devolve 401.
- Rate limit bloqueia depois de N tentativas.

## Gates
`make lint`, `make test`, e `make down && make up && make migrate && make seed` do zero, duas vezes seguidas (idempotência).

## Pronto quando
T-008 a T-011 `[x]` e o relatório da etapa 7 entregue.
