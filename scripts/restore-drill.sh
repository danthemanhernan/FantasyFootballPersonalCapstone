#!/usr/bin/env bash
set -euo pipefail

backup_file="${1:?usage: scripts/restore-drill.sh BACKUP.dump}"
test_db="fantasy_hud_restore_drill"

LC_ALL=C shasum -a 256 -c "$backup_file.sha256"
docker compose -f infra/dev/docker-compose.yml exec -T postgres \
  dropdb -U fantasy_hud --if-exists "$test_db"
docker compose -f infra/dev/docker-compose.yml exec -T postgres \
  createdb -U fantasy_hud "$test_db"
docker compose -f infra/dev/docker-compose.yml exec -T postgres \
  pg_restore -U fantasy_hud -d "$test_db" --exit-on-error < "$backup_file"
docker compose -f infra/dev/docker-compose.yml exec -T postgres \
  psql -U fantasy_hud -d "$test_db" -c \
  "SELECT COUNT(*) AS migration_count FROM schema_migrations;"
docker compose -f infra/dev/docker-compose.yml exec -T postgres \
  dropdb -U fantasy_hud "$test_db"
printf 'restore drill passed: %s\n' "$backup_file"
