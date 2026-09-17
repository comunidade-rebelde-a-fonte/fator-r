#!/usr/bin/env bash
# Teste de restore em ambiente descartável (T-701). Não toca nos bancos em uso:
# restaura em bancos/diretórios temporários e compara contagens com a origem.
# Uso: infra/backup/testar_restore.sh <pasta-do-backup>
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PASTA="${1:?informe a pasta do backup}"
APP=(docker compose -f "$RAIZ/docker-compose.yml" --env-file "$RAIZ/.env")
LF=(docker compose -f "$RAIZ/infra/langfuse/docker-compose.langfuse.yml" --env-file "$RAIZ/infra/langfuse/.env")
set -a; . "$RAIZ/.env"; . "$RAIZ/infra/langfuse/.env"; set +a

( cd "$PASTA" && shasum -a 256 -c SHA256SUMS >/dev/null ) && echo "checksums OK"

TABELAS="companies monthly_movements agent_traces pgdas_documents simulations evals_human"
contar() {
  local banco="$1" saida=""
  for t in $TABELAS; do
    saida+="$t=$("${APP[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$banco" -tAc "SELECT count(*) FROM $t") "
  done
  echo "$saida"
}

"${APP[@]}" exec -T db psql -U "$POSTGRES_USER" -d postgres -qc "DROP DATABASE IF EXISTS fator_r_restore_teste" -c "CREATE DATABASE fator_r_restore_teste"
"${APP[@]}" exec -T db pg_restore -U "$POSTGRES_USER" -d fator_r_restore_teste --no-owner < "$PASTA/app.dump"
ORIGEM="$(contar "$POSTGRES_DB")"
RESTAURADO="$(contar fator_r_restore_teste)"
echo "origem:     $ORIGEM"
echo "restaurado: $RESTAURADO"
"${APP[@]}" exec -T db psql -U "$POSTGRES_USER" -d postgres -qc "DROP DATABASE fator_r_restore_teste"
if [ "$ORIGEM" != "$RESTAURADO" ]; then
  echo "FALHA: contagens diferentes (backup antigo? rode backup e restore em seguida)"; exit 1
fi

"${LF[@]}" exec -T postgres psql -U postgres -qc "DROP DATABASE IF EXISTS langfuse_restore_teste" -c "CREATE DATABASE langfuse_restore_teste"
"${LF[@]}" exec -T postgres pg_restore -U postgres -d langfuse_restore_teste --no-owner < "$PASTA/langfuse-postgres.dump"
P_ORIG="$("${LF[@]}" exec -T postgres psql -U postgres -d postgres -tAc 'SELECT count(*) FROM projects')"
P_REST="$("${LF[@]}" exec -T postgres psql -U postgres -d langfuse_restore_teste -tAc 'SELECT count(*) FROM projects')"
"${LF[@]}" exec -T postgres psql -U postgres -qc "DROP DATABASE langfuse_restore_teste"
echo "langfuse postgres projects: origem=$P_ORIG restaurado=$P_REST"
if [ "$P_ORIG" != "$P_REST" ]; then echo "FALHA: Postgres do Langfuse"; exit 1; fi

# Senha via variável do próprio container (não aparece em ps/docker inspect do host).
ch() { "${LF[@]}" exec -T clickhouse sh -c 'clickhouse-client --user "$CLICKHOUSE_USER" --enable_full_text_index=1 --query "$1"' _ "$1"; }
"${LF[@]}" cp "$PASTA/langfuse-clickhouse.zip" clickhouse:/backups/restore-teste.zip
"${LF[@]}" exec -T -u 0 clickhouse chown 101:101 /backups/restore-teste.zip
ch "DROP DATABASE IF EXISTS restore_teste" >/dev/null
ch "RESTORE DATABASE default AS restore_teste FROM File('/backups/restore-teste.zip')" >/dev/null
C_ORIG="$(ch "SELECT sum(total_rows) FROM system.tables WHERE database = 'default' AND engine LIKE '%MergeTree'")"
C_REST="$(ch "SELECT sum(total_rows) FROM system.tables WHERE database = 'restore_teste' AND engine LIKE '%MergeTree'")"
ch "DROP DATABASE restore_teste" >/dev/null
"${LF[@]}" exec -T clickhouse rm -f /backups/restore-teste.zip
echo "clickhouse (linhas em todas as tabelas): origem=$C_ORIG restaurado=$C_REST"
if [ "$C_REST" -eq 0 ] || [ "$C_REST" -gt "$C_ORIG" ]; then
  echo "FALHA: restore do ClickHouse sem dados"; exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT  # extratos de clientes nunca ficam em /tmp se o script falhar
tar -C "$TMP" -xzf "$PASTA/uploads.tar.gz"
U_REST="$(find "$TMP/uploads" -type f | wc -l | tr -d ' ')"
U_ORIG="$("${APP[@]}" exec -T api sh -c 'find /data/uploads -type f | wc -l' | tr -d ' \r')"
echo "uploads: origem=$U_ORIG restaurado=$U_REST"
if [ "$U_ORIG" != "$U_REST" ]; then echo "FALHA: uploads"; exit 1; fi
echo "RESTORE OK"
