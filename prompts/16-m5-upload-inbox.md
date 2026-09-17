# 16 — M5 · Upload e armazenamento do PGDAS-D (T-501 a T-503)

Branch sugerida: `feat/m5-inbox-parser`
Pré-condição: M4 fechado (M3 recomendado).

## Contexto
- `docs/tasks.md` → T-501, T-502, T-503.
- `docs/prd.md` → §7.6 (fluxo, persistência, status), §8 (segurança: PDF/TXT, fora da web root).
- `docs/plan.md` → §4 (`pgdas_documents`), §6.
- `CLAUDE.md` → §5.3 (upload, URL pública), §3.13.

## Execute (ciclo §8 por tarefa)
1. **T-501:**
   - migração `pgdas_documents` (único `(firm_id, sha256)`, `trace_id NOT NULL`, enum de status, `firm_id` + RLS);
   - FK de `monthly_movements.pgdas_document_id` numa migração **nova**.
2. **T-502 — `POST /inbox/pgdas` (multipart):**
   - aceita só `application/pdf` (magic bytes `%PDF-`) e `text/plain` (UTF-8 ou Latin-1 decodificável, sem bytes nulos); a extensão é ignorada como critério;
   - tamanho máximo `UPLOAD_MAX_MB` (padrão 10) aplicado em streaming;
   - hash sha256 em streaming;
   - grava em `/data/uploads/{firm_id}/{sha256}` com nome derivado só do hash (sem nome do usuário no path) e permissão 0600;
   - duplicado devolve o documento existente (200) sem gravar de novo;
   - cria o registro `received` dentro de um `tracer.run(agente="parser_pgdas", gatilho="upload")`. O parse em si é do prompt 18: por ora o run termina em `received`.
3. **T-503:**
   - `GET /inbox/{id}/arquivo` autenticado, com `Content-Disposition: attachment` e `X-Content-Type-Options: nosniff`;
   - `GET /inbox` e `GET /inbox/{id}` básicos.

## Testes obrigatórios
- PDF renomeado para `.txt` e vice-versa, executável renomeado para `.pdf` (recusado), arquivo acima do limite.
- Tentativa de path traversal no nome do arquivo.
- Duplicado.
- Isolamento: B não baixa arquivo de A.
- O arquivo não é acessível por nenhuma rota do web.

## Gates
`make lint`, `make test`, isolamento, migração do zero.

## Pronto quando
T-501 a T-503 `[x]` e o relatório com a lista de validações de upload testadas.
