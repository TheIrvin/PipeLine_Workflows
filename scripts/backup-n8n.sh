#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VOLUME="pipeline_workflows_n8n_data"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="pipeline-backup-${STAMP}.tar.gz"
mkdir -p backups
docker volume inspect "$VOLUME" >/dev/null
restart_services() { docker compose start >/dev/null; }
trap restart_services EXIT
docker compose stop
docker run --rm --network none \
  -e BACKUP_FILE="$ARCHIVE" \
  -v "$VOLUME:/source-n8n:ro" \
  -v "$ROOT/data:/source-data:ro" \
  -v "$ROOT/backups:/backup" \
  -v "$ROOT/.env:/source-env:ro" \
  alpine:3.22 sh -c 'mkdir -p /tmp/snapshot/n8n /tmp/snapshot/project-data /tmp/snapshot/private-config && cp -a /source-n8n/. /tmp/snapshot/n8n/ && cp -a /source-data/. /tmp/snapshot/project-data/ && cp /source-env /tmp/snapshot/private-config/.env && tar -czf "/backup/$BACKUP_FILE" -C /tmp/snapshot .'
printf 'Backup creado: %s/backups/%s\n' "$ROOT" "$ARCHIVE"
