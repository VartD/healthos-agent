#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 path/to/backup.dump" >&2
  exit 2
fi

backup="$1"
test -s "$backup"

docker compose exec -T postgres pg_restore --list < "$backup" >/dev/null
echo "Backup archive is readable: $backup"
