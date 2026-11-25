#!/usr/bin/env bash
# Whole run: start, create an owner and a workflow through the API, back up, restore into a scratch DB, check the evidence.
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/up.sh
docker compose cp workflows/demo.json n8n:/tmp/demo.json >/dev/null
docker compose exec -T n8n n8n import:workflow --input=/tmp/demo.json >/dev/null
./scripts/backup.sh
./scripts/restore-test.sh
python3 -m platformcheck harden compose.yaml
python3 -m platformcheck evidence --backups backups --compose compose.yaml
