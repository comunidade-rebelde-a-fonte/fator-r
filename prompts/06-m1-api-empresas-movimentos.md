# 06 — M1 · API de empresas e movimentos + isolamento (T-106, T-107, T-110)

Branch sugerida: `feat/m1-cadastro-movimentos`

## Contexto
- `docs/tasks.md` → T-106, T-107, T-110.
- `docs/prd.md` → §7.2 (cadastro), §7.3 (movimentos).
- `docs/plan.md` → §8 (API).
- `CLAUDE.md` → §3.4, §3.6, §3.13, §5.4 (desativação lógica), §10.1 (erros de domínio → 4xx).

## Execute (ciclo §8 por tarefa)
1. **T-106:**
   - `GET /companies` (filtros `ativo`, `sujeita_fator_r`, busca por nome/CNPJ, paginação), `POST /companies`, `GET /companies/{id}`, `PATCH /companies/{id}`;
   - CNPJ validado e normalizado;
   - CNPJ duplicado no escritório devolve 409;
   - "excluir" = `PATCH ativo=false`; não existe `DELETE`.
2. **T-107:**
   - `GET /companies/{id}/movements?de=YYYY-MM&ate=YYYY-MM`;
   - `PUT /companies/{id}/movements/{competencia}` (upsert por empresa + competência, `origem=manual`, valores ≥ 0, `observacao` opcional);
   - a resposta traz `folha_mes`.
3. **T-110 — isolamento:**
   - fixture com escritórios A e B, cada um com usuário, empresas e movimentos;
   - teste **parametrizado sobre todas as rotas** do app (gerado a partir do router, para cobrir rotas futuras automaticamente): o usuário A recebe 404 em qualquer recurso do B, e listagens de A nunca contêm dados de B;
   - nome dos testes contém `isolation`.

## Regras críticas
- Recurso de outro escritório responde **404**, não 403, para não revelar a existência.
- Schemas Pydantic com `Decimal` na entrada; serialização monetária como string decimal.
- Não criar endpoint de Fator R aqui (é o prompt 10).

## Gates
`make lint`, `make test`, `pytest apps/api/tests/api -k isolation`.

## Pronto quando
T-106, T-107 e T-110 `[x]` e o relatório da etapa 7 entregue.
