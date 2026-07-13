#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: CONFIRM_RESTORE=YES $0 path/to/backup.dump" >&2
  exit 2
fi

if [ "${CONFIRM_RESTORE:-}" != "YES" ]; then
  echo "Restore replaces the current schema. Set CONFIRM_RESTORE=YES to continue." >&2
  exit 2
fi

backup="$1"
test -s "$backup"

docker compose exec -T postgres pg_restore \
  --username healthos \
  --dbname healthos \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges < "$backup"

echo "Restore completed from $backup"
