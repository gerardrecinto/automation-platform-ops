#!/usr/bin/env bash
# Append "secret X was set now" to backups/rotations.json. Only names and times are stored, never values.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
python3 - "$@" <<'P'
import datetime as dt, json, os, sys
path = "backups/rotations.json"
rows = json.load(open(path)) if os.path.exists(path) else []
at = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
rows += [{"secret": name, "at": at} for name in sys.argv[1:]]
json.dump(rows, open(path, "w"), indent=2)
P
