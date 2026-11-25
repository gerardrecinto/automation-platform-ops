#!/usr/bin/env bash
# Upgrade n8n to a new tag: back up, switch, wait for health, and roll back to the old tag if it does not come up.
set -euo pipefail
cd "$(dirname "$0")/.."
new=${1:?usage: scripts/upgrade.sh <n8n-tag>}
old=$(grep '^N8N_VERSION=' .env | cut -d= -f2)
[ "$new" != "$old" ] || { echo "already on $old"; exit 0; }
./scripts/backup.sh
setver() { sed -i.bak "s/^N8N_VERSION=.*/N8N_VERSION=$1/" .env && rm -f .env.bak; }
setver "$new"
if docker compose up -d --wait n8n worker; then
  echo "upgraded $old -> $new"
else
  echo "n8n $new did not become healthy; rolling back to $old"
  setver "$old"
  docker compose up -d --wait n8n worker
  echo "rolled back to $old. Database changes made by $new migrations are not undone; restore from the backup if the old version rejects them."
  exit 1
fi
