#!/usr/bin/env bash
# Create .env with random secrets on first run, then start the stack and wait until healthy.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\nN8N_ENCRYPTION_KEY=%s\nN8N_VERSION=1.78.1\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 24)" > .env
  ./scripts/ledger.sh POSTGRES_PASSWORD N8N_ENCRYPTION_KEY
  echo "created .env (mode 600). Back up N8N_ENCRYPTION_KEY: without it, saved credentials cannot be decrypted after a restore."
fi
docker compose up -d --wait
echo "n8n: http://127.0.0.1:5678"
