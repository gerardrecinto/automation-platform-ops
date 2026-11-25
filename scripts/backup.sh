#!/usr/bin/env bash
# Logical backup of the n8n database plus an export of workflows, with a manifest that records time, size and sha256.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
ts=$(date -u +%Y%m%dT%H%M%SZ)
dump="backups/n8n-$ts.dump"
docker compose exec -T postgres pg_dump -U n8n -d n8n -Fc > "$dump"
sha=$(shasum -a 256 "$dump" | cut -d' ' -f1)
size=$(wc -c < "$dump" | tr -d ' ')
python3 - "$dump" "$ts" "$sha" "$size" <<'P'
import json, os, sys
dump, ts, sha, size = sys.argv[1:]
path = "backups/manifest.json"
m = json.load(open(path)) if os.path.exists(path) else []
m.append({"file": dump, "taken_at": ts, "sha256": sha, "bytes": int(size)})
json.dump(m, open(path, "w"), indent=2)
P
echo "backup: $dump ($size bytes)"
