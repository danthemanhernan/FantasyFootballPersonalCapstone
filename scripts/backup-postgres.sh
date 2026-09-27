#!/usr/bin/env bash
set -euo pipefail

backup_dir="${1:-./backups}"
mkdir -p "$backup_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$backup_dir/fantasy_hud_$timestamp.dump"

docker compose -f infra/dev/docker-compose.yml exec -T postgres \
  pg_dump -U fantasy_hud -d fantasy_hud --format=custom > "$output"
LC_ALL=C shasum -a 256 "$output" > "$output.sha256"
printf '%s\n' "$output"
