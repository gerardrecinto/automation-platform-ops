"""Promotion gate: a version moves dev, qa, uat, prod in order, only with passing evidence, and every move leaves a change record."""
from __future__ import annotations

import datetime as dt
import json
import pathlib

ORDER = ["dev", "qa", "uat", "prod"]
NEEDS_APPROVER = {"uat", "prod"}
FMT = "%Y%m%dT%H%M%SZ"


def records(changes: pathlib.Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(changes.glob("CHG-*.json"))]


def gate(env: str, version: str, evidence: dict, changes: pathlib.Path, approver: str | None) -> list[str]:
    """Return the reasons a promotion is refused. Empty means allowed."""
    if env not in ORDER:
        return [f"unknown environment {env}"]
    problems: list[str] = []
    if "latest" in version or not version[:1].isdigit():
        problems.append(f"{version} is not a pinned version")
    i = ORDER.index(env)
    if i > 0:
        prev = ORDER[i - 1]
        if not any(r["env"] == prev and r["version"] == version for r in records(changes)):
            problems.append(f"{version} has no change record in {prev}")
    if evidence["baseline"]["failed"]:
        problems.append(f"baseline has {evidence['baseline']['failed']} failing rules")
    if not (evidence.get("restore_test") or {}).get("passed"):
        problems.append("no passing restore test on record")
    if env in NEEDS_APPROVER and not approver:
        problems.append(f"{env} needs --approver")
    return problems


def record(env: str, version: str, evidence: dict, changes: pathlib.Path, approver: str | None, now: dt.datetime | None = None) -> pathlib.Path:
    now = now or dt.datetime.now(dt.timezone.utc)
    changes.mkdir(exist_ok=True)
    stamp = now.strftime(FMT)
    body = {
        "id": f"CHG-{stamp}-{env}",
        "env": env,
        "version": version,
        "approved_by": approver,
        "recorded_at": stamp,
        "evidence": {
            "baseline_passed": evidence["baseline"]["passed"],
            "restore_test": evidence["restore_test"],
            "backup_sha256": evidence["backup"]["latest_sha256"],
        },
    }
    path = changes / f"{body['id']}.json"
    path.write_text(json.dumps(body, indent=2) + "\n")
    return path
