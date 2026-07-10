#!/usr/bin/env sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$BACKUP_DIR/healthos-$timestamp.dump"

docker compose exec -T postgres pg_dump \
  --username healthos \
  --dbname healthos \
  --format custom \
  --no-owner \
  --no-privileges > "$output"

test -s "$output"
echo "$output"
