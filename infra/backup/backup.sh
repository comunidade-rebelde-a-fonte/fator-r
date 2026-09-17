#!/usr/bin/env bash
# Backup diário da Plataforma Fator R (T-701).
#   - Postgres da aplicação (pg_dump -Fc)
#   - Postgres do Langfuse (pg_dump -Fc)
#   - ClickHouse do Langfuse (BACKUP DATABASE nativo)
#   - Uploads do PGDAS-D (tar.gz)
# Rotação: 7 diários, 4 semanais (domingo), 12 mensais (dia 1).
# Uso: infra/backup/backup.sh [DESTINO]   (padrão: ./backups; agendar via cron/systemd)
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESTINO="${1:-${BACKUP_DIR:-$RAIZ/backups}}"
CARIMBO="$(date +%Y%m%dT%H%M%S)"
PASTA="$DESTINO/diario/$CARIMBO"
APP=(docker compose -f "$RAIZ/docker-compose.yml" --env-file "$RAIZ/.env")
LF=(docker compose -f "$RAIZ/infra/langfuse/docker-compose.langfuse.yml" --env-file "$RAIZ/infra/langfuse/.env")

set -a; . "$RAIZ/.env"; . "$RAIZ/infra/langfuse/.env"; set +a
umask 077
mkdir -p "$PASTA"

log() { printf '[backup %s] %s\n' "$(date +%H:%M:%S)" "$*"; }

log "Postgres da aplicação"
"${APP[@]}" exec -T db pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$PASTA/app.dump"

log "Postgres do Langfuse"
"${LF[@]}" exec -T postgres pg_dump -U postgres -Fc postgres > "$PASTA/langfuse-postgres.dump"

log "ClickHouse do Langfuse"
ARQUIVO_CH="langfuse-clickhouse-$CARIMBO.zip"
# O volume de backups nasce do root; o ClickHouse roda como uid 101.
"${LF[@]}" exec -T -u 0 clickhouse chown 101:101 /backups
# Senha lida da variável CLICKHOUSE_PASSWORD já presente no container (fora da linha de comando).
"${LF[@]}" exec -T clickhouse sh -c 'clickhouse-client --user "$CLICKHOUSE_USER" --query "$1"' _ \
  "BACKUP DATABASE default TO File('/backups/$ARQUIVO_CH')" >/dev/null
"${LF[@]}" cp "clickhouse:/backups/$ARQUIVO_CH" "$PASTA/langfuse-clickhouse.zip"
"${LF[@]}" exec -T clickhouse rm -f "/backups/$ARQUIVO_CH"

log "Uploads"
"${APP[@]}" exec -T api tar -C /data -czf - uploads > "$PASTA/uploads.tar.gz"

( cd "$PASTA" && shasum -a 256 ./* > SHA256SUMS )

if [ "$(date +%u)" = "7" ]; then mkdir -p "$DESTINO/semanal" && cp -R "$PASTA" "$DESTINO/semanal/"; fi
if [ "$(date +%d)" = "01" ]; then mkdir -p "$DESTINO/mensal" && cp -R "$PASTA" "$DESTINO/mensal/"; fi

rotacionar() {
  local dir="$1" manter="$2"
  [ -d "$dir" ] || return 0
  # Portável (BSD/GNU): mantém os $manter mais recentes.
  ls -1d "$dir"/*/ 2>/dev/null | sort \
    | awk -v k="$manter" '{a[NR]=$0} END {for (i = 1; i <= NR - k; i++) print a[i]}' \
    | while read -r antigo; do
    rm -rf -- "$antigo"
  done
}
rotacionar "$DESTINO/diario" 7
rotacionar "$DESTINO/semanal" 4
rotacionar "$DESTINO/mensal" 12

log "OK: $PASTA ($(du -sh "$PASTA" | cut -f1))"
