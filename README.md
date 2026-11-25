# automation-platform-ops

[![CI](https://github.com/gerardrecinto/automation-platform-ops/actions/workflows/ci.yml/badge.svg)](https://github.com/gerardrecinto/automation-platform-ops/actions/workflows/ci.yml)

How I would run a workflow automation platform (n8n) in a regulated shop: queue mode on Docker with PostgreSQL and Redis, backups that are restored on a schedule, upgrades that roll back, a hardening baseline with rule ids, and audit evidence as JSON.

**Site: https://gerardrecinto.github.io/automation-platform-ops/**

Lab scale, one host. Not a bank, not production. See "What is verified".

## Run it

```bash
git clone https://github.com/gerardrecinto/automation-platform-ops && cd automation-platform-ops
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && pytest -q
./scripts/demo.sh        # needs Docker; about 30 seconds after the images are pulled
```

`demo.sh` starts the stack, imports a workflow, takes a backup, restores it into a scratch database and compares row counts, runs the baseline, and prints evidence. Recorded output: [docs/DEMO_OUTPUT.txt](docs/DEMO_OUTPUT.txt). `scripts/upgrade.sh <tag>` upgrades with rollback.

## What is in it

| Piece | What it does |
|---|---|
| `compose.yaml` | n8n main and worker in queue mode, PostgreSQL 16.6, Redis 7.4.1 with AOF and `noeviction`; pinned tags, loopback-only port, no-new-privileges, healthchecks, secrets from `.env` |
| `scripts/backup.sh`, `restore-test.sh` | `pg_dump` with a manifest (time, size, sha256); restore into a scratch database and compare row counts |
| `scripts/upgrade.sh` | Backup, switch tag, wait for health, roll back on failure |
| `src/platformcheck` | Baseline rules B1 to B8 over the compose file; evidence JSON; exits 1 on stale backup, no restore proof, or a failed rule |

## Design choices

- **Redis `noeviction`.** Default eviction would drop queued jobs under memory pressure. Cost: a full Redis rejects new work, so the alert on memory must fire before that. I would flip to an eviction policy only for a pure cache, which the queue is not.
- **Logical backups (`pg_dump`).** Simple, portable, restorable into a scratch database in seconds at this size. Cost: no point-in-time recovery and slow at large sizes. Flip to base backup plus WAL archiving when the database outgrows a nightly dump; see postgres-ops-lab for that run.
- **Rollback is image only.** Cost: migrations are not reversed, so the upgrade script takes a backup first and says so.

## What is verified

- **Run here and in CI:** the stack starts healthy, a workflow is imported, a backup restores into a scratch database with matching counts, the baseline passes 26 of 26, and an upgrade from 1.78.1 to 1.80.0 completes. A rollback was exercised with a tag that does not exist; a tag that pulls but fails after a migration was not.
- **Tests:** 8 pytest tests, including cases that must fail (latest tag, public port, literal password, wrong eviction policy).
- **Not done:** no SSO or OIDC (see entra-identity-governance for the Entra checks), no replication or Sentinel here (see postgres-ops-lab and redis-ops-lab), no Retool or Base64.ai, no real bank controls, no multi-environment promotion.

MIT licensed.
