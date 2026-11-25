#!/usr/bin/env bash
# Rotate the PostgreSQL password: change it in the database, update .env, restart the services, and record it in the ledger.
set -euo pipefail
cd "$(dirname "$0")/.."
new=$(openssl rand -hex 16)
docker compose exec -T postgres psql -U n8n -d n8n -v ON_ERROR_STOP=1 -c "ALTER USER n8n PASSWORD '$new'" >/dev/null
sed -i.bak "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$new/" .env && rm -f .env.bak
docker compose up -d --wait
./scripts/ledger.sh POSTGRES_PASSWORD
echo "rotated POSTGRES_PASSWORD; n8n and worker restarted with the new value"
