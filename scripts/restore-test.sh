#!/usr/bin/env bash
# Prove the newest backup restores: load it into a scratch database and compare row counts with the live one.
# A backup that has never been restored is a hope, not a backup.
set -euo pipefail
cd "$(dirname "$0")/.."
dump=$(ls -t backups/n8n-*.dump | head -1)
psql() { docker compose exec -T postgres psql -U n8n -tA "$@"; }
psql -d postgres -c "DROP DATABASE IF EXISTS restore_test" >/dev/null
psql -d postgres -c "CREATE DATABASE restore_test" >/dev/null
docker compose exec -T postgres pg_restore -U n8n -d restore_test --no-owner < "$dump"
ok=1
for t in workflow_entity user; do
  live=$(psql -d n8n -c "SELECT count(*) FROM \"$t\"")
  rest=$(psql -d restore_test -c "SELECT count(*) FROM \"$t\"")
  echo "$t: live=$live restored=$rest"
  [ "$live" = "$rest" ] || ok=0
done
psql -d postgres -c "DROP DATABASE restore_test" >/dev/null
mkdir -p backups
printf '{"backup":"%s","at":"%s","passed":%s}\n' "$dump" "$(date -u +%Y%m%dT%H%M%SZ)" "$([ $ok = 1 ] && echo true || echo false)" > backups/restore-test.json
[ $ok = 1 ] && echo "PASS restore of $dump" || { echo "FAIL restore of $dump"; exit 1; }
