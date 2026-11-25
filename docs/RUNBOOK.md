# Runbook

## Upgrade
`scripts/upgrade.sh <tag>` backs up, switches the tag in `.env`, waits for health and rolls back to the old tag if n8n does not come up. Pin the tag, read the release notes first, and upgrade Dev, then QA, then UAT, then Prod. Rollback restores the old image; it does not undo database migrations. If the old version refuses the migrated schema, restore the backup taken at the start of the upgrade.

## Promote a version
`python -m platformcheck promote <env> --version <tag> [--approver name]` allows a move only when the version has a change record in the environment before it (dev, qa, uat, prod), the baseline passes, and a restore test has passed. UAT and prod need `--approver`. It writes `changes/CHG-<time>-<env>.json` with the evidence. Commit those files; they are the change record. `--dry-run` checks without writing. `envs/*.env` hold the version each environment runs.

## Rotate the database password
`scripts/rotate-db-password.sh` changes the password in PostgreSQL, updates `.env`, restarts the services and records the time in `backups/rotations.json`. Evidence reports each secret's age and exits 1 past 90 days. `N8N_ENCRYPTION_KEY` is not rotated by this script: changing it makes saved credentials unreadable, so rotating it means re-saving every credential.

## n8n is down
`docker compose ps` and `docker compose logs --tail 100 n8n worker`. Check PostgreSQL and Redis health first, since both are dependencies. After an upgrade, roll back with the old tag in `.env`. Alert: `N8nDown` in `monitoring/alerts.yml`.

## Restore
1. `scripts/restore-test.sh` proves the newest backup loads and row counts match. Run it after every backup job.
2. Real restore: stop `n8n` and `worker`, drop and recreate the `n8n` database, `pg_restore` the dump, start the services. Keep the same `N8N_ENCRYPTION_KEY`, or saved credentials cannot be decrypted.

## Redis is full or down
Queued executions live in Redis. The policy is `noeviction`, so a full Redis rejects new jobs with an error instead of dropping queued ones. Check `redis-cli info memory`, raise `maxmemory` or drain the queue, then watch the worker. For Sentinel failover on a real primary and replicas see redis-ops-lab.

## PostgreSQL replication and failover
This repo runs a single database. Replication, promotion and point-in-time recovery are exercised in postgres-ops-lab. For a production n8n, point `DB_POSTGRESDB_HOST` at the primary through a stable name so a promotion does not need a config change.

## Evidence for an audit
`python -m platformcheck evidence` prints: images running, baseline results by rule id, newest backup age and checksum, and the last restore test. It exits 1 if the backup is older than 26 hours, no restore test passed, or a baseline rule fails. Access reviews and secret rotation are process controls and are not evidenced by this tool.
